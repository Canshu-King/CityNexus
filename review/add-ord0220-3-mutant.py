"""Register the ORD-0220 ③ mutant: a refused press that answers out loud but brings nothing on screen.

Anchor read from the product file in this run so it cannot silently miss.
"""

from pathlib import Path

ROOT = Path("D:/moodle/_qoder_integration_20260919")
HARNESS = ROOT / "review/ord0082_0087_kill_drivers.py"
PRODUCT = ROOT / "frontend/src/features/setup/JourneyTrialSetup.tsx"
MARKER = "        [(SURFACE_SPEC, ['ord0220-2-the-announcement-retires-when-the-field-is-fixed'])],\n    ),\n"
OLD = (
    '    hint.scrollIntoView({ block: "center", behavior: "smooth" });\n'
    "    hint.focus({ preventScroll: false });\n"
)
NEW = "    // reveal removed: the sentence is spoken, the screen never shows it\n"
NODE = "ord0220-3-a-refused-press-brings-its-reason-on-screen"


def main() -> int:
    source = open(PRODUCT, encoding="utf-8", newline="").read()
    if source.count(OLD) != 1:
        print(f"ABORT: the reveal body occurs {source.count(OLD)} times")
        return 2
    text = open(HARNESS, encoding="utf-8", newline="").read()
    if "killZ1-refused-press_never_reveals_its_reason" in text:
        print("already registered; nothing written")
        return 0
    if text.count(MARKER) != 1:
        print(f"ABORT: marker occurs {text.count(MARKER)} times, expected 1")
        return 3
    entry = (
        "    (\n"
        "        # ORD-0220 ③: the press still speaks but the reason never reaches the viewport --\n"
        "        # the exact 'I pressed and nothing happened' state HJ-P1 measured three times.\n"
        "        \"killZ1-refused-press-never-reveals-its-reason\",\n"
        "        WIZARD,\n"
        f"        {OLD!r},\n"
        f"        {NEW!r},\n"
        f"        [(SURFACE_SPEC, [{NODE!r}])],\n"
        "    ),\n"
    )
    index = text.index(MARKER) + len(MARKER)
    updated = text[:index] + entry + text[index:]
    open(HARNESS, "w", encoding="utf-8", newline="").write(updated)
    import ast

    ast.parse(open(HARNESS, encoding="utf-8").read())
    print(f"registered bytes={len(updated.encode('utf-8')) - len(text.encode('utf-8'))} parses=OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
