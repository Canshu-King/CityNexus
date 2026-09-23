"""Splice the four legacy arms out of the published v2 into v3, byte for byte.

Doing this with a cut-and-paste of source text rather than by hand is the point: the claim "the old arms were
not edited" has to survive a diff, and anything I retype can drift one character without changing behaviour.
"""
from __future__ import annotations

import ast
import hashlib
import pathlib
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
BASE = pathlib.Path(r"D:\moodle\_qoder_harness_ord0254\tools")
v2 = (BASE / "ord0263_verifier_v2.py").read_text(encoding="utf-8")
v3 = (BASE / "ord0263_verifier_v3.py").read_text(encoding="utf-8")

start = v2.index("def answered(")
stop = v2.index("def selftest()")
block = v2[start:stop].rstrip() + "\n"

marker = "# ---- the four old arms, copied verbatim from v2 (proved by legacy_arms_unchanged) --------------------"
i = v3.index(marker)
tail_start = v3.index("LEGACY_BLOCKS = (")
# remove my hand-typed helper pair, then splice v2's own text in its place
dup = """def answered(c: dict) -> bool:
    a = c.get("origin_answer") or {}
    return isinstance(a.get("status"), int) and a.get("thrown") is False


def no_answer(c: dict) -> bool:
    return (c.get("origin_answer") or {}).get("thrown") is True


"""
assert dup in v3[i:tail_start], "expected my hand-written helper pair not found - refusing to guess"
v3_wo_dup = v3[:i + len(marker)] + "\n\n" + v3[i + len(marker):].replace(dup, "", 1)
j = v3_wo_dup.index(marker) + len(marker)
k = v3_wo_dup.index("LEGACY_BLOCKS = (")
v3_new = v3_wo_dup[:j] + "\n\n" + block + "\n# ---- end legacy arms ----\n\n" + v3_wo_dup[k:]

ast.parse(v3_new)
(BASE / "ord0263_verifier_v3.py").write_bytes(v3_new.encode("utf-8"))
print("spliced", len(block), "chars of legacy arms from v2 into v3; syntax ok")
print("v2 blob40:", hashlib.sha1((BASE / "ord0263_verifier_v2.py").read_bytes()).hexdigest()[:16],
      "| v3 bytes now:", len(v3_new.encode('utf-8')))
