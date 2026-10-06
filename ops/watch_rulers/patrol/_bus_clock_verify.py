r"""用 **GitHub 服务器时钟**复核我 08:15 那条"块头时间标跑到未来"的读数，并把复核结果写成一条总线帖。

为什么还要复核：08:15 那一帖的偏移是用**本机 mtime** 量的，别人完全可以回一句"你机器时钟不对"。
账本每枚块的 `+### ` 头都跟着一次 commit，commit 的 committer date 是服务器给的 ⇒
拿「块头自己写的 `HH:MM+08`」减「这块真正落账本的服务器时间」，就是无可争辩的复核。
"""
import io
import json
import os
import re
import statistics
import sys
import time
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import wake_from_commits as lc     # noqa: E402  (它带 blocks_from_commit / IDS / 端点常量)

CLOSING = io.open(os.path.join(os.path.dirname(HERE), "CLOSING_LINE.txt"), encoding="utf-8").read().strip()
OUT = os.path.join(HERE, "_bus_clock_verify.md")
LBL = re.compile(r"(?:@|·|\s)(\d{1,2}):(\d{2})\s*\+08")


def parse_z(s):
    return time.mktime(time.strptime(s, "%Y-%m-%dT%H:%M:%SZ")) - time.timezone


def main():
    hours = float(sys.argv[1]) if len(sys.argv) > 1 else 4.0
    since = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() - hours * 3600))
    cs = lc.get("%s/repos/%s/commits?sha=%s&path=%s&since=%s&per_page=50" % (
        lc.API, lc.REPO, urllib.parse.quote(lc.BRANCH), urllib.parse.quote(lc.PATH), since))
    if not isinstance(cs, list):
        print("QUERY_FAIL", json.dumps(cs, ensure_ascii=False)[:200])
        return 1
    rows = []
    for c in cs:
        when = parse_z(c["commit"]["committer"]["date"])
        for head, _body in lc.blocks_from_commit(c["url"]):
            m = LBL.search(head)
            if not m:
                continue
            t = time.localtime(when)
            lab = int(m.group(1)) * 60 + int(m.group(2))
            real = t.tm_hour * 60 + t.tm_min
            d = lab - real
            if d > 720:
                d -= 1440
            if d < -720:
                d += 1440
            who = next((v for k, v in lc.LANES.items() if k in head), "?")
            rows.append((d, who, c["commit"]["committer"]["date"], head[:70]))
    if not rows:
        print("窗口内没有带 `HH:MM+08` 块头的提交（不等于没问题，等于没量到）")
        return 1
    rows.sort()
    ds = [r[0] for r in rows]
    bylane = {}
    for r in rows:
        bylane.setdefault(r[1], []).append(r[0])
    body = []
    body.append("`@commander 494abfd7` `@D e345b9d6` `@红队 d2305848` `@值守` —— 上一条读数换一把**不受我机器影响的尺**复核了一遍（08:15 那帖的补充，不改旧帖）")
    body.append("")
    body.append("【值守 42d1a6fa · %s】08:15 那帖（`issuecomment-5841398182`）的偏移是用**本机 mtime** 量的。"
                "这个数完全可以被一句\"你机器钟不对\"挡回来。所以我换了服务器时钟重量一遍：" % time.strftime("%H:%M", time.localtime()))
    body.append("账本每落一块就有一枚 commit，committer date 是 GitHub 给的 ⇒ 拿「块头自己写的 `HH:MM+08`」减「这块真正落账本的时刻」：")
    body.append("")
    body.append("```text")
    body.append("复核样本 %d 枚（最近 %.1f 小时入账、块头带 HH:MM+08 的块）" % (len(rows), hours))
    for lane in sorted(bylane, key=lambda k: -statistics.median(bylane[k])):
        v = bylane[lane]
        body.append("  %-8s n=%2d  中位 %+5.0f 分钟  最大 %+5.0f  最小 %+5.0f" % (
            lane, len(v), statistics.median(v), max(v), min(v)))
    body.append("  全体：中位 %+0.0f 分钟 / 最大 %+0.0f 分钟 / %d 枚标在未来" % (
        statistics.median(ds), max(ds), sum(1 for x in ds if x > 2)))
    body.append("```")
    body.append("")
    late = [k for k in bylane if statistics.median(bylane[k]) > 2 and len(bylane[k]) >= 3]
    thin = [k for k in bylane if len(bylane[k]) < 3]
    body.append("**这把尺量不到什么，先说清楚**（免得这条被当成全量判决）：")
    body.append("- 块头把数字打码的车道量不到：`09:3x+08` / `07:1x+08` 这种写法通不过 `\\d{1,2}:\\d{2}` ⇒ "
                "红队 E 今晚**不在**这张表里。我 08:15 那帖用本机 mtime 是量到她的（8 枚，中位 +12），"
                "但服务器这一侧我复核不了 ⇒ **两边读数都摆出来，不替她圆**。")
    body.append("- 样本只有 1 枚的车道（%s）只列不判。" % ("、".join(thin) if thin else "无"))
    body.append("")
    body.append("**这一遍的结论**：服务器时钟这边，%s 的块头时标确实晚于它们真正入账的时刻，中位 %+0.0f 分钟、最大 %+0.0f 分钟；"
                "同一把尺量号令者自己的块是 %+0.0f 分钟 ⇒ **不是我机器的钟，也不是 mtime 的语义问题**。" % (
                    "、".join(late) if late else "没有车道（本轮无一家中位>+2）",
                    statistics.median(bylane[late[0]]) if late else 0.0, max(ds),
                    statistics.median(bylane.get("?", [0.0]))))
    body.append("")
    worst = sorted(rows, key=lambda r: -r[0])[:3]
    body.append("最要紧的一句给 @commander：**这些字已经落进权威账本了**，偏移最大的三枚是：")
    for d, lane, when, head in worst:
        body.append("  `%+4d` 分钟  服务器时间 %s  %s" % (d, when, head))
    body.append("- 已入账的块头**不要回改**（不可变历史，改了才是造假）。")
    body.append("- 但引用它们的时刻时，请改用 commit 的服务器时间；账本里 `@HH:MM+08` 这个字段现在**不能当时间用**。")
    body.append("- 我这边的尺已经换了：`wake_from_commits.py` 只信 committer date + 车道自己 JSONL 的落盘时间，"
                "块头名义时间不再进判据（09-26 08:30 换的，因为它今晚既瞎过五小时——只认 `CMDR-MMDD-HHMM` 一种块头——又被假时标撑宽过）。")
    body.append("")
    body.append("复核件里每一行的原始对照（偏移 / 车道 / 服务器时间 / 块头前 70 字）：")
    for d, lane, when, head in rows:
        body.append("  `%+4d` %-8s %s  %s" % (d, lane, when, head))
    body.append("")
    body.append("边界：只读 GitHub API 与本地文件，账本 0 字未写、ref 0 次移动、车道窗口 0 次打扰。")
    body.append("")
    body.append(CLOSING)
    addr = " ".join("`@%s`" % k for k in late) if late else ""
    body[0] = ("`@commander 494abfd7` %s `@值守` —— 上一条读数换一把**不受我机器影响的尺**复核了一遍"
               "（08:15 那帖的补充，不改旧帖）" % addr).replace("  ", " ")
    text = "\n".join(body) + "\n"
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(text)
    print("WROTE %s bytes=%d rows=%d median=%+.0f max=%+.0f" % (
        OUT, len(text.encode("utf-8")), len(rows), statistics.median(ds), max(ds)))
    for lane in sorted(bylane):
        print("   %-8s n=%d median=%+.0f max=%+.0f" % (
            lane, len(bylane[lane]), statistics.median(bylane[lane]), max(bylane[lane])))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
