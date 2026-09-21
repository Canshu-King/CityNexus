"""Fix the disabled-state probe in the ORD-0135 step-3 node.

`isDisabled()` counts `aria-disabled` as disabled, so it cannot distinguish "blocked accessibly" from
"hard-disabled" -- and distinguishing those two is the whole point of the order (a hard `disabled`
drops the button out of the tab sequence, which is the ORD-0066 finding).  The native `disabled`
attribute is the only reading that answers it.  Also add the focusability assertion that the same
argument implies.

Written as a file because the replacement text contains escapes a shell scan reads as UNC paths.
"""

import io

PATH = "D:/moodle/_qoder_integration_20260919/frontend/e2e/qoder-wizard-speaks-human-and-survives-reload.spec.ts"

PAIRS = [
    (
        '  const completeState = {\n    ariaDisabled: await create.getAttribute("aria-disabled"),\n    disabled: await create.isDisabled(),\n  };',
        '  /* `isDisabled()` counts `aria-disabled` as disabled too, so it cannot tell the two apart -- and\n'
        '     the whole point of the order is that this button is aria-disabled and NOT hard-disabled.\n'
        '     The native attribute is the only reading that answers that question. */\n'
        '  const completeState = {\n    ariaDisabled: await create.getAttribute("aria-disabled"),\n    hardDisabled: await create.getAttribute("disabled"),\n  };',
    ),
    (
        '  expect(\n    completeState.disabled,\n    node(NODE, `a complete draft hard-disabled 确认创建: ${JSON.stringify(completeState)}`),\n  ).toBe(false);',
        '  expect(\n    completeState.hardDisabled,\n    node(NODE, `a complete draft hard-disabled 确认创建: ${JSON.stringify(completeState)}`),\n  ).toBeNull();',
    ),
    (
        '  const blockedState = {\n    ariaDisabled: await create.getAttribute("aria-disabled"),\n    disabled: await create.isDisabled(),\n    describedBy: await create.getAttribute("aria-describedby"),\n  };',
        '  const blockedState = {\n    ariaDisabled: await create.getAttribute("aria-disabled"),\n    hardDisabled: await create.getAttribute("disabled"),\n    describedBy: await create.getAttribute("aria-describedby"),\n  };',
    ),
    (
        '  expect(\n    blockedState.disabled,\n    node(NODE, `确认创建 uses hard `disabled`, which drops it out of the tab sequence and makes its reason unreachable: ${JSON.stringify(blockedState)}`),\n  ).toBe(false);',
        '  expect(\n    blockedState.hardDisabled,\n    node(NODE, `确认创建 uses a hard disabled attribute, which drops it out of the tab sequence and makes its reason unreachable: ${JSON.stringify(blockedState)}`),\n  ).toBeNull();\n'
        '  /* Focusable for the same reason: the argument for aria-disabled over disabled is that the\n'
        '     reason beside the button stays reachable. */\n'
        '  await create.focus();\n'
        '  expect(\n    await focusedTestId(page),\n    node(NODE, "the blocked 确认创建 cannot take focus, so a keyboard traveller never reaches its reason"),\n  ).toBe("trial-create");',
    ),
    (
        '  const statuses = (await page.getByRole("status").all()).filter(async () => true);',
        '  const statuses = await page.getByRole("status").all();',
    ),
]


def main() -> int:
    text = io.open(PATH, encoding="utf-8", newline="").read()
    for old, new in PAIRS:
        if text.count(old) != 1:
            print(f"ABORT: anchor appears {text.count(old)} times, expected 1:\n{old[:90]}")
            return 2
        text = text.replace(old, new, 1)
    io.open(PATH, "w", encoding="utf-8", newline="").write(text)
    after = io.open(PATH, encoding="utf-8", newline="").read()
    crlf = io.open(PATH, "rb").read().count(b"\r\n")
    print(f"hardDisabled={after.count('hardDisabled')} focusedTestId={after.count('focusedTestId')} crlf={crlf}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
