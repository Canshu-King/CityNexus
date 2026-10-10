from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
EXPECTED_BRANCH = "gpt/revolution-r30-consent-epoch-shock-recovery"
CHECKPOINT = Path(
    "output/revolution-r30-live-20261006/R30_LIVE_CHECKPOINT.json"
)
VERDICT = Path(
    "output/revolution-r30-live-20261006/R30_MACHINE_VERDICT.json"
)
RESULT = Path("REVOLUTION_R30_CONSENT_EPOCH_SHOCK_RECOVERY_RESULT.md")
ARTIFACTS = (CHECKPOINT, VERDICT, RESULT)


def _git(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if check and completed.returncode != 0:
        raise RuntimeError(
            "git "
            + " ".join(args)
            + " failed: "
            + (completed.stderr.strip() or completed.stdout.strip())
        )
    return completed


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with (ROOT / path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_receipt(*, require_remote_match: bool) -> dict[str, Any]:
    errors: list[str] = []

    branch = _git("branch", "--show-current").stdout.strip()
    if branch != EXPECTED_BRANCH:
        errors.append(
            f"wrong branch: expected {EXPECTED_BRANCH!r}, got {branch!r}"
        )

    local_head = _git("rev-parse", "HEAD").stdout.strip()
    status = _git("status", "--porcelain").stdout.strip()
    if status:
        errors.append("working tree is not clean after delivery commit")

    artifact_facts: dict[str, Any] = {}
    for relative in ARTIFACTS:
        absolute = ROOT / relative
        if not absolute.is_file():
            errors.append(f"missing delivery artifact: {relative.as_posix()}")
            continue

        tracked = (
            _git(
                "ls-files",
                "--error-unmatch",
                "--",
                relative.as_posix(),
                check=False,
            ).returncode
            == 0
        )
        if not tracked:
            errors.append(
                f"delivery artifact is not tracked by git: {relative.as_posix()}"
            )
        artifact_facts[relative.as_posix()] = {
            "sha256": _sha256(relative),
            "tracked": tracked,
            "bytes": absolute.stat().st_size,
        }

    verdict: dict[str, Any] = {}
    checkpoint: dict[str, Any] = {}
    if (ROOT / VERDICT).is_file():
        try:
            verdict = _read_json(VERDICT)
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"machine verdict is unreadable: {exc}")
    if (ROOT / CHECKPOINT).is_file():
        try:
            checkpoint = _read_json(CHECKPOINT)
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"checkpoint is unreadable: {exc}")

    verdict_overall = str((verdict.get("summary") or {}).get("overall") or "")
    if verdict_overall != "PROVEN":
        errors.append(
            f"R30 machine verdict is not PROVEN: {verdict_overall or 'MISSING'}"
        )

    checkpoint_status = str(checkpoint.get("status") or "")
    checkpoint_overall = str(
        ((checkpoint.get("machine_verdict") or {}).get("summary") or {}).get(
            "overall"
        )
        or ""
    )
    if checkpoint_status != "R30_PROVEN":
        errors.append(
            f"checkpoint status is not R30_PROVEN: "
            f"{checkpoint_status or 'MISSING'}"
        )
    if checkpoint_overall != "PROVEN":
        errors.append(
            "checkpoint does not embed a PROVEN machine-verdict summary"
        )

    remote_head = ""
    remote = _git(
        "ls-remote",
        "--heads",
        "origin",
        f"refs/heads/{EXPECTED_BRANCH}",
        check=False,
    )
    if remote.returncode != 0:
        if require_remote_match:
            errors.append(
                "cannot read origin R30 branch: "
                + (remote.stderr.strip() or remote.stdout.strip())
            )
    else:
        first = next(
            (line for line in remote.stdout.splitlines() if line.strip()),
            "",
        )
        remote_head = first.split()[0] if first else ""
        if require_remote_match and not remote_head:
            errors.append("origin R30 branch does not exist")
        if (
            require_remote_match
            and remote_head
            and remote_head != local_head
        ):
            errors.append(
                "push is not complete: local HEAD "
                f"{local_head} != origin R30 HEAD {remote_head}"
            )

    receipt = {
        "schema_version": "R30_DELIVERY_RECEIPT_V1",
        "ok": not errors,
        "branch": branch,
        "expected_branch": EXPECTED_BRANCH,
        "local_head": local_head,
        "remote_head": remote_head or None,
        "remote_match_required": require_remote_match,
        "remote_matches_local": bool(
            remote_head and remote_head == local_head
        ),
        "working_tree_clean": not bool(status),
        "machine_verdict_overall": verdict_overall or None,
        "checkpoint_status": checkpoint_status or None,
        "checkpoint_machine_verdict_overall": checkpoint_overall or None,
        "artifacts": artifact_facts,
        "errors": errors,
    }
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Verify that a PROVEN R30 delivery is committed, clean, and "
            "actually present on the canonical remote branch."
        )
    )
    parser.add_argument(
        "--local-only",
        action="store_true",
        help="skip the local HEAD == origin branch requirement",
    )
    args = parser.parse_args()

    receipt = build_receipt(
        require_remote_match=not args.local_only,
    )
    print(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if receipt["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
