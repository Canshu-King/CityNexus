from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from hermes_r5_idempotency_probe import ROOT, clean_state


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    output = args.output_dir.resolve()
    if output.exists():
        raise FileExistsError(f"choose a new evidence directory: {output}")
    if output == ROOT or ROOT in output.parents:
        raise ValueError("evidence output must be outside the Git worktree")
    before = clean_state()
    if before["status_porcelain_v1"]:
        raise RuntimeError("refusing capture before product calls: source worktree is dirty")

    completed = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "hermes_r5_idempotency_probe.py"),
         "--output-dir", str(output)],
        cwd=ROOT,
        capture_output=True,
    )
    output.mkdir(parents=True, exist_ok=True)
    stdout_path = output / "os-stdout.txt"
    stderr_path = output / "os-stderr.txt"
    stdout_path.write_bytes(completed.stdout)
    stderr_path.write_bytes(completed.stderr)
    (output / "exit-code.txt").write_text(f"{completed.returncode}\n", encoding="ascii")
    receipt = output / "hermes-r5-request-replan-original.json"
    stdout_matches_receipt = receipt.exists() and receipt.read_bytes() == completed.stdout
    summary = {
        "exit_code": completed.returncode,
        "output_dir": str(output),
        "stdout_equals_machine_receipt": stdout_matches_receipt,
        "stderr_bytes": len(completed.stderr),
    }
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    if not stdout_matches_receipt:
        return 2
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
