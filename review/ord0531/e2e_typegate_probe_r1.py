"""ORD-0531 follow-on: how much of the e2e corpus would a type gate actually see, and does it see itself?

Why this exists: lane 82f55d8a's ORD-0535 gate fix and this lane's V10 arm are both judged by files that
no typecheck gate includes -- `frontend/tsconfig.typecheck.json` includes only `src/**/*.ts(x)` and
`frontend/tsconfig.check.json` names five src files. So an arm with a type-level mistake (a property read
on the wrong handle, a module path that resolves to nothing) runs green and says nothing.

This script does not change any gate. It builds a throwaway config that adds `e2e/**/*.ts` to the same
options, runs the compiler once, counts what comes back per file and per error code, writes the census
next to itself, and removes the throwaway config. Run it from anywhere:

    python review/ord0531/e2e_typegate_probe_r1.py

Exit code is the census count divided by nothing -- it always reports; the verdict is in the numbers.
"""
from __future__ import annotations

import collections
import json
import re
import subprocess
from pathlib import Path

FRONT = Path(__file__).resolve().parents[2] / "frontend"
HERE = Path(__file__).resolve().parent
PROBE = FRONT / "tsconfig.e2e_probe.tmp.json"
OPTIONS = {
    "target": "ES2022",
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "jsx": "react-jsx",
    "module": "ESNext",
    "moduleResolution": "bundler",
    "skipLibCheck": True,
    "noEmit": True,
    "strict": False,
    "allowJs": True,
    "resolveJsonModule": True,
    "esModuleInterop": True,
    "types": ["vite/client", "node"],
}
LINE = re.compile(r"^(?P<file>[^(]+)\((?P<line>\d+),(?P<col>\d+)\): error (?P<code>TS\d+): (?P<msg>.*)$")


def gate_includes(name: str) -> dict:
    """What the shipped gate actually covers, read from the file rather than recited."""
    raw = (FRONT / name).read_text(encoding="utf-8", errors="replace")
    body = re.sub(r"^//.*$", "", raw, flags=re.M)
    try:
        return json.loads(body).get("include", [])
    except json.JSONDecodeError:
        return {"UNPARSED": raw[:80]}


def main() -> int:
    specs = sorted(p.name for p in (FRONT / "e2e").glob("*.spec.ts"))
    PROBE.write_text(
        json.dumps(
            {"compilerOptions": OPTIONS, "include": ["src/**/*.ts", "src/**/*.tsx", "e2e/**/*.ts"]},
            indent=1,
        ),
        encoding="utf-8",
    )
    try:
        proc = subprocess.run(
            ["npx", "tsc", "-p", PROBE.name, "--noEmit"],
            cwd=str(FRONT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            shell=(FRONT.drive != ""),
        )
    finally:
        PROBE.unlink(missing_ok=True)
    (HERE / "e2e_typegate_errors_r1.txt").write_text(proc.stdout, encoding="utf-8")

    per_file = collections.Counter()
    per_code = collections.Counter()
    hits = []
    for line in proc.stdout.splitlines():
        if "error TS" not in line:
            continue
        name = line.split("(", 1)[0]
        code = re.search(r"error (TS\d+)", line)
        per_file[name] += 1
        per_code[code.group(1) if code else "?"] += 1
        hits.append(line)

    census = {
        "instrument": "review/ord0531/e2e_typegate_probe_r1.py",
        "shipped_gate_includes": {
            "tsconfig.typecheck.json": gate_includes("tsconfig.typecheck.json"),
            "tsconfig.check.json": gate_includes("tsconfig.check.json"),
        },
        "probe_includes": ["src/**/*.ts", "src/**/*.tsx", "e2e/**/*.ts"],
        "spec_files_in_e2e": len(specs),
        "tsc_exit": proc.returncode,
        "total_errors_if_e2e_were_gated": len(hits),
        "files_with_errors": len(per_file),
        "by_error_code": per_code.most_common(),
        "by_file": per_file.most_common(),
        "lane_6a150e1e_specs": {
            name: per_file.get(f"e2e/{name}", 0)
            for name in specs
            if "ord0531" in name or "ord0466" in name
        },
    }
    (HERE / "e2e_typegate_census_r1.json").write_text(
        json.dumps(census, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    print(json.dumps({k: v for k, v in census.items() if k != "by_file"}, ensure_ascii=False, indent=1))
    print("TOP FILES:", per_file.most_common(6))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
