from __future__ import annotations

import argparse
import json
import os
import secrets
from pathlib import Path

from .service import DeveloperCompanion
from .__main__ import execution_arguments, container_configuration


def main() -> int:
    parser = argparse.ArgumentParser(description="Create and run one isolated DSH source-fix task")
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--state-dir", type=Path, required=True)
    parser.add_argument("--provider", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--repro-file", type=Path)
    parser.add_argument("--timeout", type=float, default=1200)
    execution_arguments(parser)
    args = parser.parse_args()
    args.state_dir.mkdir(parents=True, mode=0o700, exist_ok=True)
    owner_path = args.state_dir / ".owner-session"
    if not owner_path.exists():
        descriptor = os.open(owner_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(secrets.token_urlsafe(32))
    owner = owner_path.read_text(encoding="utf-8").strip()
    repro = args.repro_file.read_text(encoding="utf-8") if args.repro_file else "After accepting a replan, the same Journey's Guardian card still reports that issue unresolved. First reproduce on the current source base, then fix only the confirmed product defect."
    companion = DeveloperCompanion(source_checkout=args.source, state_dir=args.state_dir)
    task = companion.create_task(repro, args.source, owner)
    print(json.dumps({"created": task}, ensure_ascii=False), flush=True)
    result = companion.run_task(task["task_id"], owner, provider=args.provider, model=args.model, timeout_seconds=args.timeout,
                                execution_mode=args.execution_mode, container_config=container_configuration(args))
    print(json.dumps({"result": result, "artifacts": companion.get_preview_or_test_artifacts(task["task_id"], owner)}, ensure_ascii=False, indent=2))
    return 0 if result["status"] in {"COMPLETED_UNVERIFIED", "NO_CHANGE"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
