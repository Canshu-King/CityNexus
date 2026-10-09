import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

TREE = Path(r"D:/moodle/_qoder_shuangshugong_0558")
FRONT = TREE / "frontend"
TARGET = FRONT / "src/features/execution/LiveRecovery.tsx"
READOUTS = TREE / "review/shuangshugong/ord0558_readouts"
CONFIG = "playwright.shuangshugong-0558.config.ts"
SPEC = "e2e/qoder-shuangshugong-0558-live-dedup-plural-r1.spec.ts"

# The line as it stands on the authoritative line, and the two hand-joined forms this order
# exists to remove.  Each mutant breaks exactly one count state, so an arm that never goes red
# is a ruler that measures nothing.
ORIGINAL_EN = '            : `Merged ${duplicateCount} identical ${englishCountNoun(duplicateCount, "suggestion")}.`}'
MUTANTS = [
    ("A_always_plural", '            : `Merged ${duplicateCount} identical suggestions.`}', "E1en_one"),
    ("B_always_singular", '            : `Merged ${duplicateCount} identical suggestion.`}', "E2en_two"),
]

BACKUP = READOUTS / "LiveRecovery.tsx.pristine"
shutil.copyfile(TARGET, BACKUP)
pristine_text = BACKUP.read_text(encoding="utf-8")
rows = []

for name, mutant_line, arm_expected_red in MUTANTS:
    assert ORIGINAL_EN in pristine_text, "the line to mutate is not on disk as read"
    mutated = pristine_text.replace(ORIGINAL_EN, mutant_line, 1)
    assert mutated != pristine_text
    TARGET.write_text(mutated, encoding="utf-8", newline="\n")

    evidence = READOUTS / ("mutant_" + name)
    evidence.mkdir(parents=True, exist_ok=True)
    env = {"CITYNEXUS_EVIDENCE_DIR": str(evidence).replace("\\", "/")}
    import os
    run_env = dict(os.environ)
    run_env.update(env)
    command = "npx playwright test --config {0} {1} -g {2}".format(CONFIG, SPEC, '"both count states"')
    proc = subprocess.run(command, cwd=str(FRONT), shell=True, capture_output=True,
                          text=True, encoding="utf-8", errors="replace", env=run_env)
    text = (proc.stdout or "") + (proc.stderr or "")
    (evidence / ("playwright_" + name + ".txt")).write_text(text, encoding="utf-8", newline="\n")
    passed = [line.strip() for line in text.splitlines() if line.strip().startswith("ok ")]
    failed = [line.strip() for line in text.splitlines() if line.strip().startswith("x ")]
    summary = [line.strip() for line in text.splitlines() if "passed" in line or "failed" in line]
    rows.append((name, proc.returncode, len(passed), len(failed), passed, failed, summary[-1] if summary else ""))

    # Restore, and prove the restore by hashing the bytes rather than trusting the write.
    shutil.copyfile(BACKUP, TARGET)
    check = subprocess.run("git hash-object src/features/execution/LiveRecovery.tsx",
                           cwd=str(FRONT), shell=True, capture_output=True, text=True)
    restored_hash = check.stdout.strip()
    rows.append(("restored_after_" + name, restored_hash, "", "", "", "", ""))
    print("mutant {0}: rc={1} passed={2} failed={3} red_arms={4}".format(
        name, proc.returncode, len(passed), len(failed), [f.split(">")[-1].strip() for f in failed]))
    print("   restored hash {0}".format(restored_hash))

with (READOUTS / "counter_arm_r1.txt").open("w", encoding="utf-8", newline="\n") as fh:
    fh.write("# ORD-0558 counter-arm: does this lane's instrument actually bite?\n")
    fh.write("# cmd: npx playwright test --config playwright.shuangshugong-0558.config.ts "
             "e2e/qoder-shuangshugong-0558-live-dedup-plural-r1.spec.ts -g \"both count states\"\n")
    fh.write("# each mutant is restored from LiveRecovery.tsx.pristine and re-hashed right after\n")
    for row in rows:
        if str(row[0]).startswith("restored_after_"):
            fh.write("state=restored mutant={0} git_hash_object={1}\n".format(row[0], row[1]))
        else:
            name, rc, npass, nfail, passed, failed, last = row
            fh.write("mutant={0} exit_code={1} green={2} red={3}\n".format(name, rc, npass, nfail))
            for line in passed:
                fh.write("  green 条 {0}\n".format(line))
            for line in failed:
                fh.write("  red 条 {0}\n".format(line))
            fh.write("  summary {0}\n".format(last))

print(json.dumps([r[:3] for r in rows], ensure_ascii=False))
