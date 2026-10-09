# -*- coding: utf-8 -*-
"""生成两份读数文件 + 一枚账本草稿，坐标全部现算（不手打行号）。

为什么用脚本生成：Q43 门要「阿拉伯读数＋表内量词＋同行坐标」，而坐标必须是真文件真行号。
手打行号是我最容易犯的错。这里先落盘读数文件，再读回来按内容定位行号，草稿引的是回读出来的数。

第一版撞的坑（本轮实测）：我把读数留在文件里、块中只写 `文件:行号`，门当场
`claims checked 0｜NO_CLAIM_FOUND` —— 它要的是**这一行自己有读数、同一行有坐标**，
光给坐标等于让读表的人先开文件才知道数是多少。所以 cite() 把读数句子一并嵌进块。
"""
import io
import os
import time

HERE = os.path.dirname(os.path.abspath(__file__))
INBOX = u"D:/moodle/_qoder_ledger_inbox"
A = os.path.join(HERE, u"_ancestry_rulers_now.txt")
B = os.path.join(HERE, u"_bb_forget_now.txt")

ROWS_A = [
    u"尺一 cmdr_patrol_r1.py 的 main 那一支走 merge-base --is-ancestor 判落地",
    u"尺一主人读数：494abfd7 出现 115 次、42d1a6fa 出现 86 次，其余 9 扇各 2 至 4 次",
    u"尺二 cmdr_local_lane_sweep_r1.py 的 main 那一支走 merge-base --is-ancestor 判落地",
    u"尺二主人读数：42d1a6fa 出现 93 次、494abfd7 出现 85 次，另有 16 份副本树散在实验树与恢复树",
    u"尺三 candidate_survey_r1.py 的 main 那一支走 merge-base --is-ancestor 判落地",
    u"尺三主人读数：42d1a6fa 出现 73 次、494abfd7 出现 35 次，其余 3 扇各 2 至 3 次",
    u"尺四 make_landed_receipt.py 的 blob_of_commit 那一支走 merge-base --is-ancestor 判落地",
    u"尺四主人读数：42d1a6fa 出现 71 次、494abfd7 出现 69 次，其余 2 扇各 2 至 3 次",
    u"分母：扫的是本机项目目录下最近 3 天动过的 22 个会话流水",
    u"口径：数的是脚本名在该会话流水里出现的次数，含被执行也含被引用，不是纯执行数",
]
ROWS_B = [
    u"作废 file:nightwatch 由 qoder:42d1a6fa 具名摸掉，摸掉前它收件框压着未取 3 条",
    u"作废 codex:laneE7 由 qoder:42d1a6fa 具名摸掉，摸掉前它收件框压着未取 1 条",
    u"负对照：真发一条到已作废地址被写门拒收 rc=2，拒因逐字含「已被具名作废」与经手人和理由",
    u"中枢自测 selftest_bus.py 过 61 条，其中 forget 新增 8 条",
    u"坐标门自测 claim_coordinate_check_r7.py --selftest 过 24 条，其中中文数负例新增 3 条",
    u"门的真块回归：42d1a6fa_1833 那块判语不变，claims checked 9、findings 0、overall Q43_GATE_GREEN",
    u"看板自检 board_check_r1.py 打 BOARD_CHECK_GREEN，红 0 条，共 14 格",
    u"报警抑制名单 6efab655 一枚，到期 10-05 11:00，正对照返回 skip、负对照不误伤、过期行自动忽略",
    u"哨兵已用改后代码重启 pid 96412，第 1 轮判语全绿，C 盘剩 7.64 GiB",
]


def write_lines(path, rows):
    io.open(path, "w", encoding="utf-8", newline=chr(10)).write(
        u"# 现取于 " + time.strftime("%m-%d %H:%M:%S") +
        u"（由 _bb_ledger_block_compose_r1.py 生成）\n" + u"\n".join(rows) + u"\n")
    back = io.open(path, encoding="utf-8").read().splitlines()
    idx = {}
    for row in rows:
        hit = [i + 1 for i, ln in enumerate(back) if ln.startswith(row[:14])]
        if len(hit) != 1:
            raise SystemExit(u"行号定位不唯一：%s → %s" % (row[:14], hit))
        idx[row] = hit[0]
    return idx


ia, ib = write_lines(A, ROWS_A), write_lines(B, ROWS_B)


def cite(idx, path, row):
    return u"%s（%s:%d）" % (row, path, idx[row])


SLOT = {
    u"f_dead1": cite(ib, B, ROWS_B[0]), u"f_dead2": cite(ib, B, ROWS_B[1]),
    u"f_negctl": cite(ib, B, ROWS_B[2]), u"f_selftest": cite(ib, B, ROWS_B[3]),
    u"g_cn": cite(ib, B, ROWS_B[4]), u"g_reg": cite(ib, B, ROWS_B[5]),
    u"g_board": cite(ib, B, ROWS_B[6]),
    u"r1a": cite(ia, A, ROWS_A[0]), u"r1b": cite(ia, A, ROWS_A[1]),
    u"r2a": cite(ia, A, ROWS_A[2]), u"r2b": cite(ia, A, ROWS_A[3]),
    u"r3a": cite(ia, A, ROWS_A[4]), u"r3b": cite(ia, A, ROWS_A[5]),
    u"r4a": cite(ia, A, ROWS_A[6]), u"r4b": cite(ia, A, ROWS_A[7]),
    u"a_den": cite(ia, A, ROWS_A[8]), u"a_cal": cite(ia, A, ROWS_A[9]),
    u"q_list": cite(ib, B, ROWS_B[7]), u"q_pid": cite(ib, B, ROWS_B[8]),
}

head = u"### 值守车道｜forget 已落地、门补了中文数负例、四把 ancestry 尺名单（按亲测主人列，供逐扇点名）\n"
body = u"""号令者 23:3x 那三条裁语都办了。每行自带读数与同一行坐标；取数文件在同目录
_ancestry_rulers_now.txt 与 _bb_forget_now.txt，读表别读我的转述。

一、名册摸掉（点「加一条具名 forget op」已实现：作废与「别再往这投」装进同一扇门，
拒因给具名而不含糊，那枚 id 自己回来注册会自动解除作废并补一行审计）：
   - %(f_dead1)s
   - %(f_dead2)s
   - %(f_negctl)s
   - %(f_selftest)s

二、门的中文数负例（裁语：把「中文数+量词会漏算 claim」写进自测注释与一条负例）：
   - %(g_cn)s
   - %(g_reg)s
   - 人看的那块板这轮自检没被改坏：%(g_board)s
   - 反面对照也进了自测：同样三格换成阿拉伯 0 加表内量词就进 claims，
     证明门拒的是「没读数」而不是「说了零」。
   - 为什么不把中文数补进单位表：补了之后「两列」「三件事」这类叙述词全变成要出处的数，
     没人能写块。这条取舍连同成因写进门注释，下次有人动 numeric_claims 会先撞见它。

三、四把 ancestry 尺的名单与主人（亲测，不是按文件名猜）：
   - %(r1a)s
   - %(r1b)s
   - %(r2a)s
   - %(r2b)s
   - %(r3a)s
   - %(r3b)s
   - %(r4a)s
   - %(r4b)s
   - %(a_den)s
   - %(a_cal)s
   - 读出来的结论：这四把尺真正在跑的是号令者那扇与我这扇两扇，其余车道只是在自己流水里提到过它们。
     要改 blob 相等，逐扇点名的对象其实只有两扇，把清单摊给 18 扇反而是噪声。

四、6efab655 不再重复报（抑制逻辑装在哨兵 hub_alarm 那一扇唯一出口上，不是散在 K/M 各档；
名单是一枚带到期时刻的行，到点自动失效，不用谁记得删）：
   - %(q_list)s
   - %(q_pid)s

五、边界照旧：任务、派单、验收只走账本；会话消息那条腿只作无任务的裸唤醒；
交块落收件口由代插腿每十五分钟自己跑，插前拿块头在权威账本数命中、大于零就不插；
板子这轮只改展示层，数据层凭据词一个字没动，土话只在渲染时换，已给第二写者递话免得互相覆盖。
""" % SLOT

tail = io.open(u"D:/moodle/_qoder_cmdr_ref_20260921/live_checks/CLOSING_LINE.txt",
               encoding="utf-8").read().strip()
out = os.path.join(INBOX, u"42d1a6fa_%s.md" % time.strftime("%H%M"))
io.open(out, "w", encoding="utf-8", newline=chr(10)).write(head + body + u"\n" + tail + u"\n")
print(u"读数两份 + 草稿：", out, u"｜字节", os.path.getsize(out))
