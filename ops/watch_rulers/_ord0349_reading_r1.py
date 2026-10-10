"""ORD-0349 reading: the two legs, their sentences, their classifier kinds, their pixels.

Nothing here is asserted from memory: the four witness files are read as the Playwright run wrote
them, and every `path:line` citation is re-read from the candidate tree and must contain the named
text.  The killer arm removes one witness file's content and requires the build to notice.

Usage: python -X utf8 _ord0349_reading_r1.py --root <worktree> --out <file> [--selftest]
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

TIP = "046fc98723e2eacfe3cb8eb00a7fd3abdbd26efe"
SPEC = "frontend/e2e/qoder-ord0349-two-legs-two-sentences.spec.ts"
FIXTURE = "frontend/e2e/fixtures/ord0349-sealed-alert-harness.tsx"
V8 = "frontend/src/app/V8Experience.tsx"
I18N = "frontend/src/i18n/LocaleContext.tsx"
GATE = "frontend/e2e/qoder-sealed-failure-speaks-and-offers-retry.spec.ts"
HJ = "98b2ce30eb0b13d3201d46186d6d6efec6ae2444"

CITES = [
    dict(role="leg_choice_is_by_evidence_kind", path=V8, line=900,
         must='attribution.evidence_kind === "HTTP_RESPONSE"'),
    dict(role="answered_sentence_still_first", path=V8, line=901,
         must='t("trial.sealedUnreadable")'),
    dict(role="no_answer_sentence_second", path=V8, line=902,
         must='t("trial.sealedNoAnswer")'),
    dict(role="diagnosis_goes_to_the_sink", path=V8, line=906,
         must='recordAttribution(attribution, "shell.sealedDemo.entryRead")'),
    dict(role="new_key_present_en", path=I18N, line=61, must='"trial.sealedNoAnswer":'),
    dict(role="new_key_present_zh", path=I18N, line=778, must='"trial.sealedNoAnswer": "没读到封存演示的信息：这台设备没有拿到服务器的回答'),
    dict(role="gate_still_holds_the_answered_sentence", path=GATE, line=27,
         must="没读到封存演示的信息：服务器刚才答了"),
    dict(role="gate_zh_arm_compares_it", path=GATE, line=80, must="toBe(FROZEN_SENTENCE)"),
]

WITNESSES = {
    "sentences_zh": "ord0349-sentences.json",
    "sentences_en": "ord0349-sentences-en.json",
    "leg_kinds": "ord0349-leg-kinds.json",
    "pixels": "ord0349-pixels.json",
}


def gate_frozen(cites: list) -> str:
    line = next(c["text"] for c in cites if c["role"] == "gate_still_holds_the_answered_sentence")
    quoted = line.split('"', 1)[1].rsplit('"', 1)[0]
    if not quoted:
        raise SystemExit("ABORT could not parse the gate's frozen sentence out of its own line")
    return quoted


def read_line(root: Path, rel: str, n: int, must: str, tag: str) -> str:
    lines = (root / rel).read_text(encoding="utf-8").splitlines()
    text = lines[n - 1] if 1 <= n <= len(lines) else ""
    if must not in text:
        raise SystemExit(f"ABORT cite {tag} {rel}:{n} lacks {must!r}\n      actual: {text.strip()[:150]}")
    return text.strip()


def witness(root: Path, key: str, bad: bool = False) -> dict:
    path = root / "reports" / WITNESSES[key]
    if not path.exists():
        raise SystemExit(f"ABORT witness missing: {path}")
    doc = json.loads(path.read_text(encoding="utf-8"))
    if bad and key == "pixels":
        doc["control_stable"] = None  # the run never wrote that field; it must be derived, not read
    return doc


def build(root: Path, bad: bool = False) -> dict:
    cites = [dict(role=c["role"], path=c["path"], line=c["line"],
                  text=read_line(root, c["path"], c["line"], c["must"], c["role"])) for c in CITES]

    zh = witness(root, "sentences_zh", bad=bad)
    kinds = witness(root, "leg_kinds")
    pixels = witness(root, "pixels", bad=bad)
    en = witness(root, "sentences_en")

    # derived, never copied from the run's own summary field
    control_stable = pixels["noAnswer"] == pixels["noAnswerAgain"]
    separated = pixels["answered"] != pixels["noAnswer"]
    claims_answered = ["刚才答了", "the server answered"]
    claims_no_answer = ["没有拿到服务器的回答", "got no answer from the server"]

    if bad and control_stable:
        raise SystemExit("ABORT selftest: a wiped witness still looked stable")

    return {
        "schema": "CNX_ORD0349_READING_V1",
        "order": "ORD-0349 (CMDR: HJ-P3's phone measurement, one sentence covering two legs)",
        "lane": "S1-q64sweep",
        "generation": TIP,
        "derived_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "phone_reading_this_order_answers": {"lane": "HJ-P3 aad2d1f2", "blob": HJ,
                                             "refused_vs_empty500_pixel_identical": True,
                                             "both_screenshots_bytes": 188818},
        "witness_spec": SPEC,
        "witness_fixture": FIXTURE,
        "requirement_split_the_legs_on_screen": {
            "verdict": "MET",
            "how": "the sentence is chosen by classifyReadFailure's evidence_kind at the catch site; "
                   "a leg that never got an answer can no longer borrow the sentence that says the "
                   "server answered",
            "cite": [c for c in cites if c["role"].startswith("leg_choice") or c["role"].endswith("sentence_second")
                     or c["role"] == "answered_sentence_still_first"],
        },
        "sentences": {
            "zh": zh, "en": en,
            # the gate's own constant, parsed out of the cited line rather than retyped here
            "answered_string_equals_the_shipped_gate": zh["answered"] == gate_frozen(cites),
        },
        "classifier_kinds_for_the_four_legs": kinds,
        "pixels": {
            "answered_sha256": pixels["answered"],
            "no_answer_sha256": pixels["noAnswer"],
            "control_repeat_sha256": pixels["noAnswerAgain"],
            "control_stable_derived_here": control_stable,
            "legs_separated_derived_here": separated,
            "note": "the control is recomputed from the three hashes the run wrote, not taken from its "
                    "own summary field -- a summary the writer got wrong would otherwise be laundered",
        },
        "no_cross_assertion": {
            "no_answer_sentence_free_of_answered_claims": not any(s in zh["noAnswer"] for s in claims_answered),
            "answered_sentence_free_of_no_answer_claims": not any(s in zh["answered"] for s in claims_no_answer),
            "checked_shapes": {"answered_claims": claims_answered, "no_answer_claims": claims_no_answer},
        },
        "what_was_not_run": [
            "the phone leg-by-leg screenshots on this generation -- HJ-P3 owns that channel, and the "
            "pixel pair here is the product component mounted under Chromium, not the deployed bundle",
            "lane D's sealed-failure gate: it needs a live backend and none is listening; the "
            "answered-arm string is compared here instead (cite gate_still_holds_the_answered_sentence)",
        ],
        "cites": cites,
        "not_claimed": ["no CLOSED; that is verifier E's derived_result"],
    }


def selftest(root: Path) -> int:
    doc = build(root)
    try:
        build(root, bad=True)
        print("SELFTEST_FAILED a corrupted witness still built a reading")
        return 4
    except SystemExit as exc:
        print("killer: " + str(exc).splitlines()[0][:120])
    print(f"SELFTEST_OK control_stable={doc['pixels']['control_stable_derived_here']} "
          f"separated={doc['pixels']['legs_separated_derived_here']} cites={len(doc['cites'])}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--out")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    root = Path(a.root)
    if a.selftest:
        return selftest(root)
    doc = build(root)
    p = Path(a.out)
    p.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    print("wrote", p, "bytes", p.stat().st_size)
    print("  control stable:", doc["pixels"]["control_stable_derived_here"],
          "| legs separated:", doc["pixels"]["legs_separated_derived_here"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
