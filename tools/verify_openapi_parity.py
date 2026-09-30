from __future__ import annotations

import sys
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))


def runtime_paths() -> set[tuple[str, str]]:
    from app.main import app

    return {
        (route.path, method.upper())
        for route in app.routes
        for method in getattr(route, "methods", set())
        if route.path.startswith("/api/v1/") or route.path == "/api/v1"
    }


def formal_paths() -> set[tuple[str, str]]:
    spec = yaml.safe_load((ROOT / "contracts" / "openapi.yaml").read_text(encoding="utf-8"))
    result: set[tuple[str, str]] = set()
    for path, item in spec.get("paths", {}).items():
        runtime_path = "/api/v1" + (path if path != "/" else "")
        for method in item:
            if method.lower() in {"get", "post", "put", "patch", "delete", "options", "head"}:
                result.add((runtime_path, method.upper()))
    return result


GENERATED_CLIENT = ROOT / "frontend" / "src" / "generated" / "api.ts"


def formal_schemas() -> set[str]:
    """The component names the hand-written contract declares."""

    spec = yaml.safe_load((ROOT / "contracts" / "openapi.yaml").read_text(encoding="utf-8"))
    return set((spec.get("components") or {}).get("schemas") or {})


def generated_schemas(text: str) -> set[str]:
    """The component names the generated client actually carries.

    Scoped to the `components.schemas` region on purpose.  A flat search for `^        Name: {` matches 584
    lines in this file, because `parameters:` and `content:` sit at the same indent inside every operation;
    an unscoped parser would report a clean bill of health for a client that declares nothing.
    """

    lines = text.splitlines()
    try:
        start = next(i for i, ln in enumerate(lines) if ln == "export interface components {")
        start = next(i for i in range(start + 1, len(lines)) if lines[i] == "    schemas: {")
    except StopIteration:
        return set()
    names: set[str] = set()
    for i in range(start + 1, len(lines)):
        ln = lines[i]
        if ln.startswith("    ") and not ln.startswith("        "):
            break  # the next sibling of `schemas:` closes the region
        if ln.startswith("        "):
            key = ln[8:]
            if key and not key.startswith("/") and ":" in key:
                name = key.split(":", 1)[0].strip().strip('"')
                if name and name[0].isupper():
                    names.add(name)
    return names


def schema_drift(formal: set[str], generated: set[str]) -> tuple[list[str], list[str]]:
    """(missing, extra) -- `missing` is the ORD-0467 class: declared in the contract, absent from the client."""

    return sorted(formal - generated), sorted(generated - formal)


def main() -> int:
    formal = formal_paths()
    runtime = runtime_paths()
    missing = sorted(runtime - formal)
    extra = sorted(formal - runtime)
    print(
        f"OpenAPI 3.1.0; formal {len(formal)}; runtime {len(runtime)}; "
        f"missing {len(missing)}; extra {len(extra)}"
    )
    if missing:
        print("MISSING:", missing)
    if extra:
        print("EXTRA:", extra)

    # ORD-0503: the same claim, one level down.  Comparing paths and methods cannot see a component the
    # contract declares and the checked-in client does not contain, and that gap let a schema land on the
    # line with no typed client for it.  Both directions are named, because a component deleted from the
    # contract while the client keeps it is the same class of lie.
    fs = formal_schemas()
    gs = generated_schemas(GENERATED_CLIENT.read_text(encoding="utf-8"))
    s_missing, s_extra = schema_drift(fs, gs)
    print(
        f"schemas formal {len(fs)}; generated {len(gs)}; "
        f"missing {len(s_missing)}; extra {len(s_extra)}"
    )
    if s_missing:
        print("SCHEMAS MISSING FROM GENERATED CLIENT:", s_missing)
    if s_extra:
        print("SCHEMAS NOT IN CONTRACT:", s_extra)
    return 1 if (missing or extra or s_missing or s_extra) else 0


if __name__ == "__main__":
    raise SystemExit(main())

