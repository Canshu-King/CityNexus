"""Insert a block immediately after an exact anchor LINE, anywhere in the ledger.

Same safety rules learned the hard way (a heading got eaten four times by Edits anchored on headings):
  * the anchor must match EXACTLY once, else abort;
  * byte identity is proved: new.replace(block,"",1) == old;
  * the anchor line is never rewritten;
  * the block must not start or end with a blank line that could glue two headings together;
  * written with newline="" so the file's existing LF stays LF (Path.write_text flips CRLF here).
"""

import io
import subprocess
import sys

LEDGER = r"D:\moodle\CITYNEXUS_AGENT_CONTROL.md"


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    anchor = sys.argv[1]
    block_file = sys.argv[2]

    # The Q43 gate is bolted to the write door, not left to my memory: a block that the ruler refuses to
    # call CLEAN never reaches the shared ledger. Bypass exists only as an explicit, named flag.
    if "--allow-ungated" not in sys.argv:
        g = subprocess.run([sys.executable, "claim_coordinate_check_r4c.py", "--text", block_file,
                            "--expect-clean"], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=300)
        if g.returncode:
            print("ABORT: block failed the Q43 gate (rc %d). Add coordinates - do not bypass." % g.returncode)
            print((g.stdout or "")[-900:])
            return 8

    # Second bolt on the same door: every 40-hex coordinate I am about to write must resolve in the local
    # object store. Typed hashes are exactly where I slip (21:39 tonight I put a 64-char value into a lane
    # message labelled as a "true blob"), so the block is refused before it reaches the shared ledger.
    # NOTE: the fetch below is the whole branch namespace on purpose - a lane's commit may live only on its
      # own refs/heads/review/* ref, and an unfetched object reads as "unresolvable" (false alarms at 21:42,
      # and again at 00:45 and 00:59 on two lane blocks).
    import re as _re
    if "--allow-bad-coords" not in sys.argv:
        # Fetch first: a blob published minutes ago is not in this object store yet, and a gate that calls my
        # own fresh coordinates "unresolvable" trains me to distrust the gate. That is what happened at 21:54,
        # so the fetch belongs inside the rule instead of in my memory of it.
        # Fetch every branch, not just commander/control: lanes legitimately put commits on their own
        # `refs/heads/review/*` refs, and a bolt that can't see those reports a real coordinate as
        # "unresolvable" - that false alarm cost D and HJ-P3 one refused block each at 00:45 / 00:59.
        subprocess.run(["git", "-C", "D:/moodle/CityNexus", "fetch", "origin",
                        "+refs/heads/*:refs/remotes/origin/*", "--quiet"],
                       capture_output=True, timeout=900)
        _raw = io.open(block_file, encoding="utf-8", newline="\n").read()
        for _h in sorted(set(_re.findall(r"\b[0-9a-f]{40}\b", _raw))):
            _p = subprocess.run(["git", "-C", "D:/moodle/CityNexus", "cat-file", "-t", _h],
                                capture_output=True, text=True, timeout=120)
            if _p.returncode:
                print("ABORT: coordinate %s does not resolve in D:/moodle/CityNexus." % _h)
                print("       the door already fetched all origin branches; if it still fails the coordinate is not in git;")
                print("       if it still fails, the coordinate is wrong - fix it, do not bypass.")
                return 9

    old = io.open(LEDGER, encoding="utf-8", newline="").read()
    raw = io.open(block_file, encoding="utf-8", newline="\n").read()
    block = raw.strip("\n") + "\n"
    if anchor not in old:
        print(f"ABORT: anchor not found: {anchor[:60]!r}")
        return 2
    n = old.count(anchor)
    if n != 1:
        print(f"ABORT: anchor matched {n} times, expected 1")
        return 2
    idx = old.index(anchor) + len(anchor)
    new = old[:idx] + "\n" + block + "\n" + old[idx:]
    # exact proof: cutting the inserted text back out must restore `old` byte for byte
    rebuilt = new[:idx] + new[idx + 1 + len(block) + 1:]
    if rebuilt != old:
        print("ABORT: byte-identity proof failed - refusing to write")
        return 3
    with io.open(LEDGER, "w", encoding="utf-8", newline="") as fh:
        fh.write(new)
    print(f"OK inserted {len(block)} chars after anchor {anchor[:48]!r}")
    print(f"size {len(old)} -> {len(new)} chars; line delta {new.count(chr(10)) - old.count(chr(10))}")
    first = block.splitlines()[0]
    print("first line:", first[:80])
    print("count of that first line now:", new.count(first))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
