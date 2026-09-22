"""Register the ORD-0220 ① mutants in the kill harness.

The anchor is taken from the product file's own bytes in this run instead of being retyped: every
survivor this lane ever mis-reported traced back to a hand-copied anchor that no longer matched.
"""

from pathlib import Path

ROOT = Path("D:/moodle/_qoder_integration_20260919")
HARNESS = ROOT / "review/ord0082_0087_kill_drivers.py"
PRODUCT = ROOT / "frontend/src/app/V8Experience.tsx"
MARKER = '        [(COPY_SPEC, ["ord0216d-en-the-wizard-never-says-a-city-name"])],\n    ),\n'

CAVEAT_KEY = "按这个预算"
REVERSAL = "按这个预算，住宿、交通和吃饭很可能超出计划。——不过实际上预算充足，放心消费。"


def main() -> int:
    source = open(PRODUCT, encoding="utf-8", newline="").read()
    lines = [line for line in source.split("\n") if CAVEAT_KEY in line]
    if len(lines) != 1:
        print(f"ABORT: the caveat line occurs {len(lines)} times")
        return 2
    anchor = lines[0] + "\n"
    if not anchor.startswith('        ? "') or not anchor.rstrip("\n").endswith('"'):
        print(f"ABORT: unexpected shape {anchor!r}")
        return 3

    cases = [
        (
            "killX1-tight-caveat-says-the-opposite",
            anchor,
            '        ? "' + REVERSAL + '"\n',
            "the red team's arm: the caveat keeps its risk clause and appends a reassurance",
        ),
        (
            "killX2-tight-caveat-says-nothing",
            anchor,
            '        ? ""\n',
            "the empty-caveat arm: the number stands with no sentence behind it",
        ),
    ]

    text = open(HARNESS, encoding="utf-8", newline="").read()
    if "killX1-tight-caveat-says-the-opposite" in text:
        print("already registered; nothing written")
        return 0
    if text.count(MARKER) != 1:
        print(f"ABORT: the insertion marker occurs {text.count(MARKER)} times")
        return 4

    block = ""
    for name, old, new, why in cases:
        block += (
            "    (\n"
            f"        # ORD-0220 ①: {why}.\n"
            f"        {name!r},\n"
            "        EXPERIENCE,\n"
            f"        {old!r},\n"
            f"        {new!r},\n"
            '        [(TIERS_SPEC, ["ord0220-1-the-tight-caveat-cannot-contradict-itself"])],\n'
            "    ),\n"
        )
    updated = text.replace(MARKER, MARKER + block, 1)
    open(HARNESS, "w", encoding="utf-8", newline="").write(updated)
    after = open(HARNESS, encoding="utf-8", newline="").read()
    print(
        f"registered bytes={len(after.encode('utf-8')) - len(text.encode('utf-8'))} "
        f"killX1={'killX1-tight-caveat-says-the-opposite' in after} "
        f"killX2={'killX2-tight-caveat-says-nothing' in after} crlf={after.count(chr(13) + chr(10))}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
