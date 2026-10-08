"""Counter-arm for the replan door's zone normalisation.

The gap this pins: inside `generate_replan`, the step that normalises every copied activity instant
onto one offset built the journey zone with `ZoneInfo(journey.timezone or "UTC")` and no fallback --
while the two other normalisation sites in the same file both catch an unusable zone and fall back to
UTC.  So a trip whose zone cannot be used made the whole replan door raise `ZoneInfoNotFoundError`:
a 500 on a trip that can otherwise be replanned, because of one field a traveller did not get to
choose.

The step is inline in `generate_replan`, so this arm does not try to drive the door end-to-end.  It
reads the real source lines at that site from `backend/app/main.py`, executes them in both arms
(a usable zone and an unusable one), and asserts the replan's normalisation step does not raise --
i.e. it produces one offset per instant instead of ending the door.

On the pre-fix bytes the unusable arm raises `ZoneInfoNotFoundError` and the arm exits 1.
"""
from __future__ import annotations

import io
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

os.environ.setdefault("CITYNEXUS_DEMO_MODE", "true")

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
MAIN = os.path.join(REPO, "backend", "app", "main.py")

# The site: the `journey_tz = ...` assignment inside step 1b of `generate_replan`.
ANCHOR = "# 1b. Normalise every timestamp into one offset."


def source_at_site() -> str:
    """The real source lines at the normalisation site, dedented and executable.

    The site is either a bare `journey_tz = ...` or a `try: ... except ...:` around it; both are
    taken verbatim so the arm runs the bytes that are actually there.  The block ends at the first
    line that is neither blank, a comment, nor indented deeper than the block's own start.
    """
    lines = io.open(MAIN, encoding="utf-8", errors="replace").read().splitlines()
    start = next(i for i, line in enumerate(lines) if ANCHOR in line)
    base_indent = len(lines[start]) - len(lines[start].lstrip())

    i = start
    while i < len(lines) and (not lines[i].strip() or lines[i].strip().startswith("#")):
        i += 1
    if i >= len(lines):
        raise AssertionError("the normalisation site was not found in backend/app/main.py")

    block_indent = len(lines[i]) - len(lines[i].lstrip())
    out: list[str] = []
    while i < len(lines):
        line = lines[i]
        if not line.strip() or line.strip().startswith("#"):
            out.append(line)
            i += 1
            continue
        indent = len(line) - len(line.lstrip())
        # `except`/`else` sit at the block's own indent, so only a line at the *anchor's* indent
        # (the step's body level) that is not part of this statement ends the block.  A `try` block
        # is recognised and allowed to continue through its `except`.
        if out and indent <= block_indent and not (line.strip().startswith(("except", "else:"))):
            break
        out.append(line)
        i += 1
    # Drop trailing blanks / comments, and keep only through the last code line.
    while out and (not out[-1].strip() or out[-1].strip().startswith("#")):
        out.pop()
    if not out:
        raise AssertionError("the normalisation site was not found in backend/app/main.py")
    code_indent = min(len(l) - len(l.lstrip()) for l in out if l.strip())
    return "\n".join(l[code_indent:] for l in out).rstrip()


def run(timezone_name: str) -> tuple[str, str | None]:
    """Execute the real lines for one zone; return (offset used, exception name or None)."""
    src = source_at_site()
    env = {"ZoneInfo": ZoneInfo, "ZoneInfoNotFoundError": None, "journey": None}
    # `ZoneInfoNotFoundError` is imported in main.py; supply the real class here.
    from zoneinfo import ZoneInfoNotFoundError as ZNFE

    env["ZoneInfoNotFoundError"] = ZNFE
    env["journey"] = type("Journey", (), {"timezone": timezone_name})()
    exec(src, env)
    tz = env["journey_tz"]
    now = datetime(2026, 10, 9, 12, 0, 0)
    return (now.replace(tzinfo=tz).isoformat(), None)


CASES = (
    ("Asia/Shanghai", False),
    ("Mars/Phobos", True),
)


def main() -> int:
    bad: list[str] = []
    checks = 0
    rows = []

    for zone, _expect_fallback in CASES:
        checks += 1
        try:
            moment, _ = run(zone)
            rows.append((zone, moment, None))
        except Exception as exc:  # noqa: BLE001 - the arm's whole point is what raises here
            rows.append((zone, None, type(exc).__name__))
            bad.append(
                "the replan normalisation raises %s for zone %r -- an unusable zone ends the whole "
                "replan door instead of falling back to one usable offset" % (type(exc).__name__, zone)
            )

    print("replan zone normalisation: %d checks, %d bad" % (checks, len(bad)))
    for zone, moment, exc in rows:
        print("   timezone=%-16r moment=%-26s raised=%s" % (zone, moment, exc))
    if bad:
        print("\nARM BITES -- an unusable zone ends the replan door:")
        for x in bad:
            print("   " + x)
        return 1
    print("\nARM_QUIET: the replan normalisation places one offset per instant in every zone.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
