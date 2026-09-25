"""Patch ord0299_receipt.py: enforce "a cell's sentence is derivable from that cell's own record" at build.

Why a pre-check instead of trusting the ruler's pass: the ruler graded cells 7 and 9 as SOFT
(WHY_NOT_FROM_OWN_READINGS) - the sentences named shas, line numbers and ports that lived in some OTHER
cell's record. Rather than shorten those sentences, the values move into the cell that cites them, taken
from the artifacts (the mutant digest is recomputed by re-applying the recorded one-hunk patch in memory;
nothing is written to the tree to get it).

The check uses the RULER'S OWN token patterns, imported from its file, so it cannot be weaker than the gate.
"""
from __future__ import annotations

import importlib.util
import pathlib
import re

RULER = pathlib.Path(r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks\receipt_cell_derivation_check_r2.py")


def ruler_patterns():
    spec = importlib.util.spec_from_file_location("ruler_r2", RULER)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return list(m.TOKEN_PATTERNS)


def _flatten(x):
    if isinstance(x, dict):
        for v in x.values():
            yield from _flatten(v)
    elif isinstance(x, (list, tuple)):
        for v in x:
            yield from _flatten(v)
    elif x is not None:
        yield x


def cite(why: str, readings: dict, pats) -> dict:
    """Attach the values the sentence names to the cell's own record, or abort listing what is missing."""
    named = sorted({str(v) for v in _flatten(readings)})
    toks = set()
    for p in pats:
        toks.update(p.findall(why))
    missing = sorted(t for t in toks
                     if t and not any(t == n or t in n or n in t for n in named))
    if missing:
        raise SystemExit("cell sentence names values its readings do not hold: " + repr(missing[:8]) +
                         " - add the measurement to this cell or drop the claim")
    readings["named_values_the_why_uses"] = named
    return readings


def lines_of(text: str, needle: str):
    return [i + 1 for i, l in enumerate(text.splitlines()) if needle in l]


def env_pinned_by(script: pathlib.Path) -> list:
    """Read the env mapping out of the driver script that was executed, as `KEY=value` strings.

    Values the script computes at runtime (f-strings, variables) are recorded as their source text, so the
    cell cites what the script pins without pretending to have observed the interpolated value here.
    """
    import ast

    tree = ast.parse(script.read_text(encoding="utf-8"))
    pairs = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == "update" and isinstance(node.args[0], ast.Dict)):
            for k, v in zip(node.args[0].keys, node.args[0].values):
                key = k.value if isinstance(k, ast.Constant) else ast.unparse(k)
                val = v.value if isinstance(v, ast.Constant) else "<computed:" + ast.unparse(v) + ">"
                pairs.append(f"{key}={val}")
    if not pairs:
        raise SystemExit(f"no env.update({{...}}) literal found in {script}")
    return sorted(pairs)


def pop_keys(script: pathlib.Path) -> list:
    """The keys the driver removes from the environment before launching (the AI-off declaration)."""
    import ast

    out = []
    for node in ast.walk(ast.parse(script.read_text(encoding="utf-8"))):
        if (isinstance(node, ast.For) and isinstance(node.iter, ast.Tuple)
                and isinstance(node.target, ast.Name) and node.target.id == "k"):
            out += [e.value for e in node.iter.elts if isinstance(e, ast.Constant)]
    return sorted(out)


def runs_pinned(script: pathlib.Path) -> list:
    """The per-run literals the executed driver passes to run_arms: run-id prefix, frontend port, backend port.

    Read out of the script that produced the artifacts (bound by sha256 + mtime), so the receipt never
    carries a port or a db name that I remembered.
    """
    import ast

    out = []
    for node in ast.walk(ast.parse(script.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "run_arms":
            lits = []
            for a in node.args:
                if isinstance(a, ast.Constant) and isinstance(a.value, str):
                    lits.append(a.value)
                elif (isinstance(a, ast.BinOp) and isinstance(a.left, ast.Constant)
                        and isinstance(a.left.value, str)):
                    lits.append(a.left.value)  # "0299fix" + stamp[-4:] -> keep the pinned prefix
            prefixes = [l for l in lits if l.startswith("0299")]
            ports = [l for l in lits if l.isdigit()]
            if len(prefixes) != 1 or len(ports) < 2:
                raise SystemExit(f"cannot read run id/ports out of the driver: {lits}")
            out.append({"run_id_prefix": prefixes[0], "frontend_port": ports[0], "backend_port": ports[1]})
    if len(out) != 2:
        raise SystemExit(f"expected a baseline and a counter run_arms call, found {len(out)}")
    return out


def patch_bytes(pristine: bytes, mut: dict) -> bytes:
    """Re-apply the recorded counter-arm hunk in memory, so the mutant digest is computed, not remembered."""
    t = pristine.decode("utf-8")
    for needle, repl in mut.items():
        if needle not in t:
            raise SystemExit(f"the recorded hunk is no longer present: {needle[:40]}")
        t = t.replace(needle, repl, 1)
    return t.encode("utf-8")
