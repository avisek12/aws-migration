"""Same tiny HCL value formatter as ../scaffolder/hcl.py — kept as its own
small copy for the same reason as catalog.py (this service ships standalone,
never imports sibling tool code)."""


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
