"""Split the cross-line candidates into REAL cross-line ternaries and MERGE ARTIFACTS.

`multiline_blind_spot_r1.json` says 190 literals appear only when a statement is joined across its lines. That
number is not usable yet: joining two lines also lets the regex cut a template literal in half, and the half is
not a string anyone wrote -- e.g. line 241 of `app/V8Experience.tsx` is one backtick template
`` `The server refused this step (HTTP ${error.status}). Your trip is unchanged; …` `` and the joined reading
reports the fragment `). Your trip is unchanged; check the details and try again.` as if it were a new literal.

A candidate is REAL only when the captured text is a complete quoted token that lives on ONE source line, and
the operator that makes it a ternary branch sits on a DIFFERENT line. Everything else is an artifact of my own
join and is reported as such, with samples, so the residual ORD-0424 named gets a number instead of a mood.
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
QUOTE_TOKEN = re.compile(r"\"((?:[^\"\\\n]|\\.)*)\"|'((?:[^'\\\n]|\\.)*)'")


def load_r2():
    spec = importlib.util.spec_from_file_location("r2mod", R2)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def logical_lines(lines):
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


def complete_tokens(line):
    """Every fully-quoted string that lives on this single line, quote characters included."""
    return {m.group(0) for m in QUOTE_TOKEN.finditer(line)} | {
        m.group(0) for m in re.finditer(r"`[^`\n]*`", line)}


def classify(mod, lines, shape, captured, cap_line):
    """REAL if the captured text is one complete token on its own line and the operator is elsewhere."""
    toks = complete_tokens(lines[cap_line - 1])
    as_token = '"' + captured + '"' in toks or "'" + captured + "'" in toks or (
        "`" + captured + "`" in toks)
    if not as_token:
        return "artifact_fragment_not_a_whole_token"
    # the operator that made it a branch: does the same line carry it?
    rx = mod.TERN_TRUE if shape == "TERN_TRUE" else (
        mod.TERN_FALSE if shape == "TERN_FALSE" else mod.STATE_DEFAULT)
    for m in rx.finditer(lines[cap_line - 1]):
        if mod.unquote(mod.first_group(m) or "") == captured:
            return "already_seen_per_line"
    return "real_cross_line_branch"


def scan_file(mod, text):
    lines = text.split("\n")
    starts, per_line = [], set()
    for l in lines:
        starts.append(len("\n".join(lines[:len(starts)])) + 1 if False else 0)
    per_lit = {}
    for i, line in enumerate(lines):
        if line.strip().startswith(("//", "*", "/*")):
            continue
        for rx, shape in ((mod.TERN_TRUE, "TERN_TRUE"), (mod.TERN_FALSE, "TERN_FALSE"),
                          (mod.STATE_DEFAULT, "STATE_DEFAULT")):
            for m in rx.finditer(line):
                lit = mod.unquote(mod.first_group(m) or "")
                if mod.copy_candidate(lit, allow_single_label=False):
                    per_lit.setdefault((shape, lit), []).append(i + 1)
    joined = {}
    for block, start in logical_lines(lines):
        for rx, shape in ((mod.TERN_TRUE, "TERN_TRUE"), (mod.TERN_FALSE, "TERN_FALSE"),
                          (mod.STATE_DEFAULT, "STATE_DEFAULT")):
            for m in rx.finditer(block):
                lit = mod.unquote(mod.first_group(m) or "")
                if not mod.copy_candidate(lit, allow_single_label=False):
                    continue
                off = block.find(lit)
                cap_line = start + block[:max(off, 0)].count("\n") + 1
                joined.setdefault((shape, lit), cap_line)
    out = {"real": [], "artifact": [], "already": []}
    for (shape, lit), cap_line in joined.items():
        if (shape, lit) in per_lit:
            out["already"].append([shape, cap_line, lit])
            continue
        kind = classify(mod, lines, shape, lit, cap_line)
        if kind == "real_cross_line_branch":
            out["real"].append([shape, cap_line, lit])
        elif kind == "artifact_fragment_not_a_whole_token":
            out["artifact"].append([shape, cap_line, lit])
        else:
            out["already"].append([shape, cap_line, lit])
    return out, per_lit


def main():
    mod = load_r2()
    if not os.path.isdir(EXPORT):
        os.makedirs(EXPORT, exist_ok=True)
        r = subprocess.run("git -C %s -c http.proxy= -c https.proxy= archive %s frontend/src | tar -x -C %s"
                           % (REPO, TIP, EXPORT.replace("\\", "/")), shell=True, capture_output=True,
                           timeout=900)
        assert r.returncode == 0, r.stderr[:200]
    src = os.path.join(EXPORT, "frontend", "src")
    agg = {"real": [], "artifact": [], "already": []}
    n_files = 0
    for dirpath, _d, fnames in os.walk(src):
        for fn in sorted(fnames):
            if not fn.endswith((".tsx", ".ts")):
                continue
            p = os.path.join(dirpath, fn)
            rel = os.path.relpath(p, src).replace("\\", "/")
            out, per_lit = scan_file(mod, io.open(p, encoding="utf-8", errors="replace").read())
            n_files += 1
            for k in agg:
                agg[k] += [[rel] + list(x) for x in out[k]]
    res = {"tip": TIP, "files_scanned": n_files,
           "per_line_literal_count_total": None,
           "real_cross_line_branches": len(agg["real"]),
           "merge_artifacts": len(agg["artifact"]),
           "already_reported_per_line": len(agg["already"]),
           "real_samples": agg["real"][:20], "artifact_samples": agg["artifact"][:8]}
    io.open(os.path.join(WORK, "multiline_blind_spot_r2.json"), "w", encoding="utf-8").write(
        json.dumps(res, ensure_ascii=False, indent=1))
    print(json.dumps(res, ensure_ascii=False, indent=1)[:2800])
    return 0


if __name__ == "__main__":
    sys.exit(main())
