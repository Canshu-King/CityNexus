"""CMDR-DELIVER-0685 丁 · move the two lines my morning-order sibling left dangling.

`settings.lab_estimate_authority` is read at services.py:2156 on the line, but services.py never
imports `settings` and config.py never defines the field. Both bytes come from one generation
(0639d68b1efc...) named by the ruling, and this instrument refuses the whole run unless:

  * neither name exists on the tip yet (no duplicate delivery),
  * each block equals the reference bytes exactly,
  * the target files still parse, keep every original line in order, and bind the new names,
  * the field is inserted between the same two neighbours it has in the reference,
  * no second `settings = Settings()` is introduced (the CN warning in maps14/map_w1...).
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import subprocess
import sys

LIB = "D:/moodle/CityNexus"
W = "D:/moodle/_qoder_jianpanggong_0680"
REF = "0639d68b1efc5d08d7b12589a2f3a93cc001624f"
LINE_REF = "refs/heads/mirror/integration-frontend-apple-pass1"
CONFIG = "backend/app/core/config.py"
SVC = "backend/app/services.py"
EVIDENCE = W + "/review/jianpanggong-0685/move_evidence_r1.json"
APPLY = "--apply" in sys.argv


def git(*args, cwd=LIB):
    done = subprocess.run(["git", "-C", cwd] + list(args), capture_output=True)
    if done.returncode != 0:
        raise SystemExit("git {} rc={} {}".format(
            " ".join(args), done.returncode, done.stderr.decode("utf-8", "replace")[:200]))
    return done.stdout


def show(rev, path):
    return git("show", "{}:{}".format(rev, path)).decode("utf-8")


def blob_of(data):
    raw = data.encode("utf-8") if isinstance(data, str) else data
    return hashlib.sha1(b"blob %d\0" % len(raw) + raw).hexdigest()


def is_sub(old_lines, new_lines):
    it = iter(new_lines)
    return all(row in it for row in old_lines)


def bound(src):
    out = set()
    for node in ast.parse(src).body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            out.add(node.name)
        elif isinstance(node, ast.Assign):
            out.update(t.id for t in node.targets if isinstance(t, ast.Name))
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            out.add(node.target.id)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            out.update((a.asname or a.name.split(".")[0]) for a in node.names)
    return out


def take(rev, path, start, end):
    lines = show(rev, path).split("\n")
    body = "\n".join(lines[start - 1:end])
    return body, blob_of(body), lines


tip = git("ls-remote", "origin", LINE_REF).split(b"\t", 1)[0].decode().strip()
head = git("rev-parse", "HEAD", cwd=W).decode().strip()
if head != tip:
    raise SystemExit("the worktree is at {} while the line is at {}".format(head, tip))

report = {"tip": tip, "ref": REF, "moves": []}

# --- config.py: the field plus the two comment lines that explain it ---
cfg_tip = show(head, CONFIG)
if "lab_estimate_authority" in cfg_tip:
    raise SystemExit("config.py already carries the field")
if cfg_tip.count("settings = Settings()") != 1:
    raise SystemExit("the tip's config.py is not the shape I measured")
body, blob_id, ref_lines = take(REF, CONFIG, 87, 91)
ast.parse("class _X:\n" + body)  # the block must be valid inside a class body
# the neighbourhood proof: in the reference the block sits between exactly these two fields
if (not ref_lines[85].strip().startswith("real_city_mode:")
        or not ref_lines[91].strip().startswith("real_city_replay_snapshot_path:")):
    raise SystemExit("the reference neighbourhood moved; re-read the field range")

new_cfg, at = None, 0
cfg_lines = cfg_tip.split("\n")
for n, row in enumerate(cfg_lines, 1):
    if row.strip().startswith("real_city_mode:"):
        if not cfg_lines[n].strip().startswith("real_city_replay_snapshot_path:"):
            raise SystemExit("the tip does not have the reference's neighbour pair")
        new_cfg = "\n".join(cfg_lines[:n] + body.split("\n") + cfg_lines[n:])
        at = n + 1
        break
if new_cfg is None:
    raise SystemExit("real_city_mode is not on the tip; the transplant point is gone")
ast.parse(new_cfg)
if "lab_estimate_authority" not in "\n".join(
        line for line in new_cfg.split("\n") if "lab_estimate_authority" in line):
    raise SystemExit("the field did not land")
if new_cfg.count("settings = Settings()") != 1:
    raise SystemExit("a second settings instance appeared -- forbidden by maps14/map_w1 note")
if not is_sub(cfg_tip.split("\n"), new_cfg.split("\n")):
    raise SystemExit("config.py lost or reordered an original line")
report["moves"].append({"path": CONFIG, "ref_range": [87, 91], "ref_lines": 5,
                        "block_blob": blob_id, "follows_tip_line": n,
                        "lands_on_tip_lines": [n + 1, n + 5]})

# --- services.py: the import line ---
svc_tip = show(head, SVC)
if "from app.core.config import" in svc_tip:
    raise SystemExit("services.py already imports from app.core.config")
imp, imp_blob, _r = take(REF, SVC, 14, 14)
if imp != "from app.core.config import settings":
    raise SystemExit("the reference import line is not what the ruling said: " + imp)
svc_lines = svc_tip.split("\n")
anchor = [n for n, row in enumerate(svc_lines, 1)
          if row.startswith("from app.execution.traveler_twin import")]
if len(anchor) != 1:
    raise SystemExit("the import anchor in services.py is not unique: {}".format(anchor))
new_svc = "\n".join(svc_lines[:anchor[0] - 1] + [imp] + svc_lines[anchor[0] - 1:])
ast.parse(new_svc)
if "settings" not in bound(new_svc):
    raise SystemExit("settings did not bind in services.py")
if not set(bound(svc_tip)) <= bound(new_svc):
    raise SystemExit("services.py lost a top-level name")
if not is_sub(svc_tip.split("\n"), new_svc.split("\n")):
    raise SystemExit("services.py lost or reordered an original line")
report["moves"].append({"path": SVC, "ref_range": [14, 14], "ref_lines": 1,
                        "block_blob": imp_blob, "follows_tip_line": anchor[0] - 1,
                        "lands_on_tip_lines": [anchor[0], anchor[0]]})

for row in report["moves"]:
    src = new_cfg if row["path"] == CONFIG else new_svc
    if APPLY:
        with open(os.path.join(W, row["path"].replace("/", os.sep)), "w",
                  encoding="utf-8", newline="\n") as fh:
            fh.write(src)
        check = open(os.path.join(W, row["path"].replace("/", os.sep)), "rb").read()
        if blob_of(check) != blob_of(src):
            raise SystemExit("did not land byte-exact: " + row["path"])

os.makedirs(os.path.dirname(EVIDENCE), exist_ok=True)
json.dump(report, open(EVIDENCE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("APPLY" if APPLY else "DRY-RUN")
for row in report["moves"]:
    print("  {} ← 正本 {}:{}..{}（{} 行）blob {} ｜接现尖第 {} 行之后，占新文件 {} 行".format(
        row["path"], REF[:12], row["ref_range"][0], row["ref_range"][1], row["ref_lines"],
        row["block_blob"][:12], row["follows_tip_line"],
        "{}-{}".format(*row["lands_on_tip_lines"]) if row["lands_on_tip_lines"][0] != row["lands_on_tip_lines"][1] else row["lands_on_tip_lines"][0]))
print("evidence", EVIDENCE)
