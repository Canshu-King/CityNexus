# -*- coding: utf-8 -*-
"""ROUTE-STUB gap ruler (lane yanlugong, ORD-0559-b step one).

Reads the CURRENT tip only (never the CN report's generation).

  1. every @app.<method>("<path>") declaration in backend/app/main.py, including decorators
     whose path sits on the next line; the reported line is the decorator's own line. Paths
     are stored with the `/api/v1` prefix stripped, the way the CN table writes them.
  2. every backend test file at that same tip. A route is referenced when its path appears
     either literally in a line, or as the value of a module-level constant - including the
     derived form `X_PATH = BASE_PATH + "/tail"` that lanes use. `/api/v1` is optional and a
     `{param}` segment matches the literal braces in any spelling or one path segment.
     States, strongest first:
       RESPONSE_ASSERTED      - the function that uses the path or constant both touches the
                                response (`status_code` or `.json(` anywhere in it) and holds an
                                `assert` somewhere in it - judged per function, because lanes
                                split `body = answer.json()` from the assert over two lines
       ASSERT_NOT_ON_RESPONSE - a test function uses it and asserts something else only
       CALL_ONLY              - referenced inside a test function with no assert, or only at
                                module level without any use in an asserting function
       NONE                   - no test file says the path
  3. the CN table's rows, to report how far that generation's line numbers drifted.

Refuses to print a denominator it did not measure: every count travels with the number of
declarations and test files actually read.
"""

from __future__ import annotations

import collections
import json
import re
import subprocess
import sys

REPO = "D:/moodle/CityNexus"
CN_TABLE = "D:/moodle/_cn11_route559b_1800.txt"
HERE = "D:/moodle/_qoder_yanlugong_0559b/review/验路工-0559b"
OUT_TSV = HERE + "/ROUTE_STUB_GAP_r1.tsv"
OUT_JSON = HERE + "/ROUTE_STUB_GAP_r1.json"

DEC = re.compile(r'@app\.(get|post|put|patch|delete)\(\s*"(/[^"]*)"')
TESTFN = re.compile(r"^def ([A-Za-z_][A-Za-z0-9_]*)")
ASSERT = re.compile(r"\bassert\b")
ON_RESPONSE = re.compile(r"status_code|\.json\(")
CONST = re.compile(r"^([A-Z_][A-Z0-9_]*)\s*(?::[^=]*)?=\s*(.*)$")
DERIVED = re.compile(r"^([A-Z_][A-Z0-9_]*)\s*\+\s*[\"']([^\"']*)[\"']$")
LITERAL = re.compile(r"[\"'](/[^\"]*)[\"']")


def git(*args):
    p = subprocess.run(["git", "-C", REPO, *args], stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT)
    if p.returncode != 0:
        raise SystemExit("GIT_FAIL %s :: %s" % (list(args), p.stdout.decode("utf-8", "replace")[:300]))
    return p.stdout.decode("utf-8", "replace")


def strip_prefix(path):
    return path[len("/api/v1"):] if path.startswith("/api/v1") else path


def path_regex(path):
    parts = ["(?:/api/v1)?"]
    for chunk in re.split(r"(\{[^}]+\})", path):
        if not chunk:
            continue
        if chunk.startswith("{") and chunk.endswith("}"):
            parts.append(r"(?:\{[^}]*\}|[^/\"'`]+)")
        else:
            parts.append(re.escape(chunk))
    return re.compile("".join(parts) + r"(?![A-Za-z0-9_/])")


def routes_of(text):
    out, seen = [], set()
    for m in DEC.finditer(text):
        line = text[: m.start()].count("\n") + 1
        key = (m.group(1).upper(), strip_prefix(m.group(2)))
        if key in seen:
            continue
        seen.add(key)
        out.append((key[0], key[1], line))
    return out


def read_tests(tip, files):
    index = {}
    for f in files:
        rows, current = [], "<module>"
        for n, line in enumerate(git("show", "%s:%s" % (tip, f)).splitlines(), 1):
            m = TESTFN.match(line)
            if m:
                current = m.group(1)
            rows.append((n, current, line))
        bodies, asserted_fns, consts = {}, set(), {}
        touches_response, asserted_seen = set(), set()
        for n, fn, line in rows:
            if fn != "<module>":
                bodies[fn] = bodies.get(fn, "") + line + "\n"
                if ASSERT.search(line):
                    asserted_seen.add(fn)
                if ON_RESPONSE.search(line):
                    touches_response.add(fn)
            if line[:1].isspace():
                continue
            m = CONST.match(line)
            if not m:
                continue
            name, rhs = m.group(1), m.group(2).strip()
            lit = LITERAL.findall(rhs)
            if len(lit) == 1 and len(rhs) == len(lit[0]) + 2:
                consts[name] = strip_prefix(lit[0])
            else:
                d = DERIVED.match(rhs)
                if d and d.group(1) in consts:
                    consts[name] = consts[d.group(1)] + d.group(2)
        # a function counts as asserting on the response when it both reads the response
        # (`status_code` / `.json(`) somewhere inside it and holds an assert somewhere inside it
        asserted_fns = asserted_seen
        response_fns = (touches_response & asserted_seen) - {"<module>"}
        index[f] = (rows, response_fns, asserted_fns, bodies, consts)
    return index


def classify(info):
    if not info["hits"]:
        return "NONE"
    vias = {h["via"] for h in info["hits"]}
    if "response_assert" in vias:
        return "RESPONSE_ASSERTED"
    if "assert_other" in vias:
        return "ASSERT_NOT_ON_RESPONSE"
    return "CALL_ONLY"


def main():
    tip = sys.argv[1]
    if git("cat-file", "-t", tip).strip() != "commit":
        raise SystemExit("TIP_NOT_A_COMMIT")

    routes = routes_of(git("show", "%s:backend/app/main.py" % tip))
    # core.quotepath is on by default: a lane whose file name is not ASCII would come back
    # quoted, and a `.py` suffix test would then silently skip the whole file (measured)
    names = git("-c", "core.quotepath=off", "ls-tree", "-r", "--name-only", tip,
                "--", "backend/tests").splitlines()
    files = [n for n in names if n.endswith(".py")]
    if not routes or not files:
        raise SystemExit("EMPTY_READ routes=%d files=%d" % (len(routes), len(files)))

    index = read_tests(tip, files)
    patterns = {(m, p): path_regex(p) for m, p, ln in routes}
    per_route = {(m, p): {"declared_line": ln, "hits": []} for m, p, ln in routes}

    for f in files:
        rows, response_fns, asserted_fns, bodies, consts = index[f]
        # every name in this file that carries the path: module constants and the functions
        # whose own body says it
        carriers = collections.defaultdict(set)
        for name, value in consts.items():
            for key, pat in patterns.items():
                if pat.search(value):
                    carriers[key].add(name)
        for fn, body in bodies.items():
            for key, pat in patterns.items():
                if pat.search(body):
                    carriers[key].add(fn)

        def reach(key):
            """Transitive closure: constant -> helper -> test. A lane writes the path once
            in `X_PATH`, calls it inside `_x()`, and asserts on `_x().status_code` in the test."""
            names = set(carriers[key])
            grew = True
            while grew:
                grew = False
                for fn, body in bodies.items():
                    if fn in names:
                        continue
                    if any(re.search(r"\b%s\b" % re.escape(n), body) for n in names):
                        names.add(fn)
                        grew = True
            return names

        for key in per_route:
            if not carriers[key]:
                # a module-level mention that no constant and no function carries is still a
                # reference, and the table has to say so rather than claim the door is unsaid
                for n, fn, text in rows:
                    if fn == "<module>" and patterns[key].search(text):
                        per_route[key]["hits"].append(
                            {"file": f, "line": n, "function": "<module>", "via": "reference_only"})
                        break
                continue
            names = reach(key)
            hit_response = sorted(names & response_fns)
            hit_assert = sorted(names & asserted_fns)
            first_line = next((n for n, fn, text in rows
                               if fn == "<module>" and any(pat.search(text)
                                                           for pat in [patterns[key]])), None)
            via = ("response_assert" if hit_response
                   else "assert_other" if hit_assert else "reference_only")
            per_route[key]["hits"].append({
                "file": f,
                "line": first_line or 0,
                "function": hit_response[0] if hit_response else (
                    hit_assert[0] if hit_assert else "<chain>"),
                "via": via,
                "chain": sorted(names),
            })

    state = {key: classify(info) for key, info in per_route.items()}
    counts = collections.Counter(state.values())

    rows_out = []
    for (method, path), info in sorted(per_route.items(), key=lambda x: x[1]["declared_line"]):
        hits = info["hits"]
        order = ["response_assert", "assert_other", "reference_only"]
        picked = next((h for v in order for h in hits if h["via"] == v), None)
        evidence = "NONE" if picked is None else "%s:%d#%s#%s" % (
            picked["file"], picked["line"], picked["function"], picked["via"])
        rows_out.append("backend/app/main.py:%d\t%s\t%s\t%s\t%s" % (
            info["declared_line"], method, path, state[(method, path)], evidence))

    with open(OUT_TSV, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("# ROUTE-STUB-GAP tip=%s declared=%d response_asserted=%d assert_not_on_response=%d call_only=%d none=%d test_files=%d\n" % (
            tip, len(routes), counts["RESPONSE_ASSERTED"], counts["ASSERT_NOT_ON_RESPONSE"],
            counts["CALL_ONLY"], counts["NONE"], len(files)))
        fh.write("# declared_coordinate\tMETHOD\tPATH\tSTATE\tTEST_EVIDENCE\n")
        fh.write("\n".join(rows_out) + "\n")

    cn = []
    for line in open(CN_TABLE, encoding="utf-8").read().splitlines():
        m = re.match(r"^backend/app/main\.py:(\d+) \| (GET|POST|PUT|PATCH|DELETE) \| (\S+)$", line)
        if m:
            cn.append((m.group(2), m.group(3), int(m.group(1))))
    cur = {(m, p): ln for m, p, ln in routes}
    same = sum(1 for m, p, ln in cn if cur.get((m, p)) == ln)

    gap = [k for k in state if state[k] != "RESPONSE_ASSERTED"]
    fam = collections.Counter()
    for method, path in gap:
        segs = [s for s in path.split("/") if s]
        if segs and segs[0] == "journeys" and len(segs) > 2:
            fam["journeys/" + segs[2]] += 1
        else:
            fam[segs[0] if segs else path] += 1

    summary = {
        "tip": tip,
        "declared": len(routes),
        "response_asserted": counts["RESPONSE_ASSERTED"],
        "assert_not_on_response": counts["ASSERT_NOT_ON_RESPONSE"],
        "call_only": counts["CALL_ONLY"],
        "none": counts["NONE"],
        "gap_total": len(gap),
        "test_files_read": len(files),
        "cn_rows_parsed": len(cn),
        "cn_row_line_matches_current_tip": same,
        "tsv": OUT_TSV,
        "gap_by_first_segment": sorted(fam.items(), key=lambda x: -x[1]),
    }
    with open(OUT_JSON, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=1)
    print(json.dumps(summary, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
