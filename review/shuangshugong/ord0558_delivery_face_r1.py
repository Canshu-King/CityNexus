import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

LIB = Path(r"D:/moodle/CityNexus")
TREE = Path(r"D:/moodle/_qoder_shuangshugong_0558")
READ = TREE / "review/shuangshugong/ord0558_readouts"
TARGET = "frontend/src/features/execution/LiveRecovery.tsx"
BRANCH = "refs/heads/review/双数工-0558-r1"
LINE = "refs/heads/mirror/integration-frontend-apple-pass1"
BASE_SHA = "8bc584613cc5fb047453f497b2152f8ab5102ca9"


def run(command, cwd=TREE):
    proc = subprocess.run(command, cwd=str(cwd), shell=True, capture_output=True,
                          text=True, encoding="utf-8", errors="replace")
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def must(command, cwd=TREE):
    """A reading that failed is not a zero: stop rather than report a false count.
    (`^{commit}` cannot be used here either -- cmd.exe eats the caret and git then
    answers with an error text that looks like output.)"""
    rc, out = run(command, cwd)
    if rc != 0:
        raise SystemExit("command failed rc={0}: {1}\n{2}".format(rc, command, out))
    return out


out = must("git ls-remote origin " + LINE)
tip = out.split()[0]
head = must("git rev-parse HEAD").strip()
base = must("git rev-parse " + BASE_SHA).strip()
mb_rc, mb = run("git merge-base HEAD " + tip)
if mb_rc != 0:
    raise SystemExit("merge-base failed rc=" + str(mb_rc))
mb = mb.strip()

changed = [l.strip() for l in must("git diff --name-only " + base + " " + head).splitlines() if l.strip()]
areas = {
    "frontend_src": [f for f in changed if f.startswith("frontend/src/")],
    "frontend_e2e": [f for f in changed if f.startswith("frontend/e2e/")],
    "frontend_other": [f for f in changed if f.startswith("frontend/")
                       and not f.startswith("frontend/src/") and not f.startswith("frontend/e2e/")],
    "review_tools": [f for f in changed if f.startswith("review/")],
    "backend": [f for f in changed if f.startswith("backend/")],
}

blob_head = must("git rev-parse HEAD:" + TARGET).strip()
blob_tip = must("git rev-parse {0}:{1}".format(tip, TARGET)).strip()
status_rc, status = run("git status --porcelain")
gate_summary = (READ / "gate_summary_r1.txt").read_text(encoding="utf-8")

lines = []
lines.append("# ORD-0558 shuangshugong delivery face")
lines.append("authoritative_tip_ls_remote=" + tip)
lines.append("command=git ls-remote origin " + LINE)
lines.append("my_branch_head=" + head)
lines.append("branch=" + BRANCH)
lines.append("my_base=" + base)
lines.append("merge_base_head_vs_tip=" + mb + " rc=" + str(mb_rc))
lines.append("blob_target_at_my_head=" + blob_head)
lines.append("blob_target_at_tip=" + blob_tip)
lines.append("product_bytes_identical_to_line=" + str(blob_head == blob_tip))
lines.append("changed_files_total=" + str(len(changed)) + " 条")
for name, files in areas.items():
    lines.append("area=" + name + " files=" + str(len(files)) + " 条")
lines.append("worktree_porcelain_lines=" + str(len([l for l in status.splitlines() if l.strip()])) + " 条")
lines.append("--- changed file names ---")
for f in changed:
    lines.append(f)
lines.append("--- gate summary read back from gate_summary_r1.txt ---")
lines.append(gate_summary.strip())
lines.append("--- shallow repair performed in D:/moodle/CityNexus/.git/shallow ---")
lines.append("removed_boundary=2fdb7892c982748ba49bd074de5ed6df190c83c5  (this lane's own first commit)")
lines.append("remaining_boundary_untouched=03aa82b728e7a84b99ec7633babf554aae3b453e")
lines.append("backup_file=D:/moodle/CityNexus/.git/shallow.bak_shuangshugong_0558")
lines.append("revlist_count_head_after_repair=" + must("git rev-list --count HEAD").strip() + " 条")
lines.append("note=this readout and the script that wrote it land in the commit right after the ones they list")

text = "\n".join(lines) + "\n"
(READ / "delivery_face_r1.txt").write_text(text, encoding="utf-8", newline="\n")
print(text)
