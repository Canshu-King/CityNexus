"""Add the two ORD-0203 mutants to the kill-driving harness.

Written as a file because the anchors contain escaped quotes and newlines that a shell heredoc
mangles into real newlines (this has broken the harness's syntax four times tonight).
"""

import io

PATH = "D:/moodle/_qoder_integration_20260919/review/ord0082_0087_kill_drivers.py"

CONST_OLD = 'PREP_SPEC = "e2e/qoder-destination-preparation.spec.ts"\n'
CONST_NEW = CONST_OLD + 'NA_SPEC = "e2e/qoder-not-answered-cell.spec.ts"\n'

TAIL_OLD = (
    '        [(PREP_SPEC, ["ord0193-a-retryable-runtime-failure-offers-a-retry-and-a-structural-one-does-not"])],\n'
    "    ),\n"
    "]\n"
)

TAIL_NEW = (
    '        [(PREP_SPEC, ["ord0193-a-retryable-runtime-failure-offers-a-retry-and-a-structural-one-does-not"])],\n'
    "    ),\n"
    "    (\n"
    "        # ORD-0203: the fourth cell's action stops being reachable -- the branch that renders the\n"
    "        # retry is renamed so nothing matches, which is how a control silently disappears.\n"
    "        \"killR1-retry-later-is-not-rendered\",\n"
    "        PREP,\n"
    '        \'            ) : action === "RETRY_LATER" ? (\\n\',\n'
    '        \'            ) : action === "RETRY_LATER_DISABLED_FOR_THIS_MUTANT" ? (\\n\',\n'
    '        [(NA_SPEC, ["ord0203-the-fourth-cell-renders-and-its-retry-consumes-retryable"])],\n'
    "    ),\n"
    "    (\n"
    "        # ORD-0203: the fourth cell rendered with the conflation R11 froze -- plannability written\n"
    "        # as coverage completeness.  This is the exact sentence the order forbids.\n"
    '        "killR2-fourth-cell-claims-the-city-needs-data",\n'
    "        PREP,\n"
    '        "            ? `服务器说这一问没有拿到答复（${reasonCode}）——是它去问的那一头没答话，不是「这个地方不能规划」，也不是「这城市还要灌数据」。这两句服务器都没说。可以稍后重试。`\\n",\n'
    '        "            ? `这城市还要灌数据，服务器暂时没有它的资料。`\\n",\n'
    '        [(NA_SPEC, ["ord0203-the-fourth-cell-renders-and-its-retry-consumes-retryable"])],\n'
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
    print(f"killR1={'killR1' in after} killR2={'killR2' in after} NA_SPEC={'NA_SPEC' in after}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
