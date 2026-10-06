# -*- coding: utf-8 -*-
"""ORD-0574's sibling: the named survey answers rc 0 on an empty scan. Build r4 (new name) with a floor,
then measure the SAME fixture before and after, plus a positive control on a real tip.

  before  anchor_drift_survey_r3.py + empty tree sha -> rc 0, files 0        (the false green)
  after   anchor_drift_survey_r4.py + empty tree sha -> rc != 0, refuses by name
  control both on a real tip                          -> equal readings, rc 0  (the floor did not change work)

The r4 file is derived from r3's bytes with ONE exact replacement (found exactly once, else ABORT).
"""
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
MAIN = r"D:\moodle\CityNexus"
SRC = os.path.join(HERE, "anchor_drift_survey_r3.py")
OUT = os.path.join(HERE, "anchor_drift_survey_r4.py")
EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"


def clean_env():
    e = dict(os.environ)
    for k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "ALL_PROXY", "all_proxy"):
        e.pop(k, None)
    e["PYTHONIOENCODING"] = "utf-8"
    return e


def run(argv, cwd=None, timeout=900):
    p = subprocess.run(argv, capture_output=True, env=clean_env(), cwd=cwd, timeout=timeout)
    return p.returncode, p.stdout.decode("utf-8", "replace"), p.stderr.decode("utf-8", "replace")


def git_blob(data):
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def main():
    src = io.open(SRC, "rb").read()
    src_blob = git_blob(src)
    text = src.decode("utf-8")
    if "\r\n" in text:
        raise SystemExit("ABORT: CRLF in the source - the write would flip endings")

    anchor = ('    files = [f for f in git("ls-tree", "-r", "--name-only", tip, PREFIX).splitlines()\n'
              '             if f.endswith(".py")]\n')
    floor = (anchor +
             '    # ORD-0574, the same family as the ledger mirror self-check: an empty scan is not a clean scan.\n'
             '    # Two sides being equally absent is equality, not "no drift" - measured on r3, an empty tree in\n'
             '    # produced rc 0 with "files": 0 and "sites": 0, which reads as green to any caller.\n'
             '    if not files:\n'
             '        raise SystemExit("ABORT: no .py files under %s at tip %s - refusing to call an empty "\n'
             '                         "survey a clean one" % (PREFIX, tip))\n')
    n = text.count(anchor)
    if n != 1:
        raise SystemExit("ABORT: anchor found %d times (need exactly 1)" % n)
    new = text.replace(anchor, floor)
    import ast
    try:
        ast.parse(new)
    except SyntaxError as e:
        raise SystemExit("ABORT: r4 does not parse: %s" % e)
    data = new.encode("utf-8")
    io.open(OUT, "wb").write(data)

    R = {"r3": {"file": os.path.basename(SRC), "bytes": len(src), "blob": src_blob},
         "r4": {"file": os.path.basename(OUT), "bytes": len(data), "blob": git_blob(data), "edits": 1}}

    tmp = tempfile.mkdtemp(prefix="cnx_survey_")
    try:
        for f in (SRC, OUT):
            io.open(os.path.join(tmp, os.path.basename(f)), "wb").write(io.open(f, "rb").read())

        def leg(name, tip, cwd=tmp):
            rc, out, err = run([sys.executable, os.path.join(cwd, name), tip], cwd=cwd)
            files = re.search(r'"files":\s*(\d+)', out)
            sites = re.search(r'"sites":\s*(\d+)', out)
            return {"script": name, "tip": tip, "rc": rc,
                    "files": int(files.group(1)) if files else None,
                    "sites": int(sites.group(1)) if sites else None,
                    "stdout_head": out.strip()[:140], "stderr_head": err.strip()[-200:]}

        empty_before = leg("anchor_drift_survey_r3.py", EMPTY_TREE)
        empty_after = leg("anchor_drift_survey_r4.py", EMPTY_TREE)
        R["empty_before"] = empty_before
        R["empty_after"] = empty_after
        if empty_before["rc"] != 0:
            raise SystemExit("ABORT: r3 no longer answers 0 on the empty tree - the premise changed")
        if empty_after["rc"] == 0:
            raise SystemExit("ABORT: r4 still answers 0 on the empty tree - the floor does not bite")
        if "ABORT" not in empty_after["stderr_head"]:
            raise SystemExit("ABORT: r4 refused but without a named refusal")

        rc, out, err = run(["git", "-C", MAIN, "ls-remote", "--refs", "origin",
                            "refs/heads/mirror/integration-frontend-apple-pass1"])
        tip = out.split()[0]
        R["real_tip"] = tip
        real_before = leg("anchor_drift_survey_r3.py", tip)
        real_after = leg("anchor_drift_survey_r4.py", tip)
        R["real_before"] = real_before
        R["real_after"] = real_after
        if real_before["rc"] != 0 or real_after["rc"] != 0:
            raise SystemExit("ABORT: the positive control did not run clean on the real tip")
        if real_before["files"] != real_after["files"] or real_before["sites"] != real_after["sites"]:
            raise SystemExit("ABORT: r4 changed the reading on a real tip - the floor is not behaviour-neutral")
        if not real_after["files"]:
            raise SystemExit("ABORT: the real tip yields 0 files, so the control proves nothing")
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)
        R["temp_removed"] = not os.path.exists(tmp)

    R["floor_bites"] = (R["empty_after"]["rc"] != 0 and R["empty_before"]["rc"] == 0)
    R["control_unchanged"] = (R["real_before"]["files"] == R["real_after"]["files"] and
                              R["real_before"]["sites"] == R["real_after"]["sites"])
    io.open(os.path.join(HERE, "survey_r4_build_r1.json"), "w", encoding="utf-8", newline="\n").write(
        json.dumps(R, ensure_ascii=False, indent=1))
    print(json.dumps({k: R[k] for k in ("r3", "r4", "real_tip", "empty_before", "empty_after",
                                        "real_before", "real_after", "floor_bites", "control_unchanged",
                                        "temp_removed")}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
