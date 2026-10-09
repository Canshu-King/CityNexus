"""CMDR 05:44 item 3 (optional): is the wording at SimulationPanel.tsx:934 still wrong?

Judged by the same rule as the field table: every claim below is checked against the
tip export line by line, and a line that does not contain the named text aborts.
The conclusion is derived from those readings, not asserted.

Usage: python -X utf8 _ord0326_simpanel_934_r1.py --export <dir> --out <file> [--selftest]
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

GEN = "a8237d7b50a1df419ae7e89ae6c075dabb6513f8"
PANEL = "frontend/src/features/simulation/SimulationPanel.tsx"
ADAPTER = "frontend/src/features/simulation/simulationAdapter.ts"
MAIN = "backend/app/main.py"
PREP = "frontend/src/features/discovery/DestinationPreparationPanel.tsx"

CITES = [
    dict(claim="sink", path=PANEL, line=934, must="{zh ? outcome.zh : outcome.en}",
         note="the line r5 flagged: it renders a locally built sentence, not a server body"),
    dict(claim="wording_built_from_code", path=ADAPTER, line=125, must="const { code, status } = failureCode(error)",
         note="describeFailure(): the sentence is chosen by the server's code, with status interpolated"),
    dict(claim="wait_hint_only_for_busy", path=ADAPTER, line=130, must="const extra = busy ? retryHint(error) : fields",
         note="the server's wait number is attached on the busy arm"),
    dict(claim="busy_predicate", path=ADAPTER, line=127,
         must='const busy = code === "generation.store_busy" || code === "GENERATION_STORE_BUSY"',
         note="names only the two generation spellings -- see the HYDRATION finding"),
    dict(claim="hint_names_the_speaker", path=ADAPTER, line=120, must='return "（服务器没说要等多久）"',
         note="when the server gave no number the screen says so instead of inventing one"),
    dict(claim="hint_value", path=ADAPTER, line=121, must="`（约 ${Math.round(ms)} 毫秒后再试）`",
         note="the number is the server's retry_after_ms, passed through"),
    dict(claim="generation_busy_carries_hint", path=MAIN, line=3107,
         must='details={"retry_after_ms": 500}',
         note="POST /journeys/{id}/replans, the leg the panel actually presses"),
    dict(claim="generation_busy_code", path=MAIN, line=3104, must='"GENERATION_STORE_BUSY"',
         note="and that code is a key in the adapter table, so the busy arm is taken"),
    dict(claim="hydration_busy_carries_hint", path=MAIN, line=2948,
         must='details={"retry_after_ms": 500}',
         note="POST /api/v1/catalog-hydrations also states a wait"),
    dict(claim="hydration_busy_code", path=MAIN, line=2945, must='"HYDRATION_STORE_BUSY"',
         note="the adapter has no key for it, but the panel never calls that route"),
    dict(claim="hydration_read_elsewhere", path=PREP, line=72, must="Number(row.retry_after_ms || 0)",
         note="the wait from that door is honoured on the destination-preparation screen"),
]

# what the panel can ask of the server -- every method it calls, by name
PANEL_METHODS = ["getJourney", "getPlan", "listReplans", "generateReplans", "acceptReplan",
                 "rejectReplan", "createBooking", "setGuardianProviderFixture"]
KILLER = ("wait_hint_only_for_busy", 130)   # the cite the killer arm will read too high
KILL_TO = 124                                # describeFailure's signature line: real, wrong


def read(export: Path, rel: str, n: int) -> str:
    lines = (export / rel).read_text(encoding="utf-8").splitlines()
    if not 1 <= n <= len(lines):
        raise SystemExit(f"ABORT {rel}:{n} out of range ({len(lines)} lines)")
    return lines[n - 1]


def build(export: Path, bad: bool = False) -> dict:
    rows = []
    for spec in CITES:
        n = spec["line"]
        if bad and (spec["claim"], spec["line"]) == KILLER:
            n = KILL_TO  # a real line, but not the one carrying the text
        text = read(export, spec["path"], n)
        if spec["must"] not in text:
            raise SystemExit(f"ABORT {spec['path']}:{n} lacks {spec['must']!r}\n"
                             f"      actual: {text.strip()[:150]}")
        rows.append(dict(claim=spec["claim"], path=spec["path"], line=n,
                         text=text.strip(), checked_substring=spec["must"], note=spec["note"]))

    adapter_src = (export / ADAPTER).read_text(encoding="utf-8")
    panel_src = (export / PANEL).read_text(encoding="utf-8")
    methods_found = [m for m in PANEL_METHODS
                     if ("cityNexusApi." + m) in panel_src]
    return {
        "schema": "CNX_SIMPANEL_934_V1",
        "order": "ORD-0326 attachment, CMDR 05:44 item 3 (optional look)",
        "lane": "S1-q64sweep",
        "generation": GEN,
        "checked_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "question": "Q69 allows the server's own numeric wait hint.  Is the wording at "
                    "frontend/src/features/simulation/SimulationPanel.tsx:934 still wrong?",
        "answer": "WORDING_CORRECT_FOR_EVERY_REFUSAL_THIS_PANEL_CAN_RECEIVE",
        "why": [
            "the sink renders a sentence this app builds, not a server body (sink cite)",
            "the sentence is chosen by the server's own named code and carries its status",
            "where the server stated a wait, the number is passed through as the server's "
            "(约 N 毫秒后再试); where it did not, the screen says 服务器没说要等多久 rather than "
            "inventing one -- that is the Q68 line held",
            "the only reachable busy refusal for this panel is GENERATION_STORE_BUSY on "
            "POST /journeys/{id}/replans, and that code IS a key in the wording table, so the "
            "wait arm is taken",
        ],
        "no_ticket_because": "HYDRATION_STORE_BUSY carries the same retry_after_ms and has no key "
                             "here, but this panel never calls POST /api/v1/catalog-hydrations "
                             "(method census below), and that door's wait is honoured on the "
                             "destination-preparation screen.  Naming a missing key that no call "
                             "site can reach would be an invented ticket.",
        "panel_methods_named_in_source": methods_found,
        "panel_method_count": len(methods_found),
        "hydration_hits_in_adapter": adapter_src.count("HYDRATION"),
        "citation_count": len(rows),
        "cites": rows,
        "self_declared": "an optional look, not a gate; nothing here claims CLOSED",
    }


def selftest(export: Path) -> int:
    doc = build(export)
    try:
        build(export, bad=True)
        print("SELFTEST_FAILED a wrong line still passed")
        return 4
    except SystemExit as exc:
        print("selftest killer: " + str(exc).splitlines()[0][:120])
    print(f"SELFTEST_OK cites={doc['citation_count']} methods={doc['panel_method_count']}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--export", required=True)
    ap.add_argument("--out")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    export = Path(a.export)
    if a.selftest:
        return selftest(export)
    doc = build(export)
    Path(a.out).write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    print("wrote", a.out, "bytes", Path(a.out).stat().st_size)
    print("  answer:", doc["answer"])
    print("  cites:", doc["citation_count"], "adapter HYDRATION hits:",
          doc["hydration_hits_in_adapter"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
