#!/usr/bin/env python3
"""Inventory existing code WITHOUT importing the app or issuing any network request.

Usage: python tools/reform/inventory_capabilities.py --checkout revolution=/path/a
       --checkout mainline=/path/b --out /tmp/citynexus-capabilities.json

This is a migration backlog, never a certificate of availability or live success.
Registering a tool is deliberately different from advertising it to the model.
"""
from __future__ import annotations
import argparse
import ast
import json
from pathlib import Path
import subprocess

HTTP_METHODS = frozenset({"get", "post", "put", "patch", "delete", "head", "options"})
DOMAINS = {
    "agent": ("backend/app/agent", "frontend/src/features/agent"),
    "planning": ("backend/app/planning", "frontend/src/features/planning"),
    "places_and_map": ("frontend/src/features/discovery", "backend/app/execution/bootstrap_discovery.py"),
    "execution_and_rerouting": ("backend/app/execution", "frontend/src/features/execution"),
    "group_decisions": ("backend/app/collective_mediation.py", "backend/app/shared_stop_coplanning.py"),
    "weather_and_reality": ("backend/app/live_context_watch.py", "backend/app/intelligence"),
    "replanning_and_recovery": ("backend/app/replanning", "backend/app/recovery_epoch.py"),
    "transport": ("backend/app/route_session_operations.py", "frontend/src/features/mobility"),
    "traveler_preferences": ("backend/app/execution/traveler_twin.py", "frontend/src/features/traveler-twin"),
    "stay": ("backend/app/stay_generation_operations.py", "frontend/src/features/stay"),
    "booking_payment_commitments": ("backend/app/commerce",),
    "notification_inbox": ("backend/app/journey_inbox.py", "frontend/src/features/notifications"),
    "identity_and_resume": ("backend/app/traveler_principal.py", "frontend/src/lib/travelerSession.ts"),
    "history_and_trash": ("frontend/src/features/trash", "frontend/src/features/trip"),
}


def literal(node):
    try: return ast.literal_eval(node)
    except (ValueError, TypeError, SyntaxError): return None


def inspect_python(path: Path, root: Path) -> dict:
    result = {"routes": [], "registered_tools": [], "model_tools": [], "parse_errors": []}
    rel = path.relative_to(root).as_posix()
    try: tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=rel)
    except (OSError, SyntaxError, UnicodeError) as error:
        result["parse_errors"].append({"file": rel, "error_type": type(error).__name__})
        return result
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for deco in node.decorator_list:
                if not isinstance(deco, ast.Call) or not isinstance(deco.func, ast.Attribute) or not deco.args: continue
                method, url = deco.func.attr, literal(deco.args[0])
                if not isinstance(url, str): continue
                methods = [method.upper()] if method in HTTP_METHODS else []
                if method == "api_route":
                    for kw in deco.keywords:
                        if kw.arg == "methods":
                            value = literal(kw.value)
                            if isinstance(value, (list, tuple)): methods = [m.upper() for m in value if isinstance(m, str)]
                for verb in methods:
                    result["routes"].append({"method": verb, "declared_path": url, "handler": node.name,
                        "file": rel, "line": node.lineno, "status": "DECLARED_NOT_RUNTIME_VERIFIED"})
        if isinstance(node, ast.Call):
            name = node.func.id if isinstance(node.func, ast.Name) else ""
            if name == "ToolDescriptor" and len(node.args) >= 2:
                tool = literal(node.args[1])
                if isinstance(tool, str):
                    result["registered_tools"].append({"name": tool, "file": rel, "line": node.lineno,
                        "mutates_domain_truth": literal(node.args[2]) if len(node.args) > 2 else None,
                        "changes_money": literal(node.args[3]) if len(node.args) > 3 else None})
            elif name == "_tool" and node.args:
                tool = literal(node.args[0])
                if isinstance(tool, str): result["model_tools"].append({"name": tool, "file": rel, "line": node.lineno})
    return result


def collect(root: Path) -> dict:
    result = {"routes": [], "registered_tools": [], "model_tools": [], "parse_errors": []}
    for folder in (root / "backend/app", root / "trial"):
        if not folder.exists(): continue
        for path in sorted(folder.rglob("*.py")):
            if any(part in {".runtime", ".venv", "node_modules", "__pycache__"} for part in path.parts): continue
            if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()): continue
            for key, values in inspect_python(path, root).items(): result[key].extend(values)
    names = {item["name"] for item in result["model_tools"]}
    registered = {item["name"] for item in result["registered_tools"]}
    result["registered_but_not_advertised"] = sorted(registered - names)
    result["advertised_without_catalog_entry"] = sorted(names - registered)
    result["domains"] = {key: {"source_paths_present": [p for p in paths if (root / p).exists()],
        "expected_paths_missing": [p for p in paths if not (root / p).exists()],
        "live_validation": "NOT_PERFORMED", "agent_adapter_validation": "REQUIRED"}
        for key, paths in DOMAINS.items()}
    try:
        proc = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True, text=True, timeout=5)
        result["commit"] = proc.stdout.strip() if proc.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired): result["commit"] = None
    result["route_prefix_note"] = "Paths are source declarations. Reconcile include_router prefixes with live OpenAPI before binding adapters."
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkout", action="append", required=True, help="label=checkout directory")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    checkouts = {}
    for item in args.checkout:
        label, sep, directory = item.partition("=")
        if not sep or not label or label in checkouts: parser.error("Each checkout requires a unique label=directory")
        root = Path(directory).resolve()
        if not root.is_dir(): parser.error("Checkout directory does not exist")
        checkouts[label] = collect(root)
    report = {"schema_version": 1, "scope": "STATIC_MIGRATION_INVENTORY", "runtime_verified": False, "checkouts": checkouts}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(checkouts)} checkout inventories to {args.out}")

if __name__ == "__main__": main()
