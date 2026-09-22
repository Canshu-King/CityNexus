"""Register the ORD-0220 ② mutant: put the announcement snapshot back.

The anchor is read from the product file in this run so a hand-copied string cannot silently miss.
"""

from pathlib import Path

ROOT = Path("D:/moodle/_qoder_integration_20260919")
HARNESS = ROOT / "review/ord0082_0087_kill_drivers.py"
PRODUCT = ROOT / "frontend/src/features/setup/JourneyTrialSetup.tsx"
MARKER = '        [(TIERS_SPEC, ["ord0220-1-the-tight-caveat-cannot-contradict-itself"])],\n    ),\n'
OLD_LINE = "        {spokenKey === missingKey ? spokenReason : \"\"}\n"
NEW_LINE = "        {spokenReason}\n"
NODE = "ord0220-2-the-announcement-retires-when-the-field-is-fixed"


def main() -> int:
    source = open(PRODUCT, encoding="utf-8", newline="").read()
    if source.count(OLD_LINE) != 1:
        print(f"ABORT: the guarded render occurs {source.count(OLD_LINE)} times")
        return 2
    text = open(HARNESS, encoding="utf-8", newline="").read()
    if "killY1-announcement-keeps-the-stale-snapshot" in text:
        print("already registered; nothing written")
        return 0
    if text.count(MARKER) != 2:
        # two of the registered cases end on this marker line; either is a valid insertion point,
        # so anchor on the last one instead of guessing which the file grew.
        print(f"ABORT: marker occurs {text.count(MARKER)} times, expected 2")
        return 3
    entry = (
        "    (\n"
        "        # ORD-0220 ②: the announcement goes back to being a snapshot of an old missing-list,\n"
        "        # which is what the traveller's screen reader keeps re-reading after the fix.\n"
        "        \"killY1-announcement-keeps-the-stale-snapshot\",\n"
        "        WIZARD,\n"
        f"        {OLD_LINE!r},\n"
        f"        {NEW_LINE!r},\n"
        f"        [(SURFACE_SPEC, [{NODE!r}])],\n"
        "    ),\n"
    )
    index = text.rindex(MARKER)
    updated = text[: index + len(MARKER)] + entry + text[index + len(MARKER) :]
    open(HARNESS, "w", encoding="utf-8", newline="").write(updated)
    import ast

    ast.parse(open(HARNESS, encoding="utf-8").read())
    print(f"registered bytes={len(updated.encode('utf-8')) - len(text.encode('utf-8'))} parses=OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
