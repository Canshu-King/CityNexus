"""Teeth for the two anchor-drift ruler fixes (CMDR 07:57 ②).

Green-after-the-fix proves nothing on its own, so each ruler gets a drift probe (must stay green) and
a violation probe (must go red). Files are put back byte-for-byte and re-hashed after every probe.
"""

import hashlib
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(r"D:/moodle/_qoder_seed_ord0489/wt543d")
BACKEND = ROOT / "backend"
PY = r"D:/moodle/CityNexus/.venv/Scripts/python.exe"
MAIN = BACKEND / "app/main.py"
HYDR = BACKEND / "app/catalog_hydration_operations.py"
PANEL = ROOT / "frontend/src/features/shared/SharedJourneyPanel.tsx"
G4 = "tests/test_qoder_ord0296_write_deadline.py::test_G4_the_lock_wait_is_written_in_exactly_one_place"
H1 = "tests/test_qoder_ord0479_dictionary_key_shape.py::test_H01b_the_shipped_tree_clears_and_every_exemption_is_re_derivable"


def sh(args, cwd=BACKEND):
    return subprocess.run(args, cwd=str(cwd), capture_output=True, text=True,
                          encoding="utf-8", errors="replace")


def digest(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def insert_after(path: pathlib.Path, anchor: str, added: str) -> bytes:
    """Put `added` on its own line right after a *whole-line* match, and return the original bytes."""

    raw = path.read_bytes()
    text = raw.decode("utf-8")
    lines = text.split("\n")
    hits = [i for i, l in enumerate(lines) if l == anchor]
    assert len(hits) == 1, (str(path), anchor[:50], hits)
    lines.insert(hits[0] + 1, added)
    path.write_bytes("\n".join(lines).encode("utf-8"))
    return raw


def run(node: str) -> tuple[str, str]:
    proc = sh([PY, "-m", "pytest", "-p", "no:cacheprovider", "-q", "--no-header", "-rf", node])
    red = f"FAILED {node}" in proc.stdout or f"ERROR {node}" in proc.stdout
    summary = [l for l in proc.stdout.splitlines() if " passed" in l or " failed" in l or "error" in l]
    return ("red" if red else "green"), (summary[-1] if summary else proc.stdout[-160:])


def probe(name, node, path, anchor, added, want, why):
    original = insert_after(path, anchor, added)
    state, summary = run(node)
    path.write_bytes(original)
    restored = path.read_bytes() == original
    ok = state == want and restored
    print(f"  {'OK  ' if ok else 'FAIL'} {name}: want {want}, got {state}; restore byte-identical={restored}"
          f"  [{digest(path)}]  ({why})")
    print(f"       {summary}")
    return ok


def main() -> int:
    results = []
    print("== G4 (the request-path lock wait) ==")
    results.append(probe(
        "drift probe: a number-free mention in a file the old roster never listed", G4, MAIN,
        "PLAN_CLAIM_LEASE_MS = int(settings.write_deadline_ms) + int(settings.write_busy_timeout_ms)",
        "# LANE-PROBE: this route asks the module for its lock wait, it writes no number.",
        "green", "the ruler must no longer freeze filenames"))
    results.append(probe(
        "violation probe: a second lock-wait number, at a value no worker scope names", G4, MAIN,
        "PLAN_CLAIM_LEASE_MS = int(settings.write_deadline_ms) + int(settings.write_busy_timeout_ms)",
        "LANE_PROBE_BUSY_TIMEOUT = 7000  # busy_timeout = 7000",
        "red", "a new inline wait must be refused"))
    results.append(probe(
        "violation probe: the original defect shape, an inline copy of the request-path wait", G4, HYDR,
        '    session.execute(text("PRAGMA busy_timeout = 500"))',
        '    session.execute(text("PRAGMA busy_timeout = 30000"))  # LANE-PROBE',
        "red", "the constant抄两份 case the order was opened for"))

    print("\n== H01b (the dictionary-key ruler's own anchor) ==")
    results.append(probe(
        "drift probe: one line inserted above the named table", H1, PANEL,
        " *  same nine names rather than holding a second, drifting copy of this table. */",
        "/// LANE-PROBE: a line above the table, which is what any upstream edit puts there.",
        "green", "the anchor follows the symbol, not a frozen line number"))
    results.append(probe(
        "violation probe: the forgiven table stops being a translation table", H1, PANEL,
        '  token_unknown: "shared.refusedTokenUnknown",',
        '  lane_probe_key: "not-a-key-in-either-locale",',
        "red", "the re-derivation of every exemption must still bite"))

    print("\n== state after every restore ==")
    status = sh(["git", "status", "--porcelain", "--", "backend/app", "frontend/src"])
    clean = status.stdout.strip() == ""
    print(f"  git status for the three probed files: {status.stdout.strip() or '(clean)'}")
    for p in (MAIN, HYDR, PANEL):
        print(f"  {p.relative_to(ROOT).as_posix()}: {digest(p)}")
    n_ok = sum(1 for r in results if r)
    print(f"\n{n_ok}/{len(results)} probes behaved as named")
    return 0 if (n_ok == len(results) and clean) else 8


if __name__ == "__main__":
    raise SystemExit(main())
