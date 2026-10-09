"""Generate this lane's ledger block.

Every coordinate in the text is verified against a git object at run time before the file is
written: an anchor whose line does not contain what this block says it contains aborts the run
(no remembered line numbers, no shipped block with a dead coordinate).
"""
import io
import os
import re
import subprocess
import sys

REPO = "D:/moodle/CityNexus"
TIP_NOW = subprocess.run(["git", "-C", REPO, "ls-remote", "origin",
                          "refs/heads/mirror/integration-frontend-apple-pass1"],
                         capture_output=True, text=True, encoding="utf-8").stdout.split()[0]
BASE = "3ca65c3c42f7cd8f070fe3f43ab1487abad2fd75"
MYTIP = subprocess.run(["git", "-C", REPO, "ls-remote", "--refs", "origin",
                        "refs/heads/review/短瓦工-0553-r1"],
                       capture_output=True, text=True, encoding="utf-8").stdout.split()[0]
CHANG = "676b4c5a950c60c65a013ee3990254b07ef73484"
SAFE = "046adb97d62d32f42cdbccb897d4dea2e5576dd5"
LINK = "62f4ce8cfe000a4548000f9a6dd1e1bfa17aa668"

PANEL = "frontend/src/features/discovery/RealCityDiscoveryPanel.tsx"
FMT = "frontend/src/lib/formatWhen.ts"
DICT = "frontend/src/i18n/LocaleContext.tsx"
V8 = "frontend/src/app/V8Experience.tsx"
SCHEMA = "backend/app/schemas.py"
Q4SPEC = "frontend/e2e/qoder-ord0435-poi-batch-multiselect.spec.ts"
ARM = "review/duanwagong/datefmt_0553_discovery_arm_r1.py"
INST = "frontend/e2e/qoder-duanwagong-0553-batch-row-instant-r1.spec.ts"
STUB = "frontend/e2e/qoder-duanwagong-0553-batch-row-stub-r1.spec.ts"
EV_ZH = "review/duanwagong/readouts/dwg0553__Tzh.json"
EV_EN = "review/duanwagong/readouts/dwg0553__Ten.json"
EV_SZH = "review/duanwagong/readouts/dwg0553stub__Szh.json"
EV_SEN = "review/duanwagong/readouts/dwg0553stub__Sen.json"
PROBE = "frontend/tools/cnx_0553_shape_probe_r1.cjs"

_cache = {}


def blob(ref, path):
    key = (ref, path)
    if key not in _cache:
        out = subprocess.run(["git", "-C", REPO, "show", "%s:%s" % (ref, path)],
                             capture_output=True, text=True, encoding="utf-8", errors="replace")
        if out.returncode:
            raise SystemExit("ABORT cannot read %s:%s :: %s" % (ref, path, out.stderr.strip()[:200]))
        _cache[key] = out.stdout
    return _cache[key]


def at(ref, path, needle, label, occ=0):
    """Fresh line number of the `occ`-th line containing `needle`; aborts if absent."""
    hits = [i for i, line in enumerate(blob(ref, path).split("\n"), start=1) if needle in line]
    if len(hits) <= occ:
        raise SystemExit("ABORT anchor not found: %s :: %r in %s:%s" % (label, needle, ref[:9], path))
    return hits[occ]


A = {}
A["panel_before"] = at(BASE, PANEL, 'row.start_at.slice(0, 16).replace("T", " ")', "before")
A["panel_after"] = at(MYTIP, PANEL, "formatWhen(row.start_at", "after")
A["panel_import"] = at(MYTIP, PANEL, 'import { formatWhen } from "../../lib/formatWhen";', "import")
A["panel_zone"] = at(MYTIP, PANEL, "`formatWhen` renders the instant in the device zone", "zone note")
A["panel_recovery_key"] = at(MYTIP, PANEL, 't("recovery.technicalDetail")', "cross-namespace precedent")
A["fmt_export"] = at(TIP_NOW, FMT, "export function formatWhen", "wrapper export")
A["fmt_shape"] = at(TIP_NOW, FMT, 'month: "short"', "wrapper shape")
A["dict_en"] = at(TIP_NOW, DICT, '"inbox.timePending": "time pending"', "dictionary en")
A["dict_zh"] = at(TIP_NOW, DICT, u'"inbox.timePending": "时间待定"', "dictionary zh")
A["v8_defect"] = at(TIP_NOW, V8, "Slicing the raw ISO string", "in-repo defect note")
A["v8_rule"] = at(TIP_NOW, V8, "Always format instants through", "in-repo instruction")
A["schema_min"] = at(TIP_NOW, SCHEMA, "place_ids: list[str] = Field(min_length=2", "compose contract")
A["q4_wait"] = at(TIP_NOW, Q4SPEC, "produced no read-back block", "pre-existing gate wait")
A["arm_a1"] = at(MYTIP, ARM, '"A1 row renders through formatWhen', "arm A1")
A["arm_a2"] = at(MYTIP, ARM, '"A2 raw ISO slice off the screen path', "arm A2")
A["arm_a6"] = at(MYTIP, ARM, '"A6 every key this panel calls', "arm A6")
A["inst_land"] = at(MYTIP, INST, 'branch: "LAND"', "write leg land branch")
A["stub_utc"] = at(MYTIP, STUB, 'const UTC = "2026-10-10T02:00:00+00:00"', "stub UTC instant")
A["ev_zh_cell"] = at(MYTIP, EV_ZH, '"cell_on_screen"', "zh reading")
A["ev_zh_old"] = at(MYTIP, EV_ZH, '"old_slice_would_have_printed"', "zh before-reading")
A["ev_en_cell"] = at(MYTIP, EV_EN, '"cell_on_screen"', "en reading")
A["ev_szh_cells"] = at(MYTIP, EV_SZH, '"cells_on_screen"', "stub zh cells")
A["ev_sen_cells"] = at(MYTIP, EV_SEN, '"cells_on_screen"', "stub en cells")
A["probe_site"] = at(LINK, PROBE, 'RealCityDiscoveryPanel.tsx:537', "the probe's row for this site")

# The order's own exception clause, read from the live ledger (not remembered).
with io.open("D:/moodle/CITYNEXUS_AGENT_CONTROL.md", encoding="utf-8") as handle:
    LEDGER = handle.read().split("\n")
ledger_exc = [i for i, line in enumerate(LEDGER, start=1)
              if "除非你能贴出「原来那版本来就是错的」" in line]
if not ledger_exc:
    raise SystemExit("ABORT the order's exception clause is not where this block says it is")
A["order_exception"] = ledger_exc[0]
ledger_claim = [i for i, line in enumerate(LEDGER, start=1)
                if "一枚文件一扇车道，先到先得" in line and "ORD-0553" in line]
A["order_claim_rule"] = ledger_claim[0]

closing = open(r"D:/moodle/_qoder_cmdr_ref_20260921/live_checks/CLOSING_LINE.txt", "rb").read().decode("utf-8").strip()
if len(closing.encode("utf-8")) != 83:
    raise SystemExit("ABORT closing line changed size: %d bytes" % len(closing.encode("utf-8")))

print("anchors verified: %d" % len(A))
for k in sorted(A):
    print("   %s = %d" % (k, A[k]))
print("TIP_NOW=%s MYTIP=%s BASE=%s" % (TIP_NOW, MYTIP, BASE))

with io.open("D:/moodle/_dwg_ctl10/anchors.json", "w", encoding="utf-8") as handle:
    handle.write(__import__("json").dumps({"anchors": A, "TIP_NOW": TIP_NOW, "MYTIP": MYTIP,
                                           "BASE": BASE, "CHANG": CHANG, "SAFE": SAFE,
                                           "LINK": LINK, "closing": closing}, ensure_ascii=False, indent=1))
