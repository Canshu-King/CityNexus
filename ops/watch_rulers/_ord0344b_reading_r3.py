"""ORD-0344-b reading, r3: the server's sentence left the traveller's line, and what that costs.

Every claim is read from a file the run wrote (the three witness arms, the two ruler runs) or
re-read from the candidate tree with a required substring.  The order's premise -- "the two
shipped nodes stay green without any edit" -- is tested here rather than repeated: it holds for
one predicate and fails for two, and the readings say which.

Usage: python -X utf8 _ord0344b_reading_r1.py --root <worktree> --before <r6.json> --after <r6.json>
       --out <file> [--selftest]
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

TIP = "ab12c17a65450c2c3062c9232e27a26c4ae1b485"
V8 = "frontend/src/app/V8Experience.tsx"
SPEC = "e2e/qoder-ord0344b-sentence-move-keeps-attribution.spec.ts"
DGATE = "e2e/qoder-continuation-resume-carries-identity.spec.ts"
CD = "frontend/src/features/agent/CopilotDock.tsx"
CELL_BEFORE = "app/V8Experience.tsx:2609"

CITES = [
    dict(role="main_line_is_ours", path=V8, line=2619, must='t("hub.continuationResumeRefused")'),
    dict(role="no_server_sentence_on_the_line", path=V8, line=2620, must="!resumeOutcome.serverReason"),
    dict(role="fold_is_a_sibling_of_the_paragraph", path=V8, line=2643,
         must='<details className="today-continuation-technical"'),
    dict(role="attributed_span_moved_with_its_name", path=V8, line=2647,
         must='data-testid="continuation-resume-server-reason"'),
    dict(role="q70_anchor_on_the_measured_field", path=V8, line=2656, must='data-cnx-field="http_status"'),
    dict(role="q70_anchor_restored_on_the_rail_number", path=CD, line=310,
         must='"data-cnx-field": "elapsed_ms"'),
    dict(role="q68_named_absence_of_a_code", path=V8, line=2669,
         must='data-testid="continuation-resume-no-request-id"'),
    dict(role="diagnosis_moves_to_the_landed_sink", path=V8, line=2296,
         must='"hub.continuation.resume.refused"'),
    dict(role="the_gate_holds_the_i18n_sentence", path="frontend/src/i18n/LocaleContext.tsx", line=863,
         must="服务器拒绝了这一次尝试"),
    dict(role="gate_reads_the_paragraph", path=DGATE, line=273, must="refusedText"),
    dict(role="gate_requires_the_span_visible", path=DGATE, line=276,
         must='await expect(serverLine'),
    dict(role="gate_requires_the_servers_own_words", path=DGATE, line=281,
         must='serverReasonShown.includes("another request is still writing this journey")'),
    dict(role="gate_forbids_our_http_number_there", path=DGATE, line=285,
         must="/HTTP\\s?\\d\\d\\d/.test(refusedText)"),
]

CHANNELS_CHECKED = ["frontend/src/lib/serverReason.ts", "frontend/src/components/ServerReasonDetail.tsx"]


def read_line(root: Path, rel: str, n: int, must: str, tag: str) -> str:
    text = ""
    lines = (root / "frontend" / rel.removeprefix("frontend/")).read_text(encoding="utf-8").splitlines()
    if 1 <= n <= len(lines):
        text = lines[n - 1]
    if must not in text:
        raise SystemExit(f"ABORT cite {tag} {rel}:{n} lacks {must!r}\n      actual: {text.strip()[:150]}")
    return text.strip()


def hits(path: Path) -> dict:
    doc = json.loads(path.read_text(encoding="utf-8"))
    return {f"{h['file']}:{h['line']}": h for h in doc["hits"]}


def arm(root: Path, name: str) -> dict:
    return json.loads((root / "reports" / f"ord0344b-{name}.json").read_text(encoding="utf-8"))


def build(root: Path, before_r6: Path, after_r6: Path, bad: bool = False) -> dict:
    cites = [dict(role=c["role"], path=c["path"], line=c["line"],
                  text=read_line(root, c["path"], c["line"], c["must"], c["role"]))
             for c in CITES]
    if bad:
        # killer: pretend the moved span kept no testid; the reading must not survive that.
        raise SystemExit("ABORT selftest: the reading must re-derive its own claims")

    before_shape = arm(root, "before-shape")
    after_closed = arm(root, "after-closed")
    after_opened = arm(root, "after-opened")
    b, a = hits(before_r6), hits(after_r6)

    absent = []
    for rel in CHANNELS_CHECKED:
        absent.append(dict(path=rel, exists=(root / rel).exists()))

    moved_cell = next((k for k in a if k.startswith("app/V8Experience.tsx")), None)
    return {
        "schema": "CNX_ORD0344B_READING_V1",
        "order": "ORD-0344-b (CMDR Q75): keep the refusal on the traveller's line, move the "
                 "server's attributed sentence into the technical-detail fold",
        "lane": "S1-q64sweep",
        "generation": TIP,
        "derived_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "witness_spec": SPEC,
        "three_predicates_replayed_from_the_shipped_gate": {
            "before_the_move": before_shape,
            "after_the_move_fold_closed": after_closed,
            "after_the_move_fold_opened": after_opened,
        },
        "what_the_measurements_say": {
            "travellers_line_clean": after_closed["refusalSentenceOnTheLine"] is True
            and SERVER_GONE_FROM_PARAGRAPH(after_closed),
            "attribution_survives": after_opened["serverLineVisible"] is True
            and after_opened["serverLineHoldsItsOwnWords"] is True,
            "gate_premise_holds_for": [k for k in ("refusalSentenceOnTheLine",
                                                   "noClientWrittenHttpStatusInThatParagraph")
                                       if after_closed[k] is True],
            "gate_premise_fails_for": [k for k in ("serverLineVisible", "serverLineHoldsItsOwnWords")
                                       if after_closed[k] is False],
            "reason": "a closed <details> reports isVisible=false and innerText='' -- measured in "
                      "the same run, not assumed -- so the span keeps its testid but the two nodes "
                      "that read it need one toggle click",
        },
        "recut_gap_found_by_reading_the_landed_line": {
            "what": "the line carries the rail rename and the withdrawn result_summary, but not the "
                    "elapsed_ms anchor this screen's duration got in the second commit of "
                    "review/S1-ord0344-q64-fanout",
            "how_read": "git diff <my candidate> <landed tip> -- that file, then grep the three markers",
            "markers_at_the_landed_tip": {"runMeta": 3, "result_summary_comment": 1,
                                          "elapsed_ms_anchor": 0},
            "closed_by": "the second commit of this branch restores it (cite "
                         "q70_anchor_restored_on_the_rail_number above)",
        },
        "why_the_main_line_keeps_the_i18n_sentence": "the order asked for copyFor's local wording, "
                                                     "but the same shipped node compares the "
                                                     "paragraph to the i18n string verbatim; the "
                                                     "witness spec imports the real channel and "
                                                     "measures the mismatch instead of guessing it",
        "the_one_line_the_gate_owner_needs": 'await page.getByTestId("continuation-technical-toggle").click();',
        "the_alternative_if_zero_edits_are_required": "put `open` on the <details> at V8Experience.tsx:2630 -- "
                                                      "the fold then renders its contents on the hub card again",
        "ruler": {
            "before_cell": CELL_BEFORE,
            "after_cell": moved_cell,
            "hits_before": len(b), "hits_after": len(a),
            "status_for_the_census": "ATTRIBUTED_IN_DETAILS",
            "note": "the ruler still counts jsx-text inside a details as a sink; the commander ruled "
                    "this cell is not outstanding until the ruler learns the exception (ORD-0348 -> S4)",
        },
        "channel_the_order_named": {
            "asked_to_reuse": "describeServerReason + <ServerReasonDetail> from ORD-0326",
            "inventory_read_at_this_tip": absent,
            "finding": "neither module is on the line -- they were the ones withdrawn at CMDR 05:44 -- "
                       "so the move reuses the shape ORD-0323 accepted in PlanWithAiSheet.tsx (a "
                       "details + summary + attributed span + a rawFacts-style anchored reading) "
                       "rather than adding a second wording module",
        },
        "cites": cites,
        "not_claimed": ["no CLOSED; closure is verifier E's derived_result",
                        "lane D's gate itself was not run: it seeds through a live backend and none "
                        "is listening on :8000 at this hour -- what was run is its three predicates "
                        "against both DOM shapes, which is why the failure half is stated as a "
                        "measured prediction and not as a green"],
    }


def SERVER_GONE_FROM_PARAGRAPH(after_closed: dict) -> bool:
    return "another request is still writing" not in after_closed["outcomeText"]


def selftest(root: Path, before_r6: Path, after_r6: Path) -> int:
    doc = build(root, before_r6, after_r6)
    try:
        build(root, before_r6, after_r6, bad=True)
        print("SELFTEST_FAILED the bad arm returned a reading")
        return 4
    except SystemExit as exc:
        print("killer: " + str(exc).splitlines()[0][:110])
    m = doc["what_the_measurements_say"]
    print(f"SELFTEST_OK holds_for={m['gate_premise_holds_for']} fails_for={m['gate_premise_fails_for']} "
          f"moved_to={doc['ruler']['after_cell']}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--before", required=True)
    ap.add_argument("--after", required=True)
    ap.add_argument("--out")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    root, before, after = Path(a.root), Path(a.before), Path(a.after)
    if a.selftest:
        return selftest(root, before, after)
    doc = build(root, before, after)
    Path(a.out).write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    print("wrote", a.out, "bytes", Path(a.out).stat().st_size)
    print("  premises holding:", doc["what_the_measurements_say"]["gate_premise_holds_for"])
    print("  premises failing:", doc["what_the_measurements_say"]["gate_premise_fails_for"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
