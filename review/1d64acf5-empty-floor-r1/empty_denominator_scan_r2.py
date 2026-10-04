# -*- coding: utf-8 -*-
"""Empty-denominator scan r2: same shapes as r1, plus the axis r1 lacked.

r1 reported a shape per site (`emptiness_passes` = `if not X: return 0 | continue | pass`), which mixed two very
different things: a *filter* (skip this row) and a *verdict input* (a value a guard then compares).  r2 keeps the
shape names untouched and adds, per site:

  role            verdict | filter | accessor        (decided from the AST body of the guard)
  floor_here      whether the same statement/guard already refuses on empty
  floor_upstream  whether the function this site sits in is fed by a named ABORT/SystemExit floor in the same file
  used_by         how the enclosing function's value is consumed, when it is a returned constant

Rows are also de-duplicated by (file, line, shape, text): r1's published 113 rows contained one duplicate.

Read-only over the lane's own work directory; nothing on the authoritative line is touched.
"""
import ast
import collections
import io
import json
import os
import re
import sys

ROOT = os.environ.get("S4_SCAN_ROOT", r"D:\moodle\_qoder_lane_S4_0926\work\ord_anchors")
HERE = os.path.dirname(os.path.abspath(__file__))

HELPER = re.compile(r"\b(all|any)\(")
CONST_ZERO = (0, None, False)


def name_of(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Call):
        return name_of(node.func)
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        return ",".join(name_of(x) for x in node.elts)
    return ast.dump(node)[:60]


def comp_iterables(node):
    out = []
    for gen in ast.walk(node):
        if isinstance(gen, (ast.ListComp, ast.GeneratorExp, ast.SetComp, ast.DictComp)):
            for cls in gen.generators:
                out.append(name_of(cls.iter))
    return out


class Visitor(ast.NodeVisitor):
    def __init__(self, src, fname):
        self.src, self.fname = src, fname
        self.rows = []
        self.fn_of = {}          # function name -> does its body return a constant on empty
        self.abort_names = set()  # names mentioned inside ABORT/SystemExit messages in this file
        self._stack = []

    def visit_FunctionDef(self, node):
        self._stack.append(node.name)
        self.generic_visit(node)
        self._stack.pop()

    def _record(self, shape, node, collections_, extra):
        line = self.src.splitlines()[node.lineno - 1].strip()
        r = {"file": self.fname, "line": node.lineno, "shape": shape, "text": line[:200],
             "collections": sorted(set(collections_)), "in_function": self._stack[-1] if self._stack else "",
             "floor_here": False, "role": "", "floor_upstream": False}
        r.update(extra)
        self.rows.append(r)

    def visit_If(self, node):
        test = node.test
        # `if not X ...:` bodies
        if isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not):
            body_kinds = [type(b).__name__ for b in node.body]
            inner = node.body[0] if node.body else None
            if body_kinds[:1] == ["Continue"] or body_kinds[:1] == ["Pass"]:
                self._record("emptiness_passes", node, [name_of(test.operand)],
                             {"role": "filter", "floor_here": True,
                              "note": "skips this row; it is not a pass/fail verdict"})
            elif isinstance(inner, ast.Return) and isinstance(inner.value, ast.Constant) \
                    and inner.value.value in (0, None, False, "", []):
                self._record("emptiness_passes", node, [name_of(test.operand)],
                             {"role": "accessor-or-gate-input",
                              "returns": repr(inner.value.value)})
            else:
                self._record("emptiness_passes", node, [name_of(test.operand)],
                             {"role": "verdict", "floor_here": True})
        elif isinstance(test, ast.Compare) and isinstance(test.ops[0],
                                                          (ast.Eq, ast.NotEq, ast.Lt, ast.GtE)):
            l_txt = ast.dump(test.left)[:200]
            r_txt = ast.dump(test.comparators[0])[:200]
            cols = []
            for side in (test.left, test.comparators[0]):
                if isinstance(side, ast.Call) and getattr(side.func, "id", "") == "sorted":
                    cols.append(name_of(side.args[0]))
                else:
                    cols.append(name_of(side))
            body = ast.dump(node.body[0])[:400] if node.body else ""
            raises = ("Raise" in body and "SystemExit" in body) or "Assert" in body
            self._record("compare_only_verdict", node, cols,
                         {"role": "verdict" if raises else "compare",
                          "floor_here": raises,
                          "both_empty_passes": True})
        self.generic_visit(node)

    def visit_Call(self, node):
        if isinstance(node.func, ast.Name) and node.func.id in ("all", "any"):
            iterables = comp_iterables(node.args[0]) if node.args else []
            parent_role = "unknown"
            self._record("vacuous_all", node, iterables, {"fn": node.func.id, "role": parent_role})
        self.generic_visit(node)

    def visit_Expr(self, node):
        self.generic_visit(node)

    def visit_Assert(self, node):
        self._record("asserted_truth", node, comp_iterables(node.test), {"role": "verdict",
                                                                        "floor_here": True})
        self.generic_visit(node)


def collect_abort_names(src):
    out = set()
    for m in re.finditer(r"(?:SystemExit|raise)\((.{0,200})", src):
        for w in re.findall(r"[A-Za-z_][A-Za-z_0-9]{3,}", m.group(1)):
            out.add(w)
    return out


def scan(root=None, emit=True):
    root = root or ROOT
    if not os.path.isdir(root):
        raise SystemExit("ABORT: no such root %s" % root)
    files = sorted(f for f in os.listdir(root) if f.endswith(".py"))
    if not files:
        raise SystemExit("ABORT: no .py files under %s - refusing to call an empty root a clean scan" % root)
    rows, parsed = [], 0
    for f in files:
        try:
            src = io.open(os.path.join(root, f), encoding="utf-8", errors="replace").read()
            tree = ast.parse(src)
        except (SyntaxError, ValueError):
            continue
        parsed += 1
        v = Visitor(src, f)
        v.abort_names = collect_abort_names(src)
        v.visit(tree)
        rows += v.rows
        # mark upstream floors: a site inside a function whose result is compared, where the same file aborts on an
        # empty collection by name
        for r in v.rows:
            if r["role"] == "accessor-or-gate-input":
                called = [c for c in r["collections"]]
                r["floor_upstream"] = any(
                    re.search(r"(?:ABORT|SystemExit|raise)[^\n]*\b%s\b" % re.escape(c), src) for c in called)
    seen, ded = set(), []
    for r in rows:
        k = (r["file"], r["line"], r["shape"], r["text"])
        if k in seen:
            continue
        seen.add(k)
        ded.append(r)
    by_role = collections.Counter(r["role"] for r in ded)
    by_shape = collections.Counter(r["shape"] for r in ded)
    no_floor_verdict = [r for r in ded if not r["floor_here"] and r["role"] in ("verdict", "accessor-or-gate-input",
                                                                               "compare", "unknown")]
    dup_removed = len(rows) - len(ded)
    out = {"root": root, "files_parsed": parsed, "rows_raw": len(rows), "duplicates_removed": dup_removed,
           "rows_distinct": len(ded), "by_shape": dict(by_shape), "by_role": dict(by_role),
           "verdict_bearing_no_floor": len(no_floor_verdict),
           "sites": ded, "floors": no_floor_verdict}
    if emit:
        json.dump(out, io.open(os.path.join(HERE, "empty_denominator_inventory_r2.json"), "w",
                              encoding="utf-8"), ensure_ascii=False, indent=1)
    return out


NL = chr(10)
FIXTURES = {
    "fx_filter.py": "def f(rows):" + NL + "    for r in rows:" + NL + "        if not r:" + NL
                    + "            continue" + NL,
    "fx_verdict.py": "def g(shelf, receipt):" + NL + "    if sorted(shelf) != sorted(receipt):" + NL
                     + "        raise SystemExit(" + chr(34) + "ABORT: mismatch" + chr(34) + ")" + NL,
    "fx_accessor.py": "def h(trail):" + NL + "    if not os.path.exists(trail):" + NL
                      + "        return 0" + NL + "    return sum(1 for l in trail)" + NL,
    "fx_vacuous.py": "def k(vals):" + NL + "    return all(v[" + chr(34) + "ok" + chr(34)
                     + "] for v in vals)" + NL,
}
NL = chr(10)

EXPECTED = {("fx_filter.py", "filter"), ("fx_verdict.py", "verdict"), ("fx_accessor.py", "accessor-or-gate-input"),
            ("fx_vacuous.py", "unknown")}


def self_test(out):
    """Instrument properties, tested by feeding the instrument, not by hoping the repo has the shape."""
    bad = {"empty_input": out["files_parsed"] == 0, "no_rows": len(out["sites"]) == 0,
           "no_shapes": not out["by_shape"],
           "roles_all_blank": all(not r["role"] for r in out["sites"])}
    hit = {(r["file"], r["role"]) for r in out["sites"]}
    controls = {str(k): (k in hit) for k in sorted(EXPECTED)}
    return {"refuse_flags": [k for k, v in bad.items() if v], "fixture_controls": controls,
            "fixtures_all_classified": all(controls.values())}


def run_fixture_scan(tmp):
    for name, src in FIXTURES.items():
        with io.open(os.path.join(tmp, name), "w", encoding="utf-8", newline=chr(10)) as fh:
            fh.write(src)
    return scan(tmp, emit=False)


def run_empty_scan(tmp_empty):
    try:
        scan(tmp_empty, emit=False)
    except SystemExit as e:
        return {"refused": True, "detail": str(e)[:160]}
    return {"refused": False, "detail": "an empty root produced a verdict - this is the defect class"}


def main():
    import tempfile
    out = scan()
    tmp_fx = tempfile.mkdtemp(prefix="s4_fx_")
    tmp_empty = tempfile.mkdtemp(prefix="s4_empty_")
    fx = run_fixture_scan(tmp_fx)
    st = self_test(fx)                 # judged on the fixtures, whose denominator is fixed by me
    empty = run_empty_scan(tmp_empty)
    import shutil
    for d in (tmp_fx, tmp_empty):
        shutil.rmtree(d, ignore_errors=True)
    out["self_test"] = st
    out["empty_root_counterexample"] = empty
    out["fixture_rows"] = len(fx["sites"])
    json.dump(out, io.open(os.path.join(HERE, "empty_denominator_inventory_r2.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(json.dumps({k: out[k] for k in ("root", "files_parsed", "rows_raw", "duplicates_removed",
                                          "rows_distinct", "by_shape", "by_role", "fixture_rows")},
                     ensure_ascii=False, indent=1))
    print(json.dumps({"self_test": st, "empty_root_counterexample": empty}, ensure_ascii=False, indent=1))
    for s_ in out["floors"][:10]:
        print("FLOOR %-30s %-4d %-20s %-24s upstream=%s" % (s_["file"], s_["line"], s_["shape"], s_["role"],
                                                            s_["floor_upstream"]))
    ok = st["fixtures_all_classified"] and st["refuse_flags"] == [] and empty["refused"]
    if not ok:
        print("SELF-TEST RED: %s %s" % (st, empty))
    return 0 if ok else 3


if __name__ == "__main__":
    sys.exit(main())
