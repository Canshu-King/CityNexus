# -*- coding: utf-8 -*-
"""② first cell: scan this lane's own writers for verdicts that can pass on an empty denominator.

v1 used four regexes and reported 22 files; two of the shapes that actually bit me tonight were outside them,
and its "is there a floor guard" test was so loose that it cleared all 110 hits it found - a ruler that can
never produce a work list is the very defect this tool is meant to hunt. So v2 walks the syntax tree and defines
a floor narrowly: some statement in the same function must **refuse** when the collection is empty
(`assert X`, `if not X: raise|return <non-zero>`, `len(X) == 0 -> raise`, `X == 0 -> refuse`).

Shapes recorded (each with `floor_guard` computed the strict way):
  vacuous_all          `all(g for … in X)` / `any(...)` inside a returned or asserted truth value
  emptiness_passes     `if not X [or …]: return 0 | continue | pass`
  empty_eq_pass        `if X == {} / [] / set(): return <success>`
  ternary_no_floor     `return 0 if <cond containing all(...)> else <code>`
  compare_only_verdict a guard whose test is `X == Y` / `sorted(X) != sorted(Y)` - two collections compared
                       against each other, which an empty pair satisfies trivially. This is the shape that let
                       an `git add` that staged nothing through a "nothing foreign is staged" check tonight.

Self-proof (`--self-test`) writes three fixtures: one per-shape violator that MUST be reported without a floor,
one fully-guarded file that MUST be clean, and one empty-input file that MUST yield at least one hit - so the
scanner cannot pass by finding nothing. If any of the three misbehaves the exit code is 7 and no claim is made.
"""
import argparse
import ast
import io
import json
import os
import re
import tempfile

SHAPES = ("vacuous_all", "emptiness_passes", "empty_eq_pass", "ternary_no_floor", "compare_only_verdict")


def name_of(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Subscript):
        return name_of(node.value)
    if isinstance(node, ast.Call):
        return name_of(node.func)
    return None


def comp_iterables(node):
    out = []
    for g in ast.walk(node):
        if isinstance(g, (ast.ListComp, ast.GeneratorExp, ast.SetComp, ast.DictComp)):
            for c in g.generators:
                n = name_of(c.iter)
                if n:
                    out.append(n)
    return out


def refuses_when_empty(fn_lines, coll):
    """A floor exists only if the function itself refuses (raise / non-zero return / assert) on an empty coll."""
    c = re.escape(coll)
    pats = [
        (r"^\s*assert\s+%s\b(?! )" % c, None),                       # `assert staged` / `assert rows and …`
        (r"^\s*assert\s+len\(\s*%s\s*\)\s*(?:>|>=)\s*0" % c, None),
        (r"if\s+not\s+%s\b" % c, r"(raise|SystemExit|return\s+[1-9]|abort)"),
        (r"len\(\s*%s\s*\)\s*==\s*0" % c, r"(raise|SystemExit|return\s+[1-9]|abort)"),
        (r"%s\s*==\s*0\b" % c, r"(raise|SystemExit|return\s+[1-9]|abort)"),
        (r"not\s+any\(" , None),
    ]
    for i, line in enumerate(fn_lines):
        for head, tail in pats:
            if re.search(head, line):
                window = "\n".join(fn_lines[i:i + 4])
                if tail is None or re.search(tail, window):
                    return True
    return False


def scan_file(path):
    try:
        text = io.open(path, encoding="utf-8", errors="replace").read()
        tree = ast.parse(text)
    except (SyntaxError, ValueError):
        return []
    lines = text.split("\n")
    funcs = [(n, n.lineno, n.end_lineno) for n in ast.walk(tree)
             if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and getattr(n, "end_lineno", None)]

    def fn_lines(lineno):
        best = None
        for node, a, b in funcs:
            if a <= lineno <= b:
                best = (node, a, b)
        if best:
            return lines[best[1] - 1:best[2]]
        return lines

    hits = []

    def add(shape, node, colls, extra=None):
        colls = [c for c in colls if c]
        if not colls:
            return
        body = fn_lines(node.lineno)
        # a verdict computed by COMPARING two collections cannot pass on nothing if either side is required to be
        # non-empty and refused otherwise - demanding a floor on both sides manufactured a work item out of code
        # that was already guarded, which is as bad as missing one
        strict = shape in ("compare_only_verdict", "ternary_no_floor")
        checks = [refuses_when_empty(body, c) for c in colls]
        h = {"shape": shape, "line": node.lineno, "collections": sorted(set(colls)),
             "floor_guard": (any if strict else all)(checks),
             "floor_per_collection": dict(zip(sorted(set(colls)),
                                              [refuses_when_empty(body, c) for c in sorted(set(colls))])),
             "text": (lines[node.lineno - 1] if node.lineno <= len(lines) else "").strip()[:130]}
        if extra:
            h.update(extra)
        hits.append(h)

    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id in ("all", "any") and node.args:
                add("vacuous_all", node, comp_iterables(node.args[0]), {"fn": node.func.id})
        if isinstance(node, ast.If):
            tests = []
            if isinstance(node.test, ast.UnaryOp) and isinstance(node.test.op, ast.Not):
                tests.append(("not", name_of(node.test.operand)))
            if isinstance(node.test, ast.BoolOp) and isinstance(node.test.op, ast.Or):
                for v in node.test.values:
                    if isinstance(v, ast.UnaryOp) and isinstance(v.op, ast.Not):
                        tests.append(("not-or", name_of(v.operand)))
            success = any(isinstance(s, ast.Return) and isinstance(s.value, ast.Constant)
                          and isinstance(s.value.value, int) and s.value.value == 0 for s in node.body) or \
                any(isinstance(s, (ast.Continue, ast.Pass)) for s in node.body)
            for kind, n in tests:
                if success:
                    add("emptiness_passes", node, [n], {"form": kind})
            comps = [node.test] if isinstance(node.test, ast.Compare) else \
                (node.test.values if isinstance(node.test, ast.BoolOp) else [])
            for v in comps:
                if not isinstance(v, ast.Compare):
                    continue
                left, right = v.left, v.comparators[0]
                empty_lit = (isinstance(right, ast.Dict) and not right.keys) or \
                    (isinstance(right, ast.List) and not right.elts) or \
                    (isinstance(right, ast.Call) and name_of(right.func) == "set" and not right.args)
                if empty_lit and success:
                    add("empty_eq_pass", node, [name_of(left)])
                if not empty_lit and isinstance(left, ast.Call) and name_of(left.func) in ("sorted", "set",
                                                                                          "frozenset"):
                    ln = [name_of(left.args[0])] if left.args else []
                    rn = [name_of(x) for x in ([right] if isinstance(right, ast.Call) else [])
                          if name_of(getattr(x, "func", None)) in ("sorted", "set")]
                    rn = [name_of(right.args[0])] if isinstance(right, ast.Call) and right.args else []
                    op = type(v.ops[0]).__name__
                    add("compare_only_verdict", node, ln + rn,
                        {"op": op, "success_path": bool(success)})
        if isinstance(node, ast.Return) and isinstance(node.value, ast.IfExp):
            ie = node.value
            has_all = any(isinstance(x, ast.Call) and isinstance(x.func, ast.Name) and x.func.id in ("all", "any")
                          for x in ast.walk(ie.test))
            if has_all:
                add("ternary_no_floor", node, comp_iterables(ie.test))
            cmps = [c for c in ast.walk(ie.test) if isinstance(c, ast.Compare)]
            for c in cmps:
                if isinstance(c.left, ast.Call) and name_of(c.left.func) in ("sorted", "set") and c.left.args:
                    right = c.comparators[0]
                    rn = name_of(right.args[0]) if isinstance(right, ast.Call) and right.args else None
                    add("compare_only_verdict", node, [name_of(c.left.args[0]), rn],
                        {"op": type(c.ops[0]).__name__, "success_path": True})
    return [{**{"file": os.path.basename(path)}, **h} for h in hits]


def scan_dir(root, skip=()):
    rows, n = [], 0
    for f in sorted(os.listdir(root)):
        if not f.endswith(".py") or f in skip:
            continue
        n += 1
        rows.extend(scan_file(os.path.join(root, f)))
    return rows, n


FIX_BAD = '''def judge(rows):
    problems = [r for r in rows if r["bad"]]
    return 0 if all(p == {} for p in problems) else 7


def stage(paths):
    staged = collect()
    if sorted(staged) != sorted(paths):
        return 7
    return 0


def mirror(text, want):
    if not text:
        return 0
    return 0 if len(text) == len(want) else 8
'''
FIX_GOOD = '''def judge(rows):
    problems = [r for r in rows if r["bad"]]
    assert rows, "empty denominator - nothing was measured"
    return 0 if all(p["ok"] for p in rows) else 7


def stage(paths):
    staged = collect()
    if not staged:
        raise SystemExit("ABORT: nothing staged")
    if sorted(staged) != sorted(paths):
        return 7
    return 0
'''
FIX_EMPTY = '''def only():
    xs = []
    return 0 if all(x for x in xs) else 7
'''


def self_test():
    d = tempfile.mkdtemp(prefix="cnx_ed_selftest_")
    io.open(os.path.join(d, "bad_shape_fixture.py"), "w", encoding="utf-8", newline="\n").write(FIX_BAD)
    io.open(os.path.join(d, "good_shape_fixture.py"), "w", encoding="utf-8", newline="\n").write(FIX_GOOD)
    io.open(os.path.join(d, "empty_input_fixture.py"), "w", encoding="utf-8", newline="\n").write(FIX_EMPTY)
    rows = scan_dir(d)[0]
    bad = [r for r in rows if r["file"] == "bad_shape_fixture.py" and not r["floor_guard"]]
    good_bad = [r for r in rows if r["file"] == "good_shape_fixture.py" and not r["floor_guard"]]
    empty = [r for r in rows if r["file"] == "empty_input_fixture.py"]
    seen = sorted({r["shape"] for r in bad})
    out = {"bad_without_floor": len(bad), "bad_shapes": seen, "good_false_positives": len(good_bad),
           "empty_input_hits": len(empty),
           "must_include_compare_only": "compare_only_verdict" in seen,
           "must_include_vacuous_all": "vacuous_all" in seen}
    out["arms_pass"] = bool(out["bad_without_floor"] and out["must_include_compare_only"]
                            and out["must_include_vacuous_all"] and not out["good_false_positives"]
                            and out["empty_input_hits"])
    for f in os.listdir(d):
        os.remove(os.path.join(d, f))
    os.rmdir(d)
    return out


def main():
    ap = argparse.ArgumentParser(prog="empty_denominator_scan_r1.py")
    ap.add_argument("--root", default=os.path.dirname(os.path.abspath(__file__)))
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    if a.self_test:
        r = self_test()
        print(json.dumps(r, ensure_ascii=False))
        return 0 if r["arms_pass"] else 7
    st = self_test()
    if not st["arms_pass"]:
        print("ABORT: the scanner's own arms failed, so its counts cannot be used: %s"
              % json.dumps(st, ensure_ascii=False))
        return 7
    rows, n = scan_dir(a.root, skip={os.path.basename(__file__)})
    by_shape = {}
    for r in rows:
        d = by_shape.setdefault(r["shape"], {"total": 0, "no_floor": 0})
        d["total"] += 1
        if not r["floor_guard"]:
            d["no_floor"] += 1
    todo = [r for r in rows if not r["floor_guard"]]
    doc = {"root": a.root, "files_scanned": n, "hits": len(rows), "by_shape": by_shape,
           "work_list_without_floor": todo, "self_test": st,
           "counts_by_file": {f: len([r for r in todo if r["file"] == f])
                              for f in sorted({r["file"] for r in todo})}}
    if a.out:
        io.open(a.out, "w", encoding="utf-8").write(json.dumps(doc, ensure_ascii=False, indent=1))
    print(json.dumps({"files_scanned": n, "hits": len(rows), "work_list": len(todo),
                      "by_shape": by_shape, "arms": st, "files_with_work": len(doc["counts_by_file"])},
                     ensure_ascii=False))
    return 0


raise SystemExit(main())
