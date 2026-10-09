"""Fresh-read every coordinate this receipt cites.  Nothing here is remembered: each number is
taken from the authoritative tip object or from this lane's branch tip at the moment it runs.
"""
import io
import re
import subprocess

TIP = "3ca65c3c42f7cd8f070fe3f43ab1487abad2fd75"
MYBR = "c1c83d563f9a0a58cae3f18e66ecd6e9ab5eb8a4"
REPO = "D:/moodle/CityNexus"


def blob(ref, path):
    out = subprocess.run(["git", "-C", REPO, "show", "%s:%s" % (ref, path)],
                         capture_output=True, encoding="utf-8", errors="replace")
    if out.returncode:
        raise SystemExit("cannot read %s:%s -> %s" % (ref, path, out.stderr.strip()[:200]))
    return out.stdout


def lines_having(text, pattern, label, limit=6):
    hits = []
    for idx, line in enumerate(text.split("\n"), start=1):
        if re.search(pattern, line):
            hits.append((idx, line.strip()[:110]))
    print("%s | pattern=%s | hits=%d" % (label, pattern, len(hits)))
    for idx, text_line in hits[:limit]:
        print("      line %d :: %s" % (idx, text_line))
    return hits


PANEL = "frontend/src/features/discovery/RealCityDiscoveryPanel.tsx"
tip_panel = blob(TIP, PANEL)
my_panel = blob(MYBR, PANEL)
lines_having(tip_panel, r"start_at\.slice\(0, 16\)", "TIP panel: raw ISO slice on screen")
lines_having(tip_panel, r"start_at\.slice\(0, 10\)", "TIP panel: day grouping (untouched)")
lines_having(my_panel, r"formatWhen", "MY panel: import plus call site")
lines_having(my_panel, r"start_at\.slice\(0, 16\)", "MY panel: raw slice remaining (expect none)")
print("MY panel line count = %d | TIP panel line count = %d"
      % (my_panel.count("\n") + 1, tip_panel.count("\n") + 1))

FMT = "frontend/src/lib/formatWhen.ts"
lines_having(blob(TIP, FMT), r"export function formatWhen", "TIP wrapper: export")
lines_having(blob(TIP, FMT), r"month: \"short\"", "TIP wrapper: the shape it emits")

DICT = "frontend/src/i18n/LocaleContext.tsx"
lines_having(blob(TIP, DICT), r"\"inbox\.timePending\":", "TIP dictionary: both arms of the reused key")

V8 = "frontend/src/app/V8Experience.tsx"
lines_having(blob(TIP, V8), r"Slicing the raw ISO string", "TIP: the repo's own statement that slicing is wrong")
lines_having(blob(TIP, V8), r"Always format instants through", "TIP: the same note's instruction")

SCHEMA = "backend/app/schemas.py"
lines_having(blob(TIP, SCHEMA), r"place_ids: list\[str\] = Field\(min_length", "TIP: compose contract, minimum picks")

SPEC = "frontend/e2e/qoder-ord0435-poi-batch-multiselect.spec.ts"
lines_having(blob(TIP, SPEC), r"produced no read-back block", "TIP: the pre-existing gate's receipt wait")

CTRL = None
with io.open("D:/moodle/CITYNEXUS_AGENT_CONTROL.md", encoding="utf-8") as handle:
    CTRL = handle.read()
lines_having(CTRL, r"除非你能贴出", "LEDGER: the order's own exception clause")
lines_having(CTRL, r"一枚文件一扇车道，先到先得", "LEDGER: claim rule")

ARM = "review/duanwagong/datefmt_0553_discovery_arm_r1.py"
lines_having(blob(MYBR, ARM), r"A1 row renders through formatWhen", "MY arm: first assertion")
lines_having(blob(MYBR, ARM), r"A2 raw ISO slice off the screen path", "MY arm: second assertion")
lines_having(blob(MYBR, ARM), r"A6 every key this panel calls", "MY arm: dictionary parity assertion")

STUB = "frontend/e2e/qoder-duanwagong-0553-batch-row-stub-r1.spec.ts"
lines_having(blob(MYBR, STUB), r"const UTC = ", "MY stub: the UTC-offset instant held")
lines_having(blob(MYBR, STUB), r"old_slice_would_have_printed", "MY stub: the before-reading recorded")

INST = "frontend/e2e/qoder-duanwagong-0553-batch-row-instant-r1.spec.ts"
lines_having(blob(MYBR, INST), r"branch: \"LAND\"", "MY write leg: the land branch")

for name in ("review/duanwagong/readouts/dwg0553__Tzh.json",
             "review/duanwagong/readouts/dwg0553stub__Szh.json"):
    text = blob(MYBR, name)
    print("EVIDENCE %s lines=%d" % (name, text.count("\n") + 1))
    lines_having(text, r"cell_on_screen|cells_on_screen|old_slice|server_start_at|expected_from", "   readings inside")
