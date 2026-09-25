"""Build the Hermes R21 request_replan retry external-review package."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import zipfile
from pathlib import Path


CRITICAL_FILES = [
    "agent-mcp/citynexus_mcp/client.py",
    "agent-mcp/tests/test_client_error_detail.py",
    "scripts/hermes_r20_transport_reliability_probe.py",
    "scripts/hermes_r21_request_replan_retry_reliability_probe.py",
    "backend/tests/test_v18_hermes_r21_request_replan_retry_probe.py",
    "scripts/hermes_r4_contract_probe.py",
    "scripts/validate_hermes_r21_review.py",
    "scripts/build_hermes_r21_review_package.py",
    "reports/hermes/HERMES_R21_SCENARIO.md",
]


def git(root: Path, *args: str, binary: bool = False) -> bytes | str:
    value = subprocess.check_output(["git", *args], cwd=root)
    return value if binary else value.decode("utf-8").strip()


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def build(
    root: Path,
    evidence: Path,
    focused_tests: Path,
    output_zip: Path,
    additional_tests: list[Path],
) -> dict[str, str]:
    head = git(root, "rev-parse", "HEAD")
    parent = git(root, "rev-parse", "HEAD^")
    stage = output_zip.with_name(output_zip.stem + "-stage")
    if stage.exists():
        shutil.rmtree(stage)
    (stage / "evidence").mkdir(parents=True)
    for item in evidence.iterdir():
        lower_name = item.name.casefold()
        database_artifact = (
            ".sqlite" in lower_name
            or ".sqlite3" in lower_name
            or lower_name.endswith(("-wal", "-shm", ".wal", ".shm"))
        )
        if item.is_file() and not database_artifact:
            shutil.copy2(item, stage / "evidence" / item.name)
    (stage / "tests").mkdir()
    shutil.copy2(focused_tests, stage / "tests" / focused_tests.name)
    for test_output in additional_tests:
        shutil.copy2(test_output, stage / "tests" / test_output.name)
    shutil.copy2(root / "scripts/validate_hermes_r21_review.py", stage / "validate_hermes_r21_review.py")
    shutil.copy2(root / "reports/hermes/HERMES_R21_SCENARIO.md", stage / "HERMES_R21_SCENARIO.md")
    source = stage / "source"
    (source / "blobs").mkdir(parents=True)
    (source / "final-head.commit").write_bytes(git(root, "cat-file", "commit", head, binary=True))
    (source / "final-parent.commit").write_bytes(git(root, "cat-file", "commit", parent, binary=True))
    (source / "final-head.sha").write_text(head + "\n", encoding="ascii")
    (source / "final-parent.sha").write_text(parent + "\n", encoding="ascii")
    (source / "parent-to-head.patch").write_bytes(git(root, "diff", "--binary", f"{parent}..{head}", binary=True))
    (source / "changed-files.txt").write_bytes(git(root, "diff", "--name-status", f"{parent}..{head}", binary=True))
    manifest = []
    for relative in CRITICAL_FILES:
        raw = git(root, "cat-file", "blob", f"{head}:{relative}", binary=True)
        digest = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
        (source / "blobs" / f"{digest}.blob").write_bytes(raw)
        manifest.append({"path": relative, "archive_path": f"{digest}.blob", "blob_sha": digest, "bytes": len(raw)})
    write_json(source / "blob-manifest.json", manifest)
    result = json.loads((evidence / "R21-RESULT.json").read_text(encoding="utf-8"))
    runtime = result.get("runtime") or {}
    (stage / "EXTERNAL_REVIEW.md").write_text(
        f"""# Hermes R21 external review

R21 result: **{result['result']}**.

The real {runtime.get('provider')} / {runtime.get('model')} Hermes model
requested `request_replan` against a disposable ACTIVE Journey. The Harness
discarded the first recorded delivery and replayed the exact request through a
fresh MCP stdio client using the same request id, arguments, agent identity and
database. Every trial must prove semantic response equality and zero new
proposal, plan, event or idempotency identity.

Runtime: PLAN_ONLY; P7=false; CityNexus/MCP loopback; the provider warning is a
SYNTHETIC_HARNESS_FIXTURE, not LIVE/provider evidence. `accept_replan`, booking,
payment, commitment and approval actions are forbidden.

- source: `{head}`
- direct parent: `{parent}`
- audit coordinate: `LOCAL-ONLY / NO RESOLVABLE AUDIT COORDINATE`
""",
        encoding="utf-8",
    )
    write_json(stage / "REVIEW_MANIFEST.json", {
        "package": output_zip.name,
        "scenario_id": result["scenario_id"],
        "result": result["result"],
        "source_head": head,
        "source_parent": parent,
        "p7": False,
        "autonomy": "PLAN_ONLY",
        "excluded": ["SQLite DB", "WAL/SHM", ".env", "credentials", "private keys", "pycache", ".pyc"],
    })
    if output_zip.exists():
        output_zip.unlink()
    with zipfile.ZipFile(output_zip, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(item for item in stage.rglob("*") if item.is_file()):
            archive.write(path, path.relative_to(stage).as_posix())
    return {"zip": str(output_zip), "source_head": head, "source_parent": parent}


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--focused-tests", type=Path, required=True)
    parser.add_argument("--additional-tests", type=Path, action="append", default=[])
    parser.add_argument("--output-zip", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.root, args.evidence, args.focused_tests, args.output_zip, args.additional_tests), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
