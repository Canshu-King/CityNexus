"""Repair the timezone token this lane's ledger blocks have been carrying.

Measured, not assumed: every `SESSION=e345b9d6` header in CITYNEXUS_AGENT_CONTROL.md reads
`... HH:MM00` -- no block in the file carries the `+08` shape at all -- because
`ledger_insert_delivery_e345b9d6.py` stamped `f"{stamp[:16]}{stamp[19:]}"` against
`%Y-%m-%d %H:%M%z`, which drops `+08` and keeps the minute field of the offset.

The edit is mechanical and provable: only the `00` that directly follows `HH:MM` inside a
`SESSION=e345b9d6` header becomes `+08`; the byte length does not change, and deleting that
substitution reproduces the original bytes exactly.
"""
import hashlib
import io
import re
import sys

PATH = "D:/moodle/CITYNEXUS_AGENT_CONTROL.md"


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def main() -> int:
    original = io.open(PATH, encoding="utf-8", newline="").read()
    pat = re.compile(r"(SESSION=e345b9d6 @2026-\d\d-\d\d \d\d:\d\d)00")
    hits = list(pat.finditer(original))
    print(f"my lane's headers={len(hits)}  total headers in file={original.count('SESSION=')}")
    print("shapes before:", sorted({m.group(0)[-8:] for m in hits}))
    print("any correct +08 header anywhere:", bool(re.search(r"@2026-\d\d-\d\d \d\d:\d\d\+08", original)))
    if not hits:
        print("nothing to repair")
        return 0
    fixed, n = pat.subn(lambda m: m.group(1) + "+08", original)
    assert n == len(hits), f"substitutions {n} != headers {len(hits)}"
    # `00` -> `+08` is exactly one extra character per header; anything else means text moved.
    assert len(fixed) - len(original) == n, "the repair changed more than the token"
    # reversibility: the same substitution run backwards reproduces the original bytes
    back, rn = re.subn(r"(SESSION=e345b9d6 @2026-\d\d-\d\d \d\d:\d\d)\+08", r"\g<1>00", fixed)
    assert rn == n and back == original, "the repair is not reversible on its own text"
    assert fixed.count("\r\n") == original.count("\r\n"), "line endings changed"
    io.open(PATH, "w", encoding="utf-8", newline="").write(fixed)
    readback = io.open(PATH, encoding="utf-8", newline="").read()
    print(
        f"replaced={n} sha256[:16] {sha(original)} -> {sha(readback)}  "
        f"bytes {len(original.encode('utf-8'))} -> {len(readback.encode('utf-8'))}  "
        f"crlf={readback.count(chr(13))}"
    )
    print("shapes after:", sorted({m.group(0)[-11:] for m in re.finditer(pat.pattern.replace(')00', ')\\+08'), readback)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
