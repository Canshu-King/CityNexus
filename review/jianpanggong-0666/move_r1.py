"""ORD-0666 甲 · the mover for `test_replan_place_fact_binding.py`.

Four edits, all byte-exact from the representative generation, and the instrument refuses the whole
run if any single expectation fails:

  real_city.py  `Mapping` into the typing import, then `_fee_is_explicitly_free` +
                `canonical_cost_evidence` after the tip's own `normalize_opening_hours`
  services.py   `KNOWN_COST_EVIDENCE_STATUSES` after the tip's own `_plan_staleness`
  main.py       two names added to the two import groups that already exist there
  tests/        the 45-line test, byte for byte

Nothing is rewritten, nothing is re-indented, no assertion is touched.
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import subprocess
import sys

LIB = "D:/moodle/CityNexus"
W = "D:/moodle/_qoder_jianpanggong_0666"
REP = "843844c5587da01287faa8f384411915eade9a87"
LINE_REF = "refs/heads/mirror/integration-frontend-apple-pass1"
RC = "backend/app/integrations/discovery/real_city.py"
SVC = "backend/app/services.py"
MAIN = "backend/app/main.py"
TEST = "backend/tests/test_replan_place_fact_binding.py"
EVIDENCE = W + "/review/jianpanggong-0666/move_evidence_r1.json"
APPLY = "--apply" in sys.argv


def git(*args, cwd=LIB):
    done = subprocess.run(["git", "-C", cwd] + list(args), capture_output=True)
    if done.returncode != 0:
        raise SystemExit("git {} rc={} {}".format(
            " ".join(args), done.returncode, done.stderr.decode("utf-8", "replace")[:200]))
    return done.stdout


def show(rev, path):
    return git("show", "{}:{}".format(rev, path)).decode("utf-8")


def blob(data):
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def top_nodes(src):
    tree = ast.parse(src)
    out = []
    for node in tree.body:
        name = getattr(node, "name", None)
        if name is None and isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
        out.append((name, node))
    return tree, out


def bound_names(src):
    _tree, nodes = top_nodes(src)
    names = set()
    for node in ast.parse(src).body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            names.update(t.id for t in node.targets if isinstance(t, ast.Name))
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            names.update((a.asname or a.name.split(".")[0]) for a in node.names)
    return names


def block_of(rev, path, name):
    """The exact source lines of one module-level definition, plus the gap that preceded it."""
    src = show(rev, path)
    lines = src.split("\n")
    _tree, nodes = top_nodes(src)
    idx = [i for i, (n, _node) in enumerate(nodes) if n == name]
    if len(idx) != 1:
        raise SystemExit("{} is not a unique module-level name on {}: {}".format(name, rev[:12], idx))
    node = nodes[idx[0]][1]
    body = "\n".join(lines[node.lineno - 1:node.end_lineno])
    ast.parse(body)  # the slice must stand on its own
    prev_end = nodes[idx[0] - 1][1].end_lineno if idx[0] else 0
    gap = node.lineno - prev_end - 1 if idx[0] else 0
    return body, node.lineno, node.end_lineno, gap, blob(body.encode("utf-8"))


def insert_after(src, anchor_name, payload):
    """Put payload after the named module-level node, keeping the file's own blank-line rhythm."""
    lines = src.split("\n")
    _tree, nodes = top_nodes(src)
    hit = [node for n, node in nodes if n == anchor_name]
    if len(hit) != 1:
        raise SystemExit("anchor {} not unique in the target file".format(anchor_name))
    at = hit[0].end_lineno
    return "\n".join(lines[:at] + [""] + payload.split("\n") + lines[at:]), at + 2


def is_subsequence(old_lines, new_lines):
    it = iter(new_lines)
    return all(row in it for row in old_lines)


def rewrite(path, text):
    full = os.path.join(W, path.replace("/", os.sep))
    if APPLY:
        with open(full, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
    return text


tip = git("ls-remote", "origin", LINE_REF).split(b"\t", 1)[0].decode().strip()
head = git("rev-parse", "HEAD", cwd=W).decode().strip()
if head != tip:
    raise SystemExit("the worktree is at {} but the line is at {} -- re-cut first".format(head, tip))

report = {"tip": tip, "rep": REP, "moves": [], "imports": [], "test": {}}

# --- real_city.py: the two helpers, then the typing import ---
rc_tip = show(head, RC)
for name in ("_fee_is_explicitly_free", "canonical_cost_evidence"):
    if name in bound_names(rc_tip):
        raise SystemExit(name + " is already on the line -- nothing to deliver")
pair_body = ""
for name in ("_fee_is_explicitly_free", "canonical_cost_evidence"):
    body, lo, hi, gap, blob_id = block_of(REP, RC, name)
    pair_body += ("\n" if pair_body else "") + body
    report["moves"].append({"path": RC, "name": name, "rep_range": [lo, hi],
                            "rep_lines": hi - lo + 1, "rep_gap_before": gap,
                            "block_blob": blob_id, "anchor_on_tip": "normalize_opening_hours"})
new_rc, at = insert_after(rc_tip, "normalize_opening_hours", pair_body)
if not is_subsequence(rc_tip.split("\n"), new_rc.split("\n")):
    raise SystemExit("real_city.py lost or reordered an original line")
if "\nfrom typing import Any\n" not in "\n" + new_rc:
    raise SystemExit("the typing import in real_city.py is not the shape I measured")
typed = new_rc.replace("from typing import Any\n", "from typing import Any, Mapping\n", 1)
diff = [(i, a, b) for i, (a, b) in enumerate(zip(new_rc.split("\n"), typed.split("\n"))) if a != b]
if len(typed.split("\n")) != len(new_rc.split("\n")) or len(diff) != 1 \
        or diff[0][1] != "from typing import Any":
    raise SystemExit("the typing edit is not exactly one line: {}".format(diff))
new_rc = typed
report["typing_line"] = {"at_line": diff[0][0] + 1, "before": diff[0][1],
                         "after": typed.split("\n")[diff[0][0]]}
rep_typing = [row for row in show(REP, RC).split("\n") if row.startswith("from typing import")]
if rep_typing != ["from typing import Any, Mapping"]:
    raise SystemExit("the representative typing line moved: {}".format(rep_typing))
after_names = bound_names(new_rc)
need = {row["name"] for row in report["moves"]} | {"Mapping"}
if not need <= after_names:
    raise SystemExit("names did not bind: {}".format(need - after_names))
if not set(bound_names(rc_tip)) <= after_names:
    raise SystemExit("a pre-existing top-level name disappeared in real_city.py")
rewrite(RC, new_rc)
report["insert_at_line"] = at

# --- services.py: the one-line constant ---
svc_tip = show(head, SVC)
body, lo, hi, gap, blob_id = block_of(REP, SVC, "KNOWN_COST_EVIDENCE_STATUSES")
if "KNOWN_COST_EVIDENCE_STATUSES" in bound_names(svc_tip):
    raise SystemExit("KNOWN_COST_EVIDENCE_STATUSES is already on the line")
new_svc, svc_at = insert_after(svc_tip, "_plan_staleness", body)
if "KNOWN_COST_EVIDENCE_STATUSES" not in bound_names(new_svc):
    raise SystemExit("the constant did not bind in services.py")
if not is_subsequence(svc_tip.split("\n"), new_svc.split("\n")):
    raise SystemExit("services.py lost or reordered an original line")
rewrite(SVC, new_svc)
report["moves"].append({"path": SVC, "name": "KNOWN_COST_EVIDENCE_STATUSES",
                        "rep_range": [lo, hi], "rep_lines": hi - lo + 1,
                        "rep_gap_before": gap, "block_blob": blob_id,
                        "anchor_on_tip": "_plan_staleness", "insert_at_line": svc_at})

# --- main.py: add the two names to the import groups that already exist there ---
main_tip = show(head, MAIN)
new_main = main_tip
for group, name in (("from app.integrations.discovery.real_city import (", "canonical_cost_evidence"),
                    ("from app.services import (", "KNOWN_COST_EVIDENCE_STATUSES")):
    lines = new_main.split("\n")
    hits = [i for i, row in enumerate(lines) if row == group]
    if len(hits) != 1:
        raise SystemExit("import group not unique in main.py: {} ({})".format(group, len(hits)))
    if "\n    {},".format(name) in new_main:
        raise SystemExit(name + " is already imported in main.py")
    lines.insert(hits[0] + 1, "    {},".format(name))
    new_main = "\n".join(lines)
    report["imports"].append({"group": group, "name": name, "at_line": hits[0] + 2})
ast.parse(new_main)
if not is_subsequence(main_tip.split("\n"), new_main.split("\n")):
    raise SystemExit("main.py lost or reordered an original line")
rewrite(MAIN, new_main)

# --- the test itself, byte for byte ---
test_raw = git("show", "{}:{}".format(REP, TEST))
report["test"] = {"path": TEST, "bytes": len(test_raw),
                  "blob": blob(test_raw),
                  "already_on_tip": os.path.exists(os.path.join(W, TEST.replace("/", os.sep)))}
if report["test"]["already_on_tip"]:
    raise SystemExit("the test is already on the line")
if APPLY:
    with open(os.path.join(W, TEST.replace("/", os.sep)), "wb") as fh:
        fh.write(test_raw)
    if open(os.path.join(W, TEST.replace("/", os.sep)), "rb").read() != test_raw:
        raise SystemExit("the test did not land byte-exact")

json.dump(report, open(EVIDENCE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("APPLY" if APPLY else "DRY-RUN")
for row in report["moves"]:
    print("  {} ← {} 代表枝 {}..{}（{} 行，前置空行 {}）落点 {}".format(
        row["path"].split("/")[-1], row["name"], row["rep_range"][0], row["rep_range"][1],
        row["rep_lines"], row["rep_gap_before"], row.get("insert_at_line", at)))
for row in report["imports"]:
    print("  main.py 进口 + {} 于第 {} 行".format(row["name"], row["at_line"]))
print("  {} {} 字节 blob {}".format(TEST, report["test"]["bytes"], report["test"]["blob"][:12]))
print("evidence", EVIDENCE)
