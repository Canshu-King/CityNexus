"""Add the four ORD-0208 mutants to the kill-driving harness.

Written as a file because the anchors contain escaped quotes, CJK text and newlines that a shell
heredoc mangles into real newlines (this has broken the harness's syntax several times tonight).
"""

import io

PATH = "D:/moodle/_qoder_integration_20260919/review/ord0082_0087_kill_drivers.py"

CONST_OLD = 'NA_SPEC = "e2e/qoder-not-answered-cell.spec.ts"\n'
CONST_NEW = CONST_OLD + 'TONGUE_SPEC = "e2e/qoder-speaks-the-travellers-language.spec.ts"\n'

TAIL_OLD = (
    '        [(NA_SPEC, ["ord0203-the-fourth-cell-renders-and-its-retry-consumes-retryable"])],\n'
    "    ),\n"
    "]\n"
)

TAIL_NEW = (
    '        [(NA_SPEC, ["ord0203-the-fourth-cell-renders-and-its-retry-consumes-retryable"])],\n'
    "    ),\n"
    "    (\n"
    "        # ORD-0208 2: the selected state goes back to colour alone.\n"
    '        "killS1-chips-lose-their-spoken-state",\n'
    "        WIZARD,\n"
    '        "                  aria-pressed={draft.pace === option.key}\\n",\n'
    '        "                  aria-pressed={undefined}\\n",\n'
    '        [(TONGUE_SPEC, ["ord0208-chips-carry-their-state-for-ears-not-only-eyes"])],\n'
    "    ),\n"
    "    (\n"
    "        # ORD-0208 1: the enum returns to the prose -- the measured pre-fix wording.\n"
    '        "killS2-clock-sentence-prints-the-enum-again",\n'
    "        EXPERIENCE,\n"
    '        "                    ? \\"。服务器没有给出这一分钟的执行游标，这一屏的时间按行程的时间窗来读\\"\\n",\n'
    '        "                    ? `，游标状态 ${cursorStatus}`\\n",\n'
    '        [(TONGUE_SPEC, ["ord0208-the-clock-sentence-speaks-human"])],\n'
    "    ),\n"
    "    (\n"
    "        # ORD-0208 3: the inferred default passes for a typed answer again.\n"
    '        "killS3-defaults-pass-as-typed",\n'
    "        WIZARD,\n"
    '                {!touched.has("partySize") && <DefaultMark zh={zh} />}\n'
    "                \"\\n\",\n"
    "        \"\",\n"
    '        [(TONGUE_SPEC, ["ord0208-inferred-defaults-are-marked-on-the-confirmation-step"])],\n'
    "    ),\n"
    "    (\n"
    "        # ORD-0208 4: the day card prints the raw enums again.\n"
    '        "killS4-day-card-prints-raw-enums",\n'
    "        EXPERIENCE,\n"
    '        "                    {anchorLabel(day.anchor, locale.startsWith(\\"zh\\"))} ·{\" \"}\\n'
    '                    {modeLabel(day.mode, locale.startsWith(\\"zh\\"))}\\n",\n'
    '        "                    {day.anchor} anchor · {day.mode}\\n",\n'
    '        [(TONGUE_SPEC, ["ord0208-the-day-card-speaks-the-language-the-screen-uses"])],\n'
    "    ),\n"
    "]\n"
)


def main() -> int:
    text = io.open(PATH, encoding="utf-8", newline="").read()
    for old, new, label in ((CONST_OLD, CONST_NEW, "const"), (TAIL_OLD, TAIL_NEW, "tail")):
        count = text.count(old)
        if count != 1:
            print(f"ABORT: {label} anchor appears {count} times, expected 1")
            return 2
        text = text.replace(old, new, 1)
    io.open(PATH, "w", encoding="utf-8", newline="").write(text)
    after = io.open(PATH, encoding="utf-8", newline="").read()
    print(
        f"killS1={'killS1' in after} killS2={'killS2' in after} "
        f"killS3={'killS3' in after} killS4={'killS4' in after}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
