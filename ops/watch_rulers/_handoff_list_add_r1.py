# -*- coding: utf-8 -*-
u"""把今晚 20:1x–20:5x 新建的脚本补进交接稿附录，并逐枚验存在。

为什么必须补：附录那份「动过的脚本清单」是给下一班的入口。20:1x 之后我又建了十几个
（末态尺、形状闸、窗名抽取、跑批起法、四道补丁、两个自测、两个反证…），
它们不在清单里 ⇒ 明早那班找不到，也就不会用。

同时做一件交接稿自己第五节要求的自证：**逐枚打开验存在**，不靠"我记得建过"。
（今晚已经栽过一次：我曾把 `_adoption_boot_check_r1.py`、`_patch_sentinel_blindretry_r1.py`
 两个从没存在过的文件名写进清单。）

边界：只往附录末尾追加；不改正文任何一节；写盘前逐枚验路径，缺一个就整批不写。
"""
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
HAND = os.path.join(HERE, "HANDOFF_20261005_NIGHT.md")
PATROL = os.path.join(HERE, "patrol")

NEW = [
    (u"patrol/_start_patrol_loop_r1.py",
     u"巡检跑批的**真 detached 起法**（`DETACHED_PROCESS` 单独给，与 `CREATE_NEW_PROCESS_GROUP` 并用会 WinError 87）"),
    (u"patrol/_patch_loop_needseyes_r1.py",
     u"跑批主循环接上「判红＋写待看档」（用行号定位，绕开锚匹配的老毛病）"),
    (u"patrol/_patch_judge_numcmp_r2.py",
     u"`judge()` 改抽数字比较：圈号**按序号推码位**（U+2460＋n-1），不靠空格"),
    (u"patrol/_patrol_loop_needseyes_selftest_r1.py",
     u"待看判据六臂自测（真档绿｜结论变红｜该敲非零红｜栈塌红｜空文本红｜去重）"),
    (u"patrol/_verify_sentinel_red_r1.py",
     u"哨兵红因的流水核实（四扇逐条读末态；踩出「脚手架节点每分钟刷新」与「timestamp 三形制」）"),
    (u"patrol/_lane_tailform_r1.py",
     u"**末态尺**：读一扇的末三条对话节点，判「在写／交活型停着／断在半路」；`to_epoch()` 认三种时间戳形状"),
    (u"patrol/_knock_gate_shape_r1.py",
     u"**形状闸**：静默过档 **且** 末态判「断在半路」才算真该敲；交活型不列；读不到判词归不可判"),
    (u"patrol/_knock_gate_shape_selftest_r1.py",
     u"形状闸四臂自测（断在半路→真该敲｜交活型→不列｜两态分开｜判词读不到→不可判）"),
    (u"patrol/_patch_patrol_shape_gate_r1.py",
     u"把形状闸接进巡逻第②格（只动那一处分支，其余格一行不碰）"),
    (u"patrol/_patch_patrol_conclude_undec_r1.py",
     u"②b 不可判并进结论行（否则不可判会被读成「全队都在动」——单向致盲）"),
    (u"patrol/_conclude_undec_selftest_r1.py",
     u"结论行三臂自测（零过档⇒全队都在动｜交活型⇒没人该敲｜判词读不到⇒不可判不算绿）"),
    (u"patrol/_patrol_shape_gate_liveproof_r1.py",
     u"形状闸**现网反证**（同三扇同读数：旧判据列 2 扇该敲、新判据列 0 扇）；每次跑都打印「未覆盖哪一臂」"),
    (u"patrol/_recount_decision_tbl_r1.py",
     u"重算 DECISION_1006 那三行，并**把三种「读过没有」的口径分开列**（送达／有回执／零回执）"),
    (u"patrol/_codex_window_id_r1.py",
     u"**Codex 窗名指纹**：从 thread_items 头十几条里抽自报名（库里没有标题列，身份在正文里）"),
    (u"patrol/_patch_patrol_codex_name_r1.py",
     u"第⑦格接窗名（附属读数，起不来不拖整格）"),
    (u"patrol/_patch_patrol_gap_by_name_r1.py",
     u"推广缺口改**按窗名**判（一枚已接＋一枚未接＝数都是 1，减出来 0 是假零）"),
    (u"patrol/_patch_drop_numgap_r1.py",
     u"删掉与窗名判据自相矛盾的那行数差（两个互相抵消的错谓词比一个更危险）"),
    (u"patrol/_patch_invite_winR_r1.py",
     u"接入件更新：把「两侧对不上、不猜」换成真抽到的窗名"),
    (u"patrol/_patch_invite_winR2_r1.py",
     u"接入件收口：「两扇」改「那一扇」、join 示例填实 `codex:winR`、补 `--kind`"),
    (u"patrol/_patch_cell8_byseg_r1.py",
     u"第⑧格改按 `｜` 切段整段打印（原来按 120 字硬砍，砍掉了第三扇与段尾那半句「红」）"),
    (u"patrol/_verify_cell8_backlog_r1.py",
     u"核实第⑧格「已送未拆」虚高多少（车道侧 161 枚 vs 第⑧格报的 163 条 ⇒ 它本来就只统计车道侧）"),
    (u"patrol/_patch_wait_not_red2_r1.py",
     u"待看档：等单**不占红位**（结论行与③格两处一起改；只改一处等于白改）"),
    (u"patrol/_patch_j_cause_r1.py",
     u"哨兵 J 档成因改**从分类器原文取**（手写那句会在分类器只判「卡闸」时凭空造出「断在半路」）"),
    (u"patrol/_write_j_erratum_r1.py",
     u"把 20:35 那次 J 档假红的三条并排读数写进 HIT 档留痕"),
    (u"patrol/_patch_stack_add_patrolloop_r1.py",
     u"把巡检跑批挂进值守栈 COMPONENTS（工具手起只活一拍；栈腿由栈起、归属不同）"),
    (u"patrol/_patch_staleness_add_patrolloop_r1.py",
     u"陈旧度尺认得 patrol_loop 三处（LEGS／STOP_ENV／STOP_DEFAULT）——不在尺里的腿等于脱管"),
    (u"patrol/_patch_drop_numgap_r1.py", u"见上"),
    (u"patrol/_start_patrol_loop_r1.py", u"见上"),
    (u"patrol/_lane_round_len_census_r1.py", u"一轮时长分布与形态分类（早先落，列此备查）"),
    (u"patrol/stack_boot_restart.bat", u"开机起复兜底件（纯 ASCII、CRLF；幂等，重复跑不起第二支）"),
]


def main():
    miss = []
    seen = set()
    for rel, _why in NEW:
        if rel in seen:
            continue
        seen.add(rel)
        if not os.path.exists(os.path.join(HERE, rel.replace("/", os.sep))):
            miss.append(rel)
    if miss:
        print(u"REFUSE：这些路径不存在，整批不写：%s" % miss)
        return 1

    t = io.open(HAND, encoding="utf-8", newline="").read()
    have = set(re.findall(r"^- `(patrol/[^`]+)`", t, re.M))
    add = []
    n = 0
    for rel, why in NEW:
        if rel in have or rel in add:
            continue
        n += 1
        add.append(u"- `%s` → %s" % (rel, why))
    if not add:
        print(u"已在 ⇒ 不重复补（清单里现有 %d 条）" % len(have))
        return 0

    lines = t.rstrip("\n").split("\n")
    lines.append(u"")
    lines.append(u"**20:1x–20:5x 这一段新增（上接上表，%d 条）：**" % n)
    lines.extend(add)
    new = "\n".join(lines) + "\n"

    heads = re.findall(r"^## .+$", new, re.M)
    if any(h.startswith(u"## ##") for h in heads):
        print(u"REFUSE：标题粘连，未写盘")
        return 1
    bak = HAND + u".bak_list_2050"
    if not os.path.exists(bak):
        io.open(bak, "w", encoding="utf-8", newline="").write(t)
    io.open(HAND, "w", encoding="utf-8", newline="").write(new)
    print(u"已补 %d 条；清单现有 %d 条；全部路径逐枚验过存在"
          % (n, len(re.findall(r"^- `(patrol/[^`]+)`", new, re.M))))
    return 0


if __name__ == "__main__":
    sys.exit(main())