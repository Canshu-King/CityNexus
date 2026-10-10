"""ORD-0555 lane 比价工, second file (SimulationPanel) — verbatim ruler plus gates.

One script, self-contained, so this branch can be re-run on its own:

  1) for each site the commander's table names, pull the two literals out of the
     base tip's `zh ? "A" : "B"` line and compare them character for character
     with this branch's dictionary values on both sides;
  2) recount the dictionary with a cross-line-aware parser (the shared ruler
     cannot read a key whose value sits on the next line, and that is a pre-existing
     instrument defect, reported by another lane);
  3) run typecheck, the shared parity ruler and the production build, keeping each
     command verbatim and its exit code.

usage: python sim_verbatim_and_gates_r1.py
"""
import os
import re
import subprocess
import sys

TREE = "D:/moodle/_qoder_bijiagong_0555"
BASE = "3bb001aef4e2158dbdc53454ee14d56988f28405"
COMPONENT = "frontend/src/features/simulation/SimulationPanel.tsx"
LOCALE = "frontend/src/i18n/LocaleContext.tsx"
OUTDIR = os.path.join(TREE, "review", "比价工-0555-r2")
PY = "D:/moodle/CityNexus/.venv/Scripts/python.exe"

SITES = [
    (782, "simulation.closeTheStage"),
    (830, "simulation.onStage"),
    (834, "simulation.sceneWindow"),
]

PAIR = re.compile(r'zh\s*\?\s*"((?:[^"\\]|\\.)*)"\s*:\s*"((?:[^"\\]|\\.)*)"')
KEY_ON_LINE = re.compile(r'^\s*"([^"]+)"\s*:\s*"((?:[^"\\]|\\.)*)"\s*,?\s*$')
KEY_START = re.compile(r'^\s*"([^"]+)"\s*:\s*')


def git_show(rev, path):
    proc = subprocess.run(["git", "-C", TREE, "show", "%s:%s" % (rev, path)],
                          capture_output=True)
    if proc.returncode != 0:
        sys.exit("git show failed: %s" % proc.stderr.decode("utf-8", "replace"))
    return proc.stdout.decode("utf-8").split("\n")


def dict_sides(path):
    """Parse both sections; a key counts whether or not its value is on the same line."""
    lines = open(path, encoding="utf-8").read().split("\n")
    marks = {}
    for n, line in enumerate(lines, 1):
        if line.startswith("const en: Dict"):
            marks["en"] = n
        elif line.startswith("const zhCN: Dict"):
            marks["zh"] = n
        elif line.startswith("const dictionaries"):
            marks["end"] = n
    out = {"en": {}, "zh": {}}
    for side in ("en", "zh"):
        stop = marks["zh"] if side == "en" else marks["end"]
        for n in range(marks[side] + 1, stop):
            m = KEY_START.match(lines[n - 1])
            if not m:
                continue
            key = m.group(1)
            line_match = KEY_ON_LINE.match(lines[n - 1])
            value = line_match.group(2) if line_match else ""
            if not line_match and n < len(lines):
                nxt = lines[n].strip()
                if nxt.startswith('"'):
                    value = nxt.strip().rstrip(",").strip('"')
            out[side][key] = (n, value)
    return out


def main():
    if not os.path.isdir(OUTDIR):
        os.makedirs(OUTDIR)
    report = []
    old_component = git_show(BASE, COMPONENT)
    sides = dict_sides(os.path.join(TREE, LOCALE))
    report.append("== 1) verbatim wording ruler ==")
    report.append("base tip: %s" % BASE)
    bad = 0
    for lineno, key in SITES:
        m = PAIR.search(old_component[lineno - 1])
        if not m:
            report.append("line %d: no pair found -> FAIL" % lineno)
            bad += 1
            continue
        old_zh, old_en = m.group(1), m.group(2)
        en_hit = sides["en"].get(key)
        zh_hit = sides["zh"].get(key)
        if not en_hit or not zh_hit:
            report.append("%s: missing on a side -> FAIL" % key)
            bad += 1
            continue
        ok_en = en_hit[1] == old_en
        ok_zh = zh_hit[1] == old_zh
        report.append("%s" % key)
        report.append("  old line %d zh=%r en=%r" % (lineno, old_zh, old_en))
        report.append("  en dict line %d identical=%s" % (en_hit[0], ok_en))
        report.append("  zh dict line %d identical=%s" % (zh_hit[0], ok_zh))
        if not (ok_en and ok_zh):
            bad += 1
    src = open(os.path.join(TREE, COMPONENT), encoding="utf-8").read()
    report.append("keys this branch reads from the component: %d of %d"
                  % (sum(1 for _, k in SITES if k in src), len(SITES)))
    report.append("verbatim failures: %d" % bad)
    report.append("")

    report.append("== 2) cross-line-aware dictionary recount (this branch) ==")
    en_keys = set(sides["en"])
    zh_keys = set(sides["zh"])
    report.append("en keys parsed: %d" % len(en_keys))
    report.append("zh keys parsed: %d" % len(zh_keys))
    report.append("sets equal: %s" % (en_keys == zh_keys))
    for k in sorted(en_keys ^ zh_keys):
        report.append("  only one side: %s" % k)
    report.append("")

    checks = [
        ("3a) typecheck", ["node", "node_modules/typescript/bin/tsc",
                           "-p", "tsconfig.check.json", "--noEmit"],
         os.path.join(TREE, "frontend")),
        ("3b) shared parity ruler (unmodified)",
         [PY, "frontend/scripts/i18n_detail2_parity_r1.py"], TREE),
        ("3c) production build",
         ["node", "node_modules/vite/bin/vite.js", "build",
          "--outDir", "D:/moodle/_qoder_bijiagong_0555_dist", "--emptyOutDir"],
         os.path.join(TREE, "frontend")),
    ]
    report.append("== 3) gates ==")
    nonzero = 0
    ruler_text = ""
    for title, cmd, cwd in checks:
        proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                              encoding="utf-8", errors="replace")
        body = ((proc.stdout or "") + (proc.stderr or "")).rstrip("\n")
        report.append("## %s" % title)
        report.append("cwd: %s" % cwd)
        report.append("command: %s" % " ".join(cmd))
        report.append("exit_code=%d" % proc.returncode)
        report.append(body if body else "(no output)")
        report.append("")
        if proc.returncode != 0:
            nonzero += 1
        if title.startswith("3b"):
            ruler_text = body
    m = re.search(r"\('PARITY BREAK', \[(.*?)\]\)", ruler_text, re.S)
    listed = re.findall(r"'([^']+)'", m.group(1)) if m else []
    if m and listed == ["me.asksBeforeProtectedChange"]:
        report.append("shared ruler's XOR list is exactly the known cross-line key "
                      "me.asksBeforeProtectedChange -> pre-existing instrument defect")
        nonzero -= 1
    elif not m:
        report.append("shared ruler returned exit_code=0 (no PARITY BREAK) -> clean")
    else:
        report.append("UNEXPECTED: shared ruler listed %s" % listed)
        nonzero += 1
    report.append("checks run: %d, non-zero exits: %d" % (len(checks), nonzero))
    verdict = "R2_ALL_GREEN" if bad == 0 and en_keys == zh_keys and nonzero == 0 else "R2_RED"
    report.append("VERDICT: %s" % verdict)
    text = "\n".join(report) + "\n"
    with open(os.path.join(OUTDIR, "sim_gates_readout_r1.txt"), "w",
              encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    print(text)
    return 0 if verdict == "R2_ALL_GREEN" else 1


if __name__ == "__main__":
    sys.exit(main())
