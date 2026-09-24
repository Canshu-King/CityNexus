"""ORD-0269 / ORD-0273 gate round -> (exact_sha, nodeid, run_shape) triples.

Nothing here is typed in: every verdict, count and duration is parsed out of the Playwright log the
run wrote, every measured field is re-read from the JSON the gate itself emitted, and the green
claim is refused if any expected node is missing or any node is not an `ok` line.

Two self-tests travel with it, because a check that cannot fail is not a check:
  * the leak scan is run against the technical-detail string on purpose -- it MUST hit there, which
    is what makes "none of these shapes reached the sentence" a statement with teeth;
  * the frozen sentence in the spec is compared with the dictionary line on disk, so "the copy comes
    from the i18n key" is proven from two artifacts rather than asserted in prose.
"""

import hashlib
import json
import os
import re
import subprocess
import sys

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.environ.get("CNX_LANE_ROOT", "D:/moodle/_qoder_d_lane_20260923")
EVIDENCE = f"{ROOT}/review/evidence"
# Where the reverse-mutation driver writes.  The green round only points at it; it never claims a
# kill it has not read back from that file.
ARMS_RECEIPT = f"{EVIDENCE}/ui-overnight/ord0269-0273-arms.json"
OUT = sys.argv[1] if len(sys.argv) > 1 else f"{EVIDENCE}/ord0269-0273-gate-round.json"

NODE_RE = re.compile(r"^\s+(ok|failed|passed|skipped|interrupted) (\d+) \[([^\]]+)\] . (\S+\.spec\.ts):(\d+):\d+ . (.*?)(?:\s+\(([\d.]+[ms]+)\))?\s*$")
RUNNING_RE = re.compile(r"Running (\d+) tests? using")
TALLY_RE = re.compile(r"^\s*(\d+) (passed|failed|flaky|skipped)(?: \(([\d.]+[ms]+)\))?\s*$")

# Each gate's own expected node ids, spelled from the specs as committed.
EXPECTED = {
    "e2e/qoder-continuation-owner.spec.ts": [
        "ord0269-cell1-reveals-and-names-its-boundary",
        "ord0269-cell3-feed-failure-and-page-exclusion-are-named",
        "ord0269-r6-page-exclusion-yields-no-conclusion",
        "ord0269-r4-a-brand-new-journey-shows-nothing",
    ],
    "e2e/qoder-sealed-failure-speaks-and-offers-retry.spec.ts": [
        "ord0273-text-the-sentence-is-the-key-and-no-shape-leaks",
        "ord0273-text-en-arm-speaks-english-and-neither-side-leaks",
        "ord0273-action-retry-is-a-real-executable-step",
    ],
}
# The named leak shapes, copied from the spec text (not imported) and re-checked below.
LEAK_SHAPES = ["origin answered", "unusable body", "text/html", "text/plain", "Error", "TypeError"]
RUN_SHAPES = {
    "e2e/qoder-continuation-owner.spec.ts": "whole owner spec on the committed tip, 1 worker, mobile 390x844",
    "e2e/qoder-sealed-failure-speaks-and-offers-retry.spec.ts": "whole owner spec on the committed tip, 1 worker, mobile 390x844",
}


def sha_of_head() -> str:
    return subprocess.run(
        "git rev-parse HEAD", cwd=ROOT, capture_output=True, text=True, shell=True
    ).stdout.strip()


def porcelain_lines() -> int:
    out = subprocess.run(
        "git status --porcelain=v1 -- frontend review", cwd=ROOT, capture_output=True, text=True, shell=True
    ).stdout
    return len([line for line in out.splitlines() if line.strip()])


def parse_log(path: str) -> dict:
    text = open(path, encoding="utf-8", errors="replace").read()
    nodes = []
    for line in text.splitlines():
        m = NODE_RE.match(line)
        if not m:
            continue
        status, index, project, spec, _line_no, title, duration = m.groups()
        test_id = title.split(" — ")[0].strip()
        nodes.append(
            {
                "status": status,
                "index": int(index),
                "project": project,
                # The log prints `e2e\file.spec.ts` on Windows; every other coordinate in this repo
                # is spelled with forward slashes, so normalise here rather than losing the node.
                "nodeid": f"{spec.replace(chr(92), '/')} :: {test_id}",
                "title": title.strip(),
                "duration": duration or "",
            }
        )
    running = int(RUNNING_RE.search(text).group(1)) if RUNNING_RE.search(text) else 0
    tally = {}
    wall = ""
    for line in text.splitlines():
        m = TALLY_RE.match(line)
        if m:
            tally[m.group(2)] = int(m.group(1))
            if m.group(3) and m.group(2) == "passed":
                wall = m.group(3)
    ports = sorted(set(re.findall(r"frontend=:(\d+) backend=:(\d+)", text)))
    db = sorted(set(re.findall(r"db=sqlite:///(\S+?\.db)", text)))
    run_ids = sorted(set(re.findall(r"run=run(\d+)", text)))
    return {
        "log": os.path.basename(path),
        "run_ids": run_ids,
        "ports": [f"{f}/{b}" for f, b in ports],
        "db_basenames": [os.path.basename(d) for d in db],
        "running_claimed": running,
        "tally": tally,
        "wall": wall,
        "nodes": nodes,
    }


def main() -> int:
    logs = sys.argv[2:] or [
        f"{ROOT}/review/run-run222109.log",
        f"{ROOT}/review/run-run222133.log",
    ]
    head = sha_of_head()
    dirty = porcelain_lines()
    runs = [parse_log(p) for p in logs]
    all_nodes = [n for r in runs for n in r["nodes"]]

    triples = []
    problems = []
    for spec, ids in EXPECTED.items():
        for test_id in ids:
            nodeid = f"{spec} :: {test_id}"
            hits = [n for n in all_nodes if n["nodeid"] == nodeid]
            if len(hits) != 1:
                problems.append(f"{nodeid}: {len(hits)} log lines, expected exactly 1")
                continue
            hit = hits[0]
            triples.append(
                {
                    "exact_sha": head,
                    "nodeid": nodeid,
                    # The carrier coordinate has to round-trip: nodeid is rooted at the Playwright
                    # config root, so run_shape names that same directory as the cwd.  A nodeid read
                    # from <tree>/frontend with run_shape claiming <tree> is a wrong coordinate, not
                    # a product red, and the verifier cannot re-collect it.
                    "nodeid_root": f"{ROOT}/frontend",
                    "run_shape": (
                        f"cwd={ROOT}/frontend (the nodeid root above), {RUN_SHAPES[spec]}, "
                        f"command=python review/run_spec.py {spec} <port>, "
                        f"run {','.join(runs[0]['run_ids']) or '?'}"
                        f" (fresh _{runs[0]['db_basenames'][0] if runs[0]['db_basenames'] else '?'}),"
                        f" ports {','.join(runs[0]['ports']) or '?'}; verdict taken from the "
                        f"`{hit['status']} {hit['index']}` line in {hit['duration']}"
                    ),
                    "status_from_log": hit["status"],
                    "duration_from_log": hit["duration"],
                }
            )


    # green claim, derived
    for r in runs:
        if r["tally"].get("failed", 0) != 0:
            problems.append(f"{r['log']}: {r['tally'].get('failed')} failed")
        if r["tally"].get("passed", 0) != r["running_claimed"]:
            problems.append(f"{r['log']}: passed {r['tally'].get('passed')} != running {r['running_claimed']}")
    if dirty:
        problems.append(f"git status --porcelain (frontend, review) = {dirty} lines, expected 0")
    if len(triples) != sum(len(v) for v in EXPECTED.values()):
        problems.append(f"triples {len(triples)} != expected {sum(len(v) for v in EXPECTED.values())}")

    # measured fields, re-read from the gates' own output
    readings = {}
    for name in (
        "ord0269-cell1-reading.json",
        "ord0269-cell3-feed-failure.json",
        "ord0269-r6-exclusion-reading.json",
        "ord0269-r4-negative.json",
        "ord0273-text-reading.json",
        "ord0273-text-en-reading.json",
        "ord0273-action-reading.json",
    ):
        path = f"{EVIDENCE}/{name}"
        if not os.path.exists(path):
            problems.append(f"missing reading {name}")
            continue
        readings[name] = json.load(open(path, encoding="utf-8"))

    text_reading = readings.get("ord0273-text-reading.json", {})
    sentence = text_reading.get("sentence", "")
    detail = text_reading.get("detail", {}) or {}
    error_message = detail.get("errorMessage", "")
    en_reading = readings.get("ord0273-text-en-reading.json", {})
    sentence_en = en_reading.get("sentence", "")

    # self-test A: the leak scan must be able to fail -- run it against the technical detail and
    # require a hit there.  An always-false scan would "prove" the sentence clean for free.
    scan = lambda s: [shape for shape in LEAK_SHAPES if shape.lower() in s.lower()]
    has_cjk = lambda s: bool(re.search(r"[\u3400-\u9fff]", s))
    leak_shapes_seen = {
        "main_sentence": scan(sentence),
        "english_main_sentence": scan(sentence_en),
        "technical_detail_control": scan(error_message),
    }
    if leak_shapes_seen["main_sentence"]:
        problems.append(f"leak in the Chinese main sentence: {leak_shapes_seen['main_sentence']}")
    if leak_shapes_seen["english_main_sentence"]:
        problems.append(f"leak in the English main sentence: {leak_shapes_seen['english_main_sentence']}")
    if not leak_shapes_seen["technical_detail_control"]:
        problems.append("self-test A failed: the leak scan did not fire on the technical detail")

    # self-test B: each locale's painted copy must be that locale's own dictionary value, and each
    # dictionary must speak its own language.  A flat "count the key" check cannot see a Chinese
    # sentence sitting in the `en` dictionary -- that is the defect this exists to catch.
    locale_src = open(f"{ROOT}/frontend/src/i18n/LocaleContext.tsx", encoding="utf-8").read()

    def dict_block(name: str, until: str) -> str:
        start = locale_src.index(f"const {name}: Dict = {{")
        return locale_src[start : locale_src.index(until, start)]

    blocks = {
        "en": dict_block("en", "const zhCN: Dict = {"),
        "zh-CN": dict_block("zhCN", "const dictionaries: Record<TripLocale, Dict>"),
    }
    KEY_RE = re.compile(r'"trial\.sealedUnreadable":\s*\n?\s*"([^"]+)"')
    dict_values = {}
    for locale, block in blocks.items():
        hits = KEY_RE.findall(block)
        if len(hits) != 1:
            problems.append(f"trial.sealedUnreadable in the {locale} dictionary = {len(hits)} hits, expected 1")
            continue
        dict_values[locale] = hits[0]
    cjk_by_dictionary = {locale: has_cjk(value) for locale, value in dict_values.items()}
    if cjk_by_dictionary.get("zh-CN") is not True or cjk_by_dictionary.get("en") is not False:
        problems.append(f"self-test B failed: the CJK scan is not firing both ways: {cjk_by_dictionary}")
    if dict_values.get("zh-CN") != sentence:
        problems.append("the painted Chinese sentence is not the zhCN dictionary value byte-for-byte")
    if dict_values.get("en") != sentence_en:
        problems.append("the painted English sentence is not the en dictionary value byte-for-byte")


    payload = {
        "generatedBy": "e345b9d6",
        "orders": ["ORD-0269 cells 1/3 + R-4 negative + R-6 pagination", "ORD-0273 TEXT + ACTION"],
        "authoritative_tip_at_delivery": "c79e2b4f4efe414dba22a071a7136ae10b5c84aa",
        "candidate_tip": head,
        "candidate_blob_sha1_note": "sha1 of the tree bytes as committed; the authoritative line is untouched (single-writer)",
        "clean_worktree": {"porcelain_lines_frontend_review": dirty},
        "R_SCHEMA_01_class": {
            "rule": "SCHEMA_SOURCE_METHOD_CORRECTED",
            "row_source": "product API only -- e2e/_qoderRealSeed.setup.ts (travelers -> journeys -> "
            "stay-options/generate -> select) and ORD-0269 R-4's second journey via "
            "POST /api/v1/travelers + POST /api/v1/journeys",
            "not_used": ["DDL replay", "direct ensure_schema() call", "hand-written INSERTs"],
            "conclusions_depend_on": "rendered text, element visibility, HTTP status and header/body "
            "shape on the wire -- none depend on table structure, column existence, indexes, "
            "constraints, migration state or schema version",
            "therefore": "no schema re-run is required for these two gates",
        },
        "publisher_refusal_writing_rule": "evidence names the rule only (rule_hit: <NAME>); the "
        "guard's raw sentence is not copied into any artifact published for others to read",
        "runs": [
            {
                "log": r["log"],
                "run_ids": r["run_ids"],
                "ports": r["ports"],
                "dbs": r["db_basenames"],
                "running_claimed": r["running_claimed"],
                "tally": r["tally"],
                "wall": r["wall"],
                "node_lines": [
                    {"status": n["status"], "index": n["index"], "project": n["project"], "nodeid": n["nodeid"], "duration": n["duration"]}
                    for n in r["nodes"]
                ],
            }
            for r in runs
        ],
        "triples": triples,
        "measured_readings": readings,
        "leak_scan_selftest": leak_shapes_seen,
        "dictionary_equality": {
            "per_locale": {
                locale: {
                    "dictionary_value": dict_values.get(locale),
                    "painted": sentence if locale == "zh-CN" else sentence_en,
                    "equal": dict_values.get(locale)
                    == (sentence if locale == "zh-CN" else sentence_en),
                    "contains_cjk": cjk_by_dictionary.get(locale),
                }
                for locale in ("en", "zh-CN")
            },
        },
        "caught_this_round": (
            "commit 9d28c2b carried the Chinese sentence in the `en` dictionary, so an English screen "
            "would have spoken Chinese (ORD-0240's defect in the other coat). This segment replaces it "
            "with the registered English value and adds the ord0273-text-en node that reads the English "
            "arm off the rendered screen."
        ),
        "reddening_proof": (
            os.path.basename(ARMS_RECEIPT)
            if os.path.exists(ARMS_RECEIPT)
            else "NOT_PRESENT_YET -- the arm that puts the Chinese sentence back into `en` must be run "
            "before this round may claim the English node reddens"
        ),
        "verdict": "GREEN" if not problems else "PROBLEMS",
        "problems": problems,
    }
    blob = json.dumps(payload, ensure_ascii=False, indent=1).encode("utf-8")
    with open(OUT, "wb") as fh:
        fh.write(blob)
    print(f"wrote {OUT} bytes={len(blob)} sha1={hashlib.sha1(blob).hexdigest()[:16]}")
    print(f"candidate_tip={head}")
    print(f"triples={len(triples)}  problems={len(problems)}")
    for t in triples:
        print(f"  {t['status_from_log']:>7} {t['exact_sha'][:9]} {t['nodeid']} ({t['duration_from_log']})")
    for line in problems:
        print("  PROBLEM:", line)
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
