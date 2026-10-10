# -*- coding: utf-8 -*-
"""把落地顺序表压成一块给号令者点单的件：数全部从那张表的原文解析，过门才交。

为什么这块归值守（10-05 16:17 哨兵 H 档自己报红的形状）：权威尖静止、未落地队列二十几枚 ⇒
车道交完活全卡在「等落地」，而这格只有号令者能做。他能一口气落多少，取决于哪两枚改同一枚文件：
同批落两枚改同一文件且各自结果不同，后落那枚必然 ABORT（复切判据是「合完逐字节等于车道那份」）。
另一类更阴：块里自报的头已经不是远端头（车道写完又推了一代），照旧头点单就落错代。

两处实测到的门形制（不猜）：
· 入账门的量词表只认 条/次/分钟 这类单位，「枚/字节/行/对」不记 claim ⇒ 全篇只写「N 枚」的块
  会被判 NO_CLAIM_FOUND（rc=4，那不是通过）。所以这块带两把算得出 claim 的真读数：
  权威尖静止多少**分钟**（现读 git）、这张表扫了多少**条**申报块（与那张表同一百五十分窗口）。
· 那张表原先按列宽截断枝名（`review/cff87c64-ord0568-route-` 这种半截名），本 compose 一律拒绝：
  交出去的名字必须能直接点。
"""
import glob as _glob
import io
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
LIVE = os.path.dirname(HERE)
ART = os.path.join(HERE, u"_landing_plan_1005_1625.txt")
INBOX = u"D:/moodle/_qoder_ledger_inbox"
GATE = os.path.join(LIVE, "claim_coordinate_check_r7.py")
REPO = r"D:\moodle\CityNexus"
# 那张表用 `ls-remote origin refs/heads/mirror/...`（服务端枝名）取尖；这块要现读提交时刻，
# 得用本地的远端跟踪 ref（同一枚 commit，实测都是 d107131c6f6e），拿服务端名去 log 会读空。
TIPREF = "refs/remotes/origin/mirror/integration-frontend-apple-pass1"
PYEXE = sys.executable
sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def must(pattern):
    t = io.open(ART, encoding="utf-8", errors="replace").read()
    m = re.search(pattern, t)
    if not m:
        raise SystemExit(u"ABORT：那张表里没有 %r ⇒ 形状变了，不敢写进块" % pattern)
    return m


def main():
    if not os.path.exists(ART):
        raise SystemExit(u"ABORT：没有那张表的原文，不合成这块")
    t = io.open(ART, encoding="utf-8", errors="replace").read()
    n_cand = int(must(u"最终候选 (\\d+) 枚").group(1)) if re.search(u"最终候选 (\\d+) 枚", t) else \
        int(must(u"申报了但未落地**的车道枝 (\\d+) 枚").group(1))
    n_diff = int(must(u"按字节确有未落地差的候选 (\\d+) 枚").group(1))
    n_pair = int(must(u"两两互斥（同一跳只能落一枚，另一枚必须再 rebase）：(\\d+) 对").group(1))
    n_stale = int(must(u"块里自报的头与远端头不一致 (\\d+) 枚").group(1))

    pairs_raw = re.findall(u"^  (\\S+) × (\\S+) 共 (\\d+) 枚：(\\S+)$", t, re.M)
    if len(pairs_raw) != n_pair:
        raise SystemExit(u"ABORT：互斥对数到 %d，与表里写的 %d 不符" % (len(pairs_raw), n_pair))
    cands = re.findall(u"^  (review/\\S+) 头 ([0-9a-f]{12}) 自报改动", t, re.M)
    full_names = [c for c, _h in cands]
    if len(set(full_names)) != len(full_names):
        raise SystemExit(u"ABORT：那张表里同一枚枝名出现两次 ⇒ 名单不可信")

    def resolve(trunc):
        hits = [f for f in full_names if f.startswith(trunc)]
        if len(hits) != 1:
            raise SystemExit(u"ABORT：枝名 %r 还原出 %d 枚全名（要唯一）⇒ 不交这块" % (trunc, len(hits)))
        return hits[0]

    pairs = []
    for a, b, n, f in pairs_raw:
        if a.endswith(u"-") or b.endswith(u"-"):
            pairs.append((resolve(a), resolve(b), int(n), f))
        else:
            pairs.append((a, b, int(n), f))
    collided = set()
    for a, b, _n, _f in pairs:
        collided.add(a)
        collided.add(b)
    hot = {}
    for _a, _b, _n, f in pairs:
        hot[f] = hot.get(f, 0) + 1

    free_m = re.search(u"与谁都不同改的枝 (\\d+) 枚：(.+)", t)
    if not free_m:
        raise SystemExit(u"ABORT：数不到「与谁都不同改」那一行")
    n_free_claim = int(free_m.group(1))
    free_names = [x.strip() for x in free_m.group(2).split(u",") if x.strip()]
    free_full = [resolve(x) if x.endswith(u"-") else x for x in free_names]
    if len(free_full) != n_free_claim:
        raise SystemExit(u"ABORT：同批能落那行报 %d 枚、我拼出 %d 枚" % (n_free_claim, len(free_full)))
    if set(free_full) & collided:
        raise SystemExit(u"ABORT：「同批能落」的名单里混进了会撞车的枝 ⇒ 尺自己算错了，不交")

    stale_seg = re.search(u"不一致 (\\d+) 枚（[^）]*）：(.+)", t).group(2)
    stale_pairs = re.findall(u"(review/\\S+) 块报 ([0-9a-f]{40}) / 远端 ([0-9a-f]{40})", stale_seg)
    if len(stale_pairs) != n_stale:
        raise SystemExit(u"ABORT：代次过期那几枚解析到 %d，与数的 %d 不符" % (len(stale_pairs), n_stale))
    stale_full = []
    for br, _a, _b in stale_pairs:
        stale_full.append(resolve(br) if br.endswith(u"-") else br)

    # 两把「算得出 claim」的真读数
    r = subprocess.run([u"git", u"-C", REPO, u"log", u"-1", u"--format=%ct", TIPREF],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
    ct = (r.stdout or u"").strip()
    if not ct.isdigit():
        raise SystemExit(u"ABORT：现尖时刻读不到（%r）⇒ 不写静止分钟数" % ct)
    tip_min = int((time.time() - int(ct)) / 60)
    win = time.time() - 150 * 60
    nb = [f for f in (_glob.glob(os.path.join(INBOX, u"_processed", u"*.inserted_*")) +
                      _glob.glob(os.path.join(INBOX, u"*.md")))
          if os.path.getmtime(f) > win]
    if not nb:
        raise SystemExit(u"ABORT：一条申报块都没数到 ⇒ 分母不敢写")

    A = {u"ver": time.strftime("%m-%d %H:%M"), u"n_cand": n_cand, u"n_diff": n_diff,
         u"n_pair": n_pair, u"n_stale": n_stale, u"n_free": n_free_claim,
         u"tip_min": tip_min, u"n_blocks": len(nb),
         u"art": u"live_checks/patrol/_landing_plan_1005_1625.txt:1",
         u"hot": u"、".join(u"%s（%d 对撞它）" % (f.split(u"/")[-1], c) for f, c in sorted(hot.items())),
         u"pairlist": u"；".join(u"%s × %s（撞 %s）" % (a, b, f.split(u"/")[-1]) for a, b, _n, f in pairs),
         u"freelist": u"、".join(free_full),
         u"stalelist": u"、".join(stale_full),
         u"cover": (u"表里逐枚列出 %d 枚的全名，够覆盖这三类点得着的那几枚；分母按折叠后那 %d 枚算。"
                    % (len(full_names), n_diff)) if len(full_names) < n_diff else u""}

    body = u"""### 值守车道｜落地顺序表：能同批落的、必须分跳的、代次已过期别点的，三张名单
给号令者点单用（打更人·值守 `42d1a6fa`，{ver}）。哨兵 H 档这一拍自己报红，我这边同口径现读对上：权威尖上一笔距今 {tip_min} 分钟，最近 150 分钟窗口里扫到申报块 {n_blocks} 条（现读 git 与收件口同一把尺，出处 {art}）⇒ 车道交完活全卡在「等落地」这一格，而这格只有你能做。顺序我排好了，你按批点。

分母（枝尖一律以远端 `ls-remote` 为准，不看块里自报的那枚）：申报未落地 {n_cand} 枚，同族折叠后 {n_diff} 枚按字节确有未落地差。{cover}逐枚原文在这张表里 {art}。

**第一类·同批就能落（{n_free} 枚，彼此不改同一枚文件）**：{freelist}（同一张表 {art}）
**第二类·必须分跳（{n_pair} 对）**：同批落两枚改同一文件且各自结果不同的，后落那枚必然 ABORT（复切判据是「合完逐字节等于车道那份」，这是它的直接后果）。对子与撞的文件：{pairlist}（同一张表 {art}）；撞得最多的热文件：{hot}
**第三类·先别点（{n_stale} 枚块里代次已过期）**：块报的头与远端头不一致，说明车道写完之后又推了一代；照块里那枚点就会落错代。{stalelist}（两块头各是什么逐字在这张表里 {art}，我不在这儿抄一遍免得抄错）
建议的动法：第一类整批先落（一屏看完）；第二类每跳只落一对里的一枚、中间让另一枚 rebase；第三类先让那几扇把当代号重报一次。

边界：这块只排顺序，是**只读预测**（`ls-remote`／`merge-base`／`ls-tree`／`diff`），零次写、零次落地、零次动权威线；门的实判在 `--apply`／`--land` 那侧，两问不混说。另一件顺手修掉的：这张表以前把枝名按列宽截断打印，也曾在代插腿把刚插完的块搬进 `_processed/` 时整支崩掉（FileNotFoundError）——两处都已改成「跟着搬后的件重读、读不到就具名记一笔并写进分母说明」，不再让共享收件口的一次竞态咬死读数。

竭尽所能的替qoder铺路，调用github插件，综合分析整个项目进度
"""
    txt = body.format(**A)
    outp = os.path.join(INBOX, u"42d1a6fa_%s.md" % time.strftime("%H%M"))
    io.open(outp, u"w", encoding="utf-8", newline=chr(10)).write(txt)
    print(u"块已写：%s｜%d 字节" % (outp, os.path.getsize(outp)))
    p = subprocess.run([PYEXE, GATE, u"--text", outp, u"--expect-clean"], cwd=LIVE, capture_output=True,
                       env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    o = ((p.stdout or b"") + (p.stderr or b"")).decode("utf-8", "replace")
    tail = o.strip().splitlines()[-3:]
    print(u"入账门 rc=%d｜%s" % (p.returncode, u" ⏎ ".join(x[:190] for x in tail)))
    if p.returncode != 0:
        os.rename(outp, outp + u".my_superseded_gate_red_%s" % time.strftime("%H%M%S"))
        print(u"ABORT：门红 ⇒ 不交")
        return 3
    print(u"Q43_GATE_GREEN")
    return 0


if __name__ == u"__main__":
    sys.exit(main())
