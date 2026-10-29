"""Put the KeyError-family attribution onto a tracked artifact instead of a console reading.

Section 14.13 claims nine of the ten KeyError reds are the same bearer-less private read the ACL
already produces, and that the tenth is a branch the product takes only on exceptions.  The evidence
for that is two grep-shaped facts per site: does the file attach any credential anywhere, and what
does the failing line actually call.  This writes both out for every site and enforces that the row
count equals the number the published census carries for that class, so the artifact cannot drift
from the table it explains.
"""

import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
BACKEND = os.path.join(ROOT, "backend")
CENSUS = os.path.join(ROOT, "trial", "results", "20261026_gozero", "bw195-red-census-extended.txt")
RECEIPT = os.path.join(ROOT, "trial", "results", "20261026_gozero", "bw213-keyerror-family-evidence.txt")

AUTH_MARKER = re.compile(r"Authorization|_auth|bearer|traveler_token", re.I)
KEY_ERROR_CLASS = "answer lacks a key the test reads (KeyError off the server body)"
EXPECTED_ROWS = 10

SITES = [
    ("tests/test_agent_mission_runtime.py", 448, "current_activity_id"),
    ("tests/test_agent_mission_runtime.py", 1238, "budget"),
    ("tests/test_r14_terminal_disruption_recovery.py", 69, "current_activity_id"),
    ("tests/test_wp04_endpoints.py", 221, "traveler_id"),
    ("tests/test_v12_authoritative_trip_execution.py", 249, "context"),
    ("tests/test_wp06_twin_v2_gate.py", 58, "context"),
    ("tests/test_v16_integration.py", 282, "trip"),
    ("tests/test_wp06_postgate_hardening_next.py", 171, "projection_status"),
    ("tests/test_wp07_foundation_assist.py", 144, "projection_status"),
    ("tests/test_qoder_anywhere_matrix_truth.py", 466, "error_type"),
]


def census_row_count():
    text = io.open(CENSUS, encoding="utf-8", errors="replace").read()
    rows = re.findall(r"^\s+\d+ x \S+ \[%s\]" % re.escape(KEY_ERROR_CLASS), text, re.M)
    return len(rows)


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    published = census_row_count()
    if published != EXPECTED_ROWS or len(SITES) != EXPECTED_ROWS:
        print("ABORT census carries %d rows for that class and this instrument lists %d"
              % (published, len(SITES)))
        return 5

    lines = [
        "KEYERROR FAMILY EVIDENCE bw213",
        "CENSUS_ROWS_FOR_CLASS %d (read from bw195, enforced equal here)" % published,
        "AUTH_MARKER = %s" % AUTH_MARKER.pattern,
        "SITES",
    ]
    signed_files = 0
    for rel, line_no, key in SITES:
        full = os.path.join(BACKEND, rel.replace("/", os.sep))
        text = io.open(full, encoding="utf-8", errors="replace").read()
        markers = len(AUTH_MARKER.findall(text))
        if markers:
            signed_files += 1
        body = text.splitlines()
        called = ""
        for i in range(line_no - 1, max(line_no - 7, -1), -1):
            if "client.get" in body[i - 1] or "client.get" in body[i] or ".json()[" in body[i]:
                called = " ".join(part.strip() for part in body[i - 1:line_no + 1])
                break
        lines.append(
            "  %s:%d key=%s auth_markers_in_file=%d call_nearest=%s"
            % (rel, line_no, key, markers, " ".join(called.split())[:150])
        )
    lines.append("FILES_WITH_ANY_AUTH %d of %d site files" % (signed_files, len(SITES)))
    lines.append(
        "PRODUCT_SIDE (the one key that is not about credentials): error_type is assigned only on"
        " exception paths -- see app/integrations/mobility/runtime.py:189, :318, :383"
    )

    io.open(RECEIPT, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
    for line in lines:
        print(line)
    print("WROTE %s" % RECEIPT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
