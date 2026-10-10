"""ORD-0557 lane duibiaogong: the three gates plus the verbatim-move proof, one runner.

Run it in any tree:  python review/duibiaogong-0557/run_gates_r1.py <stage>
Stage `control` is meant for a tip tree that carries none of my bytes; there the verbatim arm
reports ABSENT_ON_PURPOSE instead of comparing.
Every command runs without a shell pipe so the recorded exit code belongs to that command.
"""

import datetime
import os
import re
import subprocess
import sys

STAGE = sys.argv[1]
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
FRONTEND = os.path.join(ROOT, "frontend")
OUT = os.path.join(ROOT, "review", "duibiaogong-0557", "readout_%s.txt" % STAGE)
PY = r"D:\moodle\CityNexus\.venv\Scripts\python.exe"
TIP = "996f1b7588580a14fbbdec5301a6e4a7b70c93e4"
KEY = "discovery.technicalDetail"
PANEL = "frontend/src/features/discovery/RealCityDiscoveryPanel.tsx"
DICT = "frontend/src/i18n/LocaleContext.tsx"
DIST = r"D:/moodle/_qoder_duibiaogong_0557_dist"


def sh(argv, cwd=None):
    p = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def block(path, start_marker, stop_marker):
    text = open(path, encoding="utf-8").read()
    a = text.index(start_marker)
    b = text.index(stop_marker, a)
    return text[a:b]


def verbatim_arm():
    lines = ["### arm: the two strings moved without being rewritten"]
    if STAGE == "control":
        lines.append("  skipped: this tree carries none of the lane's bytes")
        return "\n".join(lines) + "\n"
    rc, blob = sh(["git", "-C", ROOT, "show", "%s:%s" % (TIP, PANEL)])
    tip_line = blob.splitlines()[406]
    m = re.search(r'locale\.startsWith\("zh"\)\s*\?\s*"([^"]*)"\s*:\s*"([^"]*)"', tip_line)
    lines.append("  tip line 407 read from `git show %s:%s` rc=%d" % (TIP[:9], PANEL, rc))
    lines.append("  tip text = %r" % (tip_line.strip(),))
    if not m:
        lines.append("  VERDICT = SHAPE_NOT_FOUND (the ruler refuses, it does not guess)")
        return "\n".join(lines) + "\n"
    old_zh, old_en = m.group(1), m.group(2)
    en = dict(re.findall(r'^\s{2}"([^"]+)": "([^"]*)",$', block(os.path.join(ROOT, DICT), "const en: Dict = {", "const zhCN: Dict = {"), re.M))
    zhv = dict(re.findall(r'^\s{2}"([^"]+)": "([^"]*)",$', block(os.path.join(ROOT, DICT), "const zhCN: Dict = {", "const dictionaries"), re.M))
    new_en, new_zh = en.get(KEY), zhv.get(KEY)
    lines.append("  en side identical=%s  tip=%r  dict=%r" % (new_en == old_en, old_en, new_en))
    lines.append("  zh side identical=%s  tip=%r  dict=%r" % (new_zh == old_zh, old_zh, new_zh))
    verdict = bool(new_en == old_en and new_zh == old_zh)
    # negative control: the arm must be able to see a wrong value
    saved = en[KEY]
    en[KEY] = saved + " "
    corrupt = not (en[KEY] == old_en and new_zh == old_zh)
    en[KEY] = saved
    restored = en[KEY] == old_en and new_zh == old_zh
    lines.append("  negative_control trailing_space -> arm red = %s" % corrupt)
    lines.append("  negative_control restored       -> arm green = %s" % restored)
    lines.append("  VERDICT = %s" % ("VERBATIM_MOVE_PROVED" if (verdict and corrupt and restored) else "REFUSED"))
    return "\n".join(lines) + "\n"


def gate(label, cwd, argv, tail=10):
    rc, body = sh(argv, cwd=cwd)
    lines = [ln for ln in body.splitlines() if ln.strip() != ""]
    return "\n".join(
        ["### %s" % label, "cwd = %s" % cwd.replace("\\", "/"), "cmd = %s" % " ".join(argv),
         "started_local = %s" % datetime.datetime.now().strftime("%H:%M:%S"),
         "exit_code = %d" % rc, "nonempty_lines = %d" % len(lines), "tail:"]
        + ["    " + ln for ln in lines[-tail:]]
    ) + "\n"


def main():
    head = sh(["git", "-C", ROOT, "rev-parse", "HEAD"])[1].strip()
    dirty = sh(["git", "-C", ROOT, "status", "--porcelain"])[1].count("\n")
    parts = [
        "stage = %s" % STAGE,
        "tree = %s" % ROOT.replace("\\", "/"),
        "tree_head = %s" % head,
        "dirty_files = %d" % dirty,
        "python = %s" % PY,
        "",
        verbatim_arm(),
        gate("gate 1 i18n parity (shared ruler)", ROOT, [PY, os.path.join("frontend", "scripts", "i18n_detail2_parity_r1.py")]),
        gate("gate 2 typecheck (package.json line 8 shape)", FRONTEND, ["node", "node_modules/typescript/bin/tsc", "-p", "tsconfig.typecheck.json", "--noEmit"]),
        gate("gate 3 production build", FRONTEND, ["node", "node_modules/vite/bin/vite.js", "build", "--outDir", DIST, "--emptyOutDir"], 6),
    ]
    text = "\n".join(parts)
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    print(text)


if __name__ == "__main__":
    main()
