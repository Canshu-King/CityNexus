"""Q70/Q71 census: every `data-*` attribute whose value is a JSX expression.

Why this file exists: CMDR 06:05 ③ (Q70) says the element that carries an allowed field must
wear a machine-readable anchor named after the contract field, and ④ (Q71) says a `data-*`
counts as "in the DOM" and is bound by the Q64 whitelist even though it is not on screen.
The published taint ruler states in its own header that attribute interpolation is NOT a sink
(see ruler_sink_policy below), so this class has no judge today.  This script measures it.

It is a census, not a verdict: no line here claims COMPLIANT or VIOLATION.  Every site carries
the source line it came from, so a reader (or the next ruler) can judge without trusting me.

Usage: python -X utf8 _q70_q71_attribute_census_r1.py --export <dir> --out <file> [--selftest]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

GEN = "a8237d7b50a1df419ae7e89ae6c075dabb6513f8"
SRC_ROOT = "frontend/src"
ANCHOR_NAME = "data-cnx-field"

# Q64=1 allowed fields, spelled exactly as the ruling spells them
SIX = ["http_status", "content_type", "body_bytes", "response_received", "elapsed_ms", "request_id"]

# attribute-name token -> which allowed field it appears to carry.  Named on purpose: an
# unlisted name is reported as "not one of the six", never guessed into a bucket.
NAME_MAP = {
    "data-raw-http-status": "http_status",
    "data-status": "http_status",
    "data-result-status": "http_status",
    "data-raw-content-type": "content_type",
    "data-raw-bytes": "body_bytes",
    "data-request-length": "body_bytes",
    "data-elapsed-seconds": "elapsed_ms",
    "data-attribution": "composite",  # the telemetry line: several fields in one attribute
}

# an expression carrying one of these shapes is the one Q71 names as a violation *if* it
# really holds upstream text -- so it is listed for judgement, never classified by me
RISK_TOKENS = ["message", "detail", "body", "String(", "stack", "reason", "sentence",
               "text", ".error", "error)", "rawText"]

# Every name-matched candidate adjudicated by reading where its value actually comes from.
# Q70's whole point is that a name is not a contract, so `NAME_MAP` may only generate
# candidates -- a row here is what decides.  Each `trace` cite is read from the tree and must
# contain the named text, so a decision cannot survive a moved line.
ADJ = [
    dict(field="http_status", path="frontend/src/components/RawFactsPanel.tsx", line=29,
         must="data-raw-http-status={facts.http_status", verdict="CONFIRMED_CARRIER",
         why="facts is RawFacts; the value is the status this device saw on the answer",
         trace=[dict(path="frontend/src/lib/rawFacts.ts", line=22, must="http_status: response.status")]),
    dict(field="content_type", path="frontend/src/components/RawFactsPanel.tsx", line=30,
         must="data-raw-content-type={facts.content_type", verdict="CONFIRMED_CARRIER",
         why="the media type the answer carried, read off the response",
         trace=[dict(path="frontend/src/lib/rawFacts.ts", line=23,
                     must='content_type: response.headers.get("content-type")')]),
    dict(field="body_bytes", path="frontend/src/components/RawFactsPanel.tsx", line=31,
         must="data-raw-bytes={facts.bytes", verdict="CONFIRMED_CARRIER_NAME_NOT_CONTRACT",
         why="it really is the answer's octet count, but the key is spelled `bytes`, not the "
             "Q64 name `body_bytes` -- Q70 says the machine-readable name must be the contract one",
         trace=[dict(path="frontend/src/lib/rawFacts.ts", line=24,
                     must="bytes: new TextEncoder().encode(rawText).length"),
                dict(path="frontend/src/lib/rawFacts.ts", line=61, must="`bytes=${facts.bytes")]),
    dict(field="http_status", path="frontend/src/features/planning/PlanWithAiSheet.tsx", line=1060,
         must="data-raw-http-status={result.rawReading.http_status", verdict="CONFIRMED_CARRIER",
         why="rawReading is built off the same response",
         trace=[dict(path="frontend/src/features/planning/PlanWithAiSheet.tsx", line=578,
                     must="http_status: response.status")]),
    dict(field="content_type", path="frontend/src/features/planning/PlanWithAiSheet.tsx", line=1061,
         must="data-raw-content-type={result.rawReading.content_type", verdict="CONFIRMED_CARRIER",
         trace=[dict(path="frontend/src/features/planning/PlanWithAiSheet.tsx", line=579,
                     must='content_type: response.headers.get("content-type")')],
         why="same answer, same read"),
    dict(field="body_bytes", path="frontend/src/features/planning/PlanWithAiSheet.tsx", line=1062,
         must="data-raw-bytes={result.rawReading.bytes", verdict="CONFIRMED_CARRIER_NAME_NOT_CONTRACT",
         trace=[dict(path="frontend/src/features/planning/PlanWithAiSheet.tsx", line=580,
                     must="bytes: raw === null ? null : new TextEncoder().encode(raw).length")],
         why="octets of the answer body; key spelled `bytes` again, not `body_bytes`"),
    dict(field="elapsed_ms", path="frontend/src/features/planning/PlanWithAiSheet.tsx", line=959,
         must="data-elapsed-seconds={elapsed}", verdict="DIFFERENT_QUANTITY",
         why="elapsed is this component's own wall clock in whole seconds while the button is "
             "busy, not the server's elapsed_ms -- the unit and the subject both differ",
         trace=[dict(path="frontend/src/features/planning/PlanWithAiSheet.tsx", line=384,
                     must="const [elapsed, setElapsed] = useState(0);"),
                dict(path="frontend/src/features/planning/PlanWithAiSheet.tsx", line=965,
                     must="已等待 ${elapsed} 秒")]),
    dict(field="elapsed_ms", path="frontend/src/features/setup/JourneyTrialSetup.tsx", line=1142,
         must="data-elapsed-seconds={waited}", verdict="DIFFERENT_QUANTITY",
         why="waited is a locally counted number of seconds since the press",
         trace=[dict(path="frontend/src/features/setup/JourneyTrialSetup.tsx", line=589,
                     must="const waited = useElapsedSeconds(busy ? startedAt : null);")]),
    dict(field="http_status", path="frontend/src/features/discovery/DestinationPreparationPanel.tsx",
         line=456, must="data-status={job.status}", verdict="DIFFERENT_QUANTITY",
         why="job.status is the operation's own state word, printed as progress text, not an "
             "HTTP status -- a gauge that matched the attribute name would read a state string "
             "as a status code",
         trace=[dict(path="frontend/src/features/discovery/DestinationPreparationPanel.tsx",
                     line=463, must="{job.status}")]),
    dict(field="http_status", path="frontend/src/features/planning/PlanWithAiSheet.tsx", line=1007,
         must="data-result-status={result?.status", verdict="DIFFERENT_QUANTITY",
         why="result.status is the sheet's own outcome string for the run",
         trace=[dict(path="frontend/src/features/planning/PlanWithAiSheet.tsx", line=389,
                     must="status: string;")]),
    dict(field="body_bytes", path="frontend/src/features/planning/PlanWithAiSheet.tsx", line=909,
         must="data-request-length={text.trim().length}", verdict="DIFFERENT_QUANTITY",
         why="a length of the traveller's own words going out (and a character count, not "
             "octets) -- the opposite direction from body_bytes",
         trace=[]),
    dict(field="__q71__", path="frontend/src/features/setup/JourneyTrialSetup.tsx", line=1248,
         must='data-error-message={sealedDemoDetail?.message ?? ""}',
         verdict="Q71_SITE_CARRYING_AN_EXCEPTION_MESSAGE",
         why="the value is `error.message` of a caught failure, parked in a data-* on purpose. "
             "Q71 puts this outside the whitelist: an exception object's words in the DOM tree "
             "are to be treated as a violation even though nothing is rendered.  Not my file and "
             "not my call to fix -- named here for assignment.",
         trace=[dict(path="frontend/src/app/V8Experience.tsx", line=897,
                     must="{ message: error.message, name: error.name }"),
                dict(path="frontend/src/app/V8Experience.tsx", line=898,
                     must='{ message: String(error), name: "Unknown" }'),
                dict(path="frontend/src/features/setup/JourneyTrialSetup.tsx", line=339,
                     must="sealedDemoDetail?: { message: string; name: string } | null")]),
    dict(field="__q71__", path="frontend/src/features/setup/JourneyTrialSetup.tsx", line=1247,
         must='data-error-name={sealedDemoDetail?.name ?? ""}',
         verdict="Q71_SITE_CARRYING_AN_EXCEPTION_NAME",
         why="same chain, the exception's `name` (e.g. TypeError).  A token rather than a "
             "sentence, but it is not one of the six either",
         trace=[dict(path="frontend/src/app/V8Experience.tsx", line=897,
                     must="{ message: error.message, name: error.name }")]),
]

# the telemetry line my own ORD-0326 surfaces carry: derived facts, several in one attribute
COMPOSITE_NOTE = ("data-attribution holds `failureAttribution.ts`'s telemetry line -- "
                  "`attribution_reason= evidence_kind= http_status= source_layer= retryable= "
                  "recovery_action= [server_code=] [content_type=]`.  The six-allowed ones among "
                  "those are compliant under Q71; the rest are derived machine words, not the "
                  "answer's body and not upstream prose, but they are also not on the list, so "
                  "this census records them instead of ruling on them.")

ATTR_RE = re.compile(r"\bdata-[A-Za-z][A-Za-z0-9-]*=\{")

# the published r6 ruler, and the blob its header must have when the quote is taken from it
RULER_PUBLISHED_PATH = "evidence/ord0331-ast-crossfile-S4/ui_exposure_taint_ast_r3.cjs"
RULER_PUBLISHED_BLOB = "6a251d3a6bea70329e06581384a81d5ef54c96a6"


def blob_of(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob %d\x00" % len(raw) + raw).hexdigest()


def ruler_policy(ruler: Path | None) -> dict:
    """The sink policy is quoted out of the ruler's own bytes, never retyped here."""
    if ruler is None:
        return {"quoted_from": None,
                "note": "no --ruler passed, so the quote is not included rather than paraphrased"}
    got = blob_of(ruler)
    if got != RULER_PUBLISHED_BLOB:
        raise SystemExit(f"ABORT ruler copy {ruler} is blob {got}, published is {RULER_PUBLISHED_BLOB}")
    lines = ruler.read_text(encoding="utf-8", errors="replace").splitlines()
    want = [i for i, ln in enumerate(lines, 1) if "NOT sinks" in ln and "attribute interpolation" in ln]
    if len(want) != 1:
        raise SystemExit(f"ABORT could not locate the attribute-sink exclusion in {ruler}")
    n = want[0]
    return {
        "quoted_from": RULER_PUBLISHED_PATH,
        "blob": got,
        "sink_line_before": lines[n - 2].rstrip(),
        "sink_line_exclusion": lines[n - 1].rstrip(),
        "exclusion_at_line": n,
        "consequence": "the published ruler cannot see the class Q71 just made binding -- by its "
                       "own stated design, not by accident. This census is a measurement, not a "
                       "replacement judge.",
    }


def read(export: Path, rel: str, n: int) -> str:
    lines = (export / rel).read_text(encoding="utf-8").splitlines()
    return lines[n - 1]


def expr_from(line: str, start: int) -> str:
    """Balanced-brace tail from the `{` at `start`.  Quote-blind on purpose: a mis-bounded
    expression is visible in the printed line, and under-grabbing is the safer error."""
    depth = 0
    for i in range(start, len(line)):
        c = line[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return line[start:i + 1]
    return line[start:]


def sites(export: Path):
    out = []
    for p in sorted((export / SRC_ROOT).rglob("*")):
        if p.suffix not in (".ts", ".tsx") or not p.is_file():
            continue
        rel = p.relative_to(export).as_posix()
        for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            for m in ATTR_RE.finditer(line):
                name = line[m.start():m.start() + line[m.start():].index("=")].strip()
                out.append(dict(path=rel, line=n, attr=name,
                                expression=expr_from(line, m.end() - 1),
                                source_line=line.strip()))
    return out


def anchor_sites(export: Path):
    """Every place the Q70 anchor name appears at all, whatever its value."""
    hits = []
    for p in sorted((export / SRC_ROOT).rglob("*")):
        if p.suffix not in (".ts", ".tsx") or not p.is_file():
            continue
        rel = p.relative_to(export).as_posix()
        for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            if ANCHOR_NAME in line:
                hits.append(dict(path=rel, line=n, source_line=line.strip()))
    return hits


def verify(export: Path, rel: str, n: int, must: str, tag: str, shift: int = 0) -> str:
    text = read(export, rel, n + shift)
    if must not in text:
        raise SystemExit(f"ABORT {tag} {rel}:{n + shift} lacks {must!r}\n"
                         f"      actual: {text.strip()[:150]}")
    return text.strip()


def adjudicate(export: Path, shift_a_trace: bool = False) -> dict:
    """Decide each candidate by reading where its value comes from, not by its attribute name."""
    rows = []
    for i, a in enumerate(ADJ):
        # killer arm 1: shift one trace cite three lines down -- still a real line, wrong text
        shift = 3 if (shift_a_trace and i == 0) else 0
        site = verify(export, a["path"], a["line"], a["must"], "site", 0)
        traces = [dict(path=t["path"], line=t["line"],
                       text=verify(export, t["path"], t["line"], t["must"], "trace", shift),
                       checked_substring=t["must"]) for t in a["trace"]]
        rows.append(dict(field=a["field"], path=a["path"], line=a["line"],
                         source_line=site, verdict=a["verdict"], why=a["why"],
                         trace_cites=traces, trace_count=len(traces)))
    return {"rows": rows,
            "confirmed": [r for r in rows if r["verdict"].startswith("CONFIRMED")],
            "rejected": [r for r in rows if r["verdict"] == "DIFFERENT_QUANTITY"],
            "q71": [r for r in rows if r["verdict"].startswith("Q71_SITE")]}


def build(export: Path, ruler: Path | None = None, mode: str | None = None) -> dict:
    adj = adjudicate(export, shift_a_trace=(mode == "trace"))
    all_data = sites(export)
    interpolated = all_data
    names = Counter(s["attr"] for s in interpolated)
    anchors = anchor_sites(export)

    # the untrusted, name-matched candidate stage -- kept to show what a name-only gauge yields
    name_candidates = {}
    for f in SIX:
        c = [s for s in interpolated if NAME_MAP.get(s["attr"]) == f]
        name_candidates[f] = [f"{s['path']}:{s['line']}" for s in c]

    per_field = {}
    for f in SIX:
        conf = [r for r in adj["confirmed"] if r["field"] == f]
        rej = [r for r in adj["rejected"] if r["field"] == f]
        has_anchor = any(ANCHOR_NAME in r["source_line"] for r in conf)
        per_field[f] = {
            "confirmed_carriers": conf,
            "confirmed_count": len(conf),
            "look_alikes_rejected": rej,
            "look_alike_count": len(rej),
            "anchor_present_on_a_carrier": has_anchor,
            "contract_anchor_used": sorted({
                m.group(0) for r in conf
                for m in re.finditer(r'data-cnx-field(?:"=|\{)[^,}"]*', r["source_line"])}),
            "name_matched_candidates": name_candidates[f],
            "q70_verdict": ("NO_CARRIER_IN_TREE" if not conf else
                            ("ANCHOR_PRESENT" if has_anchor else "ANCHOR_MISSING")),
        }

    risk = []
    for s in interpolated:
        expr = s["expression"]
        hit_tokens = [t for t in RISK_TOKENS if t in expr]
        if hit_tokens:
            risk.append(dict(**s, matched_tokens=hit_tokens,
                             note="token shortlist only; the decision is in `adjudicated`"))

    composite = [s for s in interpolated if NAME_MAP.get(s["attr"]) == "composite"]

    if mode == "risk":
        # killer arm 2: a census that reports whatever it reported last time would still look
        # tidy, so the shortlist has to be able to move.
        risk = []

    doc = {
        "schema": "CNX_Q70_Q71_ATTRIBUTE_CENSUS_V1",
        "order": "CMDR 06:05 ③④ applied to the ORD-0326 field table (anchor column) + the "
                 "new Q71 surface",
        "lane": "S1-q64sweep",
        "generation": GEN,
        "measured_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "rulings": {
            "Q70": "human labels are free, the machine-readable field name is the contract; the "
                   "carrying element must wear a stable anchor named with the Q64 field name",
            "Q71": "data-* is not 'on screen' but it is 'in the DOM': raw body, exception object "
                   "or upstream sentence in one is treated as a violation; the six allowed values "
                   "in one are compliant and are how Q70's anchor is meant to be built",
        },
        "denominator": {
            "files_scanned": len({s["path"] for s in interpolated}),
            "data_attribute_sites_with_a_jsx_expression": len(interpolated),
            "distinct_attribute_names": len(names),
            "anchor_name_sites_anywhere": len(anchors),
            "anchor_name": ANCHOR_NAME,
        },
        "method_note": "an attribute name never decides anything here: NAME_MAP only generates "
                       "candidates, and every candidate is then decided by reading where its value "
                       "comes from (`adjudicated`).  The count of name-matched candidates that did "
                       "not survive that reading is `look_alike_rejected_count`.",
        "look_alike_rejected_count": len(adj["rejected"]),
        "adjudicated": adj["rows"],
        "ruler_sink_policy": ruler_policy(ruler),
        "q70_anchor_column_for_the_field_table": per_field,
        "composite_attribute_note": COMPOSITE_NOTE,
        "composite_attribute_sites": composite,
        "q71_sites_listed_for_judgement": risk,
        "q71_risk_count": len(risk),
        "q71_adjudicated_sites": adj["q71"],
        "attribute_name_counts": dict(sorted(names.items(), key=lambda kv: (-kv[1], kv[0]))),
        "not_claimed": ["this file states no COMPLIANT / VIOLATION for a screen: the Q71 rows are "
                        "named by the ruling's own words and left for the owner to fix",
                        "no reachability judgement (an attribute may be present yet unreachable)",
                        "the ruler is not mine to change; the sink gap is reported, not patched"],
    }
    return doc


def selftest(export: Path, ruler: Path | None) -> int:
    good = build(export, ruler)
    n = good["q71_risk_count"]
    if n == 0:
        print("SELFTEST_FAILED the shortlist is empty on a tree that has these sites")
        return 5
    try:
        build(export, ruler, mode="trace")
        print("SELFTEST_FAILED a shifted trace cite still passed")
        return 4
    except SystemExit as exc:
        print("killer arm 1 (trace cite): " + str(exc).splitlines()[0][:120])
    wiped = build(export, ruler, mode="risk")
    if wiped["q71_risk_count"] >= n:
        print("SELFTEST_FAILED the wiped run did not drop the shortlist count")
        return 4
    if ruler is not None and good["ruler_sink_policy"]["blob"] != RULER_PUBLISHED_BLOB:
        print("SELFTEST_FAILED the ruler quote is not pinned to the published blob")
        return 6
    print(f"SELFTEST_OK interpolated={good['denominator']['data_attribute_sites_with_a_jsx_expression']} "
          f"shortlist={n} wiped={wiped['q71_risk_count']} "
          f"anchors={good['denominator']['anchor_name_sites_anywhere']} "
          f"adjudicated={len(good['adjudicated'])} "
          f"look_alikes_rejected={good['look_alike_rejected_count']}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--export", required=True)
    ap.add_argument("--ruler")
    ap.add_argument("--out")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    export = Path(a.export)
    ruler = Path(a.ruler) if a.ruler else None
    if a.selftest:
        return selftest(export, ruler)
    doc = build(export, ruler)
    Path(a.out).write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    print("wrote", a.out, "bytes", Path(a.out).stat().st_size)
    d = doc["denominator"]
    print(f"  interpolated data-* sites {d['data_attribute_sites_with_a_jsx_expression']} "
          f"in {d['files_scanned']} files; names {d['distinct_attribute_names']}; "
          f"{ANCHOR_NAME} sites {d['anchor_name_sites_anywhere']}")
    for f, v in doc["q70_anchor_column_for_the_field_table"].items():
        print(f"  {f}: carriers={v['confirmed_count']} look_alikes={v['look_alike_count']} "
              f"anchor={v['q70_verdict']}")
    print("  Q71 shortlist:", doc["q71_risk_count"], " adjudicated sites:",
          len(doc["q71_adjudicated_sites"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
