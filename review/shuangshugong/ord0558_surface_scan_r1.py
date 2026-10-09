import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(r"D:/moodle/_qoder_shuangshugong_0558")
TARGET = ROOT / "frontend/src/features/execution/LiveRecovery.tsx"
OUT = ROOT / "review/shuangshugong/ord0558_readouts/surface_r1.txt"

lines = TARGET.read_text(encoding="utf-8").splitlines()

# Shape the CN ruler walked: an interpolated count sitting right next to an English word.
COUNT_THEN_WORD = re.compile(r"\$\{[^}]*\}\s*[A-Za-z][A-Za-z]*")
HAS_RULER = re.compile(r"englishCountNoun|expandPluralMarkers|regularPlural")

hits = []
for index, text in enumerate(lines, start=1):
    if COUNT_THEN_WORD.search(text):
        hits.append((index, text.strip(), bool(HAS_RULER.search(text))))

with OUT.open("w", encoding="utf-8", newline="\n") as fh:
    fh.write("# ORD-0558 LiveRecovery.tsx english count+noun surface inventory\n")
    fh.write(f"# target={TARGET.as_posix()} total_lines={len(lines)}\n")
    fh.write("# rule: a line carrying ${...} immediately followed by an english word\n")
    fh.write(f"# surfaces_found={len(hits)} on_ruler={sum(1 for h in hits if h[2])} off_ruler={sum(1 for h in hits if not h[2])}\n")
    for index, text, ruler in hits:
        fh.write(f"L{index} on_ruler={ruler} | {text}\n")

print(OUT.read_text(encoding="utf-8"))
