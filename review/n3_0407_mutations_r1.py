#!/usr/bin/env python3
"""ORD-0407 -- counter-examples: every cell in the gate has to be able to go red for its own reason.

Each arm edits one product or contract file, runs only the cell that arm targets (`-g`), reads the
runner's own log for which cells reddened by name, then puts the bytes back and re-hashes.  An arm that
reddens *everything* proves nothing about which cell does the work, so the verdict requires the
targeted cell by name.

    python review/n3_0407_mutations_r1.py            # all arms
    python review/n3_0407_mutations_r1.py M4_good_news_gains_a_button

Receipts go to review/evidence/ord0407/mutations_r1.json, and the file records the head and the
frontend tree each arm ran on, because a receipt that names no tree cannot be re-checked later.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import re
import subprocess
import sys

WT = r"D:/moodle/_qoder_n3_ord0357"
MAPCOPY = os.path.join(WT, "frontend", "src", "i18n", "mapPanelCopy.ts")
V8 = os.path.join(WT, "frontend", "src", "app", "V8Experience.tsx")
LIVE = os.path.join(WT, "frontend", "src", "features", "execution", "LiveRecovery.tsx")
CONTRACT = os.path.join(WT, "contracts", "openapi.yaml")
SPEC = "e2e/qoder-ord0407-empty-state-actions.spec.ts"

ZH_TIER = "「添加活动地点」这扇门，这一版没有（NOT_AVAILABLE）。"
BUTTON_BLOCK = """                <button
                  type="button"
                  className="v8-quiet-button"
                  data-testid="bookings-no-stay-action"
                  onClick={() => onNavigate("stay")}
                >
                  {t("bookings.noStayAction")}
                </button>
"""
NO_PROPOSAL = """          {zh ? "当前没有需要你决定的调整。" : "There is nothing for you to decide right now."}
        </p>"""
PROPOSAL_WITH_BUTTON = """          {zh ? "当前没有需要你决定的调整。" : "There is nothing for you to decide right now."}
          <button type="button" data-testid="mutation-fake-action">
            {zh ? "反件：给好消息格装一枚按钮" : "mutation: a button on a good-news cell"}
          </button>
        </p>"""
PROPOSAL_PUSHED = """          {zh ? "当前没有需要你决定的调整。" : "There is nothing for you to decide right now."}
        </p>
        <div style={{ height: 260 }} data-testid="mutation-spacer" />"""
CREATION_DOOR = """  /journeys/{journey_id}/activities:
    post:
      operationId: createJourneyActivity
      description: mutation arm -- a door that would let a traveller name a place
      responses:
        '201':
          description: created
"""
ACTIVITY_PATH_ANCHOR = "  /journeys/{journey_id}/activities/{activity_id}/complete:\n"

MUTATIONS = [
    {"id": "M1_tier_word_removed", "file": MAPCOPY, "cell": "C2",
     "find": ZH_TIER, "put": "「添加活动地点」这扇门，这一版没有。"},
    {"id": "M2_false_promise_put_back", "file": MAPCOPY, "cell": "C2",
     "find": ZH_TIER, "put": "添加活动地点或开启定位后，地图会显示正确的城市。"},
    {"id": "M3_bookings_action_removed", "file": V8, "cell": "C4", "find": BUTTON_BLOCK, "put": ""},
    {"id": "M4_good_news_gains_a_button", "file": LIVE, "cell": "C5",
     "find": NO_PROPOSAL, "put": PROPOSAL_WITH_BUTTON},
    {"id": "M5_action_pushed_below_the_line", "file": V8, "cell": "C4",
     "find": '                  className="v8-quiet-button"\n                  data-testid="bookings-no-stay-action"',
     "put": '                  className="v8-quiet-button"\n                  style={{ marginTop: 420 }}\n                  data-testid="bookings-no-stay-action"'},
    {"id": "M6_contract_gains_a_creation_door", "file": CONTRACT, "cell": "C3",
     "find": ACTIVITY_PATH_ANCHOR, "put": CREATION_DOOR + ACTIVITY_PATH_ANCHOR},
    {"id": "M7_copy_cannot_wrap", "file": MAPCOPY, "cell": "C7",
     "find": ZH_TIER,
     "put": "「添加活动地点」这扇门这一版没有（NOT_AVAILABLESEQUENTIALLYUNBREAKABLETOKENABCDEFGHIJKLMNOPQRSTUVWX）。"},
    {"id": "M8_a_reachable_control_is_pushed_down", "file": LIVE, "cell": "C6",
     "find": NO_PROPOSAL, "put": PROPOSAL_PUSHED},
]

ONLY = set(sys.argv[1].split(",")) if len(sys.argv) > 1 else None


def sha(path: str) -> str:
    return hashlib.sha256(io.open(path, "rb").read()).hexdigest()


def failing_cells(log_path: str | None) -> list[str]:
    if not log_path or not os.path.isfile(log_path):
        return []
    txt = io.open(log_path, encoding="utf-8", errors="replace").read()
    return sorted(set(re.findall(r"› (C\d)\b", txt)))


def main() -> int:
    chosen = [m for m in MUTATIONS if ONLY is None or m["id"] in ONLY]
    if ONLY:
        unknown = ONLY - {m["id"] for m in MUTATIONS}
        assert not unknown, "unknown arm id(s): %s" % ",".join(sorted(unknown))
    report = {
        "spec": SPEC,
        "arms_requested": len(chosen),
        "filter": sorted(ONLY) if ONLY else "all",
        "head": subprocess.run(["git", "-C", WT, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip(),
        "frontend_tree": subprocess.run(["git", "-C", WT, "rev-parse", "HEAD:frontend"], capture_output=True, text=True).stdout.strip(),
        "arms": [],
    }
    for m in chosen:
        raw = io.open(m["file"], "rb").read()
        text = raw.decode("utf-8")
        before = sha(m["file"])
        if text.count(m["find"]) != 1:
            report["arms"].append({"id": m["id"], "status": "ANCHOR_NOT_UNIQUE", "occurrences": text.count(m["find"])})
            print("%s -> ANCHOR_NOT_UNIQUE (%d)" % (m["id"], text.count(m["find"])))
            continue
        io.open(m["file"], "wb").write(text.replace(m["find"], m["put"], 1).encode("utf-8"))
        try:
            r = subprocess.run(
                [sys.executable, os.path.join(WT, "review", "n3_e2e_r1.py"), "--wt", WT,
                 "--target", SPEC, "--tag", "n3m" + m["id"].split("_")[0][1:].lower(),
                 "--grep", m["cell"], "--timeout-min", "20"],
                capture_output=True, text=True, errors="replace")
            run_id = (re.search(r'"run_id": "([^"]+)"', r.stdout) or [None, None])[1]
            log = (re.search(r'"log": "([^"]+)"', r.stdout) or [None, None])[1]
            counts = {k: int(v) for k, v in re.findall(r'"(passed|failed)": (\d+)', r.stdout)}
        finally:
            io.open(m["file"], "wb").write(raw)
        after = sha(m["file"])
        killed = failing_cells(log)
        targeted = m["cell"] in killed
        report["arms"].append({
            "id": m["id"],
            "file": m["file"].replace("\\", "/"),
            "cell_targeted": m["cell"],
            "run_id": run_id,
            "runner_exit_code": r.returncode,
            "counts": counts,
            "log": log.replace("\\", "/") if log else None,
            "cells_reddened_by_name": killed,
            "targeted_cell_actually_reddened": targeted,
            "sha256_before": before,
            "sha256_after_restore": after,
            "restored_byte_identical": before == after,
            "verdict": "COUNTEREXAMPLE_HOLDS"
            if r.returncode != 0 and before == after and targeted and killed == [m["cell"]]
            else "INVALID",
        })
        print("%s -> exit %s red=%s killed=%s restored=%s" % (m["id"], r.returncode, r.returncode != 0, killed, before == after))
    if len(report["arms"]) != len(chosen):
        print("ARM_COUNT_MISMATCH ran %d of %d" % (len(report["arms"]), len(chosen)))
    ok = len(report["arms"]) == len(chosen) and all(a.get("verdict") == "COUNTEREXAMPLE_HOLDS" for a in report["arms"])
    report["all_arms_hold"] = ok
    out = os.path.join(WT, "review", "evidence", "ord0407", "mutations_r1.json")
    io.open(out, "w", encoding="utf-8").write(json.dumps(report, ensure_ascii=False, indent=1) + "\n")
    print("READING " + out.replace("\\", "/"))
    return 0 if ok else 3


if __name__ == "__main__":
    sys.exit(main())
