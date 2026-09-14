"""
Customer Intake Chat — LangChain + LangGraph edition.

Same behavior as ./app.py (a self-service chat agent that asks a
customer in plain language what AWS landing zone account they need, then
generates a downloadable Terraform code folder), but talks to the model
via agent_langgraph.py's LangGraph graph instead of ./agent.py's raw
OpenAI SDK loop — see agent_langgraph.py's docstring for what that
actually changes (a @tool-bound model, a checkpointer for conversation
history instead of a per-session Python object, etc.).

This file is a deliberate, fully independent copy of app.py's Flask
routes/validation/zip-building logic — not a shared-code refactor —
specifically so app.py can stay untouched as the working, tested
baseline while this one is developed/compared against it. Runs on a
different port (5003) so both can run side by side.

Read-only by design:
  - Fetches environment templates from the public aws-migration GitHub
    repo with no credentials (github_fetch.py) and never executes any of
    that fetched content — only copies .tf/.md/.example text files.
  - Never writes back to GitHub, never touches AWS, never runs terraform.
    The only output is a zip file handed to the browser.

This is a DEMO-GRADE prototype, not a hardened public service — see
README.md's "Known limitations before real customer-facing use" section
before putting a real URL in front of real customers.

Run it with:
    pip install -r requirements-langgraph.txt
    export OPENAI_API_KEY=sk-...
    python app_langgraph.py
Then open http://127.0.0.1:5003/ yourself (no auto-open — same reasoning
as ../ui/ and ../scaffolder/).
"""
import os
import re
import secrets
import shutil
import tempfile
import time
import zipfile

from flask import Flask, jsonify, render_template, request, send_file, session

from agent_langgraph import user_says
from catalog import STACK_CATALOG
from github_fetch import get_template_dir
from hcl import render_tfvars

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", secrets.token_hex(32))

# Conversation state itself now lives in agent.py's LangGraph checkpointer
# (keyed by the same session_id, passed as LangGraph's thread_id) — no
# per-session Python object to track here anymore.
DOWNLOADS = {}      # session_id -> path to generated zip
RATE_WINDOW_SECONDS = 60
RATE_MAX_MESSAGES = 15
_rate_log = {}       # ip -> [timestamps]

FOLDER_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9-]*$")
APP_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9]+$")

JUNK_TO_STRIP = (
    ".terraform", ".terraform.lock.hcl", "terraform.tfstate",
    "terraform.tfstate.backup", "terraform.tfvars.json", "tfplan", "backend.hcl",
)


def _rate_limited(ip: str) -> bool:
    now = time.time()
    log = [t for t in _rate_log.get(ip, []) if now - t < RATE_WINDOW_SECONDS]
    log.append(now)
    _rate_log[ip] = log
    return len(log) > RATE_MAX_MESSAGES


def _get_session_id() -> str:
    if "sid" not in session:
        session["sid"] = secrets.token_hex(16)
    return session["sid"]


def _coerce(field: dict, raw):
    ftype = field.get("type", "text")
    if raw is None or raw == "":
        return None
    if ftype == "list":
        if isinstance(raw, list):
            return [str(v).strip() for v in raw if str(v).strip()]
        return [v.strip() for v in str(raw).split(",") if v.strip()]
    if ftype == "checkbox":
        return str(raw).strip().lower() in ("true", "yes", "1")
    if ftype == "number":
        try:
            return int(raw)
        except (TypeError, ValueError):
            return None
    return str(raw)


def validate_and_prepare(submission: dict):
    """Returns (target_folder_name, tfvars_values, template_dirname, errors)."""
    stack_type = submission.get("stack_type")
    if stack_type not in STACK_CATALOG:
        return None, None, None, [f"Unknown stack type '{stack_type}'."]

    stack = STACK_CATALOG[stack_type]
    raw_values = submission.get("values") or {}
    errors = []
    tfvars_values = {}

    for field in stack["fields"]:
        name = field["name"]
        if name in ("app_name", "environment") and stack.get("is_workload"):
            continue  # handled separately below
        coerced = _coerce(field, raw_values.get(name))
        if coerced is None:
            if field.get("default") is not None:
                coerced = _coerce(field, field["default"])
            elif field.get("required"):
                errors.append(f"Missing required value: {field['label']} ({name}).")
                continue
            else:
                continue
        tfvars_values[name] = coerced

    if stack.get("is_workload"):
        app_name = str(raw_values.get("app_name") or "").strip()
        environment = str(raw_values.get("environment") or "prod").strip().lower()
        if not app_name or not APP_NAME_PATTERN.match(app_name):
            errors.append("App name is required and must be letters/numbers only.")
        if environment not in ("prod", "nonprod"):
            errors.append("Environment must be 'prod' or 'nonprod'.")
        target_folder_name = f"{app_name}-{environment}" if app_name else None
    else:
        target_folder_name = str(submission.get("folder_name") or "").strip()
        if not target_folder_name or not FOLDER_NAME_PATTERN.match(target_folder_name):
            errors.append("A valid folder name (lowercase letters/numbers/hyphens) is required.")

    return target_folder_name, tfvars_values, stack["template_dirname"], errors


def build_zip(target_folder_name: str, tfvars_values: dict, template_dirname: str) -> str:
    source_dir = get_template_dir(template_dirname)
    work_dir = tempfile.mkdtemp(prefix="intake_")
    dest_dir = os.path.join(work_dir, target_folder_name)
    shutil.copytree(source_dir, dest_dir)

    for junk in JUNK_TO_STRIP:
        path = os.path.join(dest_dir, junk)
        if os.path.isdir(path):
            shutil.rmtree(path)
        elif os.path.exists(path):
            os.remove(path)

    with open(os.path.join(dest_dir, "terraform.tfvars"), "w") as f:
        f.write(render_tfvars(tfvars_values))

    zip_path = os.path.join(work_dir, f"{target_folder_name}.zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _dirs, files in os.walk(dest_dir):
            for fname in files:
                full = os.path.join(root, fname)
                arcname = os.path.join(target_folder_name, os.path.relpath(full, dest_dir))
                zf.write(full, arcname)
    return zip_path


@app.route("/")
def index():
    return render_template("chat.html")


@app.route("/api/chat", methods=["POST"])
def chat():
    ip = request.remote_addr or "unknown"
    if _rate_limited(ip):
        return jsonify({"reply": "You're sending messages faster than this demo allows — "
                                  "please wait a minute and try again.", "ready": False}), 429

    if not os.environ.get("OPENAI_API_KEY"):
        return jsonify({"reply": "This demo isn't configured with an OpenAI API key yet — "
                                  "set OPENAI_API_KEY and restart the server.", "ready": False}), 500

    message = (request.json or {}).get("message", "").strip()
    if not message:
        return jsonify({"reply": "Say something and I'll help you build a landing zone folder.",
                         "ready": False})

    sid = _get_session_id()
    result = user_says(sid, message)

    if result["submission"]:
        folder_name, tfvars_values, template_dirname, errors = validate_and_prepare(result["submission"])
        if errors:
            return jsonify({"reply": "Almost there — a couple of things need fixing: " + " ".join(errors),
                             "ready": False})
        try:
            zip_path = build_zip(folder_name, tfvars_values, template_dirname)
        except Exception as e:  # noqa: BLE001 — surface a clean message, not a stack trace, to the browser
            return jsonify({"reply": f"Something went wrong generating your code: {e}", "ready": False}), 500
        DOWNLOADS[sid] = zip_path
        return jsonify({
            "reply": result["reply"] or f"Your {folder_name} Terraform code is ready.",
            "ready": True,
            "folder_name": folder_name,
        })

    return jsonify({"reply": result["reply"], "ready": False})


@app.route("/api/download")
def download():
    sid = _get_session_id()
    zip_path = DOWNLOADS.get(sid)
    if not zip_path or not os.path.exists(zip_path):
        return jsonify({"error": "Nothing ready to download yet — finish the chat first."}), 404
    return send_file(zip_path, as_attachment=True, download_name=os.path.basename(zip_path))


if __name__ == "__main__":
    url = "http://127.0.0.1:5003/"
    print(f"\nCustomer Intake Chat (LangChain + LangGraph edition) running at {url}")
    print("Open that address yourself — it does not open a browser tab automatically.")
    if not os.environ.get("OPENAI_API_KEY"):
        print("WARNING: OPENAI_API_KEY is not set — chat will return a clear error until it is.")
    print()
    # threaded=True so one user's multi-second OpenAI call doesn't block
    # every other user's requests within this single process. This does
    # NOT make it safe to run multiple processes/instances behind a load
    # balancer — agent_langgraph.py's InMemorySaver checkpointer and this
    # file's DOWNLOADS/_rate_log dicts are all in-memory per-process, so a
    # request landing on a different process loses that user's
    # conversation and generated zip. See README's "Known limitations."
    app.run(host="127.0.0.1", port=5003, debug=False, threaded=True)
