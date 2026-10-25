"""Build the P0 evidence index by reading the receipts, not by memory.

Every row is derived: JSON receipts are parsed, line receipts are searched for the
keys named here, and screenshots are only listed when the file exists.  A missing
file prints MISSING instead of a verdict.
"""
from __future__ import annotations

import glob
import json
import os

OUT_DIR = r"D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome"
OUT = r"D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261025_P0_EVIDENCE_INDEX.md"


def png(name: str) -> str:
    path = os.path.join(OUT_DIR, name)
    if not os.path.exists(path):
        return "MISSING"
    return "%s (%d bytes)" % (name, os.path.getsize(path))


def json_file(name: str) -> dict:
    path = os.path.join(OUT_DIR, name)
    if not os.path.exists(path):
        return {}
    try:
        return json.loads(open(path, encoding="utf-8").read())
    except ValueError:
        return {}


def lines_of(name: str) -> list[str]:
    path = os.path.join(OUT_DIR, name)
    if not os.path.exists(path):
        return []
    return [line.strip() for line in open(path, encoding="utf-8", errors="replace")]


def find(lines: list[str], prefix: str) -> str:
    for line in lines:
        if line.startswith(prefix):
            return line
    return "MISSING"


def line_json(lines: list[str], label: str):
    for line in lines:
        if line.startswith(label):
            try:
                return json.loads(line[len(label):].strip())
            except ValueError:
                return {}
    return {}


def newest(pattern: str) -> str:
    found = sorted(glob.glob(os.path.join(OUT_DIR, pattern)))
    return found[-1] if found else ""


def main() -> int:
    bypass = json_file("presenter-proxy-bypass-1.txt")
    replay = json_file("pairing-replay-66.txt")
    chain = json_file("single-state-chain-65.txt")
    cities = json_file("cities-classroom-62.txt")
    after = json_file("after-merge-check.txt")
    ui = lines_of("clock-run-ui-1.txt")
    ui77 = lines_of("clock-run-ui-77.txt")
    jump = lines_of("jump-clock-87.txt")
    two_day = lines_of("clock-two-day-classroom-62.txt")
    lan = lines_of("clock-run-lan-63.txt")
    scene = lines_of("clock-scene-guardian-59.txt")
    tablet = json_file(os.path.basename(newest("tablet-evidence-*.txt"))) if newest("tablet-evidence-*.txt") else {}

    rows = []
    rows.append(("P0-1 LAN 不穿透 / 票一次性",
                 "绿" if bypass.get("BYPASS_SUSPECTED") is False
                 and (replay.get("second_redeem") or {}).get("http") == 401
                 and (replay.get("first_redeem") or {}).get("http") == 200 else "红",
                 "presenter-proxy-bypass-1.txt, pairing-replay-66.txt",
                 "BYPASS_SUSPECTED=%s；首兑 %s，重兑 %s，无 key %s" % (
                     bypass.get("BYPASS_SUSPECTED"),
                     (replay.get("first_redeem") or {}).get("http"),
                     (replay.get("second_redeem") or {}).get("http"),
                     (replay.get("pairing_without_key") or {}).get("http"))))
    rows.append(("P0-2 时钟条接同一 run（屏上）",
                 "绿" if "ERRORS []" in ui and "已走到下一站" in find(ui, "AFTER_NEXT_NOTE") else "红",
                 "clock-run-ui-1.txt",
                 "%s；%s；%s" % (find(ui, "PLUS30_1_TEXT"), find(ui, "AFTER_NEXT"), find(ui, "ERRORS"))))
    rows.append(("P0-2 时钟条三键复跑（入口落位后）",
                 "绿" if "ERRORS []" in ui77 and "已走到下一站" in find(ui77, "AFTER_NEXT_NOTE")
                 and "RELOAD_SAME_STEP true" in ui77 else "红",
                 "clock-run-ui-77.txt",
                 "%s；%s；%s" % (find(ui77, "PLUS30_1_TEXT"), find(ui77, "AFTER_NEXT"), find(ui77, "RELOAD_SAME_STEP"))))
    rows.append(("P0-2 两日闭环（真栈）",
                 "绿" if any("模拟行程已完成" in line for line in two_day) else "红",
                 "clock-two-day-classroom-62.txt, classroom-clock-run-62-live-classroom.png",
                 "%s；%s" % (find(two_day, "FINAL"), png("classroom-clock-run-62-live-classroom.png"))))
    two_day_merge = lines_of("clock-two-day-merge54-84.txt")
    rows.append(("P0-2 两日闭环（合入 PR #54 后真栈）",
                 "绿" if "模拟行程已完成" in find(two_day_merge, "FINAL")
                 and "ERRORS []" in two_day_merge
                 and "REV-CLOCK-NEXT_DISABLED true" in two_day_merge else "红",
                 "clock-two-day-merge54-84.txt, classroom-two-day-merge54-84.png",
                 "%s；%s；%s" % (
                     find(two_day_merge, "START"), find(two_day_merge, "FINAL"),
                     png("classroom-two-day-merge54-84.png"))))
    rows.append(("P0-2 LAN 平板等价路径",
                 "绿" if "ERRORS []" in lan and "执行第" in find(lan, "AFTER_NEXT") else "红",
                 "clock-run-lan-63.txt, classroom-clock-run-63-c.png",
                 "%s；%s" % (find(lan, "AFTER_NEXT"), png("classroom-clock-run-63-c.png"))))
    rows.append(("P0-2 场景→守护→缺任务",
                 "绿" if "缺少守护任务" in find(scene, "AFTER_GUARDIAN") and "RESUME_BUTTON 0" in scene else "红",
                 "clock-scene-guardian-59.txt",
                 "%s；%s" % (find(scene, "AFTER_SCENE"), find(scene, "AFTER_GUARDIAN"))))
    rows.append(("P0-2 单一状态链（CAS + 旧门）",
                 "绿" if (chain.get("advance_stale_sequence") or {}).get("http") == 409
                 and (chain.get("legacy_advance") or {}).get("http") == 409 else "红",
                 "single-state-chain-65.txt",
                 "stale=%s（%s）；legacy=%s（%s）" % (
                     (chain.get("advance_stale_sequence") or {}).get("http"),
                     (chain.get("advance_stale_sequence") or {}).get("error"),
                     (chain.get("legacy_advance") or {}).get("http"),
                     (chain.get("legacy_advance") or {}).get("error"))))
    rows.append(("P0-3 城市池 / 1 城同 run",
                 "黄（池子 BLOCKED，但不挡开演）" if cities.get("status") == "BLOCKED" else "红",
                 "cities-classroom-62.txt",
                 "池 status=%s，eligible=%s/%s，missing=%s" % (
                     cities.get("status"), cities.get("eligible_city_count"),
                     cities.get("required_city_count"),
                     ",".join((cities.get("cities") or [{}])[0].get("missing") or []))))
    guard = json_file("guardian-unavailable-67.txt")
    ai_off = lines_of("ai-off-guardian-86.txt")
    ai_guardian = line_json(ai_off, "GUARDIAN")
    ai_current = line_json(ai_off, "CURRENT_AFTER")
    ai_progress = line_json(ai_off, "PROGRESS")
    ai_verdict = line_json(ai_off, "VERDICT")
    ai_ok = (
        ai_guardian.get("status") == 503
        and ai_guardian.get("error_message") == "SIMULATION_AI_DISABLED"
        and ai_current.get("sequence_unchanged") is True
        and ai_current.get("run_status") == "PAUSED_FOR_GUARDIAN"
        and ai_progress.get("guardian_runs") == 0
        and ai_progress.get("ai_enabled") is False
        and "AI_DISABLED" in (ai_progress.get("missing") or [])
        and ai_verdict.get("ai_switch_stops_guardian") is True
    )
    rows.append(("守护 AI 开关（隔离副本）",
                 "绿" if ai_ok else "红",
                 "ai-off-guardian-86.txt, trial/human_walk/_ai_off_guardian_r1.py",
                 "guardian http=%s，elapsed_s=%s，%s；sequence_unchanged=%s；guardian_runs=%s；missing=%s" % (
                     ai_guardian.get("status"), ai_guardian.get("elapsed_s"),
                     ai_guardian.get("error_message"), ai_current.get("sequence_unchanged"),
                     ai_progress.get("guardian_runs"), ai_progress.get("missing"))))
    plan92 = lines_of("guardian-plan-applied-92.txt")
    plan92_after = line_json(plan92, "PLAN_AFTER_NEXT") or []
    plan92_titles = [item.get("title") for item in plan92_after]
    plan92_screen = line_json(plan92, "SCREEN_AFTER_NEXT")
    plan92_run = line_json(plan92, "AFTER_NEXT")
    rows.append(("接受调整后模拟换计划（r92）",
                 "绿" if plan92_run.get("status") == "SIMULATED_COMPLETED"
                 and bool(plan92_titles)
                 and "故宫" not in plan92_titles
                 and "天坛公园" in plan92_titles
                 and "ERRORS []" in plan92 else "红",
                 "guardian-plan-applied-92.txt, classroom-plan-applied-92.png",
                 "%s；活动=%s；%s" % (
                     plan92_screen.get("virtual"), plan92_titles,
                     plan92_screen.get("history")[-120:] if plan92_screen.get("history") else "")))
    plan93 = lines_of("guardian-plan-applied-tablet-93.txt")
    plan93_after = line_json(plan93, "PLAN_AFTER_NEXT") or []
    plan93_titles = [item.get("title") for item in plan93_after]
    plan93_run = line_json(plan93, "AFTER_NEXT")
    plan93_screen = line_json(plan93, "SCREEN_AFTER_NEXT")
    rows.append(("平板整链：入口→守护→接受→完成（1024×768）",
                 "绿" if plan93_run.get("status") == "SIMULATED_COMPLETED"
                 and bool(plan93_titles)
                 and "故宫" not in plan93_titles
                 and "天坛公园" in plan93_titles
                 and "ERRORS []" in plan93 else "红",
                 "guardian-plan-applied-tablet-93.txt, classroom-plan-applied-tablet-93.png",
                 "%s；%s；活动=%s" % (
                     find(plan93, "ELAPSED_S"), plan93_screen.get("virtual"), plan93_titles)))
    plan97 = lines_of("guardian-plan-applied-projector-97.txt")
    plan97_after = line_json(plan97, "PLAN_AFTER_NEXT") or []
    plan97_titles = [item.get("title") for item in plan97_after]
    plan97_run = line_json(plan97, "AFTER_NEXT")
    plan97_screen = line_json(plan97, "SCREEN_AFTER_NEXT")
    rows.append(("投影整链：入口→守护→接受→完成（1280×900）",
                 "绿" if plan97_run.get("status") == "SIMULATED_COMPLETED"
                 and bool(plan97_titles)
                 and "故宫" not in plan97_titles
                 and "天坛公园" in plan97_titles
                 and "ERRORS []" in plan97 else "红",
                 "guardian-plan-applied-projector-97.txt, classroom-plan-applied-projector-97.png",
                 "%s；%s；活动=%s" % (
                     find(plan97, "ELAPSED_S"), plan97_screen.get("virtual"), plan97_titles)))
    panel90 = line_json(lines_of("guardian-panel-live-90.txt"), "PANEL_SCREEN")
    panel91_lines = lines_of("guardian-panel-live-91.txt")
    panel91 = line_json(panel91_lines, "PANEL_SCREEN")
    rows.append(("守护屏当前事件提案（r91）",
                 "绿" if "Agent 生成" in (panel91.get("origin") or "")
                 and "ERRORS []" in panel91_lines else "红",
                 "guardian-panel-live-90.txt, guardian-panel-live-91.txt, guardian-panel-live-91-panel.png",
                 "r90 origin=%s；r91 origin=%s；proposal=%s" % (
                     panel90.get("origin"), panel91.get("origin"), panel91.get("proposal"))))
    accept = json_file("proposal-accept-68.txt")
    note70 = lines_of("acceptance-note-70.txt")
    g_progress = guard.get("progress") or {}
    g_runs = g_progress.get("guardian_runs") or []
    flow83 = lines_of("guardian-accept-flow-83.txt")
    flow83_ok = any("pending=RESOLVED" in line for line in flow83) \
        and '"status":"RUNNING"' in find(flow83, "AFTER_RESUME_PROGRESS") \
        and "ERRORS []" in flow83
    rows.append(("守护暂停（历史缺陷，#54 已修）",
                 "历史红·已修" if (guard.get("guardian") or {}).get("http") == 200
                 and (guard.get("after") or {}).get("status") == "PAUSED_FOR_ACCEPTANCE"
                 and flow83_ok else "待核",
                 "guardian-unavailable-67.txt, guardian-accept-flow-83.txt, 20261025_GUARDIAN_AI_SWITCH_REPORT.md",
                 "旧读数：guardian http=%s，after=%s；修复后：%s" % (
                     (guard.get("guardian") or {}).get("http"),
                     (guard.get("after") or {}).get("status"),
                     find(flow83, "AFTER_RESUME"))))
    rows.append(("AI 开关不拦调用（历史缺陷，#54 已修）",
                 "历史红·已修" if guard.get("ai_enabled") is False and g_runs and ai_ok else "待核",
                 "guardian-unavailable-67.txt, ai-off-guardian-86.txt",
                 "旧读数：ai_enabled=%s，guardian_runs=%s；修复后：guardian http=%s，elapsed_s=%s" % (
                     guard.get("ai_enabled"), len(g_runs),
                     ai_guardian.get("status"), ai_guardian.get("elapsed_s"))))
    before_plan = ((accept.get("journey") or {}).get("before") or {}).get("plan")
    after_plan = ((accept.get("journey") or {}).get("after") or {}).get("plan")
    rows.append(("接受调整支线",
                 "绿" if (accept.get("accept") or {}).get("http") == 200 and before_plan != after_plan else "红",
                 "proposal-accept-68.txt",
                 "accept http=%s；plan %s → %s" % (
                     (accept.get("accept") or {}).get("http"), before_plan, after_plan)))
    resume = json_file("resume-after-resolved-69.txt")
    rows.append(("resume 门（夹具）",
                 "绿" if (resume.get("resume") or {}).get("http") == 200
                 and (resume.get("after") or {}).get("status") == "RUNNING" else "红",
                 "resume-after-resolved-69.txt",
                 "resume http=%s，after=%s（事件先在副本里 RESOLVED，%s 行）" % (
                     (resume.get("resume") or {}).get("http"),
                     (resume.get("after") or {}).get("status"),
                     resume.get("resolved_rows"))))
    tablet2 = lines_of("tablet-two-day-72.txt")
    tablet2_merge = lines_of("clock-two-day-tablet-merge54-85.txt")
    rows.append(("平板视口两日（合入 PR #54 后，1024×768）",
                 "绿" if "模拟行程已完成" in find(tablet2_merge, "FINAL")
                 and "ERRORS []" in tablet2_merge else "红",
                 "clock-two-day-tablet-merge54-85.txt, classroom-two-day-tablet-merge54-85.png",
                 "%s；%s；%s" % (
                     find(tablet2_merge, "START"), find(tablet2_merge, "FINAL"),
                     png("classroom-two-day-tablet-merge54-85.png"))))
    rows.append(("平板视口两日（1024×768）",
                 "绿" if "模拟行程已完成" in find(tablet2, "FINAL") else "红",
                 "tablet-two-day-72.txt, classroom-tablet-two-day-72.png",
                 "%s；%s" % (find(tablet2, "FINAL"), png("classroom-tablet-two-day-72.png"))))
    hit = lines_of("tablet-hit-73.txt")
    hit_ok = all('"hit":true' in find(hit, key) for key in
                 ("rev-open-trip", "rev-clock-plus30", "rev-clock-plus60", "rev-clock-next"))
    rows.append(("平板形状四控件命中（1024×768）",
                 "绿" if hit_ok else "红",
                 "tablet-hit-73.txt, classroom-tablet-hit-73.png",
                 "四枚 hit 读数见回执；USER_VERIFIED 仍 PENDING"))
    jump_ok = all('"jump":true' in find(jump, key) and '"hitSelf":true' in find(jump, key)
                  for key in ("PHONE_BEFORE", "TABLET_BEFORE", "PROJECTOR_BEFORE")) and all(
                      '"clockTop":0' in find(jump, key)
                      for key in ("PHONE_AFTER", "TABLET_AFTER", "PROJECTOR_AFTER"))
    rows.append(("P0-4 带票入口落位与首屏跳转",
                 "绿" if jump_ok else "红",
                 "jump-clock-87.txt, classroom-jump-phone-before-87.png, classroom-jump-tablet-before-87.png, classroom-jump-projector-before-87.png",
                 "%s；%s；%s；%s；%s；%s" % (
                     find(jump, "PHONE_BEFORE"), find(jump, "PHONE_AFTER"),
                     find(jump, "TABLET_BEFORE"), find(jump, "TABLET_AFTER"),
                     find(jump, "PROJECTOR_BEFORE"), find(jump, "PROJECTOR_AFTER"))))
    rows.append(("死锁屏提示",
                 "绿" if "RESUME_BUTTONS 0" in note70 and "ACCEPTANCE_NOTE" in "".join(note70) else "红",
                 "acceptance-note-70.txt",
                 find(note70, "ACCEPTANCE_NOTE")[:90]))
    rows.append(("合入后一键核对",
                 "绿" if after.get("all_green") is True else "红",
                 "after-merge-check.txt",
                 "ENTRY_DOOR=%s，SIM_CONSOLE=%s，all_green=%s，tickets=%s" % (
                     after.get("ENTRY_DOOR"), after.get("SIM_CONSOLE"),
                     after.get("all_green"), after.get("tickets"))))
    rows.append(("P0-4 平板亲手点",
                 "PENDING" if tablet.get("VERDICT") == "NO_EXTERNAL_CLIENT" else "待核对",
                 os.path.basename(newest("tablet-evidence-*.txt")) or "MISSING",
                 "VERDICT=%s，外部请求=%s，run=%s" % (
                     tablet.get("VERDICT"),
                     (tablet.get("log") or {}).get("external_requests"),
                     (tablet.get("run") or {}).get("run"))))

    out = ["# P0 证据索引（由回执现读生成）", "",
           "生成器：`trial/human_walk/_p0_evidence_index_r1.py`；每条都从回执解析，缺文件写 MISSING。", "",
           "| 项目 | 判定 | 证据 | 关键读数 |", "|---|---|---|---|"]
    for name, verdict, evidence, reading in rows:
        out.append("| %s | %s | %s | %s |" % (name, verdict, evidence, reading.replace("|", "\\|")))
    out.append("")
    with open(OUT, "w", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(out))
    print("\n".join(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
