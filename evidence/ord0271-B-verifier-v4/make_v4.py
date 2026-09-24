"""Build `tools/ord0263_verifier_v4.py` from v3's own bytes plus four named edits - no retyped arms.

Why a generator rather than typing v4 out: the claim this order has to survive is *"the four old arms are
untouched and the fifth arm gained exactly one clause"*. That claim is only checkable if the inherited text
comes from v3's file rather than from my keyboard. So this script:

* slices v3's fifth-arm region (its constants, `parse_attribution`, `as_int`, `judge_v5`, `aggregate_v5`) and its
  legacy region (the four old arms and the two helpers) straight out of `ord0263_verifier_v3.py`;
* applies four edits to the fifth region, each asserted to hit exactly once, and refuses to write the file if
  any edit hits zero or several times - an edit that silently misses is how a killer ends up empty-running;
* fills the two sentinels in the v4 skeleton, which is where the new selftest arms live;
* re-hashes v3 before and after, because this script must not be able to touch the old ruler at all.

The edits, in one line each: add `BAD_REASONS_V4`; point `reason_ok` at it; surface
`only_reason_clause_failed` in the measured fields so "RED only because of the new clause" is derivable; and
extend the `rule` sentence to say what v4 now forbids.
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

BASE = Path(r"D:\moodle\_qoder_harness_ord0254")
V3 = BASE / "tools" / "ord0263_verifier_v3.py"
V4 = BASE / "tools" / "ord0263_verifier_v4.py"
V3_BLOB = "e9a4188f63e27bbbf8bfed35adfd554b9e8641d9"


def blob40(d: bytes) -> str:
    return hashlib.sha1(b"blob %d\x00" % len(d) + d).hexdigest()


def once(text: str, old: str, new: str, tag: str) -> str:
    n = text.count(old)
    if n != 1:
        raise SystemExit(f"ABORT: edit {tag} matched {n} times, expected exactly 1")
    return text.replace(old, new, 1)


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    v3_bytes = V3.read_bytes()
    if blob40(v3_bytes) != V3_BLOB:
        raise SystemExit(f"ABORT: v3 is not the published blob ({blob40(v3_bytes)}); refusing to splice")
    v3 = v3_bytes.decode("utf-8")

    i_fifth = v3.index("# ---- fifth state: measured fields")
    i_legacy = v3.index("# ---- the four old arms")
    i_end = v3.index("# ---- end legacy arms")
    fifth = v3[i_fifth:i_legacy].rstrip() + "\n"
    legacy = v3[i_legacy:i_end].rstrip() + "\n"
    if "def judge_v5(" not in fifth or "def aggregate_v5(" not in fifth:
        raise SystemExit("ABORT: fifth region does not contain both judges")
    if "def judge_v4(" not in legacy or "def answered(" not in legacy:
        raise SystemExit("ABORT: legacy region does not contain the four arms")

    # edit 1: the new vocabulary, sitting next to the old one so the difference is one line to read
    fifth = once(fifth,
                 'BAD_REASONS = {"NETWORK_UNAVAILABLE", "NO_REPLY"}\n',
                 'BAD_REASONS = {"NETWORK_UNAVAILABLE", "NO_REPLY"}\n'
                 '# v4\'s one addition. A catch-all name is not a classification either: `UNKNOWN_FAILURE` is\n'
                 '# what the product falls back to when it has decided nothing, so a fifth state filed there has\n'
                 '# lost the one fact it was meant to carry even when every other column of the line is honest.\n'
                 'BAD_REASONS_V4 = BAD_REASONS | {"UNKNOWN_FAILURE"}\n',
                 "BAD_REASONS_V4")
    # edit 2: point the reason clause at the widened set
    fifth = once(fifth,
                 "    reason_ok = bool(reason) and reason not in BAD_REASONS\n",
                 "    reason_ok = bool(reason) and reason not in BAD_REASONS_V4\n",
                 "reason_ok")
    # edit 3: make "RED only because of the new clause" derivable from the receipt itself
    fifth = once(fifth,
                 '                         "cached_copy_matches_measured_rows": copy_honours_measurement,\n',
                 '                         "cached_copy_matches_measured_rows": copy_honours_measurement,\n'
                         '                         "only_reason_clause_failed": fails == ["reason_collapsed"],\n',
                 "only_reason_clause_failed")
    # edit 4: say it in the rule line the receipt prints
    fifth = once(fifth,
                 '                    "and the sentence may not claim nothing answered"}\n',
                 '                    "and the sentence may not claim nothing answered; and the reason may not "\n'
                 '                    "be a catch-all either (v4): UNKNOWN_FAILURE names no state at all"}\n',
                 "rule sentence")

    skel = V4.read_text(encoding="utf-8")
    for sentinel, payload in (("# @@FIFTH_REGION@@", fifth), ("# @@LEGACY_REGION@@", legacy)):
        if skel.count(sentinel) != 1:
            raise SystemExit(f"ABORT: skeleton sentinel {sentinel} appears {skel.count(sentinel)} times")
        skel = skel.replace(sentinel, payload.rstrip() + "\n", 1)

    compile(skel, str(V4), "exec")
    V4.write_bytes(skel.encode("utf-8"))
    after = V3.read_bytes()
    print(f"v4 written: {V4.stat().st_size:,} B blob {blob40(V4.read_bytes())[:16]} "
          f"(fifth region {len(fifth):,} chars, legacy region {len(legacy):,} chars)")
    print(f"v3 untouched: before {blob40(v3_bytes)[:16]} after {blob40(after)[:16]} equal={after == v3_bytes}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
