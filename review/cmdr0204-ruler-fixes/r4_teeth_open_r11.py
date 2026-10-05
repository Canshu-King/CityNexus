"""Re-open R4 (CMDR 02:04 ③'s counter-check) with the full output kept.

`cmdr0204_mutants_r1.py` reports R4 as "red" because pytest exited non-zero, but its parser only
records FAILED summary lines.  A non-zero exit with no FAILED line is a *different* shape (collection
error, crash, or a fixture that refused to run), and a crash is not teeth for an assertion.  This
script keeps the whole tail so the verdict can be read instead of inferred.

Read-only apart from the one-line mutation, which is restored from the snapshot before the script
exits; the restore is verified by sha256 and by `git status --porcelain`.
"""

from __future__ import annotations

import hashlib
import pathlib
import subprocess

PY = r"D:/moodle/CityNexus/.venv/Scripts/python.exe"
TREE = pathlib.Path(r"D:/moodle/_qoder_seed_ord0489/wt504")
BACKEND = TREE / "backend"
CITY = BACKEND / "app/integrations/discovery/real_city.py"
MODULE = "tests/test_qoder_city_failure_reasons.py"
NODE = MODULE + "::test_a_live_failure_arrives_named_and_carries_the_stage_it_broke_at"
MAP_ANCHOR = "            return PROVIDER_SERVER_ERROR"
MAP_MUTANT = "            return PROVIDER_BAD_RESPONSE"


def text(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")


def pytest(args: list[str]) -> str:
    proc = subprocess.run([PY, "-m", "pytest", *args], cwd=str(BACKEND),
                          capture_output=True, text=True, encoding="utf-8", errors="replace")
    return f"exit={proc.returncode}\n" + (proc.stdout + proc.stderr)


def main() -> int:
    original = text(CITY)
    digest_before = hashlib.sha256(original.encode("utf-8")).hexdigest()[:16]
    head = subprocess.run(["git", "-C", str(TREE), "rev-parse", "HEAD"],
                          capture_output=True, text=True).stdout.strip()
    print(f"tree HEAD={head}")
    print(f"real_city.py before sha256={digest_before}")

    try:
        assert original.count(MAP_ANCHOR) == 1, "anchor not unique, refusing to mutate"
        CITY.write_text(original.replace(MAP_ANCHOR, MAP_MUTANT), encoding="utf-8", newline="")
        print(f"mutated: {MAP_ANCHOR.strip()} -> {MAP_MUTANT.strip()}")
        print("\n----- R4 mutant, single node, --tb=short -----")
        print(pytest(["-p", "no:cacheprovider", "-q", "--tb=short", "-rf", NODE]))
        print("\n----- R4 mutant, whole module, --tb=line -rf -----")
        print(pytest(["-p", "no:cacheprovider", "-q", "--tb=line", "-rf", MODULE]))
    finally:
        CITY.write_text(original, encoding="utf-8", newline="")
        digest_after = hashlib.sha256(text(CITY).encode("utf-8")).hexdigest()[:16]
        dirty = subprocess.run(["git", "-C", str(TREE), "status", "--porcelain"],
                               capture_output=True, text=True).stdout.strip().splitlines()
        print(f"\nrestored sha256={digest_after} | byte-identical={digest_before == digest_after}"
              f" | tree dirty lines={len(dirty)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
