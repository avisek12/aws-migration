"""
Shells out to the Terraform CLI and manages tfvars/profile plumbing for
the Landing Zone UI. Nothing here talks to AWS directly — it only ever
invokes the `terraform` binary already on PATH, which in turn uses
whichever AWS profile was picked on the page (via the AWS_PROFILE
environment variable).
"""
import configparser
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

TERRAFORM_ROOT = Path(__file__).resolve().parent.parent
ENVIRONMENTS_ROOT = TERRAFORM_ROOT / "environments"
AUDIT_LOG = Path(__file__).resolve().parent / "audit.log"

KNOWN_SINGLETON_DIRS = {
    "management",
    "log-archive-account",
    "audit-account",
    "network-hub-account",
    "workload-account-example",
}

TFVARS_FILENAME = "terraform.tfvars.json"
PLAN_FILENAME = "tfplan"


def target_directory(dirname: str) -> Path:
    return ENVIRONMENTS_ROOT / dirname


def list_existing_workload_dirs():
    """Workload account folders created by this tool (or by hand) —
    anything under environments/ that isn't one of the fixed singleton
    stacks or the template itself."""
    if not ENVIRONMENTS_ROOT.exists():
        return []
    return sorted(
        p.name
        for p in ENVIRONMENTS_ROOT.iterdir()
        if p.is_dir() and p.name not in KNOWN_SINGLETON_DIRS
    )


def list_aws_profiles():
    """Named profiles from ~/.aws/config and ~/.aws/credentials, so each
    page can offer a dropdown instead of anyone typing account numbers
    or keys into the browser."""
    profiles = {"default"}
    for path in (Path.home() / ".aws" / "config", Path.home() / ".aws" / "credentials"):
        if not path.exists():
            continue
        parser = configparser.ConfigParser()
        try:
            parser.read(path)
        except configparser.Error:
            continue
        for section in parser.sections():
            name = section[len("profile "):] if section.startswith("profile ") else section
            profiles.add(name)
    return sorted(profiles)


def write_tfvars(directory: Path, values: dict):
    directory.mkdir(parents=True, exist_ok=True)
    with open(directory / TFVARS_FILENAME, "w") as f:
        json.dump(values, f, indent=2)


def load_existing_tfvars(directory: Optional[Path]) -> dict:
    if directory is None:
        return {}
    tfvars_path = directory / TFVARS_FILENAME
    if not tfvars_path.exists():
        return {}
    try:
        with open(tfvars_path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def plan_is_fresh(directory: Optional[Path]) -> bool:
    """True only if a saved plan exists and was produced after the
    tfvars currently on disk — i.e. Apply would run exactly what the
    last Plan click showed, not a stale plan against changed inputs."""
    if directory is None:
        return False
    plan_file = directory / PLAN_FILENAME
    tfvars_file = directory / TFVARS_FILENAME
    if not plan_file.exists() or not tfvars_file.exists():
        return False
    return plan_file.stat().st_mtime >= tfvars_file.stat().st_mtime


def _run(directory: Path, args: list, aws_profile: str):
    env = os.environ.copy()
    for key in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN"):
        env.pop(key, None)
    env["AWS_PROFILE"] = aws_profile
    env["AWS_SDK_LOAD_CONFIG"] = "1"

    try:
        proc = subprocess.run(
            ["terraform", *args],
            cwd=str(directory),
            env=env,
            capture_output=True,
            text=True,
            timeout=1800,
        )
        output = (proc.stdout or "") + (("\n" + proc.stderr) if proc.stderr else "")
        return proc.returncode == 0, output
    except FileNotFoundError:
        return False, (
            "Terraform CLI not found on PATH. Install Terraform and confirm "
            "`terraform -version` works from a regular terminal first."
        )
    except subprocess.TimeoutExpired:
        return False, "Command timed out after 30 minutes."


def _audit(env_key: str, directory: Path, profile: str, action: str, ok: bool):
    AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(AUDIT_LOG, "a") as f:
        f.write(
            f"{datetime.now(timezone.utc).isoformat()}\t{env_key}\t{directory}\t"
            f"{profile}\t{action}\t{'OK' if ok else 'FAILED'}\n"
        )


def run_terraform_plan(directory: Path, aws_profile: str, env_key: str) -> dict:
    init_ok, init_output = _run(directory, ["init", "-input=false", "-no-color"], aws_profile)
    if not init_ok:
        _audit(env_key, directory, aws_profile, "init", False)
        return {"ok": False, "action": "plan", "output": init_output}

    plan_ok, plan_output = _run(
        directory, ["plan", "-input=false", "-no-color", f"-out={PLAN_FILENAME}"], aws_profile
    )
    _audit(env_key, directory, aws_profile, "plan", plan_ok)
    combined = init_output + "\n\n----- terraform plan -----\n\n" + plan_output
    return {"ok": plan_ok, "action": "plan", "output": combined}


def run_terraform_apply(directory: Path, aws_profile: str, env_key: str) -> dict:
    # Apply the exact saved plan file, never a fresh unreviewed plan.
    apply_ok, apply_output = _run(
        directory, ["apply", "-input=false", "-no-color", PLAN_FILENAME], aws_profile
    )
    _audit(env_key, directory, aws_profile, "apply", apply_ok)
    if apply_ok:
        plan_file = directory / PLAN_FILENAME
        if plan_file.exists():
            plan_file.unlink()  # a used plan can't be re-applied; force a fresh plan next time
    return {"ok": apply_ok, "action": "apply", "output": apply_output}
