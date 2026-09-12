"""
Catalog of scaffoldable stack types, in actual deployment order. Reuses
../ui/config.py's field definitions directly (via sys.path, not a copy)
so this tool and the Landing Zone UI can never drift out of sync on what
each stack needs — they describe the same modules/variables.tf files.

Dict insertion order matters here: templates render these in this order,
and it must match the real build sequence (docs/04 §5 /
../README.md#deployment-order) — log-archive first, workload last —
since a new employee reading top-to-bottom should see the right order
without having to already know it.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "ui"))
import config as ui_config  # noqa: E402  (../ui/config.py)
from icons import ICONS_BY_KEY  # noqa: E402

STACK_TYPES = {
    "log-archive-account": {
        "step": 1,
        "title": "Log Archive Account",
        "template_dirname": "log-archive-account",
        "fields": ui_config.ENVIRONMENTS["log-archive-account"]["fields"],
        "description": ui_config.ENVIRONMENTS["log-archive-account"]["description"],
        "singleton": True,
        "note": "Apply first — nothing else depends on anything, but everything "
                "else depends on this one's bucket/key outputs.",
    },
    "management": {
        "step": 2,
        "title": "Management Account",
        "template_dirname": "management",
        "fields": ui_config.ENVIRONMENTS["management"]["fields"],
        "description": ui_config.ENVIRONMENTS["management"]["description"],
        "singleton": True,
        "note": "Needs Log Archive Account's outputs (step 1) as inputs.",
    },
    "audit-account": {
        "step": 3,
        "title": "Audit Account",
        "template_dirname": "audit-account",
        "fields": ui_config.ENVIRONMENTS["audit-account"]["fields"],
        "description": ui_config.ENVIRONMENTS["audit-account"]["description"],
        "singleton": True,
        "note": "Its GuardDuty/Security Hub setup comes from Management (step 2) — "
                "apply Management first, or its delegation has nothing to attach to yet.",
    },
    "network-hub-account": {
        "step": 4,
        "title": "Network Hub Account",
        "template_dirname": "network-hub-account",
        "fields": ui_config.ENVIRONMENTS["network-hub-account"]["fields"],
        "description": ui_config.ENVIRONMENTS["network-hub-account"]["description"],
        "singleton": True,
        "note": "Needs Log Archive Account's outputs (step 1).",
    },
    "workload": {
        "step": 5,
        "title": "Workload Account",
        "template_dirname": "workload-account-example",
        "fields": ui_config.WORKLOAD_ENV["fields"],
        "description": ui_config.WORKLOAD_ENV["description"],
        "singleton": False,
        "note": "One per migrated application — repeat this step for every app. "
                "Needs Network Hub's transit_gateway_id (step 4) and Log Archive's "
                "outputs (step 1).",
        "is_workload": True,
    },
}

for _key, _stack in STACK_TYPES.items():
    _stack["icon"] = ICONS_BY_KEY[_key]
