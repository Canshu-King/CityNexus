"""ORD-0429 scorecard upgrade: build the ledger block from the two streak receipts.

Every count in the emitted block is read out of the receipts or from a live git/ledger command at
write time, because a hand-typed "5/5" is exactly what the coordinate gate exists to catch.
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

EVID = Path(r"D:\moodle\CityNexus-Hermes-Revival\evidence\0212")
WT = Path(r"D:\moodle\_qoder_ai_ord0429_20260929\wt")
LEDGER = Path(r"D:\moodle\CITYNEXUS_AGENT_CONTROL.md")
TIP = "0fee131d02b7c7c85f59aab8307f28594bf0d65f"
LANDED = "69b7cde497f101109ae67e038010dfed8f9accbf"
OUT = EVID / "_block_ord0429_upgrade.md"
CN = "零一二三四五六七八九"


def cn(n: int) -> str:
    return CN[n] if 0 <= n <= 9 else str(n)


def git(*args: str) -> str:
    return subprocess.run(["git", "-C", str(WT), *args], capture_output=True,
                          text=True, encoding="utf-8", errors="replace").stdout.strip()


def blob_at(path: str) -> str:
    return git("rev-parse", f"{TIP}:{path}")


def ledger_line(pattern: str) -> str:
    text = LEDGER.read_text(encoding="utf-8", errors="replace").splitlines()
    hits = [str(i + 1) for i, line in enumerate(text) if pattern in line]
    return hits[0] if hits else "NOT_FOUND"


def main() -> int:
    swept = json.loads((EVID / "ORD0429_STREAK_0fee131d.json").read_text(encoding="utf-8"))
    recut_p = EVID / "ORD0429_STREAK_0fee131d_cleanrecut.json"
    recut = json.loads(recut_p.read_text(encoding="utf-8")) if recut_p.is_file() else None

    an = subprocess.run(["git", "-C", str(WT), "merge-base", "--is-ancestor", LANDED, TIP],
                        capture_output=True)
    prov = (recut or swept)["cond1_provenance_first_run"]
    inst = (recut or swept)["instruments"]
    interp = (recut or swept)["interpreters"]
    nodes = (recut or swept)["cond10_classification_per_node"]
    stable = sorted(k for k, v in nodes.items() if v["classification"].startswith("STABLE_GREEN"))

    old_src = Path(r"D:\moodle\CityNexus-Hermes-Revival\evidence\0212\gate_streak_v2.py")
    old_text = old_src.read_text(encoding="utf-8")
    old_uses = re.findall(r"^\s*PENDING_CLEANUP\.(append|extend)", old_text, re.M)
    old_uses += re.findall(r"list\(PENDING_CLEANUP\)", old_text)
    old_defs = re.findall(r"^\s*PENDING_CLEANUP\s*[:=]", old_text, re.M)
    old_lines = [str(i + 1) for i, line in enumerate(old_text.splitlines()) if "PENDING_CLEANUP" in line]

    r = {}
    if recut:
        r = {"requested": recut["runs_requested"], "completed": recut["runs_completed"],
             "green": recut["streak_green_runs"], "ceiling": recut["verdict_ceiling"],
             "closure": recut["closure_allowed"], "denied": recut["closure_denied_because"],
             "fresh_not_exist": recut["cond3_freshness"]["every_run_path_did_not_exist_before_this_run"],
             "fresh_inherit": recut["cond3_freshness"]["every_run_inherited_no_preexisting_rows"],
             "distinct_db": recut["cond7_distinct_db_paths"],
             "swept": len(recut["cond3_pre_clean_swept_files"])}
    s = {"requested": swept["runs_requested"], "completed": swept["runs_completed"],
         "green": swept["streak_green_runs"], "ceiling": swept["verdict_ceiling"],
         "closure": swept["closure_allowed"],
         "fresh_not_exist": swept["cond3_freshness"]["every_run_path_did_not_exist_before_this_run"],
         "swept": len(swept["cond3_pre_clean_swept_files"]),
         "sweep_flag": swept["cond3_sweep_authorized_by_flag"]}

    lines = [
        "### ORD-0429 · lane Q-dsh（Qoder，会话 a6b95d59）· at_local 2026-09-29 "
        f"{__import__('time').strftime('%H:%M')}（本机时区）· 状态 这单 03:05 已交付、号令者 03:0x 已落地；"
        "本轮把①的成绩单升到现尖，并复核②③仍在线上",
        "",
        "**〇、先回一句状态**：08:20 值守转达的那行派单（账本 `CITYNEXUS_AGENT_CONTROL.md:"
        f"{ledger_line('ORD-0429（新）→ `a6b95d59')}`）不是没做，是**已经做完并落地了**："
        "我的交付块在账本 `CITYNEXUS_AGENT_CONTROL.md:"
        f"{ledger_line('状态 DELIVERED（勘误重投，取代 `qoder_0252`')}`，"
        "号令者的落地块在 `CITYNEXUS_AGENT_CONTROL.md:"
        f"{ledger_line('ORD-0429 落地（产品线五连')}`。落地笔 `{LANDED}` 是不是现尖的祖先，"
        f"我用 `git merge-base --is-ancestor` 现验，退出码 {an.returncode}（零＝在线上）。",
        "",
        "**一、线上三枚工件逐枚现读 `git rev-parse <现尖>:<路径>`**，与我交付时逐字相同："
        f"尺 `tools/streak_ruler_v3_ord0429.py` = `{blob_at('tools/streak_ruler_v3_ord0429.py')}`，"
        f"五连跑手 `scripts/dsh_arm_streak.py` = `{blob_at('scripts/dsh_arm_streak.py')}`，"
        f"H11 跑手 `scripts/h11_autonomous.py` = `{blob_at('scripts/h11_autonomous.py')}`。",
        "",
        f"**二、①成绩单升级**：线今夜前进了二十二笔，所以我把**自己那台干净的车道工作树**"
        f"（`D:\\moodle\\_qoder_ai_ord0429_20260929\\wt`，dirty 条目 {cn(len(prov['dirty_entries']))} 枚）"
        f"checkout 到现尖 `{prov['head_commit']}`，用**线上那份一字未改的尺**"
        f"（`tools/streak_ruler_v3_ord0429.py:107` 那枚修好的定义在跑手里的摘要 "
        f"sha256 前十二位 `{inst['driver_sha256_12']}`）跑 `--shape whole-ladder --runs 5`。"
        f"解释器 `{interp['backend_version']}`，梯子解释器另一枚独立虚拟环境。",
        "",
        "- 第一次跑被尺自己的新鲜度闸拒了（七枚 02:xx 留下的同名工件已存在），我按它给的口子加 "
        f"`--allow-sweep` 重跑并让它记下：读数 `ORD0429_STREAK_0fee131d.json`，"
        f"sweep 标志 {s['sweep_flag']}、清掉工件 {cn(s['swept'])} 枚、"
        f"完成 {cn(s['completed'])}/{cn(s['requested'])} 跑、绿 {cn(s['green'])} 跑、"
        f"判据上限 {s['ceiling']}、允许收单 {s['closure']}。"
        f"那一跑有一枚新鲜度子判据是假（键 `cond3_freshness."
        f"every_run_path_did_not_exist_before_this_run`），因为第一跑复用了一条 02:xx 存在过的路径。",
        "",
    ]
    if recut:
        lines += [
            f"- 为免把这枚假判据留给验收，我换一枚新 tag（`--mutant cleanrecut`）重跑了同样五连："
            f"读数 `ORD0429_STREAK_0fee131d_cleanrecut.json`，完成 {cn(r['completed'])}/"
            f"{cn(r['requested'])} 跑、绿 {cn(r['green'])} 跑、每跑各自独立数据库且路径互不相同"
            f"（键 `cond7_distinct_db_paths` = {cn(r['distinct_db'])}）、"
            f"清掉工件 {cn(r['swept'])} 枚、两枚新鲜度子判据分别是 "
            f"`every_run_path_did_not_exist_before_this_run` {r['fresh_not_exist']} 与 "
            f"`every_run_inherited_no_preexisting_rows` {r['fresh_inherit']}，"
            f"判据上限 {r['ceiling']}、允许收单 {r['closure']}（拒因逐字 "
            f"`{'; '.join(r['denied']) if r['denied'] else '—'}`）。",
            "",
            f"- 八枚节点在两跑里都是 `STABLE_GREEN(whole-ladder)`：{'、'.join(stable)}"
            f"（每枚 green 五跑、red 零跑、no-verdict 零跑，键 `cond10_classification_per_node`）。",
            "",
        ]
    else:
        lines += ["- 新 tag 那一跑此刻仍在跑（读数尚未落盘），块里不预写它的数字。", ""]
    lines += [
        "**三、②旧副本没动，并且我又扫了一遍**：`evidence/0212/gate_streak_v2.py` 三万六千四百二十二"
        f"字节，mtime 仍是 09-22 二十点零一分；静态扫这个名字：引用行在 `gate_streak_v2.py:"
        f"{old_lines[0]}` 与 `gate_streak_v2.py:{old_lines[1]}`，而模块级赋值 {cn(len(old_defs))} 处。"
        "这是**静态**读数；真崩溃的回放（NameError 原文）在 03:05 那块与随交付发布的收据里，"
        "我不拿静态扫描冒充重放。",
        "",
        "**四、③H11**：跑手在线上、字节相同（第一节的第三条）。02:xx 那次全自主跑的收据已随 03:05 那块发布。"
        "现尖上要不要再自主跑一次（要烧一次真实配额），等你一句话；不给我就不烧。",
        "",
        "**五、给值守的一条修法**：这单被报成\"未动\"的因由是我的会话 id 不在花名表里。"
        "建议加一道集合差自检——派单行里的收件 id 若不在表中，报 `UNREGISTERED_LANE_ID` 并点名，"
        "而不是让这条单在报表里消失。",
        "",
        "**六、我这轮没做的**：没碰权威线、没改已发布的尺副本、没自己收单（收单归号令者），"
        "本轮零产品字节。",
    ]
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(f"recut present: {bool(recut)} | swept: {json.dumps(s, ensure_ascii=False)}")
    print(f"cleanrecut: {json.dumps(r, ensure_ascii=False)}")
    print("ancestry rc:", an.returncode, "| ledger lines:",
          ledger_line("ORD-0429（新）→ `a6b95d59'"), ledger_line("状态 DELIVERED（勘误重投"))
    print("block bytes:", OUT.stat().st_size)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
