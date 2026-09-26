"""E's signoff criterion, applied to ORD-0323's arms: read rendered text, compare with equality,
and sign every cell with (sha, nodeid, shape).

Why each piece is where it is:
* `nodeid` goes into the spec's own teardown, so the identity of the test that produced a reading is
  written by the instrument, not transcribed by me into the receipt.
* Equality assertions parse the *field* out of the rendered line and compare the field (`===`), which is
  what "等值用 == 不用 in" asks for; the negative sweeps deliberately stay substring-based, because a
  substring hit is a *stronger* violation than an equal one -- there I say so rather than weaken them.
* The channel rule is checked as a negative with its inventory printed: which `serverReason` strings exist
  in the candidate tree, and that no `lib/serverReason.ts` exists at all.

Run this only after a matrix pass finishes: the runner executes the spec from disk.
"""
from __future__ import annotations

import ast
import pathlib
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
FE = pathlib.Path(r"D:\moodle\_qoder_b_lane_20260923\frontend")
SPEC = FE / "e2e/qoder-ord0323-two-exposure-cells.spec.ts"


def rep(t: str, old: str, new: str, want: int = 1) -> str:
    n = t.count(old)
    if n != want:
        raise SystemExit(f"expected {want}, found {n} for:\n{old[:200]}")
    return t.replace(old, new)


t = SPEC.read_text(encoding="utf-8")

# 1. every evidence file names the test that wrote it.
t = rep(t, """  const body: Readings = { ...(readings[arm] ?? {}) };""",
          """  const body: Readings = { ...(readings[arm] ?? {}) };
  /* E's signoff criterion: a reading is worth nothing unless it says which test produced it. */
  body.nodeid = info.titlePath().join(" > ");""")

# 2. T-legs: the status must *equal* what this leg asked, as a parsed field.
t = rep(t, """      status_in_slot: text.includes(String(leg.status)),""",
          """      status_in_slot: text.includes(String(leg.status)),
      status_field_equals_asked: (text.match(/http_status=(\\d+)/) || [null, ""])[1] === String(leg.status),""")
t = rep(t, """    expect(text.includes(String(leg.status)),
      node(arm, `${leg.cell}: the slot no longer states the status this device measured for THIS request (${text})`)).toBe(true);""",
      """    expect(text.includes(String(leg.status)),
      node(arm, `${leg.cell}: the slot no longer states the status this device measured for THIS request (${text})`)).toBe(true);
    /* equality on the parsed field, so a substring of another leg's status cannot pass for this one */
    expect((text.match(/http_status=(\\d+)/) || [null, "(absent)"])[1],
      node(arm, `${leg.cell}: the parsed http_status field is "${(text.match(/http_status=(\\d+)/) || [null, "(absent)"])[1]}", this leg asked ${leg.status} (${text})`)).toBe(String(leg.status));""")

# 3. F1: the machine half must be exactly what this arm answered.
t = rep(t, """    fields_in_line: /http_status=200/.test(text) && /content_type=text\\/html/.test(text),""",
        """    machine_half: (text.split(" · ").slice(-1)[0] ?? "").trim(),
    machine_half_equals: (text.split(" · ").slice(-1)[0] ?? "").trim()
      === "http_status=200 content_type=text/html;charset=UTF-8 evidence=HTTP_RESPONSE",
    fields_in_line: /http_status=200/.test(text) && /content_type=text\\/html/.test(text),""")
t = rep(t, """  expect(readings[arm].fields_in_line, node(arm, `F1: 这一行没有这台设备自己量的状态与媒体类型（${text.slice(0, 220)}）`)).toBe(true);""",
      """  expect(readings[arm].fields_in_line, node(arm, `F1: 这一行没有这台设备自己量的状态与媒体类型（${text.slice(0, 220)}）`)).toBe(true);
  expect((text.split(" · ").slice(-1)[0] ?? "").trim(),
    node(arm, `F1: 机器那一半与这台设备答的不逐字相同（${(text.split(" · ").slice(-1)[0] ?? "").trim()}）`),
  ).toBe("http_status=200 content_type=text/html;charset=UTF-8 evidence=HTTP_RESPONSE");""")

# 4. F2: the enum token must be the whole field, not a substring of a sentence.
t = rep(t, """    machine_status_in_line: text.includes("REJECTED"),""",
        """    machine_status_in_line: text.includes("REJECTED"),
    last_token_equals: (text.trim().split(/\\s+/).slice(-1)[0] ?? "") === "REJECTED",""")
t = rep(t, """  expect(readings[arm].machine_status_in_line, node(arm, `F2: 状态行不再说明这台答复自己的机器状态（${text.slice(0, 220)}）`)).toBe(true);""",
      """  expect(readings[arm].machine_status_in_line, node(arm, `F2: 状态行不再说明这台答复自己的机器状态（${text.slice(0, 220)}）`)).toBe(true);
  expect((text.trim().split(/\\s+/).slice(-1)[0] ?? ""),
    node(arm, `F2: 这一行的最后一个记号不是那枚机器枚举，而是 "${(text.trim().split(/\\s+/).slice(-1)[0] ?? "")}"（${text.slice(0, 220)}）`),
  ).toBe("REJECTED");""")

# 5/6. F3, F4: the held notice is one fixed device sentence, compared whole.
# Built by concatenation, not an f-string: a JS `${...}` inside an f-string is a Python replacement field.
for key, tid, held_msg in (("F3", "v13-2-memory-summary-held", "这一行不再说明摘要存在但不在这里展示"),
                           ("F4", "v13-2-draft-summary-held", "待审那一屏不再说明摘要存在但不在这里展示")):
    old = '    held_token_present: (await page.getByTestId("' + tid + '").count()) > 0,'
    new = (old + '\n    held_text: clean(await page.getByTestId("' + tid
           + '").textContent().catch(() => "")) ?? "",')
    t = rep(t, old, new)
    old2 = ('  expect(readings[arm].held_token_present, node(arm, "' + key + ': ' + held_msg
            + '")).toBe(true);')
    new2 = (old2 + '\n  expect(readings[arm].held_text,\n'
            '    node(arm, `' + key + ': 那一格写的不是这句设备自己的话（"${String(readings[arm].held_text)}"）`)).toBe('
            '"reasoning_summary=held 原文不在这一屏");')
    t = rep(t, old2, new2)

# 7. Q68b: the fold holds the server's sentence *whole*, which is what Q67=① allows.
t = rep(t, """    attributed_sentence_in_fold: reasonText.includes(Q68_PROSE),""",
        """    attributed_sentence_in_fold: reasonText.includes(Q68_PROSE),
    fold_text_equals_the_sentence: reasonText === Q68_PROSE,""")
t = rep(t, """  expect(reasonText.includes(Q68_PROSE),
    node(arm, `the sentence vanished from 技术详情 too (${reasonText.slice(0, 160)}) -- Q68 says the code slot is not its place, not that it may be deleted`)).toBe(true);""",
        """  expect(reasonText,
    node(arm, `技术详情 holds something other than the reply's own sentence verbatim (${reasonText.slice(0, 200)})`)).toBe(Q68_PROSE);
  expect(reasonText.includes(Q68_PROSE),
    node(arm, `the sentence vanished from 技术详情 too (${reasonText.slice(0, 160)}) -- Q68 says the code slot is not its place, not that it may be deleted`)).toBe(true);""")

# 8. N1's own boundary declaration, compared as a field.
t = rep(t, """    console_error_count: consoleErrors.length,""",
        """    console_error_count: consoleErrors.length,
    failure_text_rendered_field: (detail.match(/failure_text_rendered=(\\w+)/) || [null, ""])[1],""")
t = rep(t, """  expect(
    detail.includes("failure_text_rendered=no"),
    node(arm, `the fold no longer states its own boundary; it reads "${detail.slice(0, 200)}"`),
  ).toBe(true);""",
      """  expect(
    (detail.match(/failure_text_rendered=(\\w+)/) || [null, ""])[1],
    node(arm, `the fold no longer states its own boundary as the word no; it reads "${detail.slice(0, 200)}"`),
  ).toBe("no");""")

SPEC.write_text(t, encoding="utf-8", newline="\n")
print("spec: equality legs + nodeid stamping applied")
