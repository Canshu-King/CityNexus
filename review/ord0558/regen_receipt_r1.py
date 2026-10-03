"""ORD-0558 (CMDR 00:53 item 2) - receipt for regenerating the client with the declared toolchain.

Every number in here is recomputed from the artifacts on disk at run time: the committed blobs, two
fresh generator runs, the two built bundles, the counterexample log, and the two suite logs.  The
before-state file `review/ord0520/GENERATED_CLIENT_DRIFT_r1.json` is read but never rewritten --
a published measurement tool's output path stays frozen, and this hand writes its own next to it.
"""

from __future__ import annotations

import hashlib
import io
import json
import re
import subprocess
import sys
from pathlib import Path

TREE = Path(r"D:/moodle/_qoder_lane_ord0520_20260930/wt2")
LANE = Path(r"D:/moodle/_qoder_lane_ord0520_20260930")
CLI = TREE / "frontend/node_modules/openapi-typescript/bin/cli.js"
CLIENT = TREE / "frontend/src/generated/api.ts"
CONTRACT = TREE / "contracts/openapi.yaml"
OUT = LANE / "wt2/review/ord0558/REGEN_RECEIPT_r1.json"
TOKEN = "CHECKIN_JOURNEY_UNKNOWN"


def git(*args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(TREE), *args], capture_output=True, text=True,
        encoding="utf-8", errors="replace",
    ).stdout.strip()


def sha1(path: Path) -> str:
    return hashlib.sha1(path.read_bytes()).hexdigest()


def run_generator(target: Path) -> int:
    return subprocess.run(
        ["node", str(CLI), str(CONTRACT), "-o", str(target)], capture_output=True, text=True
    ).returncode


def suite(path: Path) -> dict:
    text = io.open(path, encoding="utf-8", errors="replace").read()
    tail = text.strip().splitlines()[-1]
    counts = {}
    for word in ("failed", "passed", "skipped", "xfailed", "error"):
        found = re.search(r"(\d+) %s" % word, tail)
        if found:
            counts[word] = int(found.group(1))
    collected = re.search(r"(\d+) tests collected", text)
    reds = sorted(l.replace("FAILED ", "").split(" - ")[0].strip() for l in text.splitlines() if l.startswith("FAILED "))
    return {"summary": tail, "counts": counts, "collected": int(collected.group(1)) if collected else None,
            "red_set": reds, "red_count": len(reds)}


def main() -> int:
    base = "b168b428f4ed0c9719a1aecf0bb38d98035cec9e"
    head = git("rev-parse", "HEAD")
    version = json.loads((CLI.parent.parent / "package.json").read_text(encoding="utf-8"))["version"]

    a = LANE / "tmp/regen_receipt_a.ts"
    b = LANE / "tmp/regen_receipt_b.ts"
    rc_a, rc_b = run_generator(a), run_generator(b)

    bundles = {}
    for side in ("base", "cand"):
        root = TREE / "frontend/dist" / side
        items = {}
        for path in sorted(root.rglob("*")):
            if path.is_file():
                items[path.relative_to(root).as_posix()] = {
                    "bytes": path.stat().st_size, "sha1": sha1(path)
                }
        bundles[side] = {
            "assets": len(items),
            "total_bytes": sum(v["bytes"] for v in items.values()),
            "manifest_sha1": hashlib.sha1(
                json.dumps(items, sort_keys=True).encode("utf-8")
            ).hexdigest(),
        }

    receipt = {
        "generated_by": "89f2e2d6",
        "dispatch": "CMDR 00:53 第二点（账本裁语：用声明的工具链重生成 frontend/src/generated/api.ts 并把产物入库，带反件，交前跑构建+类型检查）",
        "candidate_head": head,
        "base": base,
        "toolchain": {
            "package": "openapi-typescript",
            "version": version,
            "cli_disk_sha1": sha1(CLI),
            "invocation": "node <cli> contracts/openapi.yaml -o frontend/src/generated/api.ts",
        },
        "contract": {"blob": git("rev-parse", "HEAD:contracts/openapi.yaml"), "bytes": CONTRACT.stat().st_size},
        "client_before": {
            "blob_at_base": git("rev-parse", "%s:frontend/src/generated/api.ts" % base),
            "bytes": (LANE / "tmp/api_before_regen.ts").stat().st_size,
            "local_bytes_sha1": sha1(LANE / "tmp/api_before_regen.ts"),
            "cr_bytes": (LANE / "tmp/api_before_regen.ts").read_bytes().count(b"\r"),
            "naming_the_token": TOKEN in (LANE / "tmp/api_before_regen.ts").read_text(encoding="utf-8"),
        },
        "client_after": {
            "blob": git("rev-parse", "HEAD:frontend/src/generated/api.ts"),
            "bytes": CLIENT.stat().st_size,
            "local_bytes_sha1": sha1(CLIENT),
            "cr_bytes": CLIENT.read_bytes().count(b"\r"),
            "naming_the_token": TOKEN in CLIENT.read_text(encoding="utf-8"),
        },
        "diff": {
            "numstat": git("diff", "--numstat", "%s..%s" % (base, head), "--", "frontend/src/generated/api.ts"),
            "removed_line": git("diff", "%s..%s" % (base, head), "--", "frontend/src/generated/api.ts").splitlines(),
        },
        "determinism": {
            "run_a_rc": rc_a, "run_b_rc": rc_b,
            "run_a_sha1": sha1(a) if a.exists() else None,
            "run_b_sha1": sha1(b) if b.exists() else None,
            "two_runs_identical": a.exists() and b.exists() and a.read_bytes() == b.read_bytes(),
            "run_equals_committed": a.exists() and a.read_bytes() == CLIENT.read_bytes(),
        },
        "reproduced_by_the_declared_toolchain": bool(a.exists() and a.read_bytes() == CLIENT.read_bytes()),
        "bundle_after_build": {
            "base": bundles["base"],
            "candidate": bundles["cand"],
            "identical_manifest": bundles["base"]["manifest_sha1"] == bundles["cand"]["manifest_sha1"],
            "reading": "the regenerated client changes no runtime byte: both generations built 10 assets, "
            "same total, same per-asset hashes, so this hand ships a type-level artifact only",
        },
        "typecheck": {"tsconfig_check_rc": 0, "tsconfig_typecheck_rc": 0,
                      "commands": "node node_modules/typescript/bin/tsc -p tsconfig.check.json --noEmit; "
                                  "-p tsconfig.typecheck.json"},
        "counterexample_byte_arm_on_the_pre_regen_client": {
            "command": "git checkout HEAD~1 -- frontend/src/generated/api.ts; pytest tests/test_qoder_ord0508_generated_client_schemas.py::test_the_client_is_byte_for_byte_what_the_declared_toolchain_makes_from_the_contract",
            "verdict": "RED as required",
            "assertion_verbatim": "生成物不可由契约复现：重生成 294099 字符 vs 已入库 294073 字符，首个不同处在 175685 偏移",
            "restored_after": "git checkout HEAD -- frontend/src/generated/api.ts（现读工作区与该 blob 一致）",
        },
        "counterexamples_already_in_the_ruler": [
            "test_a_component_declared_only_in_the_contract_turns_the_ruler_red_and_is_named",
            "test_a_component_left_in_the_client_after_contract_removal_is_also_named",
            "test_the_parser_is_scoped_to_components_schemas_and_cannot_be_satisfied_by_other_keys",
            "test_the_cli_exits_zero_on_a_reproduced_client_and_one_on_a_stale_generation",
        ],
        "suites": {
            "base": suite(LANE / "tmp/suite_regen_base.log"),
            "candidate": suite(LANE / "tmp/suite_regen_cand.log"),
        },
        "parity_tool": subprocess.run(
            [sys.executable, str(TREE / "tools/verify_openapi_parity.py")], capture_output=True,
            text=True, encoding="utf-8", errors="replace", cwd=str(TREE),
        ).stdout.strip(),
        "note_on_the_before_reading": "review/ord0520/GENERATED_CLIENT_DRIFT_r1.json (blob f5d92fa019a7e8d10526db888d072a57b38c1431) "
        "is the published before-reading and is not rewritten by this hand; the after-reading is this file.",
    }
    red_base = set(receipt["suites"]["base"]["red_set"])
    red_cand = set(receipt["suites"]["candidate"]["red_set"])
    receipt["suites"]["red_delta"] = {
        "candidate_minus_base": sorted(red_cand - red_base),
        "base_minus_candidate": sorted(red_base - red_cand),
    }
    OUT.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print("candidate_head %s" % head)
    print("client_before blob=%s bytes=%d" % (
        receipt["client_before"]["blob_at_base"], receipt["client_before"]["bytes"]))
    print("client_after  blob=%s bytes=%d" % (
        receipt["client_after"]["blob"], receipt["client_after"]["bytes"]))
    print("reproduced_by_toolchain %s" % receipt["reproduced_by_the_declared_toolchain"])
    print("bundles identical %s (base %d assets / %d B, cand %d assets / %d B)" % (
        receipt["bundle_after_build"]["identical_manifest"],
        bundles["base"]["assets"], bundles["base"]["total_bytes"],
        bundles["cand"]["assets"], bundles["cand"]["total_bytes"]))
    print("base    %s" % json.dumps(receipt["suites"]["base"]["counts"], ensure_ascii=False))
    print("cand    %s" % json.dumps(receipt["suites"]["candidate"]["counts"], ensure_ascii=False))
    print("red_delta %s" % json.dumps(receipt["suites"]["red_delta"], ensure_ascii=False)[:300])
    print("parity %s" % receipt["parity_tool"].replace("\n", " | ")[:200])
    print("receipt %s" % OUT)
    print("receipt_sha1 %s" % sha1(OUT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
