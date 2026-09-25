"""ORD-0310 · run this lane's own reverse-mutation arms against the keyless-deadline gate.

The discipline is the one the earlier batches used, because it is what makes a red readable rather
than anecdotal:

* every arm is applied through `mutation_anchor_guard.temporary_guarded_replace`, so an anchor that
  does not hit exactly the expected number of times aborts before the gate is touched -- a "kill"
  from a mutation that never landed is worthless;
* every arm carries a same-key precondition: the node it claims to kill must have been GREEN in the
  clean round on the same bytes, otherwise the red belongs to something else;
* after each arm the file is re-hashed against the committed blob of the tested tree, and at the end
  the whole working tree is re-hashed, so the next arm (and the next reader) knows the bytes;
* `claimed_result` is what this lane observed; `derived_result` stays null -- grading belongs to the
  red team (B-1).

`K0310_DERIVATION_PROBE_CONSTANT_TO_7S` is deliberately NOT a killer: it is expected to stay green,
and it is the arm that shows the number printed on the screen and the timer that ended the request
are the same constant, which is what ORD-0310 requirement 2 actually claims.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path("D:/moodle/_qoder_d_lane_20260923")
sys.path.insert(0, str(ROOT / "live_checks"))
import mutation_anchor_guard as guard  # noqa: E402

PYTHON = "D:/moodle/CityNexus/.venv/Scripts/python.exe"
SPEC_BASE = "qoder-ord0310-keyless-write-deadline"
SPEC_PATH = f"e2e/{SPEC_BASE}.spec.ts"
NODE_RE = re.compile(r"^\s*(ok|x|✘|failed|-)\s+\d+\s+\[[^\]]+\]\s+›\s+\S+\s+›\s+(.+?)(?:\s+\([\d.]+[ms]+\))?\s*$", re.M)
TALLY_RE = re.compile(r"^\s*\d+ (passed|failed|flaky)")

SHEET = ROOT / "frontend/src/features/planning/PlanWithAiSheet.tsx"
MODULE = ROOT / "frontend/src/lib/keylessWriteDeadline.ts"
K1 = "K1 无键写腿到点：屏幕说结果未知、不能补问，秒数与计时器同源"
K2 = "K2 正控：服务器两秒内答完时，这枚期限不碰正常结局"
K3 = "K3 反控：旅行者按取消时，期限不许冒充用户"

ARMS = [
    {
        "name": "K0310_DEADLINE_RENAMED_AS_CANCEL", "file": SHEET, "expected_hits": 1,
        "anchor": '          status: "UNKNOWN_KEYLESS_WRITE_DEADLINE",',
        "mutant": '          status: "CANCELLED_AFTER_SEND",',
        "owner": K1, "kind": "kill",
        "why": "把期限那一发改写成旅行者熟悉的「已取消」形状——正是 Q54 禁的那句话。",
    },
    {
        "name": "K0310_DEVICE_NOTE_UNDER_SERVER_LABEL", "file": SHEET, "expected_hits": 1,
        "anchor": "          failureReason: keylessWriteUnknownReading(cause.method, cause.path, cause.deadlineMs),",
        "mutant": "          failureReason: { ...keylessWriteUnknownReading(cause.method, cause.path,"
                  " cause.deadlineMs), from: \"server\" as const },",
        "owner": K1, "kind": "kill",
        "why": "把设备自己拼的句子挂到「服务器给出的原因」标签下（0280 那一族在本单的复发形）。",
    },
    {
        "name": "K0310_SENTENCE_PROMISES_REPLAY", "file": MODULE, "expected_hits": 1,
        "anchor": "`也不能靠同一把键补问：这条路线不认幂等键，它没有收下这把键，没有可回读的凭条。`,",
        "mutant": '`这一笔没有发生，按"再试一次"就行：同一把键可以让服务器把它补问出来。`,',
        "owner": K1, "kind": "kill",
        "why": "未知被写成「没有发生」并承诺可补问，同时把带秒数的那半句抹掉——三处判据一起该红。",
    },
    {
        "name": "K0310_DEADLINE_IMPERSONATES_TRAVELLER", "file": MODULE, "expected_hits": 1,
        "anchor": "  const onUpstreamAbort = () => controller.abort();",
        "mutant": "  const onUpstreamAbort = () => {\n    firedHere = true;\n    controller.abort();\n  };",
        "owner": K3, "kind": "kill",
        "why": "让旅行者自己的取消也走 firedHere ⇒ 期限冒充用户，K3 必须红。",
    },
    {
        "name": "K0310_TIMER_FIRES_BEFORE_THE_CONSTANT", "file": MODULE, "expected_hits": 1,
        "anchor": "  }, deadlineMs);",
        "mutant": "  }, 0);",
        "owner": K1, "kind": "kill",
        "why": "计时器不再用那枚常数（这里直接 0 ms）⇒ 屏幕上那个数字还对、实际等待时长早就脱钩，"
               "K1 里「等待时长与常数一致」那条必须红。",
    },
    {
        "name": "K0310_KEYLESS_LEG_HAS_SIGNAL_BUT_NO_DEADLINE", "file": SHEET, "expected_hits": 1,
        "anchor": "      const response = await fetchWithKeylessWriteDeadline(",
        "mutant": "      const response = await fetch(",
        "owner": K1, "kind": "kill",
        "why": "号令者 20:5x 要的那枚双臂自证：把外层包装拆掉，`signal` 一个不少地留在选项对象里"
               "（那一发的 init 里本来就有 `signal,`），只是期限没有了。若判据是「有没有 signal」，"
               "这一枚会绿；实测 K1 必须红、K3 必须仍绿，所以判据确实是「期限到了」，"
               "而拆包装也没有动到旅行者自己的取消那一支。",
    },
    {
        "name": "K0310_DERIVATION_PROBE_CONSTANT_TO_7S", "file": MODULE, "expected_hits": 1,
        "anchor": "export const KEYLESS_WRITE_DEADLINE_MS = 60_000;",
        "mutant": "export const KEYLESS_WRITE_DEADLINE_MS = 7_000;",
        "owner": K1, "kind": "probe_expect_green",
        "why": "常数改小：这一格应仍绿，且屏幕上那个秒数与实际等待时长一起跟着变（同源证明）。",
    },
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def committed_blob(rev: str, rel: str) -> bytes:
    out = subprocess.run(["git", "show", f"{rev}:{rel}"], cwd=ROOT, capture_output=True)
    if out.returncode != 0:
        raise SystemExit(f"ABORT: cannot read committed blob {rev}:{rel}: {out.stderr[:200]!r}")
    return out.stdout


def port_free(port: int) -> bool:
    out = subprocess.run(["netstat", "-ano", "-p", "TCP"], capture_output=True, text=True,
                         encoding="utf-8", errors="replace").stdout
    return not re.search(rf":{port}\s+\S+\s+LISTENING", out)


def run_gate(label: str, port: int) -> dict:
    if not port_free(port):
        raise SystemExit(f"ABORT_PORT_OCCUPIED: :{port} already LISTENING ({label})")
    proc = subprocess.run([PYTHON, str(ROOT / "review/run_spec.py"), SPEC_BASE, str(port)],
                          cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace",
                          env={**os.environ, "CNX_LANE_ROOT": str(ROOT)})
    text = proc.stdout + proc.stderr
    # `run_spec.py` lets Playwright write to the inherited console, so the report lines are NOT in
    # this process's captured pipes; the wrapper tells us the log file it wrote. Parsing that file is
    # the only way to attribute a red to a named node (an empty node map used to read as "SURVIVED").
    log_path = re.search(r"log=(\S+)", text)
    if log_path:
        candidate = Path(log_path.group(1))
        if candidate.is_file():
            text = candidate.read_text(encoding="utf-8", errors="replace") + text
    nodes: dict[str, str] = {}
    for m in NODE_RE.finditer(text):
        mark, title = m.group(1), m.group(2).strip()
        if "seed a real journey" in title:
            continue
        nodes[title] = "GREEN" if mark == "ok" else "RED"
    run_ids = re.findall(r"run_id=(\w+)", text)
    dbs = re.findall(r"db=sqlite:///\S*?([^/\\]+\.db)", text)
    return {"label": label, "gateExit": proc.returncode, "nodes": nodes,
            "tallies": [l.strip() for l in text.splitlines() if TALLY_RE.match(l)],
            "runId": run_ids[0] if run_ids else "NO_RUN_ID",
            "db": dbs[0] if dbs else "NO_DB", "port": port,
            "lastLine": text.strip().splitlines()[-1][:200] if text.strip() else ""}


def run_arm(arm: dict, tested: str, committed_hash: dict, clean: dict, port: int) -> dict:
    path: Path = arm["file"]
    rel = path.relative_to(ROOT).as_posix()
    name = path.name
    size_before = path.stat().st_size
    with guard.temporary_guarded_replace(path, arm["anchor"].encode("utf-8"),
                                         arm["mutant"].encode("utf-8"),
                                         expected_hits=arm["expected_hits"]) as receipt:
        size_during = path.stat().st_size
        attempt = run_gate(arm["name"], port)
    after = sha256(path)
    red = sorted(t for t, v in attempt["nodes"].items() if v == "RED")
    if arm["kind"] == "kill":
        claimed = "KILLED" if (red and arm["owner"] in red) else "SURVIVED"
    else:
        claimed = "HOLDING_AS_EXPECTED" if not red else "PROBE_WENT_RED_UNEXPECTED"
    return {
        "arm": arm["name"], "kind": arm["kind"], "file": rel,
        "triple": {"exact_sha": tested, "nodeid": f"{SPEC_PATH} :: {arm['owner']}", "shape": ["chromium"]},
        "anchor_hits": receipt.anchor_hits, "expected_anchor_hits": receipt.expected_anchor_hits,
        "bytes_changed": receipt.bytes_changed,
        "sizes": {"before": size_before, "during_mutation": size_during,
                  "delta_bytes": size_during - size_before,
                  "after_restore": path.stat().st_size},
        "hashes_12": {"before": committed_hash[name][:12], "mutant": receipt.mutated_sha256[:12],
                      "after_restore": after[:12]},
        "clean_round": {"runId": clean["runId"], "db": clean["db"], "port": clean["port"],
                        "owner_node_state": clean["nodes"].get(arm["owner"], "NODE_NOT_IN_CLEAN_ROUND")},
        "same_key_precondition_holds": clean["nodes"].get(arm["owner"]) == "GREEN",
        "attempt": attempt, "red_nodes": red,
        "restored_to_tested_tree_bytes": after == committed_hash[name],
        "screen_reading_from_this_run": load_evidence(attempt["runId"]),
        "claimed_result": claimed, "derived_result": None, "why": arm["why"],
    }


EVIDENCE_DIR = ROOT / "review/evidence/ord0310"


def load_evidence(run_id: str) -> dict:
    """Read the arms' evidence file that THIS run wrote. No file, no reading: never invent one."""

    cand = EVIDENCE_DIR / f"keyless_deadline_arms-{run_id}.json"
    if not cand.is_file():
        return {"evidence_file": f"NOT_FOUND {cand.name}"}
    data = json.loads(cand.read_text(encoding="utf-8"))
    keep = {}
    for arm_id, body in (data.get("arms") or {}).items():
        keep[arm_id] = {
            "verdict": body.get("verdict"), "elapsed_ms": (body.get("elapsed_ms")),
            "post_count": (body.get("post_count")), "deadline_constant_ms": body.get("deadline_constant_ms"),
            "status": (body.get("read") or {}).get("status"),
            "card_text": ((body.get("read") or {}).get("card_text") or "")[:200],
            "reason_text": ((body.get("read") or {}).get("reason") or "")[:220],
            "origin": (body.get("read") or {}).get("origin"),
            "label": (body.get("read") or {}).get("label"),
            "detail_block_attached": (body.get("read") or {}).get("detail_block_attached"),
            "failed_claims": body.get("failed") or [],
        }
    return keep


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tested-tree", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--start-port", type=int, default=4720)
    args = ap.parse_args()
    tested = args.tested_tree.strip()
    if not re.fullmatch(r"[0-9a-f]{40}", tested):
        raise SystemExit(f"ABORT: --tested-tree is not a 40-hex: {tested!r}")
    files = [SHEET, MODULE]
    committed_hash = {f.name: hashlib.sha256(committed_blob(tested, f.relative_to(ROOT).as_posix())).hexdigest()
                      for f in files}
    before = {f.name: sha256(f) for f in files}
    drift = {k: (before[k], committed_hash[k]) for k in before if before[k] != committed_hash[k]}
    if drift:
        print(f"ABORT: working tree does not equal the tested tree: {json.dumps(drift)[:400]}")
        return 2

    clean = run_gate("clean-round", args.start_port)
    print(f"clean {clean['runId']} :{clean['port']} nodes={json.dumps(clean['nodes'], ensure_ascii=False)[:260]}")
    results = []
    for i, arm in enumerate(ARMS):
        rec = run_arm(arm, tested, committed_hash, clean, args.start_port + 10 * (i + 1))
        results.append(rec)
        print(f"  {arm['name']:42s} {rec['claimed_result']:22s} run={rec['attempt']['runId']} "
              f"red={len(rec['red_nodes'])} restored={rec['restored_to_tested_tree_bytes']}")

    payload = {
        "order": "ORD-0310", "lane": "D e345b9d6",
        "generated_at": datetime.datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M:%S%:z"),
        "tested_tree": tested, "spec": SPEC_PATH,
        "gate_command": f"python review/run_spec.py {SPEC_BASE} <port>   (CNX_LANE_ROOT={ROOT})",
        "clean_round": clean,
        "arms_total": len(results),
        "killed": sum(1 for r in results if r["claimed_result"] == "KILLED"),
        "survived": sum(1 for r in results if r["claimed_result"] == "SURVIVED"),
        "probes": sum(1 for r in results if r["kind"] != "kill"),
        "all_arms_restored_to_tested_tree_bytes": all(r["restored_to_tested_tree_bytes"] for r in results),
        "tree_unchanged_by_this_run": all(sha256(f) == before[f.name] for f in files),
        "every_arm_parsed_at_least_one_node": all(r["attempt"]["nodes"] for r in results),
        "all_arms_carry_a_green_same_key_precondition": all(r["same_key_precondition_holds"] for r in results),
        "arms": results,
        "discipline": {"refs_pushed": 0, "authority_line_moved": 0, "demo_reset": 0,
                       "user_db_reads_writes": 0, "credentials_printed": 0,
                       "note": "claimed_result is observation by this lane; derived_result belongs to "
                               "the verifier and stays null here"},
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {out} {out.stat().st_size} B tree_unchanged={payload['tree_unchanged_by_this_run']} "
          f"all_restored={payload['all_arms_restored_to_tested_tree_bytes']} killed={payload['killed']}/"
          f"{payload['arms_total'] - payload['probes']}")
    return 0


raise SystemExit(main())
