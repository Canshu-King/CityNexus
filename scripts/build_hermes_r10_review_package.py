"""Build the external Hermes R10 review package without copying the worktree."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import zipfile
from pathlib import Path


CRITICAL_FILES = [
    "scripts/hermes_r9_mcp_context_probe.py",
    "scripts/hermes_r10_tool_planning_probe.py",
    "scripts/recompute_hermes_r10_evidence.py",
    "scripts/validate_hermes_r10_review.py",
    "scripts/build_hermes_r10_review_package.py",
    "backend/tests/test_v18_hermes_r10_tool_planning_probe.py",
    "reports/hermes/HERMES_R10_SCENARIO.md",
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


def build(root: Path, primary: Path, rerun: Path, focused_tests: Path, output_zip: Path) -> dict[str, object]:
    head = git(root, "rev-parse", "HEAD")
    parent = git(root, "rev-parse", "HEAD^")
    stage = output_zip.with_name(output_zip.stem + "-stage")
    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir(parents=True)

    evidence = stage / "evidence"
    copy_tree(primary, evidence)
    copy_tree(rerun, stage / "evidence" / "corrected-rerun-blocked")
    (stage / "tests").mkdir(exist_ok=True)
    shutil.copy2(focused_tests, stage / "tests" / focused_tests.name)
    shutil.copy2(root / "scripts/validate_hermes_r10_review.py", stage / "validate_hermes_r10_review.py")
    shutil.copy2(root / "reports/hermes/HERMES_R10_SCENARIO.md", stage / "HERMES_R10_SCENARIO.md")

    source = stage / "source"
    (source / "blobs").mkdir(parents=True)
    source_head = git(root, "cat-file", "commit", head, binary=True)
    source_parent = git(root, "cat-file", "commit", parent, binary=True)
    (source / "final-head.commit").write_bytes(source_head)
    (source / "final-parent.commit").write_bytes(source_parent)
    (source / "final-head.sha").write_text(head + "\n", encoding="ascii")
    (source / "final-parent.sha").write_text(parent + "\n", encoding="ascii")
    (source / "parent-to-head.patch").write_bytes(git(root, "diff", "--binary", f"{parent}..{head}", binary=True))
    (source / "changed-files.txt").write_bytes(git(root, "diff", "--name-status", f"{parent}..{head}", binary=True))
    manifest = []
    for path in CRITICAL_FILES:
        raw = git(root, "cat-file", "blob", f"{head}:{path}", binary=True)
        blob_sha = hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()
        archive_name = blob_sha + ".blob"
        (source / "blobs" / archive_name).write_bytes(raw)
        manifest.append({"path": path, "archive_path": archive_name, "blob_sha": blob_sha, "bytes": len(raw)})
    write_json(source / "blob-manifest.json", manifest)

    primary_result = json.loads((evidence / "R10-RESULT.json").read_text(encoding="utf-8"))
    rerun_result = json.loads((stage / "evidence/corrected-rerun-blocked/R10-RESULT.json").read_text(encoding="utf-8"))
    external_review = f"""# Hermes R10 external review package

## Result

The primary R10 evidence is **PASS**: three baseline and three guided real
DeepSeek/Hermes trials completed, with PLAN_ONLY and no authority mutation.
The tool-guidance optimization is **REJECTED**. It lowered median provider
tokens and MCP calls, but increased cumulative MCP response bytes and did not
reduce successful-request follow-up `list_replans`; one guided trial recorded
MCP validation errors.

Corrected primary medians:

| arm | total tokens | MCP calls | cumulative response bytes | post-success list reads | redundant post-success reads |
| --- | ---: | ---: | ---: | ---: | ---: |
| baseline | 98499 | 16 | 51133 | 0 | 0 |
| r10-guided | 73574 | 10 | 76071 | 1 | 1 |

The primary raw chronology was remeasured after correcting the proposal identity
reader to include both `proposal_views[*].proposal_id` and `proposals[*].id`.
The full `structuredContent` remained unchanged.

## Source binding

- branch: `{primary_result['source']['post']['branch']}`
- execution source: `{primary_result['source']['head']}`
- final package source: `{head}`
- direct parent: `{parent}`
- P7: false
- autonomy: PLAN_ONLY
- audit coordinate: LOCAL-ONLY / NO RESOLVABLE AUDIT COORDINATE

The package contains byte-faithful raw commit objects, their direct parent,
the parent-to-source binary patch, changed files, and current critical source
blob identities. The primary runtime evidence was collected before the
measurement-only correction; the package records the correction explicitly and
retains the later corrected rerun.

## Corrected rerun

The later corrected rerun is preserved under
`evidence/corrected-rerun-blocked/`. It is not substituted for the primary
checkpoint: its baseline trial 2 did not observe `request_replan`, so the runner
correctly reported `BLOCKED`. This is a real model-run variability observation,
not a reason to relabel the complete primary evidence.

## Validation

```powershell
$env:PYTHONPATH='.'
uv run --project backend python validate_hermes_r10_review.py --package <this-zip>
```

The validator derives identity/repetition metrics from raw chronology, checks
the full proposal contract, verifies structured-content equality, checks the
PLAN_ONLY/no-mutation boundary, and recomputes Git commit/blob identities.
"""
    (stage / "EXTERNAL_REVIEW.md").write_text(external_review, encoding="utf-8")
    write_json(stage / "REVIEW_MANIFEST.json", {
        "package": output_zip.name,
        "scenario_id": primary_result.get("scenario_id"),
        "result": primary_result.get("result"),
        "optimization_decision": primary_result.get("optimization_decision"),
        "source_head": head,
        "source_parent": parent,
        "execution_source": primary_result.get("source", {}).get("head"),
        "corrected_rerun_result": rerun_result.get("result"),
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
    parser.add_argument("--primary-evidence", type=Path, required=True)
    parser.add_argument("--corrected-rerun", type=Path, required=True)
    parser.add_argument("--focused-tests", type=Path, required=True)
    parser.add_argument("--output-zip", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.root, args.primary_evidence, args.corrected_rerun, args.focused_tests, args.output_zip), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
