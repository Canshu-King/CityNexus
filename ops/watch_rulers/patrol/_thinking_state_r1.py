# -*- coding: utf-8 -*-
u"""「思考状态」尺：读 Codex 侧 `thread_items` 的 `reasoning` 新鲜度，判断后台在不在思考。

**为什么要有它**（22:33 主人问的）：前端 UI 上那枚转动的思考状态，后台**看得见**——
它是 `~/.codex/thread_history_1.sqlite` 的 `thread_items` 里 `item_type='reasoning'` 的行，
每枚带 `created_at_ms`。所以"在工作的我能看见转圈、在偷懒的没转"是可以后台判的。

**但判据是「新鲜度」，不是「有没有」**（22:33 实测出来的关键）：
  · `01a10cd0` 在跑：末轮 20 分前，reasoning **1 分前**、commandExecution 2 分前、fileChange 1 分前；
  · `01a0fd19` **末轮 438 分前**，可 reasoning **0 分前**、mcpToolCall 2 分前
    ⇒ 它**没在跑新轮次，却在后台思考**。只看"末轮多久前"会把它判成停摆，**判错**。
  · 停着的那几枚（1816／2626／2630 分前）：reasoning 与其它类型**一起旧**，
    最新的一枚 reasoning 也有 1816 分 ⇒ 那才是真静。

**一个陷阱（我今晚栽过）**：`thread_items` 末尾会混入 `active-leaf`／`runtime-config` 一类
**脚手架节点**，它们**每分钟被工具刷新**——只看"文件 mtime"或"最后一行是什么"会把
停着的车读成"一直��动"。所以本尺**只看 reasoning／commandExecution／mcpToolCall／
fileChange 这四类真干活节点**的**各自最新时刻**，不碰脚手架节点。

用法：python _thinking_state_r1.py            # 近 6 小时的 thread 全列
      python _thinking_state_r1.py <id8>…    # 只看指定的
输出每枚：末轮(分前)｜reasoning(分前)｜干活四类里最新(分前)｜判语

判语三档（阈值按 22:33 现读分布定的，写在下面，改前先量分布）：
  在思考   干活四类最新 ≤ 8 分（哪怕末轮很久前——它在后台想）
  刚停     8 分 < 最新 ≤ 60 分
  真静     最新 > 60 分  ⇒ **交活型停着还是停摆，仍要读末态形状**（末态尺管那个）
"""
import os
import sqlite3
import sys
import time

DB = os.path.expanduser(u"~/.codex/thread_history_1.sqlite")
WORK = ("reasoning", "commandExecution", "mcpToolCall", "fileChange", "agentMessage")
SCAFFOLD = ("active-leaf", "runtime-config", "file-history-snapshot", "workspace-directories")
WINDOW_MIN = 360.0
FRESH_MIN = 8.0
COLD_MIN = 60.0


def rows_of(con, tid, limit=120):
    out = {}
    for it, ms in con.execute(
            "select item_type, created_at_ms from thread_items where thread_id=?"
            " order by rollout_ordinal desc limit ?", (tid, limit)):
        if it in SCAFFOLD:            # 脚手架节点：不参与判断（它们每分钟被刷新）
            continue
        if it not in out:
            out[it] = ms
    return out


def main():
    if not os.path.isfile(DB):
        print(u"REFUSE：%s 不在" % DB)
        return 1
    con = sqlite3.connect(u"file:%s?mode=ro" % DB, uri=True, timeout=8)
    now = time.time()
    try:
        if len(sys.argv) > 1:
            # 给的可能是 8 位短码，要展开成全 id（22:33 第一版直接拿短码去查，全落空）
            tids = []
            for a in sys.argv[1:]:
                hit = con.execute("select distinct thread_id from thread_turns where thread_id like ?",
                                   (a + "%",)).fetchall()
                tids.extend([h[0] for h in hit] or [a])
        else:
            cut = now - WINDOW_MIN * 60
            tids = [r[0] for r in con.execute(
                "select distinct thread_id from thread_turns"
                " where coalesce(completed_at,started_at) >= ?", (cut,))]
        if not tids:
            print(u"近 %d 分钟没有活跃 thread" % int(WINDOW_MIN))
            return 0
        print(u"现读 %s｜窗口 %d 分｜thread %d 枚｜只认干活四类（reasoning/commandExecution/mcpToolCall/fileChange）"
              % (time.strftime("%H:%M:%S"), int(WINDOW_MIN), len(tids)))
        print(u"%-10s %9s %11s %11s  %s" % (u"thread", u"末轮(分)", u"reasoning", u"干活最新", u"判语"))
        for tid in tids:
            m = con.execute("select max(coalesce(completed_at,started_at)) from thread_turns"
                            " where thread_id=?", (tid,)).fetchone()[0] or now
            d = rows_of(con, tid)
            rea = (now - d["reasoning"] / 1000.0) / 60.0 if d.get("reasoning") else None
            ages = [(k, (now - v / 1000.0) / 60.0) for k, v in d.items() if k in WORK]
            newest = min(a for _k, a in ages) if ages else None
            if newest is None:
                verdict = u"**读不到干活节点**（不可判，不当绿）"
            elif newest <= FRESH_MIN:
                verdict = u"在思考（末轮 %.0f 分前也不妨碍——它在后台想）" % ((now - m) / 60.0) \
                    if (now - m) / 60.0 > FRESH_MIN else u"在干活"
            elif newest <= COLD_MIN:
                verdict = u"刚停（≤ %d 分），**是否停摆仍要读末态形状**" % int(COLD_MIN)
            else:
                verdict = u"真静（最新 %.0f 分前）⇒ 交活型还是停摆，读末态尺" % newest
            print(u"%-10s %9.0f %11s %11s  %s" % (
                tid[:8], (now - m) / 60.0,
                u"%.0f 分前" % rea if rea is not None else u"无",
                u"%.0f 分前" % newest if newest is not None else u"无",
                verdict))
        print()
        print(u"边界：只读 sqlite（mode=ro）；0 次写入、0 次发消息、0 次敲门。")
        print(u"提醒：真静只说明\\u300c它没在动\\u300d，**不等于偷懒**——末态形状（交活型停着 vs 断在半路）由 `_lane_tailform_r1.py` 判。")
        return 0
    finally:
        con.close()


if __name__ == "__main__":
    sys.exit(main())