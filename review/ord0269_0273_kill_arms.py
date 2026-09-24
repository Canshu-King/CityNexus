"""ORD-0269 / ORD-0273 acceptance: the named reverse mutations, one owning node each.

Each arm is the *shape of the defect*, restored by byte-digest afterwards:

  K269_REMOVE_MARKER_WRITE            the clause-1 write disappears -> cell 1 must redden
  K269_CLEAR_MARKER_BEFORE_REQUEST    clause 5's violation shape: the marker is wiped as the
                                      request goes out, so a re-entry has nothing to resume from
  K269_FEED_FAILURE_SILENT            an unreadable feed is reported as "nothing pending" -> cell 3
  K269_PAGINATION_GUESS               absence from a capped, ascending page is read as a
                                      conclusion -> R-6
  K269_GLOBAL_MARKER                  the key stops being journey-scoped -> R-4's negative control
  K273_RAW_MESSAGE_BACK               error.message re-enters the main sentence -> TEXT
  K273_EN_DICT_CHINESE                the `en` dictionary carries the Chinese sentence -> TEXT-EN,
                                      and only that node: this is the reddening proof for the defect
                                      this segment fixed
  K273_NO_RETRY_STEP                  the failure screen loses its executable step -> ACTION

Nodes are keyed by their FULL test id, not by the `ord0269` prefix: several nodes in these two
specs share the prefix, and a prefix key would let one node's verdict overwrite another's.
Receipt carries claimed_result only; derived_result belongs to the verifier.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from hashlib import sha256
from pathlib import Path

ROOT = Path("D:/moodle/_qoder_d_lane_20260923")
sys.path.insert(0, str(Path("D:/moodle/_qoder_integration_20260919/live_checks")))
from mutation_anchor_guard import temporary_guarded_replace  # noqa: E402

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

SHEET = ROOT / "frontend/src/features/planning/PlanWithAiSheet.tsx"
MODULE = ROOT / "frontend/src/api/journeyContinuation.ts"
HOOK = ROOT / "frontend/src/api/useContinuationState.ts"
V8 = ROOT / "frontend/src/app/V8Experience.tsx"
LOCALE = ROOT / "frontend/src/i18n/LocaleContext.tsx"
SETUP = ROOT / "frontend/src/features/setup/JourneyTrialSetup.tsx"
SPEC_269 = "e2e/qoder-continuation-owner.spec.ts"
SPEC_273 = "e2e/qoder-sealed-failure-speaks-and-offers-retry.spec.ts"
PYTHON = "D:/moodle/CityNexus/.venv/Scripts/python.exe"
RECEIPT_DIR = ROOT / "review/evidence/ui-overnight"

FILES = [SHEET, MODULE, HOOK, V8, LOCALE, SETUP]

MARK_BLOCK = (
    "      if (mission?.id) {\n"
    "        markPendingContinuation(journeyId, String(mission.id));\n"
    "      }\n"
)
MARK_BLOCK_CLEARED = MARK_BLOCK + (
    "      /* clause-5 shape: the marker is gone by the time the next request leaves */\n"
    "      window.localStorage.removeItem(`citynexus.v8.continuation.${journeyId}`);\n"
)
MARKER_KEY_LINE = (
    "const MARKER_KEY = (journeyId: string) => `citynexus.v8.continuation.${journeyId}`;"
)
MARKER_KEY_GLOBAL = (
    "const MARKER_KEY = (_journeyId: string) => `citynexus.v8.continuation.global`;"
)
UNREADABLE_LINE = '    return { kind: "unconfirmable", reason: "feed_unreadable" };'
HOOK_ERROR_RETURN = (
    "    return { state: { kind: \"unconfirmable\", reason: \"feed_unreadable\" }, feedReadFailed: true };"
)
OUT_OF_PAGE_LINE = '    return { kind: "unconfirmable", reason: "mission_out_of_page" };'
SENTENCE_SET_LINE = '      setSealedDemoUnavailable(t("trial.sealedUnreadable"));'
EN_DICT_ENTRY = (
    '  "trial.sealedUnreadable":\n'
    '    "Couldn\'t read the sealed demo: the server answered just now, but what it answered '
    'isn\'t something we can use. Nothing you filled in caused this.",'
)
ZH_SENTENCE = "没读到封存演示的信息：服务器刚才答了，但答的内容我们用不了。这不是你填错了什么。"
RETRY_BLOCK = (
    "          <button\n"
    "            type=\"button\"\n"
    "            className=\"trial-back-link\"\n"
    "            data-testid=\"trial-sealed-retry\"\n"
    "            disabled={busy}\n"
    "            onClick={() => void onUseSealedDemo()}\n"
    "          >\n"
    "            {zh ? \"重试\" : \"Retry\"}\n"
    "          </button>\n"
)

# name, owner node, spec, file, anchor, mutant, why
ARMS = [
    (
        "K269_REMOVE_MARKER_WRITE",
        "ord0269-cell1-reveals-and-names-its-boundary",
        SPEC_269,
        SHEET,
        MARK_BLOCK,
        "",
        "the clause-1 write is gone: after leg 1 answers there is nothing to trust, so a re-entry "
        "must show neither the sentence nor the door",
    ),
    (
        "K269_CLEAR_MARKER_BEFORE_REQUEST",
        "ord0269-cell1-reveals-and-names-its-boundary",
        SPEC_269,
        SHEET,
        MARK_BLOCK,
        MARK_BLOCK_CLEARED,
        "arbiter clause 5's own shape: the marker is written and then wiped as the request goes out, "
        "so the interrupted run is unfindable again -- this is the design the ruling rejected",
    ),
    (
        "K269_FEED_READ_FAILURE_SILENT",
        "ord0269-cell3-feed-failure-and-page-exclusion-are-named",
        SPEC_269,
        HOOK,
        HOOK_ERROR_RETURN,
        "    return { state: { kind: \"none\" }, feedReadFailed: false };",
        "the read fails and the hook reports 'nothing pending': cell 3's first read (feed 500) is "
        "the one that exercises this emitter",
    ),
    (
        "K269_MALFORMED_FEED_SILENT",
        "ord0269-cell3-feed-failure-and-page-exclusion-are-named",
        SPEC_269,
        MODULE,
        UNREADABLE_LINE,
        '    return { kind: "none" };',
        "an answered-but-unusable 200 (no events array) is reported as silence. The first arms pass "
        "ran this same mutant against a gate that only read the 500 path, and it survived -- which "
        "proved the guard had no reader, not that the product was right; cell 3 now has its own read",
    ),
    (
        "K269_PAGINATION_GUESS",
        "ord0269-r6-page-exclusion-yields-no-conclusion",
        SPEC_269,
        MODULE,
        OUT_OF_PAGE_LINE,
        '    return { kind: "pending", missionId: marker.missionId };',
        "absence from a capped, ascending page is read as a conclusion -- the exact inference R-6 "
        "forbids; cell 3's page-exclusion half is expected as collateral",
    ),
    (
        "K269_GLOBAL_MARKER",
        "ord0269-r4-a-brand-new-journey-shows-nothing",
        SPEC_269,
        MODULE,
        MARKER_KEY_LINE,
        MARKER_KEY_GLOBAL,
        "the marker stops being journey-scoped, so one journey's interrupted round lights up on a "
        "brand-new journey -- R-4 exists to catch exactly that",
    ),
    (
        "K273_RAW_MESSAGE_BACK",
        "ord0273-text-the-sentence-is-the-key-and-no-shape-leaks",
        SPEC_273,
        V8,
        SENTENCE_SET_LINE,
        "      setSealedDemoUnavailable(`${t(\"trial.sealedUnreadable\")}: ${error.message}`);",
        "the pre-fix shape: raw error.message glued onto the user sentence, so MIME and error shapes "
        "land in the main copy; every 0273 node that reads the sentence is expected red, the "
        "retry-node red is collateral from the same sentence assertion",
    ),
    (
        "K273_EN_DICT_CHINESE",
        "ord0273-text-en-arm-speaks-english-and-neither-side-leaks",
        SPEC_273,
        LOCALE,
        EN_DICT_ENTRY,
        f'  "trial.sealedUnreadable": "{ZH_SENTENCE}",',
        "the defect this segment fixed, put back on purpose: the English dictionary speaking "
        "Chinese. Only the English node may redden -- if the Chinese node reddens too, the arms "
        "are not independent",
    ),
    (
        "K273_NO_RETRY_STEP",
        "ord0273-action-retry-is-a-real-executable-step",
        SPEC_273,
        SETUP,
        RETRY_BLOCK,
        "",
        "the failure screen keeps its sentence but loses its next step: ACTION must redden while the "
        "two TEXT nodes stay green, which is what proves ACTION is judged on its own",
    ),
]

NODE_RE = re.compile(r"^\s*(ok|x|✘|failed|-)\s+\d+\s+\[[^\]]+\]\s+›\s+\S+\s+›\s+(.+?)(?:\s+\([\d.]+[ms]+\))?\s*$")


def digests() -> dict[str, str]:
    return {path.name: sha256(path.read_bytes()).hexdigest() for path in FILES}


def port_busy(port: int) -> bool:
    out = subprocess.run(
        "netstat -ano -p tcp",
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        shell=True,
    ).stdout
    return any(f":{port} " in line and "LISTENING" in line for line in out.splitlines())


def slug(title_with_path: str) -> str:
    """Full test id, without the Chinese tail and without the spec path."""
    return title_with_path.split(" — ")[0].strip()


def run(label: str, port: int, spec: str) -> dict:
    env = dict(os.environ)
    env["CNX_LANE_ROOT"] = str(ROOT)
    started = time.time()
    proc = subprocess.run(
        [PYTHON, str(ROOT / "review/run_spec.py"), spec, str(port)],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    out = proc.stdout + proc.stderr
    run_id = next(
        (line.split("run_id=", 1)[1].split()[0] for line in out.splitlines() if line.startswith("run_id=")), ""
    )
    summary = next(
        (line.strip() for line in reversed(out.splitlines()) if " passed" in line or " failed" in line), ""
    )
    nodes: dict[str, str] = {}
    for line in out.splitlines():
        m = NODE_RE.match(line)
        if not m:
            continue
        token, title = m.group(1), slug(m.group(2))
        if not title.startswith("ord02"):
            continue  # the real-seed setup project is not a judged node
        nodes[title] = {"ok": "GREEN"}.get(token, "RED")
    print(
        f"[{label}] exit={proc.returncode} run={run_id} {round(time.time() - started)}s {summary!r} "
        + " ".join(f"{k.split('-')[0]}:{v}" for k, v in sorted(nodes.items())),
        flush=True,
    )
    return {
        "label": label,
        "spec": spec,
        "exitCode": proc.returncode,
        "runId": run_id,
        "summary": summary,
        "stackStarted": bool(summary),
        "nodes": nodes,
    }


def main() -> int:
    tag = sys.argv[1] if len(sys.argv) > 1 else "first"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 4960
    span = list(range(port, port + 2 * len(ARMS)))
    busy = sorted({p for p in span + [p + 4000 for p in span] if port_busy(p)})
    if busy:
        print(f"ABORT: ports already listening: {busy}")
        return 6
    originals = digests()
    for name, _owner, _spec, path, anchor, _mutant, _why in ARMS:
        hits = open(path, encoding="utf-8", newline="").read().count(anchor)
        if hits != 1:
            print(f"ABORT: {name} anchor hits={hits} in {path.name}, expected exactly 1")
            return 2

    record = {
        "generatedBy": "e345b9d6",
        "orders": ["ORD-0269 cells 1/3 + R-4 + R-6", "ORD-0273 TEXT / TEXT-EN / ACTION"],
        "runTag": tag,
        "at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "head": subprocess.run(
            "git rev-parse HEAD", cwd=str(ROOT), capture_output=True, text=True, shell=True
        ).stdout.strip(),
        "tree": str(ROOT),
        "arms": [],
        "verifierNote": (
            "claimed_result is self-reported; derived_result / direct_red / collateral_red are "
            "WRITTEN_BY_VERIFIER"
        ),
        "filesBefore": originals,
    }
    for name, owner, spec, path, anchor, mutant, why in ARMS:
        print(f"\n=== {name} (owner {owner}) ===", flush=True)
        baseline = run("baseline-owner-spec", port, spec)
        port += 1
        before = digests()
        with temporary_guarded_replace(path, anchor.encode(), mutant.encode(), expected_hits=1) as guard:
            attempt = run("mutated-owner-spec", port, spec)
            port += 1
        after = digests()
        red = sorted(k for k, v in attempt["nodes"].items() if v == "RED")
        green = sorted(k for k, v in attempt["nodes"].items() if v == "GREEN")
        record["arms"].append(
            {
                "name": name,
                "ownerNode": owner,
                "why": why,
                "file": str(path),
                "anchor_hits": guard.anchor_hits,
                "bytes_changed": guard.bytes_changed,
                "mutated_sha256": guard.mutated_sha256,
                "restored_exact": after[path.name] == before[path.name] == originals[path.name],
                "baseline": baseline,
                "attempt": attempt,
                "redSet": red,
                "greenSet": green,
                "exclusiveToOwner": red == [owner],
                "claimed_result": (
                    "INVALID_STACK"
                    if not (baseline["stackStarted"] and attempt["stackStarted"])
                    else "KILLED"
                    if attempt["nodes"].get(owner) == "RED" and baseline["nodes"].get(owner) == "GREEN"
                    else "SURVIVED"
                    if attempt["nodes"].get(owner) == "GREEN"
                    else "BASELINE_RED -- arm not measured"
                ),
            }
        )

    record["filesAfter"] = digests()
    record["treeUnchangedByThisRun"] = record["filesAfter"] == originals
    record["allArmsKilled"] = all(a["claimed_result"] == "KILLED" for a in record["arms"])
    record["baselineNodesGreen"] = sorted(
        {n for a in record["arms"] for n, v in a["baseline"]["nodes"].items() if v == "GREEN"}
    )
    out_path = RECEIPT_DIR / f"ord0269-0273-arms-{tag}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    for arm in record["arms"]:
        print(
            f"{arm['claimed_result']:14s} owner={arm['ownerNode'][:46]:46s} red={','.join(arm['redSet']) or '-'} "
            f"anchor={arm['anchor_hits']} bytes={arm['bytes_changed']} restored={arm['restored_exact']}"
        )
    print(f"allArmsKilled={record['allArmsKilled']} treeUnchanged={record['treeUnchangedByThisRun']}")
    print(f"receipt={out_path}")
    return 0 if record["treeUnchangedByThisRun"] and record["allArmsKilled"] else 1


if __name__ == "__main__":
    sys.exit(main())
