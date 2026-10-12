# -*- coding: utf-8 -*-
"""ORD-0616 wiring: give the inbox import door a replay-safe identity for the artefact it took.

Three asserted replacements in the one host this order allows (`backend/app/operations/v9.py`).
Each anchor must match exactly once or the patch aborts without writing.
"""
import io
import sys

WT = "D:/moodle/_jz_0616/wt/"
V9 = WT + "backend/app/operations/v9.py"

EDITS = [
    (
        "from app.core.audit import record_audit\n",
        "from app.core.audit import record_audit\n"
        "from app.journey_inbox import inbox_artifact_fingerprint\n",
    ),
    (
        "    unresolved = [field for field in CRITICAL_RESERVATION_FIELDS"
        " if not extracted.get(field)]\n",
        "    # The same confirmation pasted twice has to land as one artefact, so the audit trail\n"
        "    # carries the inbox module's content identity rather than a run id or a timestamp.\n"
        "    artifact_fingerprint = inbox_artifact_fingerprint(\n"
        "        source_kind=kind,\n"
        "        normalized_text=_json(payload) if kind == \"STRUCTURED_JSON\" else text,\n"
        "    )\n"
        "    unresolved = [field for field in CRITICAL_RESERVATION_FIELDS"
        " if not extracted.get(field)]\n",
    ),
    (
        "        after={\"status\": draft.status, \"unresolved_fields\": unresolved,"
        " \"extraction_mode\": mode},\n",
        "        after={\n"
        "            \"status\": draft.status,\n"
        "            \"unresolved_fields\": unresolved,\n"
        "            \"extraction_mode\": mode,\n"
        "            \"artifact_fingerprint\": artifact_fingerprint,\n"
        "        },\n",
    ),
]


def main():
    body = io.open(V9, encoding="utf-8").read()
    for i, (old, new) in enumerate(EDITS, 1):
        n = body.count(old)
        if n != 1:
            print("ABORT hunk %d matched %d times (need exactly 1)" % (i, n))
            return 1
        body = body.replace(old, new, 1)
    io.open(V9, "w", encoding="utf-8", newline="\n").write(body)
    print("patched %s : %d hunks" % (V9, len(EDITS)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
