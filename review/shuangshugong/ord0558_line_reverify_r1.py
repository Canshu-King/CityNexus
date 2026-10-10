import os
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

TREE = Path(r"D:/moodle/_qoder_shuangshugong_0558")
FRONT = TREE / "frontend"
READ = TREE / "review/shuangshugong/ord0558_readouts"
LINE = "refs/heads/mirror/integration-frontend-apple-pass1"
TARGET = "frontend/src/features/execution/LiveRecovery.tsx"


def run(command, env_extra=None):
    env = dict(os.environ)
    env.update(env_extra or {})
    proc = subprocess.run(command, cwd=str(FRONT), shell=True, capture_output=True,
                          text=True, encoding="utf-8", errors="replace", env=env)
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


rows = []
rows.append("# ORD-0558 shuangshugong: this lane's instrument re-run ON the authoritative line")
tip_rc, tip_out = run("git ls-remote origin " + LINE)
tip = tip_out.split()[0] if tip_out.strip() else "unreadable"
rows.append("authoritative_tip=" + tip)
rows.append("worktree_head=" + run("git rev-parse HEAD")[1].strip())
rows.append("target_blob_on_line=" + run("git rev-parse HEAD:" + TARGET)[1].strip())

rc_type, out_type = run("npm run typecheck:all")
rows.append("gate_typecheck_exit_code=" + str(rc_type))

evidence = READ / "run_on_the_line"
evidence.mkdir(parents=True, exist_ok=True)
rc_spec, out_spec = run(
    "npx playwright test --config playwright.shuangshugong-0558.config.ts",
    {"CITYNEXUS_EVIDENCE_DIR": str(evidence).replace("\\", "/"),
     "CITYNEXUS_SPEC": "qoder-shuangshugong-0558-live-dedup-plural-r1"},
)
(evidence / "playwright_on_the_line.txt").write_text(out_spec, encoding="utf-8", newline="\n")
lines = [l.strip() for l in out_spec.splitlines()]
rows.append("spec_exit_code=" + str(rc_spec))
rows.append("spec_green=" + str(len([l for l in lines if l.startswith("ok ")])) + " 条")
rows.append("spec_red=" + str(len([l for l in lines if l.startswith("x ")])) + " 条")
for arm in [l for l in lines if l.startswith("ok ") or l.startswith("x ")]:
    rows.append("arm: " + arm.split(">")[-1].strip())
rows.append("summary: " + ([l for l in lines if "passed" in l or "failed" in l][-1] if any("passed" in l or "failed" in l for l in lines) else "(none)"))

text = "\n".join(rows) + "\n"
(READ / "line_reverify_r1.txt").write_text(text, encoding="utf-8", newline="\n")
print(text)
