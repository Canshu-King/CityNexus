"""Run the edited spec against the candidate bytes, then put the worktree back.

Comment-only edits inside a docstring can still break a file -- a stray quote would take the whole spec down
with it -- so the candidate is compiled and the two ORD-0500 modules are executed through the lane's own
arm (private database, shared store byte-checked) before I call this deliverable anything.  The worktree is
restored to HEAD afterwards and the restoration is verified by blob, not by trust.
"""
import json
import os
import shutil
import subprocess
import sys

LANE = r"D:/moodle/_qoder_phone_ord0485_20260930"
WT = os.path.join(LANE, "wt22")
PY = r"D:/moodle/CityNexus/.venv/Scripts/python.exe"
FILE = "backend/tests/test_qoder_ord0500_journey_refusal.py"
ENV = {k: v for k, v in os.environ.items() if k.upper() not in ("HTTP_PROXY", "HTTPS_PROXY")}
ENV["NO_PROXY"] = "*"
ENV["PYTHONIOENCODING"] = "utf-8"


def git(*a):
    p = subprocess.run(["git", "-C", WT] + list(a), capture_output=True, env=ENV, timeout=300)
    return p.returncode, p.stdout.decode("utf-8", "replace")


def main():
    tip = git("ls-remote", "--refs", "origin", "refs/heads/mirror/integration-frontend-apple-pass1"
              )[1].split()[0]
    before_head = git("rev-parse", "HEAD")[1].strip()
    dirty_before = [l for l in git("status", "--porcelain")[1].splitlines() if l.strip()]
    if dirty_before:
        raise SystemExit("ABORT_DIRTY_BEFORE " + json.dumps(dirty_before[:4], ensure_ascii=False))

    body = open(os.path.join(LANE, "run", "anchor_form_candidate.py"), encoding="utf-8").read()
    target = os.path.join(WT, FILE)
    shutil.copyfile(target, target + ".r26backup")
    open(target, "w", encoding="utf-8", newline="\n").write(body)
    rc_comp = subprocess.run([PY, "-c", "import ast;ast.parse(open(r'%s',encoding='utf-8').read())"
                              % target], capture_output=True, env=ENV).returncode
    env = dict(ENV)
    env["R6_BASE_TIP"] = tip
    p = subprocess.run([PY, os.path.join(LANE, "tools", "pytest_r6.py")], cwd=LANE,
                       capture_output=True, env=env, timeout=1800)
    arm_out = p.stdout.decode("utf-8", "replace") + p.stderr.decode("utf-8", "replace")

    git("restore", "--source=HEAD", "--worktree", "--", FILE)
    git("clean", "-fdq", "--", os.path.dirname(FILE))
    if os.path.exists(target + ".r26backup"):
        os.remove(target + ".r26backup")
    dirty_after = [l for l in git("status", "--porcelain")[1].splitlines() if l.strip()]
    after_head = git("rev-parse", "HEAD")[1].strip()
    blob_now = git("rev-parse", "HEAD:%s" % FILE)[1].strip()
    blob_tip = git("rev-parse", "%s:%s" % (tip, FILE))[1].strip()

    receipt = json.load(open(os.path.join(LANE, "evidence", "pytest_r6.json"), encoding="utf-8"))
    out = {"schema": "CNX_ORD0500_ANCHOR_FORM_SPEC_V1", "tool": "anchor_form_spec_r26", "tip": tip,
           "candidate_compiles": rc_comp == 0, "arm_rc": p.returncode,
           "arm_tail_line": (receipt.get("summary_lines") or [""])[-1],
           "arm_shared_store_untouched": receipt.get("shared_untouched"),
           "arm_rows_after_the_arms": receipt.get("checkin_rows_after_the_arms"),
           "arm_exit": receipt.get("exit"),
           "worktree_clean_after_restore": not dirty_after,
           "head_unchanged": before_head == after_head,
           "file_blob_after_restore": blob_now, "blob_equals_tip": blob_now == blob_tip,
           "arm_raw_tail": arm_out.strip().splitlines()[-1][:200] if arm_out.strip() else ""}
    dest = os.path.join(LANE, "evidence", "anchor_form_spec_r26.json")
    json.dump(out, open(dest, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print(json.dumps(out, ensure_ascii=False, indent=1))
    if not (out["candidate_compiles"] and out["arm_rc"] == 0 and out["worktree_clean_after_restore"]
            and out["head_unchanged"] and out["blob_equals_tip"]):
        raise SystemExit("ANCHOR_FORM_SPEC_NOT_ALL_TRUE")


if __name__ == "__main__":
    main()
