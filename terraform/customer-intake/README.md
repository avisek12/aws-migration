# Customer Intake Chat

A self-service chat agent for people who don't know Terraform or AWS field
names: they describe what they need in plain language, the agent asks for
whatever's still missing, and once it has everything it generates a
downloadable Terraform code folder — copied from the same tested templates
[`../ui/`](../ui/) and [`../scaffolder/`](../scaffolder/) use — for the
customer to review and run themselves.

**Two independent, functionally identical implementations live here on
purpose**, so one can be developed/compared against a known-working
baseline without risking it:

| | Files | Model client | Port | Install |
|---|---|---|---|---|
| **Raw OpenAI SDK** (the working baseline) | [`agent.py`](agent.py), [`app.py`](app.py) | `openai`'s `OpenAI().chat.completions.create(...)` directly | `5002` | `requirements.txt` |
| **LangChain + LangGraph** (the standard going forward — same stack as the sibling [`gen-ai-agentic-ai`](../../../gen-ai-agentic-ai/) repo) | [`agent_langgraph.py`](agent_langgraph.py), [`app_langgraph.py`](app_langgraph.py) | `ChatOpenAI` + a LangGraph graph | `5003` | `requirements-langgraph.txt` |

They share `catalog.py`, `github_fetch.py`, `hcl.py`, and the
`templates`/`static` folders — only the model-calling code and its Flask
wiring differ between the two.

**This is a demo-grade prototype**, not a hardened public service. Read
"Known limitations" below before putting a real URL in front of real
customers.

## What it does and doesn't do

- ✅ Asks plain-language questions, using the same field catalog as the other tools ([`catalog.py`](catalog.py), a standalone copy of [`../ui/config.py`](../ui/config.py)'s fields).
- ✅ Fetches the matching environment template **read-only**, with zero credentials, from the public `avisek12/aws-migration` GitHub repo ([`github_fetch.py`](github_fetch.py)).
- ✅ Writes a real `terraform.tfvars` and hands back a `.zip` for the browser to download.
- ❌ Never runs `terraform` itself.
- ❌ Never touches AWS.
- ❌ Never writes back to GitHub — no push, no PR, no token needed for that at all.
- ❌ Never executes anything fetched from GitHub — only copies `.tf`/`.md`/`.example` text files into the zip.

## Run it

**Raw SDK version:**
```
cd aws-migration/terraform/customer-intake
pip install -r requirements.txt
export OPENAI_API_KEY=sk-...          # required
python app.py
```
Open `http://127.0.0.1:5002/`.

**LangChain + LangGraph version** (can run at the same time — different port):
```
cd aws-migration/terraform/customer-intake
pip install -r requirements-langgraph.txt
export OPENAI_API_KEY=sk-...          # required
python app_langgraph.py
```
Open `http://127.0.0.1:5003/`.

Neither auto-opens a browser tab — same reasoning as [`../ui/`](../ui/)
and [`../scaffolder/`](../scaffolder/README.md).

Optional for both: `OPENAI_MODEL` (default `gpt-4o-mini`) and
`FLASK_SECRET_KEY` (a random one is generated per process if unset — set
this explicitly if you run more than one worker process, since sessions
are in-memory per process; see limitations below).

### Troubleshooting: `openai.APIConnectionError` / `TypeError: process() takes no keyword arguments`

Hit this once on this exact machine, with a real, valid API key — it
looked like a network/connectivity problem (that's literally the
exception name) but wasn't. Root cause: `openai`'s newer versions use a
transport library called `httpx2`, which supports decoding Brotli-
compressed API responses via the third-party `Brotli` package. `httpx2`
calls `Decompressor.process(data, output_buffer_limit=...)` — a keyword
argument that only exists in `Brotli` **1.1.0+**. An older installed
`Brotli` (1.0.9 here) has a `process()` that only accepts a positional
argument, so the very first real API response that happened to come
back Brotli-compressed raised a plain `TypeError` deep inside response
decoding — which `openai`'s client then reports upward as
`APIConnectionError`, with nothing in the message pointing at Brotli at
all. A fake/invalid API key never triggers this, since OpenAI's error
responses apparently aren't Brotli-compressed — only genuine successful
responses were affected, which made it look even more like a pure
connectivity issue.

Fix:
```
pip install --upgrade Brotli
```
Confirm it's new enough:
```
python -c "import brotli; d = brotli.Decompressor(); d.process(b'', output_buffer_limit=1024); print('ok')"
```
If that raises `TypeError: process() takes no keyword arguments`, the
installed `Brotli` is still too old.

## How the LangGraph version is built

[`agent_langgraph.py`](agent_langgraph.py) is a small LangGraph graph, not
a hand-rolled OpenAI SDK loop:
- A `@tool`-decorated `submit_landing_zone_request` function, bound to
  the model via LangChain's `.bind_tools()` — the model's **only** way to
  finish is calling it with a structured `{stack_type, values}` payload,
  never by us parsing its free text.
- One graph node (`agent`) calls the model; a conditional edge routes to
  `extract_submission` when the response includes a tool call, or ends
  the turn otherwise.
- Conversation history is kept by a LangGraph checkpointer
  (`InMemorySaver`), keyed by `session_id` as the graph's `thread_id` —
  the standard LangGraph persistence pattern (see
  `gen-ai-agentic-ai/docs/03-langgraph-basics.md`), not a hand-rolled
  per-session Python object. This is also why `app_langgraph.py` has no
  `SESSIONS` dict, unlike `app.py` — conversation state lives entirely
  inside the graph instead.

Either version, every value the model proposes is still re-validated
server-side in that file's own `validate_and_prepare` (required fields
present, folder names restricted to `[a-z0-9-]`, app names to
`[a-zA-Z0-9]`) before anything touches disk — this is the main defense
against a customer trying to prompt-inject their way into something
unintended, and it's identical in both versions: the model has no tool
that does anything but propose values for us to check, whether it's
called via the raw SDK or via LangChain.

## Known limitations before real customer-facing use

- **Single process only, in both versions.** `app.run(..., threaded=True)`
  means concurrent users within *one* process are handled properly — one
  person's multi-second OpenAI call no longer blocks everyone else. It
  does **not** mean either version is safe to run as multiple processes
  or instances behind a load balancer: conversation history
  (`IntakeAgent`'s in-memory message list in `app.py`'s `SESSIONS` dict,
  or `agent_langgraph.py`'s `InMemorySaver` checkpointer) and each
  version's own `DOWNLOADS`/`_rate_log` dicts all live in that one
  process's memory. A request that lands on a different process/instance
  has no memory of that user's conversation or generated zip — their
  session just breaks. Scaling past one process needs a shared store —
  see `../../gen-ai-agentic-ai/production-rag-service/` for exactly this
  fix done for real (Redis-backed distributed rate limiting, a real
  database for durable conversation history); S3 with presigned URLs
  would be the equivalent fix for downloads here.
- **Basic rate limiting only** — an in-memory per-IP sliding window
  (15 messages/minute). It resets on restart and doesn't account for
  IPs behind a shared NAT/proxy. A public deployment should add real
  throttling in front of this (API Gateway, WAF, or similar) — a public
  chat endpoint calling a paid LLM API without one can run up a real bill.
- **No authentication** — anyone with the URL can use it. Decide whether
  that's actually what you want before hosting it publicly.
- **Generated zips accumulate on disk** — nothing currently cleans up
  `tempfile.mkdtemp()` output after a download. Add a cleanup job (or a
  short-lived object store with expiry, e.g. S3 with a lifecycle rule) for
  anything longer-running than a demo.
- **Dev server** — `app.run()` is Flask's built-in server, fine for this
  demo, not for production traffic. Use a real WSGI server (gunicorn,
  uWSGI) behind whatever you deploy this on.
- **No hosting included** — this repo gives you the application code only.
  Actually reaching customers needs you to deploy it somewhere (Lambda +
  Function URL, App Runner, ECS, a plain EC2 instance, etc.) and supply
  `OPENAI_API_KEY` there as a real secret (Secrets Manager/SSM Parameter
  Store), not a plaintext environment variable in source control.

## Keeping the field catalog in sync

[`catalog.py`](catalog.py) is a deliberate standalone copy of
[`../ui/config.py`](../ui/config.py)'s field definitions, not a live
import — this service only ever fetches plain data files from GitHub at
runtime, never executable code, so its own field knowledge has to ship
with it. If you add/change fields in `ui/config.py`, update `catalog.py`
to match by hand.
