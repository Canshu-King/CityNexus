# -*- coding: utf-8 -*-
"""Replay the commander's inline-visible-CJK ruler against one named generation.

The ruler derives its subject from one `ls-remote` call; this stubs that single leg so the answer is the
ref given on the command line.  Everything after it -- the `git grep -l -P` file list, the per-file
`git show`, comment stripping, the literal/JSX matchers and the paired-copy-table exclusion -- runs as
the commander's own bytes.
"""
import io
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = r"D:/moodle/_qoder_cmdr_ref_20260921/live_checks"
SRC = os.path.join(HERE, "_cmdr_inline_literal_cjk_r2.py")
LINE = "refs/heads/mirror/integration-frontend-apple-pass1"
want = sys.argv[1]

g = {}
exec(compile(io.open(SRC, encoding="utf-8").read(), SRC, "exec"), g)
real_sh = g["sh"]


def shim(args, cwd):
    if "ls-remote" in " ".join(args):
        return 0, "%s\t%s\n" % (want, LINE)
    return real_sh(args, cwd)


g["sh"] = shim
sys.exit(g["main"]())
