"""ORD-0545 counter-arms -- take the moved sentence away and show the screen's guard still bites.

The order rules that the channel badge moves from `t()` into the screen's own copy table, paired.  A
green gate after a move proves nothing by itself: the two failure modes a move actually creates are

  M1 -- the table loses the entry while the union keeps the name.  This is the shape the old
        dictionary fallback used to survive by printing `poiImport.channelLocal`.  Here the answer must
        be that the product cannot be built: `tsc` refuses, because the table is typed
        `Record<PoiImportCopyKey, { zh, en }>`.  So both halves of the claim are read: the type gate
        output, and the screen arm's rc.

  M2 -- the call site goes back to `t()` without the dictionary entry coming with it, i.e. the defect
        ORD-0533 closed is reopened.  B2 must go red AND the key name must be visible in the rendered
        text, which is the symptom in the commander's own words.

Both mutations are applied to one file at a time, reverted from the original bytes, and the reverted
file is re-hashed; then the whole arm set runs again expecting green, so the tree this receipt
describes is the tree that ships.

    D:/moodle/CityNexus/.venv/Scripts/python.exe review/ord0545/ord0545_counterarms_r1.py
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
TABLE = FRONTEND / "src/features/poiimport/poiImportCopy.ts"
PANEL = FRONTEND / "src/features/poiimport/PoiImportPanel.tsx"
CONFIG = "playwright.ord0533-copygate.config.ts"
DATA = pathlib.Path("D:/moodle/_qoder_newlane_ord0545_data")
TAG = os.environ.get("CITYNEXUS_ORD0545_TAG", "ord0545")
BASE_TIP = os.environ.get("CITYNEXUS_ORD0545_BASE_TIP", "")
assert len(BASE_TIP) == 40 and all(c in "0123456789abcdef" for c in BASE_TIP), (
    "set CITYNEXUS_ORD0545_BASE_TIP to the 40-hex tip this candidate was cut from"
)
RECEIPT = pathlib.Path(
    os.environ.get("CITYNEXUS_ORD0545_RECEIPT", "") or (DATA / f"counterarms_receipt_{TAG}.json")
)

TABLE_ENTRY_BLOCK = (
    "  channelLocal: {\n"
    '    zh: "本地解析，不打开链接",\n'
    '    en: "Local parse, no links opened",\n'
    "  },\n"
)
CALL_NEW = '          {poiImportCopy(locale, "channelLocal")}\n'
CALL_OLD = '          {t("poiImport.channelLocal")}\n'


def _digest(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _tsc() -> dict:
    finished = subprocess.run(
        ["node", "node_modules/typescript/bin/tsc", "-p", "tsconfig.check.json", "--noEmit"],
        cwd=FRONTEND,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=900,
    )
    output = finished.stdout + finished.stderr
    return {
        "rc": finished.returncode,
        "diagnostic_lines": len([line for line in output.splitlines() if "error TS" in line]),
        "names_channelLocal": "channelLocal" in output,
        "first_error": next((line for line in output.splitlines() if "error TS" in line), ""),
    }


def _arms(grep: str) -> dict:
    environment = dict(os.environ)
    environment.pop("DEEPSEEK_API_KEY", None)
    environment["CITYNEXUS_ORD0533_BASE_TIP"] = BASE_TIP
    environment["CITYNEXUS_ORD0533_TAG"] = TAG
    finished = subprocess.run(
        ["node", "node_modules/@playwright/test/cli.js", "test", "-c", CONFIG, "--grep", grep],
        cwd=FRONTEND,
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=900,
    )
    output = finished.stdout + finished.stderr
    titles = sorted(
        {
            line.split("›")[-1].strip()
            for line in output.splitlines()
            if line.strip().startswith(("x", "✘")) and "›" in line
        }
    )
    passed = next(
        (int(line.split("passed")[0].strip().split()[-1]) for line in reversed(output.splitlines()) if "passed" in line),
        0,
    )
    return {
        "rc": finished.returncode,
        "arms_that_ran": passed + len(titles),
        "red_arm_titles": titles,
        "key_name_rendered": "poiImport.channelLocal" in output,
        "summary": next(
            (line.strip() for line in reversed(output.splitlines()) if " passed" in line or " failed" in line),
            "",
        ),
    }


def _mutate(path: pathlib.Path, old: str, new: str, digest: str) -> None:
    text = path.read_text(encoding="utf-8")
    assert text.count(old) == 1, (path.name, text.count(old))
    path.write_text(text.replace(old, new, 1), encoding="utf-8", newline="\n" if "\r\n" not in text else "\r\n")
    assert digest != _digest(path), "the mutation was a no-op"


def main() -> int:
    DATA.mkdir(parents=True, exist_ok=True)
    originals = {path: path.read_bytes() for path in (TABLE, PANEL)}
    before = {str(path): _digest(path) for path in originals}

    control_before = _arms("ORD-0533")

    # M1: the table loses the entry, the union keeps the name.
    _mutate(TABLE, TABLE_ENTRY_BLOCK, "", before[str(TABLE)])
    m1_type = _tsc()
    m1_screen = _arms("B2")
    TABLE.write_bytes(originals[TABLE])

    # M2: the call goes back through t(), with no dictionary entry to catch it.
    _mutate(PANEL, CALL_NEW, CALL_OLD, before[str(PANEL)])
    m2_screen = _arms("B2")
    PANEL.write_bytes(originals[PANEL])

    restored = all(_digest(path) == before[str(path)] for path in originals)
    control_after = _arms("ORD-0533")

    receipt = {
        "run_at": datetime.now(timezone.utc).isoformat(),
        "generation": {"tag": TAG, "base_tip": BASE_TIP},
        "interpreter": sys.executable,
        "command_shape": f"node node_modules/@playwright/test/cli.js test -c {CONFIG} --grep <arm>",
        "files_mutated": [str(path.relative_to(ROOT)) for path in originals],
        "control_before_mutations": control_before,
        "M1_table_entry_removed": {
            "type_gate": m1_type,
            "screen_arm": m1_screen,
            "killed": m1_type["rc"] != 0 and m1_type["names_channelLocal"] and m1_screen["rc"] != 0,
            "reading": "the sentence cannot go missing at run time any more: the table is typed, so the "
                       "build refuses first and the screen arm is a second, independent red",
        },
        "M2_call_site_reopened_on_t": {
            "screen_arm": m2_screen,
            "key_name_rendered": m2_screen["key_name_rendered"],
            "killed": m2_screen["rc"] != 0 and m2_screen["key_name_rendered"],
            "reading": "reopening ORD-0533's defect still reproduces the exact symptom the commander "
                       "reported: the key name reaches the glass",
        },
        "restored_byte_identical": restored,
        "control_after_restore": control_after,
    }
    RECEIPT.parent.mkdir(parents=True, exist_ok=True)
    RECEIPT.write_text(json.dumps(receipt, indent=2, ensure_ascii=False), encoding="utf-8", newline="\n")
    print(f"receipt={RECEIPT}")
    print(
        f"control_before arms={control_before['arms_that_ran']} rc={control_before['rc']} | "
        f"M1 tsc rc={m1_type['rc']} names_key={m1_type['names_channelLocal']} errors={m1_type['diagnostic_lines']} "
        f"screen rc={m1_screen['rc']} | M2 screen rc={m2_screen['rc']} key_name_rendered={m2_screen['key_name_rendered']} | "
        f"restored={restored} | control_after arms={control_after['arms_that_ran']} rc={control_after['rc']} "
        f"summary={control_after['summary']}"
    )
    return 0 if (
        control_before["rc"] == 0
        and receipt["M1_table_entry_removed"]["killed"]
        and receipt["M2_call_site_reopened_on_t"]["killed"]
        and restored
        and control_after["rc"] == 0
        and control_after["arms_that_ran"] >= 4
    ) else 1


if __name__ == "__main__":
    sys.exit(main())
