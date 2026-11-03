from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from .service import CompanionError, DeveloperCompanion
from .container_runtime import ContainerConfig


def execution_arguments(parser):
    parser.add_argument("--execution-mode", choices=["container", "local"], default="container")
    parser.add_argument("--image", help="Explicitly built local sha256 image ID; never pulled by a task")
    parser.add_argument("--broker-endpoint", help="Trusted host gateway base URL ending in /v1")
    parser.add_argument("--broker-key-file", type=Path, help="Host-only raw key file outside the checkout; never mounted")


def container_configuration(args):
    if args.execution_mode == "local":
        return None
    if not (args.image and args.broker_endpoint and args.broker_key_file):
        return None
    return ContainerConfig(args.image, args.broker_endpoint, args.broker_key_file, args.model)


def main() -> int:
    parser = argparse.ArgumentParser(description="Explicit local CityNexus DSH Developer Companion")
    parser.add_argument("--source", type=Path, required=True, help="Configured source checkout root; it is read only")
    parser.add_argument("--state-dir", type=Path, required=True, help="Private task directory outside the source checkout")
    parser.add_argument("--owner-file", type=Path, help="Local owner-session token file; alternatively set CITYNEXUS_COMPANION_OWNER")
    commands = parser.add_subparsers(dest="action", required=True)
    create = commands.add_parser("create-task")
    create.add_argument("--repro-file", type=Path, required=True)
    create.add_argument("--allow-path", action="append", dest="allowed_paths")
    for name in ("progress", "diff", "stop", "artifacts", "run", "finalize", "verify", "rollback"):
        command = commands.add_parser(name)
        command.add_argument("task_id")
        if name == "run":
            command.add_argument("--provider", required=True)
            command.add_argument("--model", required=True)
            command.add_argument("--timeout", type=float, default=1200)
            execution_arguments(command)
        elif name == "verify":
            command.add_argument("--commands-file", type=Path, required=True, help="Developer-selected JSON array of argv arrays")
            command.add_argument("--timeout", type=float, default=300)
    args = parser.parse_args()
    try:
        owner = args.owner_file.read_text(encoding="utf-8").strip() if args.owner_file else os.environ.get("CITYNEXUS_COMPANION_OWNER", "")
        if len(owner) < 16:
            raise CompanionError("Set a local developer owner-session token (at least 16 characters)")
        companion = DeveloperCompanion(source_checkout=args.source, state_dir=args.state_dir)
        if args.action == "create-task":
            result = companion.create_task(args.repro_file.read_text(encoding="utf-8"), args.source, owner, allowed_paths=args.allowed_paths)
        elif args.action == "run":
            result = companion.run_task(args.task_id, owner, provider=args.provider, model=args.model, timeout_seconds=args.timeout,
                                        execution_mode=args.execution_mode, container_config=container_configuration(args))
        elif args.action == "verify":
            result = companion.verify_task(args.task_id, owner, json.loads(args.commands_file.read_text(encoding="utf-8")), timeout_seconds=args.timeout)
        elif args.action == "rollback":
            result = companion.rollback_task(args.task_id, owner)
        elif args.action == "finalize":
            result = companion.finalize_task(args.task_id, owner)
        elif args.action == "diff":
            sys.stdout.write(companion.get_diff(args.task_id, owner))
            return 0
        elif args.action == "progress":
            result = companion.get_task_progress(args.task_id, owner)
        elif args.action == "stop":
            result = companion.stop_task(args.task_id, owner)
        else:
            result = companion.get_preview_or_test_artifacts(args.task_id, owner)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (CompanionError, OSError, ValueError) as exc:
        print(json.dumps({"error": type(exc).__name__, "message": str(exc)[:240]}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
