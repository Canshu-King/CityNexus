import io, sys

P = "frontend/src/features/simulation/SimulationPanel.tsx"
with io.open(P, "r", encoding="utf-8", newline="") as f:
    lines = f.read().split("\n")

OLD = '?? "未知"'
NEW = '?? categoryLabel("UNKNOWN", zh)'
targets = [221, 440, 445, 470, 471, 541, 542, 798, 1077]

bad = []
for ln in targets:
    row = lines[ln - 1]
    if row.count(OLD) != 1:
        bad.append((ln, row.count(OLD)))
if bad:
    for ln, n in bad:
        sys.stdout.write("ABORT line=%d hits=%d\n" % (ln, n))
    sys.exit(3)

for ln in targets:
    lines[ln - 1] = lines[ln - 1].replace(OLD, NEW, 1)

text = "\n".join(lines)
whole = text.split("\n")
assert sum(r.count(OLD) for r in whole) == 0, "leftover hardcoded fallback"
assert sum(r.count(NEW) for r in whole) == len(targets), "new reads count mismatch"

anchor = 'import { useLocale } from "../../i18n/LocaleContext";'
idx = [i for i, r in enumerate(whole) if r == anchor]
assert len(idx) == 1, "import anchor not unique: %d" % len(idx)
whole.insert(
    idx[0] + 1, 'import { categoryLabel } from "../../i18n/travelerLabels";'
)
assert sum(r.count("categoryLabel(") for r in whole) == len(targets)

with io.open(P, "w", encoding="utf-8", newline="") as f:
    f.write("\n".join(whole))
sys.stdout.write("OK unknown_rewritten=%d import_lines=1\n" % len(targets))
