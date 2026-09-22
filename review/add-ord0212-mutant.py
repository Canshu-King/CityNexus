"""Add the ORD-0212 kill mutant: the tight advisory keeps its number but loses its caveat.

Written as a file because the anchors contain comment-free JSX with escapes that a heredoc mangles
into real newlines, which has broken this harness's syntax several times tonight.
"""

import io

PATH = "D:/moodle/_qoder_integration_20260919/review/ord0082_0087_kill_drivers.py"

CONST_OLD = 'DEMO_SPEC = "e2e/qoder-demo-entry-addresses-dont-create.spec.ts"\n'
CONST_NEW = CONST_OLD + 'TIERS_SPEC = "e2e/qoder-budget-advisory-tiers.spec.ts"\n'

# The tight branch's hint line sits between the strong (number) and the action row.  Removing only
# the hint keeps 每人每天约 X while deleting 按这个预算…很可能超出计划 -- the exact fake precision
# the order warns against.
TAIL_OLD = (
    '        [(DEMO_SPEC, ["ord0209-the-demo-entry-addresses-the-sealed-journey"])],\n'
    "    ),\n"
    "]\n"
)

HINT_OLD = '              <span>{advisory.hint}</span>\n'
ACTION_OLD = '              <div className="today-advisory-actions">\n'
HINT_AND_ACTION = HINT_OLD + ACTION_OLD

TAIL_NEW = (
    '        [(DEMO_SPEC, ["ord0209-the-demo-entry-addresses-the-sealed-journey"])],\n'
    "    ),\n"
    "    (\n"
    "        # ORD-0212's own warned trap: following \"remove the tier\" so literally that the caveat\n"
    "        # is stripped while the derived number stays -- a vague sentence replaced by a\n"
    "        # fake-precision figure.  The invariant tripwire must catch exactly that.\n"
    '        "killU1-tight-advisory-keeps-number-drops-caveat",\n'
    "        EXPERIENCE,\n"
    '        "              <span>{advisory.hint}</span>\\n              <div className=\\"today-advisory-actions\\">\\n",\n'
    '        "              <div className=\\"today-advisory-actions\\">\\n",\n'
    '        [(TIERS_SPEC, ["ord0212-stripping-the-caveat-while-keeping-the-number-must-go-red"])],\n'
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
    # Sanity: the hint-and-action concatenation must exist in the product file exactly once.
    prod = io.open(
        "D:/moodle/_qoder_integration_20260919/frontend/src/app/V8Experience.tsx",
        encoding="utf-8",
        newline="",
    ).read()
    hits = prod.count(HINT_AND_ACTION)
    if hits != 1:
        print(f"ABORT: product anchor appears {hits} times, expected 1")
        return 3
    io.open(PATH, "w", encoding="utf-8", newline="").write(text)
    after = io.open(PATH, encoding="utf-8", newline="").read()
    print(f"killU1={'killU1' in after} TIERS_SPEC={'TIERS_SPEC' in after} productAnchorHits={hits}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
