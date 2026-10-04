# -*- coding: utf-8 -*-
"""Leg reachability audit r3 - write points taken from the AST, not from a line regex.

r2's failure (measured, in this lane's own trail): it called the first `subprocess.run` or the first
`open(..., "rb")` a "mutation", so the cut landed above every guard and 127 of 131 legs looked unguarded.
r3 decides, per file and from the syntax tree:

  claim_write   = a call to open()/io.open() whose mode argument is a constant containing w or a,
                  or a call to json.dump / pickle.dump / writerow  - the moment a green claim becomes durable
  external_write= subprocess.run/Popen whose argv contains a write verb (push, commit-tree, update-ref,
                  --apply, bus.py send), or an HTTP request built with data=
  cut           = the earlier of the two

A leg is GUARDED when an emptiness floor is reachable before that cut: an `if not X:` / `if len(X) == 0:`
whose body raises, or a refusal whose message carries floor wording.  A raise on a failed command is NOT a
floor - measured today: `anchor_drift_survey_r3.py` refuses when git fails and exits code 0 when git returns
nothing.

Positive controls are the three legs measured by real runs; any disagreement aborts with exit code 3.
"""
import ast
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "empty_leg_reachability_r3.json")
WRITE_MODE = re.compile(r"[wa]")
FLOOR_MSG = re.compile(r"nothing|no such|enumerates|empty|no \.py|refus|zero|does not exist|missing|"
                       r"aborton|ABORT|clean scan", re.I)
RAISE_VERB = re.compile(r"SystemExit|sys\.exit|AssertionError|RuntimeError|ValueError|Error\(|assert ")
WRITE_VERBS = ("push", "commit-tree", "update-ref", "--apply", "send", "delete", "-d")


def call_name(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Call):
        return call_name(node.func)
    return ""


def literals(node):
    out = []
    for sub in ast.walk(node):
        if isinstance(sub, ast.Constant) and isinstance(sub.value, str):
            out.append(sub.value)
    return out


class Probe(ast.NodeVisitor):
    def __init__(self):
        self.claim_writes = []
        self.external_writes = []
        self.floors = []
        self.failure_raises = 0
        self.floor_raises = []
        self._if_stack = []

    def visit_Call(self, node):
        nm = call_name(node.func)
        if nm in ("open",):
            mode = node.args[1] if len(node.args) > 1 else None
            if isinstance(mode, ast.Constant) and isinstance(mode.value, str) and WRITE_MODE.search(mode.value):
                self.claim_writes.append(node.lineno)
        if nm in ("writerow", "writelines"):
            self.claim_writes.append(node.lineno)
        # `json.dump(obj, fh)` writes; `ast.dump(node)` and `json.dumps(obj)` do not - the file handle is the tell
        if nm == "dump" and len(node.args) >= 2:
            self.claim_writes.append(node.lineno)
        if nm in ("run", "Popen", "check_output", "call", "request"):
            lits = " ".join(literals(node))
            if any(v in lits for v in WRITE_VERBS):
                self.external_writes.append(node.lineno)
        if nm == "Request" and any(isinstance(k, ast.keyword) and k.arg == "data" for k in node.keywords):
            self.external_writes.append(node.lineno)
        self.generic_visit(node)

    def visit_Raise(self, node):
        txt = ast.unparse(node)
        if RAISE_VERB.search(txt):
            if FLOOR_MSG.search(txt):
                self.floor_raises.append({"line": node.lineno, "text": txt[:120]})
            else:
                self.failure_raises += 1
        self.generic_visit(node)

    def visit_If(self, node):
        test = ast.unparse(node.test)
        empty_shape = bool(re.search(r"\bnot \w", test)) or bool(
            re.search(r"len\([^)]*\)\s*(==|<|<=)\s*\d+", test)) or bool(re.search(r"(==|<|<=)\s*0\b", test))
        body = "\n".join(ast.unparse(n) for n in node.body)
        if empty_shape and RAISE_VERB.search(body):
            self.floors.append({"line": node.lineno, "test": test[:90]})
        self.generic_visit(node)


def analyse(path):
    name = os.path.basename(path)
    src = io.open(path, encoding="utf-8", errors="replace").read()
    r = {"file": name, "bytes": len(src.encode("utf-8"))}
    try:
        tree = ast.parse(src)
    except SyntaxError as e:
        r.update({"verdict": "unparseable", "detail": str(e)[:120]})
        return r
    p = Probe()
    p.visit(tree)
    cands = [min(p.claim_writes) if p.claim_writes else None,
             min(p.external_writes) if p.external_writes else None]
    cut = min([c for c in cands if c is not None], default=None)
    r["claim_write_lines"] = sorted(set(p.claim_writes))[:6]
    r["external_write_lines"] = sorted(set(p.external_writes))[:6]
    r["cut_line"] = cut
    if cut is None:
        r["verdict"] = "no-write-leg"
        return r
    floors_before = [f for f in p.floors if f["line"] < cut]
    msg_before = [f for f in p.floor_raises if f["line"] < cut]
    r["floors_before_cut"] = [f["line"] for f in floors_before]
    r["floor_worded_raises_before_cut"] = [f["line"] for f in msg_before]
    r["failure_only_raises_before_cut"] = p.failure_raises
    r["refusal_texts_before_cut"] = [{"line": i, "text": l.strip()[:110]}
                                     for i, l in enumerate(src.splitlines(), 1)
                                     if i < cut and RAISE_VERB.search(l)]
    r["verdict"] = "guarded" if (floors_before or msg_before) else "unguarded"
    return r


KNOWN = {"block_census_r3_r1.py": "guarded",
         "anchor_drift_survey_r3.py": "unguarded",
         "empty_denominator_scan_r2.py": "guarded"}


LEG_NO_FLOOR = (
    "import io, json, os\n"
    "def main():\n"
    "    rows = json.load(io.open('rows.json'))\n"
    "    doc = {'n': len(rows), 'verdict': 'GREEN'}\n"
    "    io.open(os.path.join('out', 'receipt.json'), 'w').write(json.dumps(doc))\n"
    "main()\n")

LEG_WITH_FLOOR = (
    "import io, json, os\n"
    "def main():\n"
    "    rows = json.load(io.open('rows.json'))\n"
    "    if not rows:\n"
    "        raise SystemExit('ABORT: rows enumerated nothing')\n"
    "    doc = {'n': len(rows), 'verdict': 'GREEN'}\n"
    "    io.open(os.path.join('out', 'receipt.json'), 'w').write(json.dumps(doc))\n"
    "main()\n")


def fixture_discrimination():
    """The analyzer must call the floorless leg unguarded and the floored leg guarded, on synthetic bytes whose
    truth I fixed in advance - otherwise 113 'unguarded' is just a word."""
    import tempfile
    tmp = tempfile.mkdtemp(prefix="s4_legfx_")
    try:
        for name, src in (("fx_no_floor.py", LEG_NO_FLOOR), ("fx_with_floor.py", LEG_WITH_FLOOR)):
            io.open(os.path.join(tmp, name), "w", encoding="utf-8", newline="\n").write(src)
        a = analyse(os.path.join(tmp, "fx_no_floor.py"))
        b = analyse(os.path.join(tmp, "fx_with_floor.py"))
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)
    return {"no_floor_says": a["verdict"], "with_floor_says": b["verdict"],
            "no_floor_cut": a["cut_line"], "with_floor_floors": b["floors_before_cut"],
            "discriminates": a["verdict"] == "unguarded" and b["verdict"] == "guarded"}


def main():
    fx = fixture_discrimination()
    files = sorted(f for f in os.listdir(HERE) if f.endswith(".py"))
    rows = [analyse(os.path.join(HERE, f)) for f in files]
    if not rows:
        raise SystemExit("ABORT: no .py files under %s" % HERE)
    legs = [r for r in rows if r["verdict"] in ("guarded", "unguarded")]
    counts = {"guarded": sum(1 for r in legs if r["verdict"] == "guarded"),
              "unguarded": sum(1 for r in legs if r["verdict"] == "unguarded"),
              "no-write-leg": sum(1 for r in rows if r["verdict"] == "no-write-leg"),
              "unparseable": sum(1 for r in rows if r["verdict"] == "unparseable")}
    by = {r["file"]: r for r in rows}
    known = {n: {"measured": w, "analyzer": by.get(n, {}).get("verdict"),
                 "agrees": by.get(n, {}).get("verdict") == w} for n, w in KNOWN.items()}
    bad = [n for n, v in known.items() if not v["agrees"]]
    out = {"root": HERE, "py_files": len(rows), "write_legs": len(legs), "counts": counts,
           "unparseable_files": [{"file": r["file"], "detail": r.get("detail", "")}
                                 for r in rows if r["verdict"] == "unparseable"],
           "known_cases": known, "mismatched_controls": bad, "fixture_discrimination": fx,
           "unguarded_legs": [r for r in legs if r["verdict"] == "unguarded"], "legs": legs}
    json.dump(out, io.open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({"py_files": len(rows), "write_legs": len(legs), "counts": counts,
                      "known_cases": known, "mismatched_controls": bad,
                      "fixture_discrimination": fx}, ensure_ascii=False, indent=1))
    for r in out["unguarded_legs"][:10]:
        print("UNGUARDED %-32s cut@%-4s claim=%s external=%s" %
              (r["file"], r["cut_line"], r["claim_write_lines"][:3], r["external_write_lines"][:3]))
    return 3 if (bad or not fx["discriminates"]) else 0


if __name__ == "__main__":
    sys.exit(main())
