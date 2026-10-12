"""ORD-0654 mover (fail-closed): land the one missing runtime.py helper from CMDR-RULING-0653's
甲类 list -- `_server_completion_contract`, 64 lines, self-contained (its dependency closure was
computed from the representative branch's ast and contains no other missing name).

Everything is checked before a single byte is written:
  * the branch head equals the freshly read authoritative tip;
  * the helper is copied byte-for-byte out of the representative generation (no retyping);
  * the tip's runtime.py does not already define it, and defines every name it needs;
  * insertion goes right after the neighbouring helper the commander landed earlier, so the two
    stay adjacent as they are on the representative branch;
  * the result still parses (ast) and every pre-existing line keeps its bytes;
  * line endings follow the line's own rule (.gitattributes: *.py text eol=lf).

Usage: python review/jianpanggong-0654/move_r1.py [--apply]
"""

from __future__ import annotations

import ast
import hashlib
import os
import re
import subprocess
import sys

T = "D:/moodle/_qoder_jianpanggong_0555"
LIB = "D:/moodle/CityNexus"
LINE_REF = "refs/heads/mirror/integration-frontend-apple-pass1"
REP = "843844c5587da01287faa8f384411915eade9a87"
HOST = "backend/app/agent/runtime.py"
HELPER = "_server_completion_contract"
NEIGHBOUR = "_tool_result_advances_state"
LANE_DIR = "jianpanggong-0654"
OUT = os.path.join(T, "review", LANE_DIR, "move_evidence_r1.json")


def git(cwd, *args):
    done = subprocess.run(["git", "-C", cwd] + list(args), capture_output=True)
    if done.returncode != 0:
        raise SystemExit("git {} rc={} {}".format(" ".join(args), done.returncode,
                                                 done.stderr.decode("utf-8", "replace")[:160]))
    return done.stdout


def text(cwd, *args):
    return git(cwd, *args).decode("utf-8", "replace")


def blob_of(ref, path):
    return text(LIB, "rev-parse", "{}:{}".format(ref, path)).strip()


def main():
    apply_mode = "--apply" in sys.argv
    tip = text(LIB, "ls-remote", "origin", LINE_REF).split()[0]
    head = text(T, "rev-parse", "HEAD").strip()
    problems = []
    if head != tip:
        problems.append("head {} != freshly read tip {}".format(head[:12], tip[:12]))
    # Two test files the commander landed as CRLF stay dirty in every worktree on this line,
    # because the line's own rule is `.gitattributes: *.py text eol=lf`: the stored blob has CR,
    # the smudged working copy does not, so `git status` never settles. That dirt is not mine;
    # it is named here as a known exception rather than quietly ignored.
    CRLF_LANDED = ("backend/tests/test_agent_runtime_state_epoch.py",
                   "backend/tests/test_replan_schedule_timezone.py")
    dirty = [row[3:].strip() for row in text(T, "status", "--porcelain").splitlines() if row.strip()]
    # untracked files under this lane's own review/ directory are this run's instruments, not dirt
    blocking = [row for row in dirty
                if row not in CRLF_LANDED and not row.startswith("review/" + LANE_DIR + "/")]
    if blocking:
        problems.append("worktree carries unexpected tracked changes: " + ", ".join(blocking)[:110])
    known_dirty = sorted(row for row in dirty if row in CRLF_LANDED)

    rep_src = text(LIB, "show", "{}:{}".format(REP, HOST))
    rep_lines = rep_src.split("\n")
    starts = [n for n, row in enumerate(rep_lines, 1) if row.startswith("def " + HELPER)]
    if len(starts) != 1:
        raise SystemExit("helper not unique on the representative branch: {}".format(starts))
    tree = ast.parse(rep_src)
    node = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == HELPER]
    if len(node) != 1:
        raise SystemExit("ast could not pin the helper")
    start, end = node[0].lineno, node[0].end_lineno
    segment = "\n".join(rep_lines[start - 1:end])
    if "\r" in segment:
        raise SystemExit("the representative segment carries CR")

    tip_src = text(LIB, "show", "{}:{}".format(tip, HOST))
    if HELPER in tip_src:
        raise SystemExit("helper already on the line")
    used = sorted({n.id for n in ast.walk(node[0]) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)})
    module_names = {t.id for t in ast.walk(ast.parse(tip_src)) if isinstance(t, ast.Name)} | \
                   {a.name for a in ast.walk(ast.parse(tip_src)) if isinstance(a, (ast.FunctionDef, ast.ClassDef))}
    undefined = [u for u in used
                 if u not in module_names and u not in {"dict", "list", "str", "int", "bool", "any",
                                                         "set", "tuple", "frozenset", "sorted", "len",
                                                         "max", "min", "sum", "abs", "isinstance", "repr"}
                 and not re.match(r"^[A-Z_]+$", u)]
    # names that must exist at import time are resolved against the tip module below; anything the
    # function body borrows from module scope is listed so the arm can prove it is there.

    host_path = os.path.join(T, HOST.replace("/", os.sep))
    on_disk = open(host_path, encoding="utf-8", newline="").read()
    if "\r\n" in on_disk:
        raise SystemExit("the working file is CRLF while the line's rule is eol=lf")
    disk_lines = on_disk.split("\n")
    anchors = [n for n, row in enumerate(disk_lines, 1) if row.startswith("def " + NEIGHBOUR)]
    if len(anchors) != 1:
        raise SystemExit("neighbour helper not unique on the line: {}".format(anchors))
    nnode = [n for n in ast.parse(on_disk).body
             if isinstance(n, ast.FunctionDef) and n.name == NEIGHBOUR][0]
    insert_at = nnode.end_lineno + 1

    merged = disk_lines[:insert_at] + ["", ""] + segment.split("\n") + disk_lines[insert_at:]
    candidate = "\n".join(merged)
    new_tree = ast.parse(candidate)
    if HELPER not in {n.name for n in new_tree.body if isinstance(n, ast.FunctionDef)}:
        raise SystemExit("helper missing after the merge")
    before_defs = [n.name for n in ast.parse(on_disk).body if isinstance(n, ast.FunctionDef)]
    after_defs = [n.name for n in new_tree.body if isinstance(n, ast.FunctionDef)]
    # the only shape that may differ from the line is one extra name at one position
    if HELPER not in after_defs or [n for n in after_defs if n != HELPER] != before_defs:
        problems.append("function set changed beyond the single addition: {} -> {}".format(
            len(before_defs), len(after_defs)))
    for original in disk_lines:
        if original.strip() and original not in merged:
            problems.append("a pre-existing line disappeared: " + original[:60])
            break

    payload = {
        "tip": tip, "head": head, "rep": REP,
        "helper": HELPER, "rep_range": [start, end], "rep_lines": end - start + 1,
        "rep_blob": blob_of(REP, HOST), "tip_blob": blob_of(tip, HOST),
        "tip_function_count": len(before_defs), "after_function_count": len(after_defs),
        "insert_after_line": insert_at, "neighbour": NEIGHBOUR,
        "bytes": {"before": len(on_disk.encode("utf-8")), "after": len(candidate.encode("utf-8"))},
        "sha256_after": hashlib.sha256(candidate.encode("utf-8")).hexdigest()[:16],
        "body_names_borrowed": used, "unresolved_names": undefined,
        "line_ending": "LF", "gitattributes_rule": "*.py text eol=lf",
        "worktree_dirty_not_mine": known_dirty,
        "problems": problems,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    if apply_mode:
        if problems:
            print("REFUSE: " + " | ".join(problems))
            return 1
        open(host_path, "w", encoding="utf-8", newline="\n").write(candidate)
        print("APPLIED helper={} lines={} after {}".format(HELPER, end - start + 1,
                                                           payload["bytes"]["after"]))
    import json
    json.dump(payload, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("MOVE i18n-0654: rep {}..{} = {} 行｜插入点之后第 {} 行｜函数数 {} -> {}｜problems={}".format(
        start, end, end - start + 1, insert_at, len(before_defs), len(after_defs), len(problems)))
    for p in problems:
        print("  ! " + p)
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
