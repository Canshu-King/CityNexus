import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(r"D:/moodle/_qoder_shuangshugong_0558")
E2E = ROOT / "frontend/e2e"
OUT = ROOT / "review/shuangshugong/ord0558_readouts/e2e_gap_r1.txt"

# Does anything on the authoritative line already assert this screen's dedup copy?
NEEDLES = ["live-deduped", "identical suggestion", "已合并", "duplicateCount"]

specs = sorted(E2E.glob("*.spec.ts"))
hits = {needle: [] for needle in NEEDLES}
for needle in NEEDLES:
    for spec in specs:
        text = spec.read_text(encoding="utf-8", errors="replace")
        for index, line in enumerate(text.splitlines(), start=1):
            if needle in line:
                hits[needle].append(f"{spec.name}:{index} | {line.strip()}")

with OUT.open("w", encoding="utf-8", newline="\n") as fh:
    fh.write("# ORD-0558 LiveRecovery dedup copy: does any existing e2e assert it?\n")
    fh.write(f"# dir={E2E.as_posix()} spec_files={len(specs)}\n")
    for needle in NEEDLES:
        fh.write(f"needle={needle} hits={len(hits[needle])} 条\n")
        for record in hits[needle]:
            fh.write(f"  {record}\n")

print(OUT.read_text(encoding="utf-8"))
