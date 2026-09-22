"""Commander's ledger writer — thin wrapper over the mandated preflight tool.

Single implementation (arbiter ③ / commit 620c8e60): newline profile, unique local anchor and
reversibility all live in `ledger_write_preflight.py`. Nothing is re-implemented here; this file
only translates two commander operations into (before, target, after, replacement) spans, and
does the post-write readback the preflight tool asks the caller to verify.
"""
import io, os, pathlib, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ledger_write_preflight import atomic_write, plan_edit  # noqa: E402

LEDGER = pathlib.Path(r"D:\moodle\CITYNEXUS_AGENT_CONTROL.md")
HEAD = "## ORDERS（收件箱：worker 每完成一个动作、每开始下一个动作之前先读这里）"


def _span_edit(before, target, after, replacement):
    original = LEDGER.read_bytes()
    candidate, proof = plan_edit(original, before.encode("utf-8"), target.encode("utf-8"),
                                  after.encode("utf-8"), replacement.encode("utf-8"))
    atomic_write(LEDGER, candidate)
    after_bytes = LEDGER.read_bytes()
    if after_bytes != candidate:
        raise SystemExit(f"POST_WRITE_READBACK_MISMATCH expected={len(candidate)} got={len(after_bytes)}")
    print("[ledger_write] applied | proof:", {k: proof[k] for k in sorted(proof) if k != "receipt"})
    return proof


def insert_block(path):
    body = io.open(path, encoding="utf-8", newline="\n").read().strip("\n") + "\n"
    t = LEDGER.read_text(encoding="utf-8")
    # Dedupe key must be the WHOLE heading line: two headings can share a 40-char prefix
    # (e.g. "## commander 亲测 @2026-09-22T13:5x+08 —— ..." twice on 09-22), which silently
    # skipped a genuinely new block. A skip has to be auditable, so print the key.
    key = body.splitlines()[0]
    if key in t:
        print(f"[skip] block already present | key={key[:110]}")
        return
    i = t.index(HEAD)
    before, after = t[max(0, i - 40):i], t[i + len(HEAD): i + len(HEAD) + 40]
    _span_edit(before, HEAD, after, HEAD + "\n" + body)


def amend(oid, path):
    note = io.open(path, encoding="utf-8", newline="\n").read().strip()
    t = LEDGER.read_text(encoding="utf-8")
    start = t.index("- id: " + oid)
    nxt = t.find("\n- id: ORD-", start + 1)
    region = t[start:nxt if nxt > 0 else len(t)]
    # dedupe must be scoped to THIS order: several orders carry notes with the same opening
    if note in region:
        print(f"[skip] {oid} already amended"); return
    k = region.index("\n  status: ")
    line_end = region.index("\n", k + 1)
    target = region[k + 1:line_end]
    before, after = region[:k + 1], region[line_end:line_end + 40]
    _span_edit(before, target, after, target + note)
    print(f"[amend] {oid} annotated")


if __name__ == "__main__":
    a = sys.argv[1:]
    if a and a[0] == "--insert-block":
        insert_block(a[1])
    elif a and a[0] == "--amend":
        amend(a[1], a[2])
    else:
        raise SystemExit(__doc__)
