# LangGraph Version — Full Code Walkthrough

This is a line-by-line-level guide to how `agent_langgraph.py` and
`app_langgraph.py` actually work together, for anyone who knows what the
app *does* (see [`README.md`](README.md)) but wants to understand *how*
every piece of the LangGraph implementation fits together.

It does not touch or need changes to `agent.py`/`app.py` (the raw OpenAI
SDK baseline) — those are a separate, intentionally untouched
implementation of the same idea. Where a comparison helps build intuition,
this doc calls it out explicitly.

---

## 1. The 30-second mental model

A browser sends a chat message to Flask. Flask hands the message and a
session id to a **compiled LangGraph graph**. The graph has exactly two
nodes:

```
        ┌────────┐   no tool call    
   ───► │ agent  │ ─────────────────► END (reply back to browser)
        └───┬────┘
            │ tool call present
            ▼
   ┌────────────────────┐
   │ extract_submission  │ ───► END (submission back to Flask)
   └────────────────────┘
```

The `agent` node is "call the LLM." The LLM either replies with plain text
(still gathering info) or calls a single tool,
`submit_landing_zone_request`, once it believes it has everything. Flask
never lets the LLM's tool call *do* anything by itself — it just reads the
structured arguments back out and re-validates them itself before
generating any files. That's the whole security model in one sentence.

Everything else in both files is plumbing around that one graph:
persisting conversation history, turning the model's structured output
into an actual Terraform folder, rate limiting, and session cookies.

---

## 2. Request lifecycle, start to finish

Walk through one real conversation turn end to end:

1. **Browser** — [`templates/chat.html`](templates/chat.html) posts
   `{"message": "..."}` to `POST /api/chat` via `fetch()` (see the
   `form.addEventListener('submit', ...)` block at the bottom of that
   file). No page reload; the JS just appends the reply bubble and shows
   the download bar if `data.ready` comes back `true`.

2. **Flask route** — `app_langgraph.py`'s `chat()`:
   - Checks the per-IP rate limit (`_rate_limited`).
   - Checks `OPENAI_API_KEY` is set at all (fails fast with a clear
     message rather than letting the graph fail deeper inside).
   - Reads `message` from the JSON body.
   - Calls `_get_session_id()` — reads/creates `session["sid"]`, a random
     32-hex-char token stored in Flask's signed cookie. This is the only
     piece of "who is this" the whole app has; there's no login.
   - Calls `agent_langgraph.user_says(sid, message)` — this is the entire
     handoff into LangGraph. Everything about *how* the model is called
     lives on the other side of that one function call.

3. **`user_says(session_id, text)`** (`agent_langgraph.py`):
   ```python
   config = {"configurable": {"thread_id": session_id}}
   result = _GRAPH.invoke(
       {"messages": [HumanMessage(content=text)], "submission": None},
       config=config,
   )
   ```
   - `thread_id` is LangGraph's name for "which conversation is this."
     Using the Flask session id *as* the thread id is the entire
     mechanism that makes conversation history "remember" a customer
     across HTTP requests — no separate mapping table needed.
   - The input dict only needs to contain the *new* human message.
     LangGraph's checkpointer (see §4) merges it onto whatever message
     history already exists for that `thread_id` — you never manually
     load old messages back in.
   - `.invoke()` runs the graph **synchronously to completion** — it walks
     `agent` → (conditionally) `extract_submission` → `END` and returns
     the final state as a plain dict.

4. **Inside the graph** — see §3 for the node-by-node breakdown. Net
   result: `result["messages"][-1]` is either the model's plain-text
   reply (AIMessage) or a ToolMessage acknowledging the tool call, and
   `result["submission"]` is `None` unless the model just called the tool.

5. **Back in `user_says`**, this is flattened into the small,
   LangGraph-agnostic dict that `app_langgraph.py` actually deals with:
   ```python
   {"reply": last.content or "", "submission": result.get("submission")}
   ```
   This is a deliberate boundary: `app_langgraph.py` never imports
   anything from `langchain_core`/`langgraph` directly, and never sees a
   `Message` object. If the LangGraph internals ever change, only this
   one function's return shape is a contract to keep.

6. **Back in `chat()`** — if `result["submission"]` is falsy, it's still a
   normal back-and-forth turn: reply straight back as
   `{"reply": ..., "ready": false}`.

   If it's truthy, the model just decided it has everything — now Flask
   does the part it never delegates to the model:
   - `validate_and_prepare(submission)` — re-checks every field against
     [`catalog.py`](catalog.py)'s definitions (required fields present,
     coerces types, defaults applied, folder/app-name regex checks). This
     runs **regardless of what the model claims** — the model's job was
     only ever to *propose* `{stack_type, values, folder_name}`.
   - `build_zip(...)` — fetches the matching template dir from GitHub
     (`github_fetch.get_template_dir`), copies it to a temp dir, strips
     Terraform junk files (state, lock file, etc.), writes a real
     `terraform.tfvars` (`hcl.render_tfvars`), zips it.
   - The zip path is stashed in the in-memory `DOWNLOADS[sid]` dict.
   - Response includes `"ready": true` — this is what makes the browser
     reveal the download button.

7. **Download** — a separate `GET /api/download` request (triggered by
   clicking the link, not by the chat JS) looks up `DOWNLOADS[sid]` and
   streams the zip via `send_file`.

That's the entire round trip. Steps 2, 6, and 7 are **identical in
concept** to `app.py`'s raw-SDK version — the only thing that changed is
step 3/4, how the model itself is invoked and how history is kept.

---

## 3. The graph itself, node by node

### State schema

```python
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    submission: Optional[dict]
```

- `messages` uses LangGraph's `add_messages` **reducer**. Without a
  reducer, returning `{"messages": [new_msg]}` from a node would *replace*
  the whole messages list with a one-item list. `add_messages` instead
  means "append `new_msg` to whatever `messages` already is" (and it also
  knows how to overwrite a message in place if you return one with a
  matching `id`, which this graph never needs). Every node in this graph
  therefore only ever returns the *new* message(s) it produced, never the
  full history.
- `submission` has **no reducer**, so LangGraph uses the default
  behavior: the value returned by a node simply replaces the old one.
  This is why `user_says` passes `"submission": None` on every fresh
  `.invoke()` call — it resets the flag for *this turn's* return value,
  it does **not** erase submission history, because submission was never
  meant to be persisted across turns in the first place. It's an
  ephemeral per-turn signal, not conversation state — which is also why
  `app_langgraph.py` reads it once and never looks at it again for that
  session (it acts on it immediately, generating the zip that same
  request).

### Node: `agent` (`_call_model`)

```python
def _call_model(state: AgentState) -> dict:
    messages = state["messages"]
    if not messages or not isinstance(messages[0], SystemMessage):
        messages = [SystemMessage(content=SYSTEM_PROMPT), *messages]
    response = _MODEL_WITH_TOOLS.invoke(messages)
    return {"messages": [response]}
```

- The checkpointer (§4) persists `messages` between turns, but it never
  stores the system prompt — this function re-prepends `SYSTEM_PROMPT`
  fresh on *every* invocation, only if the stored history doesn't already
  start with one (it never will, since it's never saved — this check is
  just a defensive no-op / documents the intent rather than doing
  anything load-bearing today).
- Why not just save the system message into the checkpointed history
  once? Because then changing `SYSTEM_PROMPT` (e.g. editing the catalog
  or the instructions) would have zero effect on any conversation that
  had already started — old threads would keep using whatever prompt text
  existed when they began. Re-prepending fresh means every turn — even
  turn 10 of a long conversation — always uses the current prompt in the
  running process.
- `_MODEL_WITH_TOOLS.invoke(messages)` is one call to the LLM (via
  LangChain's `ChatOpenAI`, or the fake — see §5). Returns a single
  `AIMessage`, which may or may not carry `.tool_calls`.
- The node returns only `{"messages": [response]}` — the `add_messages`
  reducer appends it to state for us.

### Conditional edge: `_route_after_model`

```python
def _route_after_model(state: AgentState) -> str:
    last = state["messages"][-1]
    return "extract_submission" if getattr(last, "tool_calls", None) else END
```

This is the entire decision point in the whole app: did the model just
call `submit_landing_zone_request`, or is it still asking questions?
`getattr(..., "tool_calls", None)` guards against message types that
don't even have that attribute (shouldn't happen here, but it's the
idiomatic LangChain way to check "does this message carry tool calls").

### Node: `extract_submission`

```python
def _extract_submission(state: AgentState) -> dict:
    last = state["messages"][-1]
    call = last.tool_calls[0]
    tool_response = ToolMessage(content="Received — generating your code now.", tool_call_id=call["id"])
    return {"submission": call["args"], "messages": [tool_response]}
```

- `call["args"]` is the tool call's arguments **as the model formatted
  them** — i.e. exactly the untrusted `{stack_type, values, folder_name}`
  dict that `validate_and_prepare` in `app_langgraph.py` treats as hostile
  input, never as ground truth.
- The `ToolMessage` is not decorative. OpenAI's function-calling API
  requires every `tool_calls`-bearing assistant message to be immediately
  followed by a matching `tool` role message with the same
  `tool_call_id`, or a *later* call on that same message thread will be
  rejected by the API as malformed. This graph ends right after this
  node, so nothing sends this particular ToolMessage back to OpenAI in
  *this* turn — but it's now saved in the checkpointed history, so if the
  same customer keeps chatting afterward (e.g. "actually change the
  region"), the next `.invoke()` on this thread includes a
  properly-paired tool_call → tool_response and OpenAI accepts it. Omitting
  this would work fine for a single-submission conversation and then
  break confusingly the moment someone kept talking after submitting.
- Only `submit_landing_zone_request`'s *first* tool call is read
  (`tool_calls[0]`) — the system prompt only ever describes one tool, so
  in practice there's only ever one, but this is worth knowing if you ever
  add a second tool later.

### Graph construction

```python
def _build_graph():
    graph = StateGraph(AgentState)
    graph.add_node("agent", _call_model)
    graph.add_node("extract_submission", _extract_submission)
    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", _route_after_model, {"extract_submission": "extract_submission", END: END})
    graph.add_edge("extract_submission", END)
    return graph.compile(checkpointer=InMemorySaver())
```

Read this as: start at `agent`; after `agent` runs, call
`_route_after_model` to pick the next node by name from that dict; after
`extract_submission` runs, unconditionally go to `END`. `.compile(...)`
turns this declarative graph into the actual runnable `_GRAPH` object that
`user_says` calls `.invoke()` on. `_MODEL_WITH_TOOLS` and `_GRAPH` are
both built once at **import time** (bottom of `agent_langgraph.py`,
module-level), not per-request — that's why `app_langgraph.py` can just
`from agent_langgraph import user_says` and call it directly without any
setup step of its own.

---

## 4. Conversation memory: the checkpointer

`InMemorySaver()` is LangGraph's simplest checkpointer implementation —
a Python dict in the graph's process, keyed internally by `thread_id`.
Every `.invoke(..., config={"configurable": {"thread_id": sid}})` call:

1. Loads whatever `AgentState` was last saved for that `thread_id` (or
   starts empty if it's a new one).
2. Merges the input you passed in on top of it (via each field's
   reducer — `add_messages` appends, `submission` replaces).
3. Runs the graph.
4. Saves the resulting state back under that same `thread_id`.

This is a **direct replacement** for what `app.py` does by hand: that
version keeps a `SESSIONS: dict[str, IntakeAgent]` where `IntakeAgent` is
a small class holding its own Python list of message dicts. Conceptually
identical ("a dict from session id to that session's message history"),
but here it's LangGraph's built-in mechanism instead of custom code —
which is also why `app_langgraph.py` has no `SESSIONS` dict of its own at
all; conversation state lives entirely on the LangGraph side.

**Limitation inherited either way**: `InMemorySaver`, like `app.py`'s
`SESSIONS` dict, lives in this one Python process's RAM. Restart the
process, or run more than one process/instance behind a load balancer,
and a customer's mid-conversation history is gone or split across
instances. See `README.md`'s "Known limitations" section — this is the
same limitation, just implemented via a different mechanism.

---

## 5. The model: real vs. fake, and the `.bind_tools()` bug

```python
def build_model_with_tools():
    if os.environ.get("OPENAI_API_KEY"):
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model=MODEL, temperature=0).bind_tools([submit_landing_zone_request])

    from langchain_core.language_models.fake_chat_models import FakeListChatModel
    fake = FakeListChatModel(responses=[...])
    return fake.bind(tools=[submit_landing_zone_request])
```

- **With a real key**: `ChatOpenAI(...).bind_tools([...])` is LangChain's
  standard pattern for tool-calling models. `.bind_tools()` converts the
  Python function's type hints and docstring into a proper OpenAI
  function-calling JSON schema — including turning the module-level
  `StackType = Literal[tuple(STACK_CATALOG.keys())]` type hint into a JSON
  Schema `enum` constraint, so the model is structurally prevented from
  inventing a `stack_type` value that isn't one of the five real catalog
  keys (verified directly during development, not assumed).
- **Without a key**: falls back to `FakeListChatModel`, a LangChain
  testing utility that always returns the same canned string, so the
  Flask routes/graph plumbing can still be smoke-tested with no API calls
  at all (e.g. confirming `/`, `/api/chat` don't 500 before a key is even
  configured).
- **The bug that was found and fixed here**: `FakeListChatModel` does
  **not** implement `.bind_tools()` at all — it's a provider-specific
  method that each real chat model subclass implements differently, and
  the base fake class raises `NotImplementedError` if you call it. This
  was discovered by actually importing the module with no
  `OPENAI_API_KEY` set (not assumed from reading docs), which crashed at
  import time. The fix was to call the **generic** LangChain Runnable
  method `.bind(tools=[...])` instead for the fake path only — this just
  attaches the `tools` kwarg without doing any real schema conversion,
  which is fine here since `FakeListChatModel` ignores it either way (it
  always returns the same fixed string, never a real tool call) — so the
  "submission ready" path can only ever be reached with a real key,
  exactly as intended.

---

## 6. `catalog.py` — the shared source of truth

Both the raw-SDK and LangGraph versions, and both files within each
version, import from the same `STACK_CATALOG` dict:

- `_catalog_summary()` in `agent_langgraph.py` turns it into the numbered
  list of stack types + fields embedded directly in `SYSTEM_PROMPT` — this
  is literally how the model learns what fields exist and what's
  required; there's no separate "tool schema" describing the *content* of
  `values`, only the free-text description in the prompt (the tool schema
  itself just says `values: dict`, deliberately loose, because the field
  set differs per `stack_type`).
- `validate_and_prepare()` in `app_langgraph.py` walks the same
  `STACK_CATALOG[stack_type]["fields"]` list to coerce and require values
  — this is the server-side re-validation step, and it's checking the
  submission against the exact same field definitions the model was told
  about, just independently and without trusting the model got it right.
- If you ever add/change a field, `catalog.py` is the one place to edit —
  both the prompt text and the validation logic pick it up automatically
  (see `README.md`'s "Keeping the field catalog in sync" section for why
  this file is a standalone copy of `../ui/config.py` rather than a live
  import).

---

## 7. Everything else app_langgraph.py owns that has nothing to do with LangGraph

These are unchanged in spirit from `app.py` and not LangGraph-specific —
listed here only so the "total process" picture is complete:

- **Rate limiting** (`_rate_limited`, `_rate_log`): an in-memory
  per-IP sliding window, 15 messages/60 seconds. Resets on restart, not
  shared across processes — same caveat as the checkpointer.
- **Sessions** (`_get_session_id`): Flask's signed cookie holds a random
  `sid`; there is no server-side session store beyond what LangGraph and
  `DOWNLOADS` key by that same `sid`.
- **`_coerce`**: turns raw submitted values into real Python types per
  field `type` (`list` → split on commas, `checkbox` → bool, `number` →
  int, else left as string).
- **`build_zip`**: the only place that touches the filesystem/network
  (via `github_fetch.get_template_dir`) — fetches a cached copy of the
  public `avisek12/aws-migration` repo, copies the matching
  `terraform/environments/<template_dirname>` folder, strips
  Terraform state/lock junk, writes `terraform.tfvars`
  (`hcl.render_tfvars`), zips it.
- **`DOWNLOADS`**: a plain dict, `session_id -> zip path`, checked by
  `/api/download`. Nothing ever cleans these up — see README limitations.

---

## 8. Side-by-side with the raw SDK version

| Concern | `agent.py` / `app.py` (raw SDK) | `agent_langgraph.py` / `app_langgraph.py` |
|---|---|---|
| Model call | `OpenAI().chat.completions.create(...)` directly | `ChatOpenAI(...).bind_tools([...])` via LangChain |
| Tool schema | Hand-written OpenAI function-calling JSON dict | Auto-derived from `submit_landing_zone_request`'s type hints/docstring via `.bind_tools()` |
| Conversation history | `SESSIONS: dict[str, IntakeAgent]`, a hand-rolled Python list per session | LangGraph `InMemorySaver` checkpointer, keyed by `thread_id = session_id` |
| Control flow | A Python `while`/`if` loop reacting to the API response shape | A `StateGraph` with one conditional edge |
| Everything in §7 (rate limit, sessions, zip building, validation) | Identical logic, separate file | Identical logic, separate file |

Both are equally strict about **never trusting the model's output for
anything that touches disk** — that property comes from the app-level
`validate_and_prepare` step, which exists independently of which SDK
called the model, and is why switching frameworks here was safe to do
without changing the actual security posture of the tool at all.
