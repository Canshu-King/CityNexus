# -*- coding: utf-8 -*-
"""Replay the commander's dictionary language ruler against a candidate generation.

Two supply legs are stubbed: `ls-remote` answers the candidate sha, and the `fetch` leg is a no-op
because the candidate was placed on the ruler's own tmp ref (`refs/tmp/cmdr_copylang`) beforehand.
The dictionary read (`git show refs/tmp/cmdr_copylang:frontend/src/i18n/LocaleContext.tsx`) and every
judgement line (ONE_SIDED / EN_SIDE_HAS_CJK / SAME_TEXT / PLACEHOLDER DRIFT / ZH_SIDE_LATIN_ONLY)
are the ruler's own bytes, unchanged.
"""
import io
import os
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = r"D:/moodle/_qoder_cmdr_ref_20260921/live_checks"
SRC = os.path.join(HERE, "_cmdr_dict_copy_lang_check_r1.py")
CAND = sys.argv[1]
REF = "refs/heads/mirror/integration-frontend-apple-pass1"

g = {}
code = compile(io.open(SRC, encoding="utf-8").read(), SRC, "exec")
exec(code, g)

real_sh = g["sh"]


def shim(args):
    joined = " ".join(args)
    if "ls-remote" in joined:
        return 0, "%s\t%s\n" % (CAND, REF)
    if "fetch" in joined:
        # The candidate generation is placed on the ruler's own tmp ref before this run (see the
        # evidence file), so the ruler's `git show refs/tmp/cmdr_copylang:<dict>` leg reads for real.
        return 0, ""
    return real_sh(args)


g["sh"] = shim
rc = g["main"]()
print("LANG_CHECK_RC %s" % rc)
sys.exit(rc)
