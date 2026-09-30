"""ORD-0533 反件 -- take the two dictionary lines away and prove the screen prints the key again.

The order asks for exactly this: "把新键拿掉，屏上必须重新出现键名".  A green copy gate that stays
green when the words are removed is not guarding anything, and the only way to know is to remove
them and look.

Two arms are run under the mutation, because they fail for two different reasons and the defect
reached the traveller in a way neither one alone would catch:
  B1 is static and goes red because the key is no longer defined in either book;
  B2 is the screen at 390x844 and goes red because the rendered text now contains
     `poiImport.channelLocal` -- the reported symptom, reproduced from the product's own fallback.

The dictionary file is restored from the original bytes and re-hashed, and the same arm is run again
expecting green, so the tree this receipt describes is the tree that ships.

    D:/moodle/CityNexus/.venv/Scripts/python.exe review/ord0533/ord0533_counterarms_r1.py
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
DICTIONARY = FRONTEND / "src/i18n/LocaleContext.tsx"
CONFIG = "playwright.ord0533-copygate.config.ts"
DATA = pathlib.Path("D:/moodle/_qoder_newlane_ord0533_data")
RECEIPT = pathlib.Path(
    os.environ.get("CITYNEXUS_ORD0533_RECEIPT", "") or (DATA / "ord0533_counterarms_receipt_r1.json")
)

ADDED_LINES = (
    '  "poiImport.channelLocal": "Local parse, no links opened",',
    '  "poiImport.channelLocal": "本地解析，不打开链接",',
)

# The generation every reading in this campaign is stamped with.  Passed in rather than guessed at,
# and required: the first cut left the three evidence files carrying base_tip="unknown", which makes
# a reader infer the provenance from a console log instead of finding it in the artifact.
TAG = os.environ.get("CITYNEXUS_ORD0533_TAG", "r1")
BASE_TIP = os.environ.get("CITYNEXUS_ORD0533_BASE_TIP", "")
assert len(BASE_TIP) == 40 and all(
    c in "0123456789abcdef" for c in BASE_TIP
), "set CITYNEXUS_ORD0533_BASE_TIP to the 40-hex tip this candidate was cut from"


def run(grep: str) -> dict:
    environment = dict(os.environ)
    environment.pop("DEEPSEEK_API_KEY", None)
    # Every reading this campaign writes carries the generation it came from.  The first cut forgot
    # to pass these through, so the evidence files landed with base_tip="unknown" -- a reading whose
    # provenance has to be inferred from a console log is not a delivery.
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
        (
            int(line.split("passed")[0].strip().split()[-1])
            for line in reversed(output.splitlines())
            if "passed" in line
        ),
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


def main() -> int:
    DATA.mkdir(parents=True, exist_ok=True)
    original = DICTIONARY.read_bytes()
    digest_before = hashlib.sha256(original).hexdigest()
    text = original.decode("utf-8")
    for line in ADDED_LINES:
        assert text.count(line) == 1, (line[:48], text.count(line))

    mutated = text
    for line in ADDED_LINES:
        mutated = mutated.replace(line + "\n", "", 1)
    DICTIONARY.write_bytes(mutated.encode("utf-8"))
    try:
        screen = run("390 宽")
        static = run("B1")
    finally:
        DICTIONARY.write_bytes(original)
    restored = hashlib.sha256(DICTIONARY.read_bytes()).hexdigest() == digest_before

    # The control run must be a run that actually ran something.  The first cut grepped a Chinese
    # phrase that appears only in this file's comments, never in the English test titles, so it
    # selected zero tests, exited 0 and reported an empty summary -- a control that controls nothing.
    control = run("ORD-0533")
    if control["arms_that_ran"] < 3:
        print(f"CONTROL_RAN_TOO_FEW_ARMS: {control}")

    receipt = {
        "run_at": datetime.now(timezone.utc).isoformat(),
        "command_shape": f"node node_modules/@playwright/test/cli.js test -c {CONFIG} --grep <arm>",
        "dictionary_sha256_before": digest_before,
        "dictionary_sha256_after_restore": hashlib.sha256(DICTIONARY.read_bytes()).hexdigest(),
        "restored_byte_identical": restored,
        "mutation": {
            "lines_removed": list(ADDED_LINES),
            "removed_count": len(ADDED_LINES),
        },
        "B2_screen_under_mutation": screen,
        "B1_static_under_mutation": static,
        "control_run_after_restore": control,
        "screen_arm_killed": screen["rc"] != 0 and screen["key_name_rendered"],
        "static_arm_killed": static["rc"] != 0,
    }
    RECEIPT.parent.mkdir(parents=True, exist_ok=True)
    RECEIPT.write_text(json.dumps(receipt, indent=2, ensure_ascii=False), encoding="utf-8", newline="\n")
    print(f"receipt={RECEIPT}")
    print(
        f"B2 screen red under mutation={screen['rc'] != 0} key_name_rendered={screen['key_name_rendered']} "
        f"| B1 static red={static['rc'] != 0} | restored={restored} "
        f"| control arms={control['arms_that_ran']} rc={control['rc']} summary={control['summary']}"
    )
    return (
        0
        if (
            receipt["screen_arm_killed"]
            and receipt["static_arm_killed"]
            and restored
            and control["arms_that_ran"] >= 3
            and control["rc"] == 0
        )
        else 1
    )


if __name__ == "__main__":
    sys.exit(main())
