"""Cut `tools/cnx_copy_tiers_multiline_fallback_r1.py` out of r2's published bytes, splicing two verbatim files.

The splice text lives in `snippet_helpers.txt` / `snippet_loop.txt` and is read as-is, because the previous
attempt embedded it in a string and lost the regex escapes to two layers of quoting -- the generated file then
parsed but meant something else, which is worse than not generating it. Both snippets are syntax-checked on
their own before anything is written, and r2's own bytes are only ever read.
"""
import ast
import io
import os

WORK = os.path.dirname(os.path.abspath(__file__))
TOOLS = r"D:\moodle\_qoder_cmdr_ref_20260921\tools"
SRC = os.path.join(TOOLS, "cnx_copy_tiers_r2.py")
DST = os.path.join(TOOLS, "cnx_copy_tiers_multiline_fallback_r1.py")
OLD_LOOP = "    # ---- ternary branches and useState defaults, read per line ----"


def read(p):
    return io.open(p, encoding="utf-8").read()


def main():
    helpers = read(os.path.join(WORK, "snippet_helpers.txt")).rstrip("\n")
    loop = read(os.path.join(WORK, "snippet_loop.txt")).rstrip("\n")
    base = read(SRC)

    ast.parse(helpers, "<helpers>")                      # top-level snippet
    ast.parse("def _probe(lines, push, starts, unquote, first_group, copy_candidate,\n"
              "          TERN_TRUE, TERN_FALSE, STATE_DEFAULT):\n" + loop + "\n", "<loop>")

    assert base.count(OLD_LOOP) == 1, "the r2 loop anchor moved; refuse to guess"
    i = base.index(OLD_LOOP)
    j = base.index("    return out", i)
    old = base[i:j]
    assert old.count("push(") == 1 and "TERN_TRUE" in old, old[:200]

    anchor = "def fallback_hits("
    assert base.count(anchor) == 1
    out = base.replace(anchor, helpers + "\n\n\n" + anchor, 1)
    out = out[:i] + loop + "\n" + out[j:]
    ast.parse(out)
    assert "def _stranded_operator(" in out and "bounded cross-line window" in out
    if os.path.exists(DST):
        os.remove(DST)                    # my own unpublished cut; the published r2 path is never written
    io.open(DST, "w", encoding="utf-8", newline="\n").write(out)
    import hashlib
    print("cut %s: %d bytes, blob %s; r2 read-only at %d bytes"
          % (os.path.basename(DST), len(out.encode("utf-8")),
             hashlib.sha1(b"blob %d" % len(out.encode("utf-8")) + chr(0).encode()
                          + out.encode("utf-8")).hexdigest(), len(base.encode("utf-8"))))
    return 0


if __name__ == "__main__":
    main()
