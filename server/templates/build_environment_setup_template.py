#!/usr/bin/env python3
"""Regenerate server/templates/environment_setup/ from a reference Cognigy
package export.

This is a maintenance script, not something the running server calls. Re-run
it if the reference "*_Environment_Setup" flow changes and the template needs
to be refreshed.

It reads the ORIGINAL flow (whatever its name is in the source package, so
long as it matches --flow-name), keeps only:
    Start -> "Payload data from Studio" (code) -> "Code : Env Variables" (code)
    -> the non-disabled Set Session Config -> the environment switch/case
    nodes -> the per-environment "Code : ... url" nodes -> End
and drops everything from the HTTP Request node onward (the access-token
call, the If/Then/Else, Add To Context, Stop and Return) except the End node
itself, and drops any disabled node.

It also scrubs any baseUrl/client_id/client_secret literals found in the
kept code nodes to empty strings - the resulting template must never contain
real credentials, regardless of what the source package had.

Usage:
    python build_environment_setup_template.py /path/to/source-package.zip
"""

from __future__ import annotations

import json
import re
import sys
import zipfile
from pathlib import Path

FLOW_NAME_SUFFIX = "Environment_Setup"  # matches "*.HRB_Environment_Setup" etc.

# Node labels to keep from the original chart, by their role in the trimmed flow.
KEEP_LABELS = {
    "Start",
    "Payload data from Studio",
    "Code : Env Variables",
    # the enabled duplicate, not the disabled original "Set Session Config"
    "Set Session Config (2)",
    "Lookup Environment",
    "Default",
    "DEV",
    "QA",
    "PROD",
    "Code : Dev Url",
    "Code : UAT url",
    "Code : prod url",
    "End",
}

CONTEXT_SECRET_PATTERN = re.compile(
    r'api\.addToContext\("configuration\.(baseUrl|client_id|client_secret)"\s*,\s*"[^"]*"\s*,\s*"simple"\)'
)
# Matches `voice: "<long hex token>"` / `chat: "<long hex token>"` entries like
# the endpointTokenMap in "Code : Env Variables" - these are real, per-tenant
# Cognigy endpoint URL tokens, not just placeholders, even though the task
# that asked for this template only named baseUrl/client_id/client_secret.
ENDPOINT_TOKEN_PATTERN = re.compile(r'(\b(?:voice|chat)\s*:\s*")[0-9a-fA-F]{16,}(")')


# Node-config fields that identify a specific tenant's account/resources
# (e.g. a cloned/custom ElevenLabs voice ID) rather than generic settings -
# blanked regardless of node type. `ttsVoice` was found to still contain a
# real customer voice ID even after the code-node secret scrub above (an
# Aikido high-severity finding caught it) - if you add another provider-
# specific id field here in the future, add it to this set too.
TENANT_SPECIFIC_CONFIG_FIELDS = {"ttsVoice"}


def scrub_secrets(code: str) -> str:
    code = CONTEXT_SECRET_PATTERN.sub(
        lambda m: f'api.addToContext("configuration.{m.group(1)}","","simple")', code
    )
    code = ENDPOINT_TOKEN_PATTERN.sub(lambda m: f"{m.group(1)}{m.group(2)}", code)
    return code


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: build_environment_setup_template.py /path/to/source-package.zip", file=sys.stderr)
        return 1

    src = zipfile.ZipFile(sys.argv[1])
    names = src.namelist()

    flow_entries = [n for n in names if n.startswith("flow/")]
    flow_name_entry = None
    flow_doc = None
    for n in flow_entries:
        d = json.loads(src.read(n))
        if d.get("name", "").endswith(FLOW_NAME_SUFFIX):
            flow_name_entry, flow_doc = n, d
            break
    if flow_doc is None:
        print(f"No flow ending in '{FLOW_NAME_SUFFIX}' found in {sys.argv[1]}", file=sys.stderr)
        return 1

    flow_id = flow_doc["_id"]
    chart_id = flow_doc["chartReference"]
    chart_doc = json.loads(src.read(f"chart/{chart_id}"))

    node_docs: dict[str, dict] = {}
    for rel in chart_doc["relations"]:
        nid = rel["node"]
        node_docs[nid] = json.loads(src.read(f"nodeData/{nid}"))

    keep_ids = {nid for nid, doc in node_docs.items() if doc.get("label") in KEEP_LABELS}
    missing = KEEP_LABELS - {node_docs[nid]["label"] for nid in keep_ids}
    if missing:
        print(f"WARNING: expected labels not found in source flow: {missing}", file=sys.stderr)

    # Rewire: the switch's `next` (originally the HTTP Request node) becomes
    # the End node id directly, dropping everything in between.
    switch_id = next(nid for nid in keep_ids if node_docs[nid]["label"] == "Lookup Environment")
    end_id = next(nid for nid in keep_ids if node_docs[nid]["label"] == "End")

    original_next = {rel["node"]: rel.get("next") for rel in chart_doc["relations"]}

    def resolve_next(nid: str | None) -> str | None:
        """Follow `next` pointers through dropped (e.g. disabled) nodes until
        landing on a kept node, or run out of chain."""
        seen = set()
        while nid is not None and nid not in keep_ids:
            if nid in seen:  # defensive: don't loop forever on a cycle
                return None
            seen.add(nid)
            nid = original_next.get(nid)
        return nid

    new_relations = []
    for rel in chart_doc["relations"]:
        nid = rel["node"]
        if nid not in keep_ids:
            continue
        if nid == switch_id:
            # Deliberate content trim, not a disabled-node skip: drop the
            # HTTP Request / If / Then / Else / AddToContext / Stop chain
            # entirely and go straight to End.
            next_id = end_id
        else:
            next_id = resolve_next(rel.get("next"))
        new_relations.append(
            {
                "node": nid,
                "children": [c for c in rel.get("children", []) if c in keep_ids],
                "next": next_id,
                "_id": rel["_id"],
            }
        )

    out_dir = Path(__file__).resolve().parent / "environment_setup"
    for sub in ["flow", "chart", "nodeData", "flowSettings", "flowState", "locale"]:
        (out_dir / sub).mkdir(parents=True, exist_ok=True)

    # locale (needed for localeMapping on import)
    locale_id = flow_doc["localizedData"][0]["localeReference"]
    locale_doc = json.loads(src.read(f"locale/{locale_id}"))
    (out_dir / "locale" / locale_id).write_text(json.dumps(locale_doc, indent=2), encoding="utf-8")

    # flow (name will be overwritten at import time to match the project name,
    # but a placeholder name is required in the template itself)
    flow_doc["name"] = "Environment_Setup"
    (out_dir / "flow" / flow_id).write_text(json.dumps(flow_doc, indent=2), encoding="utf-8")

    chart_doc["relations"] = new_relations
    (out_dir / "chart" / chart_id).write_text(json.dumps(chart_doc, indent=2), encoding="utf-8")

    for nid in keep_ids:
        doc = node_docs[nid]
        for ld in doc.get("localizedData", []):
            cfg = ld.get("config")
            if isinstance(cfg, dict) and isinstance(cfg.get("code"), str):
                cfg["code"] = scrub_secrets(cfg["code"])
            if isinstance(cfg, dict) and isinstance(cfg.get("transpiled"), str):
                cfg["transpiled"] = scrub_secrets(cfg["transpiled"])
            if isinstance(cfg, dict):
                for field in TENANT_SPECIFIC_CONFIG_FIELDS:
                    if cfg.get(field):
                        cfg[field] = ""
        (out_dir / "nodeData" / nid).write_text(json.dumps(doc, indent=2), encoding="utf-8")

    # flowSettings / flowState referencing this flow
    for n in names:
        if n.startswith("flowSettings/"):
            d = json.loads(src.read(n))
            if d.get("flowReference") == flow_id:
                (out_dir / "flowSettings" / d["_id"]).write_text(json.dumps(d, indent=2), encoding="utf-8")
        if n.startswith("flowState/"):
            d = json.loads(src.read(n))
            if d.get("flowReference") == flow_id:
                (out_dir / "flowState" / d["_id"]).write_text(json.dumps(d, indent=2), encoding="utf-8")

    index = {
        "cognigyVersion": flow_doc.get("cognigyVersion", "unknown"),
        "type": "package",
        "name": "environment-setup-template",
        "description": "Trimmed, secret-scrubbed Environment Setup flow template used by create_project.",
        "skippedResources": [],
        "partial": False,
        "missingTypes": [],
    }
    (out_dir / "index.json").write_text(json.dumps(index, indent=2), encoding="utf-8")

    kept_labels = sorted(node_docs[nid]["label"] for nid in keep_ids)
    print(f"Wrote template to {out_dir}")
    print(f"Kept {len(keep_ids)} nodes: {kept_labels}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
