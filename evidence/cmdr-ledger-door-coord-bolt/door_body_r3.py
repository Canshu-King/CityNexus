"""Insert a block immediately after an exact anchor LINE, anywhere in the ledger.

Same safety rules learned the hard way (a heading got eaten four times by Edits anchored on headings):
  * the anchor must match EXACTLY once, else abort;
  * byte identity is proved: new.replace(block,"",1) == old;
  * the anchor line is never rewritten;
  * the block must not start or end with a blank line that could glue two headings together;
  * written with newline="" so the file's existing LF stays LF (Path.write_text flips CRLF here).
"""

import io
import json
import os
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
        _HEX40 = _re.compile(r"\b[0-9a-f]{40}\b")
        # Phrases an author uses to disclose that a 40-hex value is NOT a git object.  Matching is on literal
        # prose, so an unlabelled typo still aborts; and the exemption is only granted when the SAME line also
        # carries a value that does resolve, which keeps the claim anchored to something fetchable.
        _NON_RETRIEVABLE = ("故意不可取回", "从未入 git", "非 blob", "不可 cat-file", "本地字节重算",
                            # S4's wording at 04:12 is the same disclosure in the other direction: it names the
                            # VALUE TYPE (a plain sha1 over bytes) rather than denying git-ness.  Both are honest
                            # and both are recomputable, so both count - and a git-blob claim still must resolve.
                            "sha1(over bytes)", "sha1 over bytes")
        # Literal phrases kept turning into a game of whack-a-mole (S4's second block said `文件 sha1`, which no
        # literal in the list matched).  Patterns instead: the disclosure must be about the VALUE BEING A PLAIN
        # CONTENT HASH OR NOT IN GIT, expressed either in Chinese or English, anywhere on the value's own line.
        _NON_RETRIEVABLE_PAT = _re.compile(
            u"sha1\\s*[\\(（]?\\s*(over|of)\\s+bytes"          # "sha1(over bytes)", "sha1 over bytes"
            u"|文件\\s*sha1|本机\\s*sha1|内容\\s*sha1"          # "the file's sha1" (a content hash, not a ref)
            u"|本地字节重算|字节重算的\\s*sha"                     # recomputed over local bytes
            u"|从未入\\s*git|未入\\s*git|不在对象库"              # never entered git
            u"|非\\s*blob|不是\\s*blob|不可\\s*cat-file|故意不可取回",
            _re.I)
        _resolves = {}
        for _h in sorted(set(_HEX40.findall(_raw))):
            _p = subprocess.run(["git", "-C", "D:/moodle/CityNexus", "cat-file", "-t", _h],
                                capture_output=True, text=True, timeout=120)
            _resolves[_h] = _p.returncode == 0
        _exempted = []
        # Anchor scope = the paragraph (the run of consecutive non-blank lines) the value sits in, while the
        # disclosure phrase must be on the value's OWN line.  Line-scoped anchoring was too strict in practice:
        # HJ-P3's block declares its non-git sha1 on one bullet and names the fetchable container on the next,
        # and refusing that punished honesty rather than sloppiness.  Cross-paragraph stays refused, so a lone
        # unanchored claim in its own paragraph still cannot ride a blob mentioned somewhere else in the block.
        _lines = _raw.splitlines()

        def _paragraph(idx):
            lo = hi = idx
            while lo > 0 and _lines[lo - 1].strip():
                lo -= 1
            while hi < len(_lines) - 1 and _lines[hi + 1].strip():
                hi += 1
            return "\n".join(_lines[lo:hi + 1])

        for _ln, _text in enumerate(_lines, 1):
            for _h in sorted(set(_HEX40.findall(_text))):
                if _resolves.get(_h):
                    continue
                _declared = bool(_NON_RETRIEVABLE_PAT.search(_text))
                _anchored = any(_resolves.get(_o) for _o in _HEX40.findall(_paragraph(_ln - 1)) if _o != _h)
                if _declared and _anchored:
                    _exempted.append({"line": _ln, "value": _h, "declared": True, "line_has_resolvable": True})
                    continue
                print("ABORT: coordinate %s (line %d) does not resolve in D:/moodle/CityNexus." % (_h, _ln))
                print("       the door already fetched all origin branches; if it still fails the coordinate is not in git;")
                print("       if it still fails, the coordinate is wrong - fix it, do not bypass.")
                print("       exemption exists but needs BOTH: the line declares it non-retrievable (%s=%s) "
                      "AND the line carries a resolvable coordinate (%s=%s)."
                      % ("declared", _declared, "anchored", _anchored))
                return 9
        if _exempted:
            print("COORD-BOLT: carried %d declared-non-retrievable value(s): %s"
                  % (len(_exempted), "; ".join("line %d %s" % (e["line"], e["value"][:12] + "…") for e in _exempted)))
            io.open(os.path.join(os.path.dirname(os.path.abspath(block_file)),
                                 "_non_retrievable_carried.json"), "w", encoding="utf-8",
                    newline="\n").write(json.dumps({"schema": "CNX_CMDR_DOOR_NON_RETRIEVABLE_V1",
                                                    "file": os.path.basename(block_file),
                                                    "carried": _exempted}, ensure_ascii=False, indent=1))

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
