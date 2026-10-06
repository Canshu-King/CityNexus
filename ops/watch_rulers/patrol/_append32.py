r"""追加 08:58–09:02 这一拍：新尺第一次报出真候选，三条判过不敲都留了字。"""
import io
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(HERE, "PATROL_LOG.md")
sys.path.insert(0, HERE)
import wake_from_commits as wc     # noqa: E402

DEC = os.path.join(HERE, "wake_from_commits_state.json")

ENTRY = """
## 08:58–09:02 · 值守第 32 拍 —— 新尺第一次报出**真候选**，三条判过不敲、每条都留了理由

- 08:58:55 拍：`wake_from_commits` 抓到 `CMDR 08:55`（commit `06941aeb`，服务器时间 2026-09-26T00:50:20Z = 08:50+08）
  点名 F / E / S3 且三家落账本之后再没写过盘 ⇒ **candidates=3**。
  这是换尺之后第一次报出候选（旧尺从 03:35 起一直没看见这类块）。
- **开枪前照例读尾句 + 读那块的原话**（两条都读了，不靠猜）：
  - F `8ccd71d8` 尾句「ORD-0332 交完码了」，块里那句是「F 在做 ORD-0332」⇒ 号令者这条状态**滞后**（她已经交了），
    欠的是他的验收，不是她的字 ⇒ **不敲**。
  - E `d2305848` 尾句「ORD-0340 交付完成，两枚签级全 MET」，块里那句是「E 手上是 ORD-0323 / ORD-0339 的派生签级」
    ⇒ 她交的正是这两枚 ⇒ **不敲**。
  - S3 `a17ae861` 块里原话：「**S3 我还没派**——它的状态板是协调件不是产品件，等我这一轮把落地节奏稳下来再说」
    ⇒ 这是号令者**主动挂起**，我去敲就是越权 ⇒ **不敲**。
- 三条判定都写进了 `wake_from_commits_state.json`（键 = `commit前8|车道id`），同一枚块不再反复报；
  重跑同一窗口 ⇒ `candidates=0`，那一行现在显示 `[已判过不敲: F、E 红队、S3]`，判过的痕迹留着可查。
- **那一拍真正派出去的单**（从块的正文逐行读的，不是从块头猜的）：
  ORD-0349 / ORD-0350 → S1 `8e094dec`（复核页那句「我们替你填的」要有可达出口、以及「服务器答了但用不了」要分两种腿）；
  ORD-0351 → S2 `d9e2c9ae`（包里没有为已存 journey id 准备的客户端路由 ⇒ 错误边界根本不可达）。
  两家落账本后都在写（08:59 实测 idle 0m / 0m）⇒ **派单没有被睡掉**，这次不需要我出手。
- 09:00 车队 idle：S3 @S3@、E @E@、F @F@、B @B@、号令者 @C@，其余 5 条 ≤1 分钟。`quota_dead=0/10`。
  root 待发 @LIVE@ 枚（@LIVENAMES@）；root 里作者自判废副本 @DEAD@ 枚（这些不占队列，别再当积压报）。
- 本拍 0 次敲门、0 次进别人窗口、账本 0 字未写。
"""


def main():
    now = time.time()
    BASE = wc.BASE

    def idle(key):
        import glob
        ps = glob.glob(os.path.join(BASE, key + "*.jsonl"))
        return (now - max(os.stat(p).st_mtime for p in ps)) / 60.0 if ps else -1
    ib = r"D:\moodle\_qoder_ledger_inbox"
    live = sorted(f for f in os.listdir(ib) if f.endswith(".md"))
    dead = [f for f in os.listdir(ib) if (".superseded" in f or ".bad_" in f or "my_superseded" in f)]
    rep = {
        "@S3@": "%.0fm" % idle("a17ae861"), "@E@": "%.0fm" % idle("d2305848"),
        "@F@": "%.0fm" % idle("8ccd71d8"), "@B@": "%.0fm" % idle("c01d72a3"),
        "@C@": "%.0fm" % idle("494abfd7"),
        "@LIVE@": str(len(live)), "@LIVENAMES@": "、".join(live) or "空",
        "@DEAD@": str(len(dead)),
    }
    entry = ENTRY
    for k, v in rep.items():
        entry = entry.replace(k, v)
    assert "@" not in entry.split("—— 新尺")[0] and all(x not in entry for x in rep)
    cur = io.open(LOG, encoding="utf-8", newline="").read()
    assert cur.endswith("\n")
    before = len(cur.encode("utf-8"))
    io.open(LOG, "a", encoding="utf-8", newline="").write(entry)
    print("filled: %s" % json.dumps(rep, ensure_ascii=False)[:180])
    print("APPENDED +%d B (=%d -> %d)" % (os.stat(LOG).st_size - before, before, os.stat(LOG).st_size))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
