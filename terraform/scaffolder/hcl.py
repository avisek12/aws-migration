"""Tiny HCL value formatter — just enough to render a terraform.tfvars
file from the simple field types the scaffolder collects (strings,
numbers, bools, flat lists of strings). No dependency needed for this;
nothing here handles nested maps/objects because none of the module
variables in this repo need one in a tfvars file."""


def hcl_value(value) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        return "[" + ", ".join(hcl_value(v) for v in value) + "]"
    escaped = str(value).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def render_tfvars(values: dict) -> str:
    lines = [f"{key} = {hcl_value(val)}" for key, val in values.items()]
    return "\n".join(lines) + "\n"
