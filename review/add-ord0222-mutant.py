"""Register the ORD-0222 ④ mutant: put the raw enum back on the day-card row."""

from pathlib import Path

ROOT = Path("D:/moodle/_qoder_integration_20260919")
HARNESS = ROOT / "review/ord0082_0087_kill_drivers.py"
PRODUCT = ROOT / "frontend/src/app/V8Experience.tsx"
MARKER = "        [(TIERS_SPEC, [\"ord0220-1-the-tight-caveat-cannot-contradict-itself\"])],\n    ),\n"
OLD = '              <span className="mode-mark">{modeLabel(day.mode, zh)}</span>{" "}\n'
NEW = '              <span className="mode-mark">{day.mode}</span>{" "}\n'
NODE = "ord0222-1-visual-scan-no-raw-enums-and-no-mixed-english"


def main() -> int:
    source = open(PRODUCT, encoding="utf-8", newline="").read()
    if source.count(OLD) != 1:
        print(f"ABORT: the mapped day-card row occurs {source.count(OLD)} times")
        return 2
    text = open(HARNESS, encoding="utf-8", newline="").read()
    if "killAA1-day-card-row_prints_the_raw_mode" in text:
        print("already registered; nothing written")
        return 0
    if text.count(MARKER) != 2:
        print(f"ABORT: marker occurs {text.count(MARKER)} times, expected 2")
        return 3
    entry = (
        "    (\n"
        "        # ORD-0222 4: the row HJ-P1 read twice goes back to printing the provider enum.\n"
        "        \"killAA1-day-card-row-prints-the-raw-mode\",\n"
        "        EXPERIENCE,\n"
        f"        {OLD!r},\n"
        f"        {NEW!r},\n"
        f"        [(ENUM_SPEC, [{NODE!r}])],\n"
        "    ),\n"
    )
    index = text.rindex(MARKER) + len(MARKER)
    updated = text[:index] + entry + text[index:]
    if "ENUM_SPEC =" not in updated:
        updated = updated.replace(
            'COPY_SPEC = "e2e/qoder-demo-entry-copy-matches-the-stage.spec.ts"\n',
            'COPY_SPEC = "e2e/qoder-demo-entry-copy-matches-the-stage.spec.ts"\n'
            'ENUM_SPEC = "e2e/qoder-raw-enums-never-reach-the-traveller.spec.ts"\n',
            1,
        )
    open(HARNESS, "w", encoding="utf-8", newline="").write(updated)
    import ast

    ast.parse(open(HARNESS, encoding="utf-8").read())
    print(f"registered bytes={len(updated.encode('utf-8')) - len(text.encode('utf-8'))} parses=OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
