# -*- coding: utf-8 -*-
"""Live counter-example for ②: run a real publisher leg with an EMPTY file list and see what it says.

The static scan put 19 write-path entries on one shape - `return 0 if (all(r["byte_equal"] for r in rows) and
doc["all_local_byte_equal"])`. `all([])` is True and `all([]) ` vacuity is exactly how an empty publication
self-reports success. Reading a syntax tree is not proof, so this takes tonight's own publisher, gives it an
empty list in a throwaway copy, and asks it out loud whether it is green.

Safety: the copy writes its receipt to a temp path and its file list is emptied, so it publishes nothing, pushes
nothing, and re-hashes nothing except read-only `ls-tree`/`fetch` of the evidence branch. The real publisher and
every shelf path are untouched. A second copy, identical except for one added floor line, must refuse - that is
the fix shape being demonstrated, not asserted.
"""
import io
import json
import os
import re
import subprocess
import sys
import tempfile

WORK = r"D:\moodle\_qoder_lane_S4_0926\work\ord_anchors"
SRC = "publish_hook_r1.py"
ENV = dict(os.environ, HTTPS_PROXY="", HTTP_PROXY="", NO_PROXY="*", PYTHONIOENCODING="utf-8")
for _k in ("http_proxy", "https_proxy"):
    ENV[_k] = ""


def variant(src, floor=False):
    s = io.open(os.path.join(WORK, src), encoding="utf-8").read()
    i = s.index("NEW = [")
    j = s.index("]", i) + 1
    s = s[:i] + "NEW = []" + s[j:]
    k = s.index('RECEIPT = "')
    m = s.index('"', k + 11)
    s = s[:k] + 'RECEIPT = r"%s"' % os.path.join(tempfile.gettempdir(),
                                                 "cnx_empty_publisher_receipt%s.json" % ("_floored" if floor else "")) + s[m + 1:]
    if floor:
        anchor = "    rows = [put(n) for n in NEW]\n"
        assert s.count(anchor) == 1, "the publisher's body moved; the fix line has nowhere to go"
        s = s.replace(anchor, anchor + '    if not rows:\n'
                                   '        print(json.dumps({"refused": "empty file list - nothing was '
                                   'asked to publish, which is not a pass"}))\n'
                                   '        return 5\n')
    ast = compile(s, "<variant>", "exec")
    return s, ast


def run(tag, code):
    path = os.path.join(tempfile.gettempdir(), "cnx_empty_publisher_%s.py" % tag)
    io.open(path, "w", encoding="utf-8", newline="\n").write(code)
    r = subprocess.run([sys.executable, path], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env=ENV, timeout=1800, cwd=WORK)
    out = ((r.stdout or "") + (r.stderr or "")).strip().splitlines()
    os.remove(path)
    return {"tag": tag, "rc": r.returncode, "line": (out[-1] if out else "")[:300],
            "claims_green": r.returncode == 0}


def main():
    bad_src, _ = variant(SRC, floor=False)
    good_src, _ = variant(SRC, floor=True)
    bad = run("as_is", bad_src)
    fixed = run("floored", good_src)
    doc = {"as_is": bad, "with_floor": fixed,
           "reading": "as_is rc %d means an empty publication calls itself green; with_floor rc %d means one "
                      "floor line turns the same code into a refusal" % (bad["rc"], fixed["rc"]),
           "arms_pass": bool(bad["rc"] == 0 and fixed["rc"] != 0)}
    n = os.path.join(WORK, "empty_publisher_counterexample_r1.json")
    io.open(n, "w", encoding="utf-8").write(json.dumps(doc, ensure_ascii=False, indent=1))
    print(json.dumps(doc, ensure_ascii=False))
    return 0 if doc["arms_pass"] else 7


raise SystemExit(main())
