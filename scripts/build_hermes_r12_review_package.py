"""Build the external review package for the Hermes R12 delay matrix."""

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
    "scripts/hermes_r11_reliability_probe.py",
    "scripts/hermes_r12_delay_reliability_probe.py",
    "backend/tests/test_v18_hermes_r12_delay_reliability_probe.py",
    "scripts/validate_hermes_r12_review.py",
    "scripts/build_hermes_r12_review_package.py",
    "reports/hermes/HERMES_R12_SCENARIO.md",
]


def git(root: Path, *args: str, binary: bool = False) -> bytes | str:
    value = subprocess.check_output(["git", *args], cwd=root)
    return value if binary else value.decode("utf-8").strip()


def copy_tree(source: Path, target: Path) -> None:
    target.mkdir(parents=True, exist_ok=True)
    for item in source.iterdir():
        destination = target / item.name
        if item.is_dir():
            copy_tree(item, destination)
        else:
            shutil.copy2(item, destination)


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")


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
    shutil.copy2(root / "scripts/validate_hermes_r12_review.py", stage / "validate_hermes_r12_review.py")
    shutil.copy2(root / "reports/hermes/HERMES_R12_SCENARIO.md", stage / "HERMES_R12_SCENARIO.md")

    source = stage / "source"
    (source / "blobs").mkdir(parents=True)
    (source / "final-head.commit").write_bytes(git(root, "cat-file", "commit", head, binary=True))
    (source / "final-parent.commit").write_bytes(git(root, "cat-file", "commit", parent, binary=True))
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

    result = json.loads((evidence / "R12-RESULT.json").read_text(encoding="utf-8"))
    (stage / "EXTERNAL_REVIEW.md").write_text(
        f"""# Hermes R12 external review

R12 is **{result.get('result')}** across four real DeepSeek/Hermes runs: two
traffic-delay proposal trials and two traffic-delay read-only trials. The
independent validator derives proposal identity, event type, mutation absence,
and before/after authority from raw evidence.

The delay and mobility inputs are `SYNTHETIC_HARNESS_FIXTURE`, not LIVE provider
evidence. Runtime remains `PLAN_ONLY`, `P7=false`, with no acceptance, booking,
payment, or commitment mutation.

- branch: `{result['source']['post']['branch']}`
- source: `{head}`
- direct parent: `{parent}`
- audit coordinate: `LOCAL-ONLY / NO RESOLVABLE AUDIT COORDINATE`

Validate with:

```powershell
python validate_hermes_r12_review.py --package <this-zip>
```
""",
        encoding="utf-8",
    )
    write_json(stage / "REVIEW_MANIFEST.json", {
        "package": output_zip.name,
        "scenario_id": result.get("scenario_id"),
        "result": result.get("result"),
        "source_head": head,
        "source_parent": parent,
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
