# -*- coding: utf-8 -*-
"""扫街工 WP-A′ · 票夹（行程收件箱）屏的表面字面量清扫。

替换前把「每处应出现几次」钉成断言，数不对整批 ABORT；只做同行等值替换，
不插行不删行 ⇒ styles.css 行号前后逐字相同，两把尺可以按行直接对表。
"""
import io
import sys

P = r"D:/moodle/_cmdr_saojieggong_1016/tree/frontend/src/styles.css"

EDITS = [
    # ── aside.v9-inbox：收件栏这张纸 + 它的标签墨 + textarea 的控件边（简报 §2 第 3 条）
    (".v9-inbox { align-self: start; display: grid; gap: var(--cn-s-10); padding: 22px; border: 1px solid var(--v8-line); border-radius: var(--cn-r-12); background: #fff; }",
     ".v9-inbox { align-self: start; display: grid; gap: var(--cn-s-10); padding: 22px; border: 1px solid var(--v8-line); border-radius: var(--cn-r-12); background: var(--cn-elev-1); }",
     1),
    (".v9-inbox label { color: #6c7889; font-size: 11px; font-weight: 750; }",
     ".v9-inbox label { color: var(--cn-on-elev-1-muted); font-size: 11px; font-weight: 750; }",
     1),
    (".v9-inbox textarea { min-height: 150px; padding: 12px; border: 1px solid #cfd5df;",
     ".v9-inbox textarea { min-height: 150px; padding: 12px; border: 1px solid var(--cn-control-border);",
     1),
    # ── 票夹卡片本体
    (".v8-booking-card { display: flex; align-items: center; gap: 16px; padding: 20px; border: 1px solid var(--v8-line); border-radius: var(--cn-r-12); background: #fff; }",
     ".v8-booking-card { display: flex; align-items: center; gap: 16px; padding: 20px; border: 1px solid var(--v8-line); border-radius: var(--cn-r-12); background: var(--cn-elev-1); }",
     1),
    (".v8-booking-card p { margin: 0 0 9px; color: #8994a3; font-size: 11px; }",
     ".v8-booking-card p { margin: 0 0 9px; color: var(--cn-on-elev-1-muted); font-size: 11px; }",
     1),
    (".v8-booking-card.selected { border-color: #b8c0f1; background: #fbfbff; }",
     ".v8-booking-card.selected { border-color: #b8c0f1; background: var(--cn-elev-2); }",
     1),
    # ── 卡图标：图形枚的地板是 3:1（非文字），底进契约、墨留 --v8-indigo（本来就随主题）
    ("color: var(--v8-indigo); background: #eef0ff; }",
     "color: var(--v8-indigo); background: var(--cn-elev-2); }",
     1),
    (".v8-booking-icon.muted { color: #718095; background: #f1f3f6; }",
     ".v8-booking-icon.muted { color: var(--cn-on-elev-1-muted); background: var(--cn-elev-2); }",
     1),
    # ── 状态小牌：琥珀那枚的墨若留着，换纸后暗色只有 2.97 ⇒ 纸墨成对一起走
    ("color: #8e6b34; background: #fff6e8; font-size: 9px; font-weight: 800; white-space: nowrap; }",
     "color: var(--cn-on-elev-1-muted); background: var(--cn-elev-2); font-size: 9px; font-weight: 800; white-space: nowrap; }",
     1),
    (".v8-booking-state.safe { color: var(--v8-green); background: #effaf5; }",
     ".v8-booking-state.safe { color: var(--cn-success-text); background: var(--cn-elev-2); }",
     1),
    (".v8-selected-label.neutral { color: #68758a; background: #f1f3f6; }",
     ".v8-selected-label.neutral { color: var(--cn-on-elev-1-muted); background: var(--cn-elev-2); }",
     1),
    # ── 「无需支付」条：底/墨/边三枚一组，只换其中两枚会在暗色留下发光边
    ("border: 1px solid #dcefe7; border-radius: var(--cn-r-8); color: #46655a; background: #f6fcf9; font-size: 11px; }",
     "border: 1px solid var(--cn-rule); border-radius: var(--cn-r-8); color: var(--cn-on-elev-2); background: var(--cn-elev-2); font-size: 11px; }",
     1),
    (".v8-no-payment b { flex: none; color: var(--v8-green); }",
     ".v8-no-payment b { flex: none; color: var(--cn-success-text); }",
     1),
    (".v8-no-payment span { color: #728d83; line-height: 1.45; }",
     ".v8-no-payment span { color: var(--cn-on-elev-1-muted); line-height: 1.45; }",
     1),
]


def main():
    src = io.open(P, encoding="utf-8", newline="").read()
    before_lines = src.count("\n")
    plan = []
    for old, new, want in EDITS:
        got = src.count(old)
        if got != want:
            print("ABORT  期望 %d 次，实际 %d 次：%.90s" % (want, got, old))
            return 2
        plan.append((old, new))
    for old, new in plan:
        src = src.replace(old, new, 1)
    if src.count("\n") != before_lines:
        print("ABORT  行数被移动：%d → %d" % (before_lines, src.count("\n")))
        return 3
    io.open(P, "w", encoding="utf-8", newline="").write(src)
    print("落了 %d 处替换，行数保持 %d" % (len(plan), before_lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
