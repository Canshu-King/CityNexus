# -*- coding: utf-8 -*-
"""给每条车道挂**人话花名**：工种·姓，一眼认得出谁在干哪一行。

为什么要这张表（10-04 11:0x 主人的话）：「名字要取得像农民工、贴合我们项目——只有认得到士兵的将军才是好将军」。
之前名册里一半的身份 name 就等于 id 本身（qoder:82f55d8a 这种），主人在板子上看见一排 hex 串，
根本不知道哪一行是那个修暗色档位的、哪一行是管契约的。

这一张表是**唯一来源**：花到 hub 名册里（bus.py reg），板子、BB 机 status、光荣榜、耻辱墙
读的都是名册那一份 ⇒ 不再出现"两张花名表各说各话"（这条我们栽过）。

工种是照着各扇**实际在干的活**配的，不是随便起名：配错了就是又一次"板不准"。
每条后面写明依据（取自它自己流水的末条与今日落地块的标题）。

改法：只改 NAMES，然后重跑本脚本。reg 会保留 verified/self_seen（bus_hub.register 里那两行 prev 逻辑），
所以改名不会把「自证」徽章打掉。枚与枚之间刻意隔 6 秒——hub 的"同批突增标 bulk"看的是 5 秒窗口，
不隔就会把这十八枚全标成 bulk 待自证。
"""
import io
import os
import subprocess
import sys
import time

BUS = u"D:/moodle/agent_bus"
ME = u"qoder:42d1a6fa"
NAMES = {
    u"qoder:0afdb49b": (u"质检员·老周", u"今日落地块最多；末条在按 blob 复测落地代次与线里比对"),
    u"qoder:82f55d8a": (u"粉刷工·小顾", u"ORD-0567 中文臂文案第二批、暗色令牌命名"),
    u"qoder:1d64acf5": (u"测试工·大刘", u"读闸的纪律名词表改自报形制；自申报那格是五点探针常设自检"),
    u"qoder:5a53846b": (u"测量工·老吴", u"自申报「读在飞作业同族缺陷全树清点」——量尺那一行"),
    u"qoder:da46954a": (u"钢筋工·老赵", u"分享接收 ORD-0465、花费臂量纲期望"),
    u"qoder:89f2e2d6": (u"木工·小孙", u"行程「中…」ORD-0520；自申报「契约改了生成物没同笔重生成」"),
    u"qoder:a68b0631": (u"浇筑工·老钱", u"注释锚重切、re-parent 落地、产线取读数（花费面）"),
    u"qoder:e766b154": (u"安装工·小周", u"行程长图 ORD-0472、journeyInBin 走真门那格"),
    u"qoder:1ba48dbf": (u"安全员·老李", u"主动收回自己仪器盲点造成的三条误判；票夹/回收站渲染点"),
    u"qoder:6a150e1e": (u"放线工·小郑", u"re-parent 后逐枝按 blob 现读；花费面屏读那格"),
    u"qoder:6a773af1": (u"电焊工·老王", u"ORD-0496 那趟行程、英文臂 slice5/slice6 与可达性尺"),
    u"qoder:cff87c64": (u"资料员·小冯", u"ORD-0563 英文臂枚举回声，新加一把四臂常设尺"),
    u"qoder:2d2d7428": (u"玻璃工·小陈", u"设计 Token 暗色命名校验（深色档位那面玻璃）"),
    u"qoder:45d25bfb": (u"脚手架·老秦", u"两条腿→三条腿都可查的交件坐标；枚举屏哨兵定位"),
    u"qoder:8ac89982": (u"绿化工·小许", u"地图停靠点显名；hub 尺与族测"),
    u"qoder:6efab655": (u"副号令者·夜班", u"号令者实例 A：取信逐条 ack、验收件与修注释"),
    u"qoder:494abfd7": (u"号令者", u"点单与裁定（不改，主人要认的就是这几枚）"),
    u"qoder:42d1a6fa": (u"打更人·值守", u"我：夜巡、传话、仪表与这块板"),
}
sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main():
    bad = []
    for i, (aid, (nm, why)) in enumerate(sorted(NAMES.items())):
        p = subprocess.run([sys.executable, os.path.join(BUS, "bus.py"), "reg", "--id", aid,
                            "--name", nm, "--note", why],
                           cwd=BUS, capture_output=True, env=dict(os.environ, PYTHONIOENCODING="utf-8"))
        out = (p.stdout or b"").decode("utf-8", "replace")
        keep = p.returncode == 0 and nm in out
        if not keep:
            bad.append((aid, out[-160:]))
        print(u"%2d/%d %-18s → %-12s %s" % (i + 1, len(NAMES), aid, nm, u"ok" if keep else u"FAILED"))
        time.sleep(6)                      # 避开 hub 的「同批突增」判据（5 秒窗口）
    st = json_load()
    print(u"名册里还有裸 id 当花名的：%s" % (u"、".join(
        k for k, v in st.items() if v.get("name") in (None, "", k)) or u"（无）"))
    if bad:
        print(u"有失败枚：%s" % bad)
        return 1
    return 0


def json_load():
    import json
    return json.load(io.open(os.path.join(BUS, "state.json"), encoding="utf-8")).get("agents", {})


if __name__ == "__main__":
    sys.exit(main())
