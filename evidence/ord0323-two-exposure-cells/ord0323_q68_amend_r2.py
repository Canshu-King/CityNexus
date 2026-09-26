"""Second cut of the Q68 amendment: name the finding, do not bend the assertion.

Measured on the candidate: a sentence-only refusal lands on the no-plan copy
「…但没有给出具体原因编号…」, not on the code slot's 「（没给编号）」 -- requirement ① makes
`serverReasonCode` answer "", and every producer of `BLOCKED:` then holds a non-empty code, so the slot's
no-code branch cannot be reached. That is a fork for the commander, so this leg asserts what both
sanctioned wordings mean (the screen names the absence of a machine code) and records which one fired.

No backslash-escaped parentheses anywhere: `[(]` matches "(" in a regex and keeps this file out of the
Python-string-escaping trap that ate the first cut.
"""
from __future__ import annotations

import pathlib
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
SPEC = pathlib.Path(r"D:\moodle\_qoder_b_lane_20260923\frontend\e2e\qoder-ord0323-two-exposure-cells.spec.ts")
t = SPEC.read_text(encoding="utf-8")

SLOT = "（没给编号）|[(]none given[)]"
NO_PLAN = "没有给出具体原因编号"


def rep(old: str, new: str, want: int) -> None:
    global t
    n = t.count(old)
    if n != want:
        raise SystemExit(f"expected {want}, found {n} for:\n{old[:200]}")
    t = t.replace(old, new)


# 0. normalise the escaped-paren spelling the first cut shipped with, so one form is searched everywhere.
BS = chr(92)  # a backslash, spelled out so this file never has to double-escape one
rep(f"{BS}(none given{BS})", "[(]none given[)]", 2)

# 1. the arm name is read out of the test title; the two new arms collapsed into "N6" without this.
rep("/^N6_(Q68[ab])_/", "/^N6_(Q68[abcd])_/", 1)

# 2. which wording the screen used is a reading, not an assumption.
rep(
    f"    no_code_branch_on_screen: /{SLOT}/.test(cardAll),",
    "    no_code_branch_on_screen: noCodeAnyWording,\n"
    f"    no_code_copy_in_the_code_slot: /{SLOT}/.test(cardAll),\n"
    f"    no_code_copy_in_the_no_plan_state: /{NO_PLAN}/.test(cardAll),\n"
    f"    which_no_code_branch: /{SLOT}/.test(cardAll)\n"
    '      ? "code_slot"\n'
    f"      : /{NO_PLAN}/.test(cardAll)\n"
    '        ? "no_plan_state"\n'
    '        : "neither",',
    1,
)

# 3. define it after cardAll, before the readings block.
rep(
    '''  const cardWithoutReason = cardAll.replace(reasonText, "");''',
    '''  const cardWithoutReason = cardAll.replace(reasonText, "");
  /* both copies the product is allowed to use for "the server gave no machine code" */
  const noCodeAnyWording = /''' + SLOT + "|" + NO_PLAN + '''/.test(cardAll);''',
    1,
)

# 4. the positive leg names the absence in either sanctioned wording.
rep(
    f'''  expect(
    /{SLOT}/.test(cardAll),
    node(arm, `the slot fell through neither the code nor the "no code" copy (${{cardAll.slice(0, 240)}}) -- an invented code and a silent slot are both wrong`),
  ).toBe(true);''',
    '''  expect(
    noCodeAnyWording,
    node(arm, `the screen names no absence of a machine code in either sanctioned wording (${{cardAll.slice(0, 240)}}) -- an invented code and a silent slot are both wrong`),
  ).toBe(true);''',
    1,
)

if "noCodeAnyWording" not in t or t.count("Q68[abcd]") != 1:
    raise SystemExit("the second cut did not land")
if t.find("const cardAll =") > t.find("const noCodeAnyWording ="):
    raise SystemExit("ordering bug: noCodeAnyWording is computed before cardAll exists")
SPEC.write_text(t, encoding="utf-8", newline="\n")
print("arm naming fixed; the no-code leg now records which branch fired; escaped parens:",
      len(re.findall(r"\\\\\(", t)), "occurrence(s)")
