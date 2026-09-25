from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Any

from hermes_r5_idempotency_probe import ROOT, clean_state


R4_SOURCE = "974938854d7bc40faa01bcd1464b42da98336a3a"
FOCUSED_TESTS = [
    "backend/tests/test_hermes_r5_cached_replan_compatibility.py",
    "agent-mcp/tests/test_client_error_detail.py",
    "agent-mcp/tests/test_mcp_boundary.py",
    "agent-mcp/tests/test_hermes_validation_principal.py",
    "agent-mcp/tests/test_replan_proposal_view.py",
    "backend/tests/test_agent_principal_boundary.py",
]


def git(*args: str, binary: bool = False) -> str | bytes:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=not binary, stderr=subprocess.DEVNULL)


def add(data: dict[str, bytes], name: str, value: bytes | str) -> None:
    data[name] = value.encode("utf-8") if isinstance(value, str) else value


def package(evidence_dir: Path, archive_path: Path) -> dict[str, Any]:
    evidence_dir = evidence_dir.resolve()
    archive_path = archive_path.resolve()
    if archive_path.exists():
        raise FileExistsError(archive_path)
    if archive_path == ROOT or ROOT in archive_path.parents:
        raise ValueError("review package must be outside the Git worktree")
    if evidence_dir == ROOT or ROOT in evidence_dir.parents:
        raise ValueError("runtime evidence must be outside the Git worktree")
    state = clean_state()
    if state["status_porcelain_v1"]:
        raise RuntimeError("refusing package: source worktree is dirty")
    receipt_path = evidence_dir / "hermes-r5-request-replan-original.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if receipt.get("result") != "PASS" or receipt.get("source_binding_after", {}).get("head") != state["head"]:
        raise RuntimeError("runtime receipt does not prove PASS from current HEAD")

    tests = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", *FOCUSED_TESTS],
        cwd=ROOT,
        capture_output=True,
    )
    tests_text = (tests.stdout + tests.stderr).decode("utf-8", errors="replace")
    if tests.returncode:
        raise RuntimeError(f"focused tests failed; package not created:\n{tests_text}")
    if clean_state()["status_porcelain_v1"]:
        raise RuntimeError("focused tests changed source worktree")

    commit = state["head"]
    parent = git("rev-parse", "HEAD^").strip()
    parent_to_source = git("diff", "--binary", parent, commit, binary=True)
    r4_to_source = git("diff", "--binary", R4_SOURCE, commit, binary=True)
    direct_files = git("diff", "--name-only", parent, commit).splitlines()
    cumulative_files = git("diff", "--name-only", R4_SOURCE, commit).splitlines()
    commit_object = git("cat-file", "commit", commit, binary=True)
    parent_object = git("cat-file", "commit", parent, binary=True)

    data: dict[str, bytes] = {}
    data["EXTERNAL_REVIEW.md"] = f"""# External review request — Hermes R5

Result from executable run: **PASS**. Run ID: `{receipt['run_id']}`.

Please independently review the cached `request_replan` compatibility adapter,
the tests, and all three runtime arms. The source is local-only unless this
commit coordinate resolves in the repository: `{commit}` (direct parent
`{parent}`). Do not infer a publication or mainline merge from this package.

Key checks in the receipts: R4 direct-vs-stdio contract; same-key/same-signature
cross-version legacy cache retry; full proposal views with frozen old status;
unchanged exact Journey/PlanVersion/Event/ReplanProposal/IdempotencyKey state;
missing persisted ID fails with `AGENT_IDEMPOTENCY_RESPONSE_SCHEMA_UNAVAILABLE`.

Safety: proposal-only, no `accept_replan`; `P7=false`; H11 is `NOT_RUN`; model
`NOT_USED`; provider evidence is mock/synthetic; no production credentials,
live/preview/user DB, or authority/mainline write.

Run `python validation/validate_hermes_r5_package.py <archive.zip>` first. Use
`validation/reproduce_hermes_r5.ps1` with the source checkout and isolated
Python runtime to reproduce the measurement.
""".encode()
    data["REVIEW_MANIFEST.md"] = f"""# Hermes R5 review manifest

- Source SHA: `{commit}`
- Direct parent SHA: `{parent}`
- R4 source coordinate: `{R4_SOURCE}` (supplied source was local-only)
- Scenario: `hermes-r5-request-replan-idempotency-upgrade`
- Result: `PASS`; run `{receipt['run_id']}`
- Branch: `{state['branch']}`
- Focused tests: `{tests_text.splitlines()[-1] if tests_text.splitlines() else 'PASS'}`
- Evidence database: disposable SQLite only; databases are excluded from this archive
- Provenance: mock mobility / synthetic fixture; model `NOT_USED`; `P7=false`
- No production credentials, live/preview/user DB, H11 model run, or authority/mainline merge

Machine-readable per-file sizes and SHA-256 values are in `REVIEW_MANIFEST.json`.
""".encode()

    source_docs = {
        "HERMES_R5_SCENARIO.md": "reports/hermes/HERMES_R5_SCENARIO.md",
        "reports/HERMES_R5_REPORT.md": "reports/hermes/HERMES_R5_REPORT.md",
    }
    for destination, relative in source_docs.items():
        add(data, destination, git("show", f"{commit}:{relative}", binary=True))

    evidence_names = (
        "hermes-r5-request-replan-original.json",
        "hermes-r5-legacy-cache-retry.json",
        "hermes-r5-missing-proposal.json",
        "r4-regression-receipt.json",
        "os-stdout.txt",
        "os-stderr.txt",
        "exit-code.txt",
        "network-guard.jsonl",
    )
    for name in evidence_names:
        add(data, f"evidence/{name}", (evidence_dir / name).read_bytes())
    add(data, "evidence/focused-tests.txt", tests_text)

    add(data, "source/source.commit-object.txt", commit_object)
    add(data, "source/parent.commit-object.txt", parent_object)
    add(data, "source/parent-to-source.patch", parent_to_source)
    add(data, "source/r4-to-r5.patch", r4_to_source)
    add(data, "source/changed-files.txt", "\n".join(direct_files) + "\n")
    add(data, "source/changed-files-from-r4.txt", "\n".join(cumulative_files) + "\n")
    add(data, "source/blob-bindings.json", json.dumps(receipt["tracked_blob_binding_before"], indent=2, sort_keys=True) + "\n")

    for relative in direct_files:
        try:
            final_bytes = git("show", f"{commit}:{relative}", binary=True)
        except subprocess.CalledProcessError:
            continue
        add(data, f"source/final-tree/{relative}", final_bytes)
        try:
            parent_bytes = git("show", f"{parent}:{relative}", binary=True)
        except subprocess.CalledProcessError:
            continue
        add(data, f"source/parent-tree/{relative}", parent_bytes)

    for relative in cumulative_files:
        try:
            add(data, f"source/files/{relative}", git("show", f"{commit}:{relative}", binary=True))
        except subprocess.CalledProcessError:
            pass
    add(data, "validation/reproduce_hermes_r5.ps1", git("show", f"{commit}:scripts/reproduce_hermes_r5.ps1", binary=True))
    add(data, "validation/validate_hermes_r5_package.py", git("show", f"{commit}:scripts/validate_hermes_r5_package.py", binary=True))

    manifest = {
        "source_commit": commit,
        "direct_parent": parent,
        "branch": state["branch"],
        "run_id": receipt["run_id"],
        "result": receipt["result"],
        "files": {
            name: {"size": len(content), "sha256": hashlib.sha256(content).hexdigest()}
            for name, content in sorted(data.items())
        },
    }
    add(data, "REVIEW_MANIFEST.json", json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, content in sorted(data.items()):
            archive.writestr(name, content)
    return {"archive": str(archive_path), "source_commit": commit, "direct_parent": parent,
            "run_id": receipt["run_id"], "files": len(data), "tests": tests_text.splitlines()[-1]}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(package(args.evidence_dir, args.output), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
