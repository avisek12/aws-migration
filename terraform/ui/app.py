"""
Landing Zone UI — a local Flask app so an employee who doesn't know
Terraform can fill in a form, review a `terraform plan`, and click
Apply, without touching the command line.

Run it with:
    python app.py

Then open http://127.0.0.1:5000/ yourself — it does not open a browser
tab for you (deliberately: this app runs real terraform commands, and
auto-opening a live form is how a stray click can trigger a real
apply). It only ever talks to the Terraform CLI already installed on
this machine and to AWS via whichever profile is picked on each page —
no credentials are typed into or stored by this tool. See README.md in
this folder for prerequisites and safety notes.
"""
import re
import shutil

from flask import Flask, redirect, render_template, request, url_for

from config import ENVIRONMENTS, WORKLOAD_ENV
from icons import ALERT_CIRCLE, CHECK_CIRCLE, CLOUD_STACK
from terraform_runner import (
    list_aws_profiles,
    list_existing_workload_dirs,
    load_existing_tfvars,
    plan_is_fresh,
    run_terraform_apply,
    run_terraform_plan,
    target_directory,
    write_tfvars,
)

app = Flask(__name__)
app.secret_key = "landing-zone-ui-local-only"


@app.context_processor
def inject_icons():
    # Available in every template without passing them from each route.
    return {"cloud_icon": CLOUD_STACK, "check_icon": CHECK_CIRCLE, "alert_icon": ALERT_CIRCLE}

APP_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9]+$")


def build_values_from_form(fields, form):
    """Turn submitted form data into a tfvars-ready dict, validating
    required fields. Returns (values, errors)."""
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


def form_display_values(fields, saved):
    """Flatten saved tfvars values back into the strings/bools the
    HTML form controls expect."""
    display = {}
    for field in fields:
        name = field["name"]
        value = saved.get(name, field.get("default", ""))
        if field.get("type") == "list" and isinstance(value, list):
            value = ", ".join(value)
        display[name] = value
    return display


@app.route("/")
def index():
    return render_template(
        "index.html",
        environments=ENVIRONMENTS,
        workload=WORKLOAD_ENV,
        existing_workloads=list_existing_workload_dirs(),
    )


@app.route("/env/<env_key>", methods=["GET", "POST"])
def environment_page(env_key):
    if env_key not in ENVIRONMENTS:
        return redirect(url_for("index"))

    env = ENVIRONMENTS[env_key]
    directory = target_directory(env["dirname"])
    profiles = list_aws_profiles()

    saved = load_existing_tfvars(directory)
    values = form_display_values(env["fields"], saved)
    selected_profile = request.values.get("aws_profile", profiles[0] if profiles else "")
    result = None

    if request.method == "POST":
        action = request.form.get("action")
        selected_profile = request.form.get("aws_profile", selected_profile)

        if action == "plan":
            values_out, errors = build_values_from_form(env["fields"], request.form)
            if errors:
                result = {"ok": False, "action": "plan", "output": "\n".join(errors)}
            else:
                write_tfvars(directory, values_out)
                values = form_display_values(env["fields"], values_out)
                result = run_terraform_plan(directory, selected_profile, env_key)

        elif action == "apply":
            confirm_text = (request.form.get("confirm_text") or "").strip()
            if not plan_is_fresh(directory):
                result = {
                    "ok": False, "action": "apply",
                    "output": "No up-to-date plan found for these inputs. "
                              "Click 'Save & Plan' again first, then Apply.",
                }
            elif confirm_text != "APPLY":
                result = {
                    "ok": False, "action": "apply",
                    "output": "Type APPLY exactly (case-sensitive) in the "
                              "confirmation box to run apply.",
                }
            else:
                result = run_terraform_apply(directory, selected_profile, env_key)

    return render_template(
        "env.html",
        env=env,
        env_key=env_key,
        values=values,
        profiles=profiles,
        selected_profile=selected_profile,
        result=result,
        directory=str(directory),
        plan_fresh=plan_is_fresh(directory),
        existing_workloads=None,
    )


@app.route("/workload", methods=["GET", "POST"])
def workload_page():
    env = WORKLOAD_ENV
    profiles = list_aws_profiles()
    existing = list_existing_workload_dirs()

    app_name = request.values.get("app_name", "").strip()
    environment = request.values.get("environment", "prod").strip()
    directory = target_directory(f"{app_name}-{environment}") if app_name else None

    saved = load_existing_tfvars(directory)
    values = form_display_values(env["fields"], saved)
    values["app_name"] = app_name
    values["environment"] = environment
    selected_profile = request.values.get("aws_profile", profiles[0] if profiles else "")
    result = None

    if request.method == "POST":
        action = request.form.get("action")
        selected_profile = request.form.get("aws_profile", selected_profile)
        app_name = (request.form.get("app_name") or "").strip()
        environment = (request.form.get("environment") or "prod").strip()
        values["app_name"], values["environment"] = app_name, environment

        if not app_name or not APP_NAME_PATTERN.match(app_name):
            result = {
                "ok": False, "action": action,
                "output": "App name is required and must contain only letters/numbers "
                          "(e.g. ordermgmt) — it's used to build a folder name.",
            }
        else:
            directory = target_directory(f"{app_name}-{environment}")

            if action == "plan":
                if not directory.exists():
                    template_dir = target_directory(env["template_dirname"])
                    shutil.copytree(template_dir, directory)

                values_out, errors = build_values_from_form(env["fields"], request.form)
                if errors:
                    result = {"ok": False, "action": "plan", "output": "\n".join(errors)}
                else:
                    write_tfvars(directory, values_out)
                    values = form_display_values(env["fields"], values_out)
                    values["app_name"], values["environment"] = app_name, environment
                    result = run_terraform_plan(directory, selected_profile, directory.name)

            elif action == "apply":
                confirm_text = (request.form.get("confirm_text") or "").strip()
                if not directory.exists() or not plan_is_fresh(directory):
                    result = {
                        "ok": False, "action": "apply",
                        "output": "No up-to-date plan found for these inputs. "
                                  "Click 'Save & Plan' again first, then Apply.",
                    }
                elif confirm_text != "APPLY":
                    result = {
                        "ok": False, "action": "apply",
                        "output": "Type APPLY exactly (case-sensitive) in the "
                                  "confirmation box to run apply.",
                    }
                else:
                    result = run_terraform_apply(directory, selected_profile, directory.name)

    return render_template(
        "env.html",
        env=env,
        env_key="workload",
        values=values,
        profiles=profiles,
        selected_profile=selected_profile,
        result=result,
        directory=str(directory) if directory else "(not created yet — pick an app name below)",
        plan_fresh=plan_is_fresh(directory),
        existing_workloads=existing,
    )


if __name__ == "__main__":
    url = "http://127.0.0.1:5000/"
    print(f"\nLanding Zone UI running at {url}")
    print("Open that address in your browser. It does NOT open automatically —")
    print("this app runs real terraform commands, so nothing loads a page for you.\n")
    app.run(host="127.0.0.1", port=5000, debug=False)
