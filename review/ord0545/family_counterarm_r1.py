"""ORD-0545 slice 2 counter-arms -- each one breaks exactly one claim the family move makes.

Three claims, three mutations, all run for real:

  M1  a refusal sentence can no longer be orphaned, because FAILURE_SENTENCE is typed as the key union.
      Mutation: misspell one map value.  Expect: `tsc` refuses and the diagnostic names it.  This is the
      leg the screen cannot show without a real server refusal, so the type is the proof -- and this
      arm is what stops that being an assertion.

  M2  every name in the union has both halves.
      Mutation: delete one table pair, leave the union name.  Expect: `tsc` red AND the G1 census arm red.

  M3  a moved sentence has one owner.
      Mutation: put one moved entry back into the Chinese book (a second owner, the state two orders ago).
      Expect: G1 red, naming the duplicate.

Every file is restored from the bytes read at the start and re-hashed, and the gate runs green again at
the end, so the tree this receipt describes is the tree that ships.

    D:/moodle/CityNexus/.venv/Scripts/python.exe review/ord0545/family_counterarm_r1.py
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import subprocess
import sys
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parents[2]
FRONTEND = ROOT / "frontend"
PANEL = FRONTEND / "src/features/poiimport/PoiImportPanel.tsx"
TABLE = FRONTEND / "src/features/poiimport/poiImportCopy.ts"
DIC = FRONTEND / "src/i18n/LocaleContext.tsx"
CONFIG = "playwright.ord0545-family.config.ts"
DATA = pathlib.Path("D:/moodle/_qoder_newlane_ord0545_data")
TAG = os.environ.get("CITYNEXUS_ORD0545_TAG", "r1")
BASE_TIP = os.environ.get("CITYNEXUS_ORD0545_BASE_TIP", "")
assert len(BASE_TIP) == 40 and all(c in "0123456789abcdef" for c in BASE_TIP), (
    "set CITYNEXUS_ORD0545_BASE_TIP to the 40-hex tip this was measured on")
RECEIPT = DATA / f"family_counterarms_{TAG}.json"

MAP_LINE = '  JOURNEY_NOT_FOUND: "errJourneyNotFound",'
PAIR_BLOCK = '  counts: {\n'
# an anchor that survives the move -- one of the 13 entries still in the Chinese book (that family
# belongs to PoiCandidateCard.tsx and to two dead lines, and this order moves none of them)
DICT_ANCHOR_PREFIX = '  "poiImport.cardSelect": "'
DUPLICATE_LINE = '  "poiImport.counts": "a second owner, injected by M3",\n'\


def tsc() -> dict:
    finished = subprocess.run(
        ["node", "node_modules/typescript/bin/tsc", "-p", "tsconfig.check.json", "--noEmit"],
        cwd=FRONTEND, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=900)
    out = finished.stdout + finished.stderr
    errors = [l for l in out.splitlines() if "error TS" in l]
    return {"rc": finished.returncode, "errors": len(errors),
            "names_counts_or_the_map": ("counts" in out) or ("errJourneyNotFound" in out),
            "first": errors[0][:180] if errors else ""}


def gate() -> dict:
    env = dict(os.environ)
    env.pop("DEEPSEEK_API_KEY", None)
    env["CITYNEXUS_ORD0545_TAG"] = TAG
    env["CITYNEXUS_ORD0545_BASE_TIP"] = BASE_TIP
    finished = subprocess.run(
        ["node", "node_modules/@playwright/test/cli.js", "test", "-c", CONFIG],
        cwd=FRONTEND, env=env, capture_output=True, text=True, encoding="utf-8",
        errors="replace", timeout=900)
    out = finished.stdout + finished.stderr
    titles = sorted({line.split("›")[-1].strip() for line in out.splitlines()
                     if line.strip().startswith(("x", "✘")) and "›" in line})
    passed = next((int(l.split("passed")[0].strip().split()[-1]) for l in reversed(out.splitlines())
                   if "passed" in l), 0)
    ran = next((l for l in out.splitlines() if l.startswith("Running ")), "")
    collected = int(ran.split()[1]) if ran.split()[1:2] and ran.split()[1].isdigit() else 0
    return {"rc": finished.returncode, "collected": collected, "passed": passed,
            "red_arms": titles, "summary": next((l.strip() for l in reversed(out.splitlines())
                                                 if " passed" in l or " failed" in l), "")}


def mutate(path: pathlib.Path, old: str, new: str, expect_present: int = 1) -> None:
    text = path.read_text(encoding="utf-8")
    assert text.count(old) == expect_present, (path.name, text.count(old), old[:40])
    path.write_bytes(text.replace(old, new, 1).encode("utf-8"))


def main() -> int:
    DATA.mkdir(parents=True, exist_ok=True)
    originals = {p: p.read_bytes() for p in (PANEL, TABLE, DIC)}
    before = {str(p): hashlib.sha256(b).hexdigest() for p, b in originals.items()}
    control_open = gate()

    # M1 -- the map names a key the table does not hold
    mutate(PANEL, MAP_LINE, MAP_LINE.replace("errJourneyNotFound", "errJourneyNotFoundRenamed"))
    m1_type, m1_gate = tsc(), gate()
    PANEL.write_bytes(originals[PANEL])

    # M2 -- a union name with no pair
    table_text = TABLE.read_text(encoding="utf-8")
    start = table_text.index(PAIR_BLOCK)
    end = table_text.index("\n  },\n", start) + len("\n  },\n")
    removed_pair = table_text[start:end]
    TABLE.write_bytes((table_text[:start] + table_text[end:]).encode("utf-8"))
    m2_type, m2_gate = tsc(), gate()
    TABLE.write_bytes(originals[TABLE])

    # M3 -- a moved sentence gets a second owner in the Chinese book
    anchor = next(line for line in DIC.read_text(encoding="utf-8").splitlines(keepends=True)
                  if line.startswith(DICT_ANCHOR_PREFIX) and line.endswith(',\n'))
    mutate(DIC, anchor, anchor + DUPLICATE_LINE)
    m3_gate = gate()
    DIC.write_bytes(originals[DIC])

    restored = all(hashlib.sha256(p.read_bytes()).hexdigest() == before[str(p)] for p in originals)
    control_close = gate()

    receipt = {
        "run_at": datetime.now(timezone.utc).isoformat(),
        "generation": {"tag": TAG, "base_tip": BASE_TIP},
        "control_open": control_open,
        "M1_map_names_a_missing_key": {
            "type_gate": m1_type, "gate": m1_gate,
            "killed": m1_type["rc"] != 0 and m1_type["names_counts_or_the_map"] and m1_gate["rc"] != 0,
            "claim": "a refusal sentence cannot be orphaned at run time -- the build refuses first",
        },
        "M2_union_name_without_a_pair": {
            "removed": removed_pair.splitlines()[0],
            "type_gate": m2_type, "gate": m2_gate,
            "killed": m2_type["rc"] != 0 and m2_gate["rc"] != 0,
            "claim": "every union name has both halves",
        },
        "M3_second_owner_reappears": {
            "gate": m3_gate,
            "killed": m3_gate["rc"] != 0 and any("G1" in t for t in m3_gate["red_arms"]),
            "claim": "a moved sentence has exactly one owner",
        },
        "restored_byte_identical": restored,
        "control_close": control_close,
    }
    RECEIPT.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n",
                       encoding="utf-8", newline="\n")
    print(f"receipt={RECEIPT}")
    print(f"control open={control_open['passed']}/{control_open['collected']} rc={control_open['rc']} | "
          f"M1 tsc rc={m1_type['rc']} names={m1_type['names_counts_or_the_map']} gate rc={m1_gate['rc']} | "
          f"M2 tsc rc={m2_type['rc']} gate rc={m2_gate['rc']} | M3 gate rc={m3_gate['rc']} reds={len(m3_gate['red_arms'])} | "
          f"restored={restored} | control close={control_close['passed']}/{control_close['collected']} rc={control_close['rc']}")
    return 0 if (
        control_open["rc"] == 0 and control_close["rc"] == 0 and restored
        and receipt["M1_map_names_a_missing_key"]["killed"]
        and receipt["M2_union_name_without_a_pair"]["killed"]
        and receipt["M3_second_owner_reappears"]["killed"]
        and control_close["collected"] >= 3
    ) else 1


if __name__ == "__main__":
    sys.exit(main())
