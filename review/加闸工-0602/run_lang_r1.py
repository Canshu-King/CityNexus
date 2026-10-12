# -*- coding: utf-8 -*-
"""Run the commander's own dictionary language ruler twice: on the authoritative tip and on my
candidate.  The ruler source is used verbatim except for two substitutions, both printed here.
"""
import io
import re
import sys

RULER = "D:/moodle/_qoder_cmdr_ref_20260921/live_checks/_cmdr_dict_copy_lang_check_r1.py"
CAND = "5ed85afea5d86b71be117a6dba80c8f0e24020e9"

HEAD = (
    '    rc, tip = sh(["git", "-C", AUTH, "ls-remote", "origin", LINE])\n'
    "    if rc:\n"
    '        print("ABORT ls-remote rc=%s" % rc)\n'
    "        return 3\n"
    '    tip = tip.split("\\t")[0].strip()\n'
)


def run(label, src):
    print("\n" + "=" * 70)
    print("== %s" % label)
    print("=" * 70)
    ns = {"__name__": "__main__", "__file__": RULER}
    try:
        exec(compile(src, RULER, "exec"), ns)
    except SystemExit as exc:
        print("[ruler exit code = %s]" % exc.code)


def main():
    src = io.open(RULER, encoding="utf-8").read()
    sha = sys.argv[1]
    tag = sys.argv[2]
    cand_src = src.replace(HEAD, '    tip = "%s"\n' % sha, 1)
    if cand_src == src:
        print("ABORT 取尖那一段没在尺的原文里逐字命中，不改写、不猜")
        return 1
    cand_src2 = cand_src.replace("refs/tmp/cmdr_copylang", "refs/tmp/%s" % tag)
    n = len(re.findall(r"refs/tmp/%s" % tag, cand_src2))
    print("\n[substitutions: 1 处取尖改为四十位 %s，%d 处临时 ref 改名为 %s（避开上一趟占用的同名 ref）]"
          % (sha[:12], n, tag))
    run("%s via %s, same ruler source" % (sha[:12], tag), cand_src2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
