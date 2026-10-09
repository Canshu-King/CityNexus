"""Insert a block immediately BEFORE an exact anchor line (used to append at the end of a section)."""
import io, sys
LEDGER = r"D:\moodle\CITYNEXUS_AGENT_CONTROL.md"
def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    anchor, block_file = sys.argv[1], sys.argv[2]
    old = io.open(LEDGER, encoding="utf-8", newline="").read()
    if "\r\n" in old:
        print("ABORT: ledger is CRLF"); return 2
    if old.count(anchor) != 1:
        print(f"ABORT: anchor matched {old.count(anchor)} times"); return 2
    block = io.open(block_file, encoding="utf-8", newline="\n").read().strip("\n") + "\n"
    if anchor in block:
        print("ABORT: block contains the anchor"); return 2
    i = old.index(anchor)
    new = old[:i] + block + "\n" + old[i:]
    rebuilt = new[:i] + new[i + len(block) + 1:]
    if rebuilt != old:
        print("ABORT: byte-identity proof failed"); return 3
    with io.open(LEDGER, "w", encoding="utf-8", newline="") as fh:
        fh.write(new)
    rb = io.open(LEDGER, encoding="utf-8", newline="").read()
    print("readback equal:", rb == new, "| chars", len(old), "->", len(new), "| CRLF", "\r\n" in rb)
    print("block occurrences:", rb.count(block))
    return 0
raise SystemExit(main())
