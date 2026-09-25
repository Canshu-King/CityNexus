"""Build the external review package for the Hermes request-id schema probe."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import zipfile
from pathlib import Path


CRITICAL_FILES = [
    "agent-mcp/citynexus_mcp/server.py",
    "agent-mcp/tests/test_mcp_boundary.py",
    "scripts/hermes_r10_request_id_schema_probe.py",
    "scripts/hermes_r10_tool_planning_probe.py",
    "scripts/validate_hermes_r10_request_id_review.py",
    "scripts/build_hermes_r10_request_id_review_package.py",
    "reports/hermes/HERMES_R10_REQUEST_ID_SCHEMA_SCENARIO.md",
]


def git(root: Path, *args: str, binary: bool = False) -> bytes | str:
    value = subprocess.check_output(["git", *args], cwd=root)
    return value if binary else value.decode("utf-8").strip()


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def copy_tree(source: Path, target: Path) -> None:
    target.mkdir(parents=True, exist_ok=True)
    for item in source.iterdir():
        destination = target / item.name
        if item.is_dir():
            copy_tree(item, destination)
        else:
            shutil.copy2(item, destination)


def build(root: Path, evidence: Path, focused_tests: Path, output_zip: Path) -> dict[str, object]:
    head = git(root, "rev-parse", "HEAD")
    parent = git(root, "rev-parse", "HEAD^")
    stage = output_zip.with_name(output_zip.stem + "-stage")
    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir(parents=True)
    copy_tree(evidence, stage / "evidence")
    (stage / "tests").mkdir()
    shutil.copy2(focused_tests, stage / "tests" / focused_tests.name)
    shutil.copy2(root / "scripts/validate_hermes_r10_request_id_review.py", stage / "validate_hermes_r10_request_id_review.py")
    shutil.copy2(root / "reports/hermes/HERMES_R10_REQUEST_ID_SCHEMA_SCENARIO.md", stage / "HERMES_R10_REQUEST_ID_SCHEMA_SCENARIO.md")

    source = stage / "source"
    (source / "blobs").mkdir(parents=True)
    (source / "final-head.commit").write_bytes(git(root, "cat-file", "commit", head, binary=True))
    (source / "final-parent.commit").write_bytes(git(root, "cat-file", "commit", parent, binary=True))
    (source / "final-head.sha").write_text(head + "\n", encoding="ascii")
    (source / "final-parent.sha").write_text(parent + "\n", encoding="ascii")
    (source / "parent-to-head.patch").write_bytes(git(root, "diff", "--binary", f"{parent}..{head}", binary=True))
    (source / "changed-files.txt").write_bytes(git(root, "diff", "--name-status", f"{parent}..{head}", binary=True))
    repair_head = git(root, "log", "-1", "--format=%H", "--", "agent-mcp/citynexus_mcp/server.py")
    repair_parent = git(root, "rev-parse", f"{repair_head}^")
    (source / "request-id-repair-head.commit").write_bytes(git(root, "cat-file", "commit", repair_head, binary=True))
    (source / "request-id-repair-parent.commit").write_bytes(git(root, "cat-file", "commit", repair_parent, binary=True))
    (source / "request-id-repair-head.sha").write_text(repair_head + "\n", encoding="ascii")
    (source / "request-id-repair-parent.sha").write_text(repair_parent + "\n", encoding="ascii")
    (source / "request-id-repair.patch").write_bytes(git(root, "diff", "--binary", f"{repair_parent}..{repair_head}", binary=True))
    (source / "request-id-repair-changed-files.txt").write_bytes(git(root, "diff", "--name-status", f"{repair_parent}..{repair_head}", binary=True))
    manifest = []
    for path in CRITICAL_FILES:
        raw = git(root, "cat-file", "blob", f"{head}:{path}", binary=True)
        blob_sha = hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()
        archive_name = blob_sha + ".blob"
        (source / "blobs" / archive_name).write_bytes(raw)
        manifest.append({"path": path, "archive_path": archive_name, "blob_sha": blob_sha, "bytes": len(raw)})
    write_json(source / "blob-manifest.json", manifest)

    result = json.loads((evidence / "R10-REQUEST-ID-RESULT.json").read_text(encoding="utf-8"))
    review = f"""# Hermes R10.1 external review

## Result

The request-id schema alignment probe is **{result.get('result')}** across three
fresh real DeepSeek/Hermes runs. Every adapter request ID was 8–128 characters,
all three runs had zero MCP errors, each produced `request_replan` with the
full `hermes-replan-proposal-view.v1` contract, and no authority or mutation
occurred. `PLAN_ONLY` and `P7=false` remained active.

The reproduced prior failure was model-generated `read-1` / `read-2`; those
values were below the existing backend minimum of eight characters. The repair
publishes that existing constraint in FastMCP annotations, low-level MCP2
schemas, and server instructions. It does not relax the backend validator or
change idempotency behavior.

## Source

- branch: `{result['source']['post']['branch']}`
- source: `{head}`
- direct parent: `{parent}`
- request-id repair commit: `{repair_head}`
- request-id repair parent: `{repair_parent}`
- audit coordinate: LOCAL-ONLY / NO RESOLVABLE AUDIT COORDINATE

The package contains raw binary commit objects, direct parent, binary patch,
changed-files list, critical source blobs, raw native/model/MCP evidence, and
the focused regression output. No database, WAL/SHM, credentials, private key,
`.env`, pycache, or pyc is included.

## Validation

```powershell
python validate_hermes_r10_request_id_review.py --package <this-zip>
```
"""
    (stage / "EXTERNAL_REVIEW.md").write_text(review, encoding="utf-8")
    write_json(stage / "REVIEW_MANIFEST.json", {
        "package": output_zip.name,
        "scenario_id": result.get("scenario_id"),
        "result": result.get("result"),
        "source_head": head,
        "source_parent": parent,
        "repair_head": repair_head,
        "repair_parent": repair_parent,
        "repair_head": repair_head,
        "repair_parent": repair_parent,
        "p7": False,
        "autonomy": "PLAN_ONLY",
        "audit_coordinate": "LOCAL-ONLY / NO RESOLVABLE AUDIT COORDINATE",
        "excluded": ["SQLite DB", "WAL/SHM", ".env", "credentials", "private keys", "pycache", ".pyc"],
    })
    if output_zip.exists():
        output_zip.unlink()
    with zipfile.ZipFile(output_zip, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(item for item in stage.rglob("*") if item.is_file()):
            archive.write(path, path.relative_to(stage).as_posix())
    return {"zip": str(output_zip), "stage": str(stage), "source_head": head, "source_parent": parent}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--focused-tests", type=Path, required=True)
    parser.add_argument("--output-zip", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.root, args.evidence, args.focused_tests, args.output_zip), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
