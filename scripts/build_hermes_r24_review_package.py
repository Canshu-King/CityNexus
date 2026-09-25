"""Build the Hermes R24 concurrent-idempotency external-review package."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import zipfile
from pathlib import Path


CRITICAL_FILES = [
    "scripts/hermes_r24_concurrent_request_replan_probe.py",
    "backend/tests/test_v18_hermes_r24_concurrent_request_replan_probe.py",
    "backend/app/agent/gateway.py",
    "backend/app/main.py",
    "scripts/hermes_r4_contract_probe.py",
    "scripts/validate_hermes_r24_review.py",
    "scripts/build_hermes_r24_review_package.py",
    "reports/hermes/HERMES_R24_SCENARIO.md",
]


def git(root: Path, *args: str, binary: bool = False) -> bytes | str:
    data = subprocess.check_output(["git", *args], cwd=root)
    return data if binary else data.decode("utf-8").strip()


def write_json(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def build(
    root: Path,
    evidence: Path,
    focused_tests: Path,
    output_zip: Path,
) -> dict[str, str]:
    head = git(root, "rev-parse", "HEAD")
    parent = git(root, "rev-parse", "HEAD^")
    stage = output_zip.with_name(output_zip.stem + "-stage")
    if stage.exists():
        shutil.rmtree(stage)
    (stage / "evidence").mkdir(parents=True)
    for item in evidence.iterdir():
        lowered = item.name.casefold()
        if item.is_file() and not any(
            fragment in lowered
            for fragment in (
                ".sqlite",
                ".sqlite3",
                ".db-wal",
                ".db-shm",
                ".wal",
                ".shm",
            )
        ):
            shutil.copy2(item, stage / "evidence" / item.name)
    (stage / "tests").mkdir()
    shutil.copy2(focused_tests, stage / "tests" / focused_tests.name)
    shutil.copy2(
        root / "scripts/validate_hermes_r24_review.py",
        stage / "validate_hermes_r24_review.py",
    )
    shutil.copy2(
        root / "reports/hermes/HERMES_R24_SCENARIO.md",
        stage / "HERMES_R24_SCENARIO.md",
    )
    source = stage / "source"
    (source / "blobs").mkdir(parents=True)
    (source / "final-head.commit").write_bytes(
        git(root, "cat-file", "commit", head, binary=True)
    )
    (source / "final-parent.commit").write_bytes(
        git(root, "cat-file", "commit", parent, binary=True)
    )
    (source / "final-head.sha").write_text(head + "\n", encoding="ascii")
    (source / "final-parent.sha").write_text(parent + "\n", encoding="ascii")
    (source / "parent-to-head.patch").write_bytes(
        git(root, "diff", "--binary", f"{parent}..{head}", binary=True)
    )
    (source / "changed-files.txt").write_bytes(
        git(root, "diff", "--name-status", f"{parent}..{head}", binary=True)
    )
    manifest = []
    for relative in CRITICAL_FILES:
        raw = git(root, "cat-file", "blob", f"{head}:{relative}", binary=True)
        digest = hashlib.sha1(
            b"blob " + str(len(raw)).encode() + b"\0" + raw
        ).hexdigest()
        (source / "blobs" / f"{digest}.blob").write_bytes(raw)
        manifest.append(
            {
                "path": relative,
                "archive_path": f"{digest}.blob",
                "blob_sha": digest,
                "bytes": len(raw),
            }
        )
    write_json(source / "blob-manifest.json", manifest)
    result = json.loads((evidence / "R24-RESULT.json").read_text(encoding="utf-8"))
    runtime = result.get("runtime") or {}
    (stage / "EXTERNAL_REVIEW.md").write_text(
        f"""# Hermes R24 external review

R24 result: {result['result']}.

Two independent MCP client processes issued one identical request_replan
request concurrently against one disposable database. The package records both
responses, the exact identity sets before and after, and whether the two calls
shared one idempotent proposal-generation result.

Runtime: PLAN_ONLY; P7=false; loopback CityNexus/MCP. The provider and event
state is synthetic harness evidence, not LIVE evidence.

- source: {head}
- direct parent: {parent}
- provider/model profile: {runtime.get('provider')} / {runtime.get('model')}
- audit coordinate: LOCAL-ONLY / NO RESOLVABLE AUDIT COORDINATE
""",
        encoding="utf-8",
    )
    write_json(
        stage / "REVIEW_MANIFEST.json",
        {
            "package": output_zip.name,
            "scenario_id": result["scenario_id"],
            "result": result["result"],
            "source_head": head,
            "source_parent": parent,
            "p7": False,
            "autonomy": "PLAN_ONLY",
            "excluded": [
                "SQLite DB",
                "WAL/SHM",
                ".env",
                "credentials",
                "private keys",
                "pycache",
                ".pyc",
            ],
        },
    )
    if output_zip.exists():
        output_zip.unlink()
    with zipfile.ZipFile(
        output_zip, "w", zipfile.ZIP_DEFLATED, compresslevel=9
    ) as archive:
        for path in sorted(item for item in stage.rglob("*") if item.is_file()):
            archive.write(path, path.relative_to(stage).as_posix())
    return {"zip": str(output_zip), "source_head": head, "source_parent": parent}


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--focused-tests", type=Path, required=True)
    parser.add_argument("--output-zip", type=Path, required=True)
    args = parser.parse_args()
    print(
        json.dumps(
            build(args.root, args.evidence, args.focused_tests, args.output_zip),
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
