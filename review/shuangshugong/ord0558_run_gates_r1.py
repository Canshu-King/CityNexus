import subprocess
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FRONT = Path(r"D:/moodle/_qoder_shuangshugong_0558/frontend")
OUT = Path(r"D:/moodle/_qoder_shuangshugong_0558/review/shuangshugong/ord0558_readouts")
OUT.mkdir(parents=True, exist_ok=True)

# (readout file, human label, command)
STEPS = [
    ("gate_typecheck_r1.txt", "typecheck:all", "npm run typecheck:all"),
    ("gate_build_r1.txt", "build", "npm run build"),
]

log = []
for name, label, command in STEPS:
    started = time.strftime("%H:%M:%S")
    proc = subprocess.run(command, cwd=str(FRONT), shell=True, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    finished = time.strftime("%H:%M:%S")
    text = (proc.stdout or "") + (proc.stderr or "")
    lines = [line for line in text.splitlines() if line.strip()]
    path = OUT / name
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write("# ORD-0558 shuangshugong frontend gate readout\n")
        fh.write("label={0}\n".format(label))
        fh.write("cwd={0}\n".format(FRONT.as_posix()))
        fh.write("command={0}\n".format(command))
        fh.write("started={1} finished={2}\n".format(label, started, finished))
        fh.write("exit_code={0}\n".format(proc.returncode))
        fh.write("output_line_count={0}\n".format(len(lines)))
        fh.write("--- output verbatim ---\n")
        fh.write(text if text.strip() else "(no output)\n")
    log.append((label, proc.returncode, len(lines), name))
    print("{0} exit_code={1} output_lines={2} -> {3}".format(label, proc.returncode, len(lines), name))

with (OUT / "gate_summary_r1.txt").open("w", encoding="utf-8", newline="\n") as fh:
    fh.write("# ORD-0558 frontend gates, one line per gate\n")
    for label, code, count, name in log:
        fh.write("gate={0} exit_code={1} output_lines={2} readout={3}\n".format(label, code, count, name))
print("summary -> gate_summary_r1.txt")
