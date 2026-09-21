"""Append this lane's delivery block to the control ledger without eating anyone's heading.

The failure this guards against (recorded twice in the ledger): inserting by replacing the *next*
lane's `###` heading deletes their title.  So the block is inserted immediately before a stable
section heading, the file is re-read afterwards, and both the new block and the section heading are
proved to still be present byte-for-byte.
"""

import sys

LEDGER = "D:/moodle/CITYNEXUS_AGENT_CONTROL.md"
BEFORE = "## ORDERS（收件箱：worker 每完成一个动作、每开始下一个动作之前先读这里）"


def main() -> int:
    block_path = sys.argv[1]
    # Read the block the same way as the ledger and force LF: `Path.write_text` and universal-newline
    # reads both silently turn `\n` into `\r\n` on Windows, and the ledger is LF by agreement -- three
    # CRLF rewrites today broke every lane's whole-line anchor matching.
    block = open(block_path, encoding="utf-8", newline="").read().replace("\r\n", "\n")
    text = open(LEDGER, encoding="utf-8", newline="").read()
    if BEFORE not in text:
        print("ABORT: the ORDERS anchor is not in the ledger; nothing was written")
        return 2
    marker = block.splitlines()[0].strip()
    if marker and marker in text:
        print(f"ABORT: this block is already in the ledger ({marker[:60]})")
        return 3
    head, tail = text.split(BEFORE, 1)
    inserted = f"{block.rstrip()}\n\n{BEFORE}"
    updated = f"{head}{inserted}{tail}"
    open(LEDGER, "w", encoding="utf-8", newline="").write(updated)

    after = open(LEDGER, encoding="utf-8", newline="").read()
    kept_block = marker in after
    kept_anchor = BEFORE in after
    grew = len(after) - len(text)
    # Taking my block back out has to give the previous file back byte for byte.  If another lane
    # wrote while I was assembling, that round trip fails instead of quietly dropping their work.
    round_trip = after.replace(inserted, BEFORE, 1) == text
    crlf = after.count("\r\n")
    print(
        f"appended bytes={grew} block_present={kept_block} orders_anchor_present={kept_anchor} "
        f"round_trip={round_trip} crlf_lines={crlf}"
    )
    if not (kept_block and kept_anchor and round_trip and crlf == 0):
        print("VERIFY FAILED — restore from the pre-append copy")
        return 4
    count = sum(1 for line in after.splitlines() if line.startswith(BEFORE))
    print(f"ORDERS headings now: {count}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
