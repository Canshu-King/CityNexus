"""Diagnose the splice: compile the in-memory text and print the line that actually failed."""
import hashlib
import sys
from pathlib import Path

BASE = Path(r"D:\moodle\_qoder_harness_ord0254")
sys.path.insert(0, str(BASE / "tools"))
import make_v4 as mk  # noqa: E402

v3 = (BASE / "tools" / "ord0263_verifier_v3.py").read_text(encoding="utf-8")
i_fifth, i_legacy, i_end = (v3.index("# ---- fifth state: measured fields"),
                            v3.index("# ---- the four old arms"), v3.index("# ---- end legacy arms"))
fifth = v3[i_fifth:i_legacy].rstrip() + "\n"
legacy = v3[i_legacy:i_end].rstrip() + "\n"
fifth = fifth.replace('BAD_REASONS = {"NETWORK_UNAVAILABLE", "NO_REPLY"}\n',
                      'BAD_REASONS = {"NETWORK_UNAVAILABLE", "NO_REPLY"}\n'
                      'BAD_REASONS_V4 = BAD_REASONS | {"UNKNOWN_FAILURE"}\n', 1)
fifth = fifth.replace("    reason_ok = bool(reason) and reason not in BAD_REASONS\n",
                      "    reason_ok = bool(reason) and reason not in BAD_REASONS_V4\n", 1)
skel = (BASE / "tools" / "ord0263_verifier_v4.py").read_text(encoding="utf-8")
skel = skel.replace("# @@FIFTH_REGION@@", fifth.rstrip() + "\n", 1)
skel = skel.replace("# @@LEGACY_REGION@@", legacy.rstrip() + "\n", 1)
lines = skel.splitlines()
try:
    compile(skel, "spliced", "exec")
    print("COMPILES")
except SyntaxError as e:
    print("SyntaxError line", e.lineno, "offset", e.offset, "msg", e.msg)
    lo = max(0, (e.lineno or 1) - 6)
    for n in range(lo, min(len(lines), (e.lineno or 1) + 4)):
        print(f"{n+1:>5}: {lines[n]}")
print("fifth region first 3 / last 6 lines:")
for l in fifth.splitlines()[:3]:
    print("   |", l)
for l in fifth.splitlines()[-6:]:
    print("   $", l)
