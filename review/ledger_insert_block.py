"""Insert one of this lane's delivery blocks before the `## ORDERS` anchor and stamp the measured
insertion receipt into the block itself.

Two writes, both verified: the first lands the block with placeholder tokens, the second replaces
those tokens with what I actually measured.  The second write is refused if anything outside my own
region moved -- the recorded failure mode here is a lane swallowing another lane's concurrent append.

Usage: ledger_insert_block.py <block.md> <heading-prefix> [<neighbour-heading>]
"""

import hashlib
import subprocess
import sys

LEDGER = "D:/moodle/CITYNEXUS_AGENT_CONTROL.md"
ANCHOR = "## ORDERS（收件箱：worker 每完成一个动作、每开始下一个动作之前先读这里）"
ENDS_WITH = "我只对「我这一段可逆」负责。"


def read(path: str) -> str:
    # Universal newlines would silently turn LF into CRLF on Windows; the ledger is LF by agreement.
    return open(path, encoding="utf-8", newline="").read()


def stamp(text: str) -> dict:
    body = text.encode("utf-8")
    return {
        "bytes": len(body),
        "sha": hashlib.sha256(body).hexdigest()[:16],
        "crlf": text.count("\r\n"),
        "anchor_count": text.count(ANCHOR),
        "cut": text.find(ANCHOR),
    }


def main() -> int:
    block_path, head = sys.argv[1], sys.argv[2]
    neighbour = sys.argv[3] if len(sys.argv) > 3 else ""
    block = read(block_path).replace("\r\n", "\n").rstrip() + "\n\n"
    if head == "@FIRSTLINE":
        # Git-bash argv cannot be trusted with emoji/CJK here, so the block names its own heading.
        head = block.splitlines()[0][:70]
    if not head.startswith("### ") or head not in block:
        print("ABORT: the heading prefix must be a `### ` title that opens this block")
        return 2
    if block.count("@ROUNDTRIP@") != 1:
        print("ABORT: the block does not hold exactly one receipt placeholder")
        return 3

    before_text = read(LEDGER)
    pre = stamp(before_text)
    if pre["anchor_count"] != 1 or pre["cut"] < 0:
        print(f"ABORT: ledger anchor state is not unique: {pre}")
        return 4
    if head in before_text:
        print("ABORT: this block is already in the ledger")
        return 5
    if neighbour and neighbour not in before_text:
        print("ABORT: the neighbour heading I meant to sit after is not in the file")
        return 6
    now = subprocess.run(
        ["powershell", "-NoProfile", "-Command", "Get-Date -Format 'yyyy-MM-dd HH:mm:ss'"],
        capture_output=True, text=True,
    ).stdout.strip()

    filled = (
        block.replace("@BYTES_BEFORE@", f"{pre['bytes']:,}")
        .replace("@SHA_BEFORE@", pre["sha"])
        .replace("@CRLF_BEFORE@", str(pre["crlf"]))
        .replace("@ANCHOR_BEFORE@", str(pre["anchor_count"]))
        .replace("@CUT_BEFORE@", str(pre["cut"]))
        .replace("@BLOCK_BYTES@", str(len(block.encode("utf-8"))))
        .replace("@NOW@", now)
    )
    head_part, tail_part = before_text.split(ANCHOR, 1)
    inserted = f"{filled.rstrip()}\n\n{ANCHOR}"
    open(LEDGER, "w", encoding="utf-8", newline="").write(f"{head_part}{inserted}{tail_part}")

    mid_text = read(LEDGER)
    if mid_text.count(ANCHOR) != 1 or mid_text.count(head) != 1:
        print(f"ABORT after first write: heading/anchor not unique ({mid_text.count(head)}/{mid_text.count(ANCHOR)})")
        return 7
    start, end = mid_text.find(head), mid_text.find(ANCHOR)
    region = mid_text[start:end]
    foreign = [ln for ln in region.splitlines() if ln.startswith("### ") and not ln.startswith(head)]
    if foreign:
        print(f"ABORT after first write: my region holds a foreign heading: {foreign[0][:70]}")
        return 8
    if not region.rstrip().endswith(ENDS_WITH):
        print(f"ABORT after first write: my region does not end where I think: ...{region.rstrip()[-40:]}")
        return 9

    post = stamp(mid_text)
    removable = (mid_text[:start] + mid_text[end:]) == before_text
    final = (
        filled.replace("@BYTES_AFTER@", f"{post['bytes']:,}")
        .replace("@SHA_AFTER@", post["sha"])
        .replace("@CUT_AFTER@", str(post["cut"]))
        .replace("@ANCHOR_AFTER@", str(post["anchor_count"]))
        .replace("@BLOCK_COUNT@", str(mid_text.count(head)))
        .replace("@ROUNDTRIP@", "是" if removable else "否")
    )
    tokens = [
        "@BYTES_AFTER@", "@SHA_AFTER@", "@CUT_AFTER@", "@ANCHOR_AFTER@", "@BLOCK_COUNT@", "@ROUNDTRIP@",
        "@BYTES_BEFORE@", "@SHA_BEFORE@", "@CRLF_BEFORE@", "@ANCHOR_BEFORE@", "@CUT_BEFORE@",
        "@BLOCK_BYTES@", "@NOW@",
    ]
    leftovers = [t for t in tokens if t in final]
    if leftovers:
        print(f"ABORT: unfilled placeholders remain: {leftovers}")
        return 10
    open(LEDGER, "w", encoding="utf-8", newline="").write(f"{mid_text[:start]}{final}{mid_text[end:]}")

    after = read(LEDGER)
    checks = {
        "block_present_once": after.count(head) == 1,
        "orders_anchor_unique": after.count(ANCHOR) == 1,
        "no_placeholder_left": all(t not in after for t in tokens),
        "still_pure_lf": after.count("\r") == 0,
        "neighbour_intact": (neighbour in after) if neighbour else True,
        "region_reversible": removable,
    }
    a = stamp(after)
    print(
        f"bytes {pre['bytes']:,} -> {a['bytes']:,} (delta {a['bytes'] - pre['bytes']})  "
        f"sha {pre['sha']} -> {a['sha']}  cut {pre['cut']} -> {a['cut']}  crlf {a['crlf']}  "
        + "  ".join(f"{k}={'ok' if v else 'FAIL'}" for k, v in checks.items())
    )
    if not all(checks.values()):
        print(f"VERIFY FAILED — restore from the pre-append read (before sha {pre['sha']})")
        return 11
    return 0


if __name__ == "__main__":
    sys.exit(main())
