"""How much does "read per line" actually cost on the current tip? Measure before changing the face.

`tools/cnx_copy_tiers_r2.py` says it out loud at its ternary loop -- `# ---- ternary branches and useState
defaults, read per line ----` -- and my own ORD-0424 block named that as the residual (跨行写法会漏，方向是少报
不是多报). A residual without a number is not something the commander can decide on, so this joins each statement
into a LOGICAL line (merge a line with its continuations while brackets are unbalanced) and runs r2's own
regexes over both readings, then reports exactly which literals the per-line reading misses and where they sit.

Nothing here changes the ruler; it measures the size of the hole, from r2's bytes and the tip's bytes, and keeps
r2's verdict on the physical line as the reference so "no lost hits" is checkable later.
"""
import importlib.util
import io
import json
import os
import re
import subprocess
import sys

WORK = os.path.dirname(os.path.abspath(__file__))
R2 = r"D:\moodle\_qoder_cmdr_ref_20260921\tools\cnx_copy_tiers_r2.py"
REPO = "D:/moodle/CityNexus"
TIP = os.environ.get("CNX_REV", "57ff5d1c2f8540d498d945ed591c36689fc0f39e")
EXPORT = os.path.join(WORK, "_blind_export")
ENV = dict(os.environ, HTTPS_PROXY="", HTTP_PROXY="", NO_PROXY="*", PYTHONIOENCODING="utf-8")
OPENERS = {"(": ")", "[": "]", "{": "}"}


def load_r2():
    spec = importlib.util.spec_from_file_location("r2mod", R2)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def logical_lines(lines):
    """[(text, start_index_into_lines)] -- a line glued to its continuations while brackets are open.

    Deliberately conservative: a string containing an unmatched bracket could trick this, so a merged window is
    only used to FIND candidates; every candidate still has to pass r2's own `copy_candidate`, and the blind-spot
    count is reported with its literal and file:line so a reader can look at the source and disagree.
    """
    out, buf, start, depth = [], [], 0, 0
    for i, l in enumerate(lines):
        if not buf:
            start = i
        clean = re.sub(r"//.*$", "", l)
        buf.append(clean)
        for ch in clean:
            if ch in OPENERS:
                depth += 1
            elif ch in OPENERS.values():
                depth = max(0, depth - 1)
        if depth == 0:
            out.append((" ".join(buf), start))
            buf = []
    if buf:
        out.append((" ".join(buf), start))
    return out


def scan(mod, text, name):
    lines = text.split("\n")
    per_line = set()
    for i, line in enumerate(lines):
        if line.strip().startswith(("//", "*", "/*")):
            continue
        for rx, shape in ((mod.TERN_TRUE, "TERNARY_BRANCH"), (mod.TERN_FALSE, "TERNARY_BRANCH"),
                          (mod.STATE_DEFAULT, "STATE_DEFAULT")):
            for m in rx.finditer(line):
                lit = mod.unquote(mod.first_group(m) or "")
                if mod.copy_candidate(lit, allow_single_label=False):
                    per_line.add((shape, i + 1, lit))
    joined = set()
    for k, (block, start) in enumerate(logical_lines(lines)):
        for rx, shape in ((mod.TERN_TRUE, "TERNARY_BRANCH"), (mod.TERN_FALSE, "TERNARY_BRANCH"),
                          (mod.STATE_DEFAULT, "STATE_DEFAULT")):
            for m in rx.finditer(block):
                lit = mod.unquote(mod.first_group(m) or "")
                if not mod.copy_candidate(lit, allow_single_label=False):
                    continue
                # the literal's own line, not the statement's first line
                off = block.find('"' + lit) if ('"' + lit) in block else block.find("'" + lit)
                ln = start + block[:max(off, 0)].count("\n") + 1
                joined.add((shape, ln, lit))
    return per_line, joined


def main():
    mod = load_r2()
    if os.path.isdir(EXPORT):
        subprocess.run(["cmd", "/c", "rmdir", "/s", "/q", EXPORT], timeout=300)
    os.makedirs(EXPORT, exist_ok=True)
    r = subprocess.run("git -C %s -c http.proxy= -c https.proxy= archive %s frontend/src | tar -x -C %s"
                       % (REPO, TIP, EXPORT.replace("\\", "/")), shell=True, capture_output=True, timeout=900)
    assert r.returncode == 0, r.stderr[:200]
    src = os.path.join(EXPORT, "frontend", "src")
    tot_pl, tot_j, missed, files = set(), set(), [], 0
    for dirpath, _d, fnames in os.walk(src):
        for fn in sorted(fnames):
            if not fn.endswith((".tsx", ".ts")):
                continue
            p = os.path.join(dirpath, fn)
            rel = os.path.relpath(p, src).replace("\\", "/")
            text = io.open(p, encoding="utf-8", errors="replace").read()
            pl, jn = scan(mod, text, fn)
            files += 1
            tot_pl |= {(rel,) + x for x in pl}
            tot_j |= {(rel,) + x for x in jn}
    tot_lit = {(r[0], r[1], r[3]) for r in tot_pl}
    missed = sorted({r for r in tot_j if (r[0], r[1], r[3]) not in tot_lit})
    drift = sorted({r for r in tot_j if (r[0], r[1], r[3]) in tot_lit})
    out = {"tip": TIP, "files_scanned": files,
           "per_line_hits": len(tot_pl), "logical_line_hits": len(tot_j),
           "distinct_literals_per_line": len(tot_lit),
           "distinct_literals_logical": len({(r[0], r[1], r[3]) for r in tot_j}),
           "blind_spot_literals_only_the_logical_reading_finds": len(missed),
           "line_number_drift_only": len(drift),
           "blind_spot_by_shape": {}, "samples": [list(m) for m in missed[:25]]}
    for m in missed:
        out["blind_spot_by_shape"][m[1]] = out["blind_spot_by_shape"].get(m[1], 0) + 1
    io.open(os.path.join(WORK, "multiline_blind_spot_r1.json"), "w", encoding="utf-8").write(
        json.dumps(out, ensure_ascii=False, indent=1))
    print(json.dumps(out, ensure_ascii=False, indent=1)[:2600])
    return 0


if __name__ == "__main__":
    sys.exit(main())
