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


def run(command, cwd=TREE):
    proc = subprocess.run(command, cwd=str(cwd), shell=True, capture_output=True,
                          text=True, encoding="utf-8", errors="replace")
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


rc, out = run("git ls-remote origin " + LINE)
tip = out.split()[0]
head = run("git rev-parse HEAD")[1].strip()
base = run("git rev-parse 8bc584613cc5fb047453f497b2152f8ab5102ca9^{commit}")[1].strip()
mb_rc, mb = run("git merge-base HEAD " + tip)
mb = mb.strip()

changed = [l.strip() for l in run("git diff --name-only " + base + " HEAD")[1].splitlines() if l.strip()]
areas = {
    "frontend_src": [f for f in changed if f.startswith("frontend/src/")],
    "frontend_e2e": [f for f in changed if f.startswith("frontend/e2e/")],
    "frontend_other": [f for f in changed if f.startswith("frontend/")
                       and not f.startswith("frontend/src/") and not f.startswith("frontend/e2e/")],
    "review_tools": [f for f in changed if f.startswith("review/")],
    "backend": [f for f in changed if f.startswith("backend/")],
}

blob_head = run("git rev-parse HEAD:" + TARGET)[1].strip()
blob_tip = run("git rev-parse {0}:{1}".format(tip, TARGET))[1].strip()
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
lines.append("revlist_count_head_after_repair=" + run("git rev-list --count HEAD")[1].strip() + " 条")

text = "\n".join(lines) + "\n"
(READ / "delivery_face_r1.txt").write_text(text, encoding="utf-8", newline="\n")
print(text)
