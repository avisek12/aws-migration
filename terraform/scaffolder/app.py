"""
Environment Scaffolder — a separate local tool from ../ui/. Its job ends
at generating files: pick a stack type, fill in the same variables the
Landing Zone UI would ask for, and it copies the matching, already-tested
environment folder (main.tf/variables.tf/outputs.tf/providers.tf/
backend.tf — the real, tracked files, so the generated code can never
drift from what's actually tested) into a brand-new
terraform/environments/<name>/ folder, with a real terraform.tfvars
written next to them from what you filled in.

It never runs terraform and never talks to AWS — the output is ordinary,
self-contained Terraform code you review, commit, and run with
`terraform init` / `plan` / `apply` from the CLI (or point ../ui/ at it
afterward, for the stack types ../ui/ already knows about).

Run it with:
    python app.py
Then open http://127.0.0.1:5001/ yourself — it does not open a browser
tab automatically (same reasoning as ../ui/app.py: an auto-opened form
is how a stray click turns into an unintended action).
"""
import os
import re
import shutil

from flask import Flask, redirect, render_template, request, url_for

from hcl import render_tfvars
from icons import ALERT_CIRCLE, CHECK_CIRCLE, CLOUD_STACK
from stack_types import STACK_TYPES

app = Flask(__name__)
app.secret_key = "environment-scaffolder-local-only"

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
TERRAFORM_ROOT = os.path.abspath(os.path.join(THIS_DIR, ".."))
ENVIRONMENTS_ROOT = os.path.join(TERRAFORM_ROOT, "environments")

FOLDER_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9-]*$")
APP_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9]+$")

# Never carry a template's own generated/local-state artifacts into a new
# folder — a freshly scaffolded environment should look untouched.
JUNK_TO_STRIP = (
    ".terraform", ".terraform.lock.hcl", "terraform.tfstate",
    "terraform.tfstate.backup", "terraform.tfvars.json", "tfplan", "backend.hcl",
)


def build_values_from_form(fields, form):
    """Same shape as ../ui/app.py's helper of the same name — kept as a
    separate small copy rather than imported, since this tool has no
    other reason to depend on ui/app.py (which builds a Flask app on
    import)."""
    values = {}
    errors = []
    for field in fields:
        name = field["name"]
        ftype = field.get("type", "text")

        if ftype == "checkbox":
            values[name] = name in form
            continue

        raw = (form.get(name) or "").strip()
        if not raw:
            if field.get("required"):
                errors.append(f"{field['label']} is required.")
            continue

        if ftype == "list":
            values[name] = [item.strip() for item in raw.split(",") if item.strip()]
        elif ftype == "number":
            try:
                values[name] = int(raw)
            except ValueError:
                errors.append(f"{field['label']} must be a whole number.")
        else:
            values[name] = raw

    return values, errors


def strip_junk(directory: str):
    for name in JUNK_TO_STRIP:
        path = os.path.join(directory, name)
        if os.path.isdir(path):
            shutil.rmtree(path)
        elif os.path.exists(path):
            os.remove(path)


@app.route("/")
def index():
    return render_template("index.html", stack_types=STACK_TYPES, cloud_icon=CLOUD_STACK)


@app.route("/new/<stack_key>", methods=["GET", "POST"])
def new_environment(stack_key):
    if stack_key not in STACK_TYPES:
        return redirect(url_for("index"))

    stack = STACK_TYPES[stack_key]
    is_workload = stack.get("is_workload", False)
    result = None

    if request.method == "POST":
        folder_name = ""

        if is_workload:
            app_name = (request.form.get("app_name") or "").strip()
            environment = (request.form.get("environment") or "prod").strip()
            if not app_name or not APP_NAME_PATTERN.match(app_name):
                result = {
                    "ok": False,
                    "message": "App name is required and must contain only "
                               "letters/numbers (e.g. ordermgmt).",
                }
            else:
                folder_name = f"{app_name}-{environment}"
        else:
            folder_name = (request.form.get("folder_name") or "").strip()
            if not folder_name or not FOLDER_NAME_PATTERN.match(folder_name):
                result = {
                    "ok": False,
                    "message": "Folder name is required — lowercase letters, "
                               "numbers, and hyphens only, starting with a letter "
                               "(e.g. network-hub-dr, audit-clientb).",
                }

        if result is None:
            dest_dir = os.path.join(ENVIRONMENTS_ROOT, folder_name)
            if os.path.exists(dest_dir):
                result = {
                    "ok": False,
                    "message": f"terraform/environments/{folder_name}/ already "
                               "exists — pick a different name, or edit it "
                               "directly if you meant to update it. This tool "
                               "never overwrites an existing folder.",
                }
            else:
                values, errors = build_values_from_form(stack["fields"], request.form)
                if is_workload:
                    values["app_name"] = app_name
                    values["environment"] = environment

                if errors:
                    result = {"ok": False, "message": " ".join(errors)}
                else:
                    source_dir = os.path.join(ENVIRONMENTS_ROOT, stack["template_dirname"])
                    shutil.copytree(source_dir, dest_dir)
                    strip_junk(dest_dir)

                    with open(os.path.join(dest_dir, "terraform.tfvars"), "w") as f:
                        f.write(render_tfvars(values))

                    result = {
                        "ok": True,
                        "folder": f"terraform/environments/{folder_name}",
                        "files": sorted(os.listdir(dest_dir)),
                    }

    return render_template(
        "new.html", stack=stack, stack_key=stack_key, result=result,
        check_icon=CHECK_CIRCLE, alert_icon=ALERT_CIRCLE,
    )


if __name__ == "__main__":
    url = "http://127.0.0.1:5001/"
    print(f"\nEnvironment Scaffolder running at {url}")
    print("Open that address yourself — it does not open a browser tab")
    print("automatically. It only writes files; it never runs terraform")
    print("or talks to AWS.\n")
    app.run(host="127.0.0.1", port=5001, debug=False)
