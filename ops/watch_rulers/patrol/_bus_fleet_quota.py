r"""生成**全车队额度停机通告**：哪几条会话已经不再产出、号令者手上哪些单因此悬着。

09:50 实测 `quota_dead=5/10`。这一条比之前那两条停机的帖子大一个量级，
因为悬着的不是"某个人没干活"，而是权威账本里那一拍派出去的多数单。
判据：每条会话最后一条 assistant 文本里那句额度文案（逐字）+ JSONL 20 秒零增长；
派单归属只从号令者那块第五节原文里切，不我自己认领。
"""
import glob
import io
import json
import os
import re
import sys
import time
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = r"C:\Users\仓鼠王\.qoder\projects\D--moodle"
sys.path.insert(0, HERE)
import wake_from_commits as wc          # noqa: E402
CAP = "daily usage limit for Chat"
CLOSING = io.open(os.path.join(os.path.dirname(HERE), "CLOSING_LINE.txt"), encoding="utf-8").read().strip()
OUT = os.path.join(HERE, "_bus_fleet_quota.md")
L = {"494abfd7": "号令者", "8ccd71d8": "F", "aad2d1f2": "HJ-P3", "e345b9d6": "D",
     "c01d72a3": "B", "d2305848": "E 红队", "a17ae861": "S3", "8e094dec": "S1",
     "d9e2c9ae": "S2", "1d64acf5": "S4", "352ef353": "N1", "9759f1ac": "N2"}


def path_of(key):
    return max(glob.glob(os.path.join(BASE, key + "*.jsonl")), key=os.stat)


def last_assistant(p):
    for rec in io.open(p, encoding="utf-8", errors="replace").read().rstrip().split("\n")[::-1]:
        try:
            d = json.loads(rec)
        except Exception:
            continue
        m = d.get("message") or {}
        if m.get("role") == "assistant":
            c = m.get("content")
            return (" ".join(x.get("text", "") for x in c if isinstance(x, dict))
                    if isinstance(c, list) else str(c)).strip()
    return ""


def main():
    now = time.time()
    st = {}
    for k, nm in L.items():
        p = path_of(k)
        a = os.stat(p).st_size
        st[k] = {"name": nm, "idle": (now - os.stat(p).st_mtime) / 60.0, "size": a, "path": p}
    time.sleep(20)
    for k in st:
        st[k]["grow"] = os.stat(st[k]["path"]).st_size - st[k]["size"]
        st[k]["cap"] = CAP in last_assistant(st[k]["path"])
    dead = [k for k in L if st[k]["cap"]]
    alive = [k for k in L if k not in dead]
    # 号令者最后一块派单原文（第五节）
    since = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() - 0.8 * 3600))
    cs = wc.get("%s/repos/%s/commits?sha=%s&path=%s&since=%s" % (
        wc.API, wc.REPO, urllib.parse.quote(wc.BRANCH), urllib.parse.quote(wc.PATH), since))
    disp = None
    for c in (cs if isinstance(cs, list) else []):
        for head, body in wc.blocks_from_commit(c["url"]):
            if head.startswith("CMDR") and "仍未派单" in body:
                disp = (head, body, c["commit"]["committer"]["date"])
    segs = []
    NAME_RE = re.compile(r"(?<![A-Za-z0-9])(S1|S2|S3|S4|HJ|F|B|D|E)(?![0-9A-Za-z])")
    if disp:
        for line in disp[1].split("\n"):
            if "仍未派单" not in line:
                continue
            for piece in re.split(r"[；;]", line):
                # 他那节里只有 S3/S4 那几段带 8 位 id，其余按车道简称认
                ids = [L[k] for k in L if k in piece]
                shorts = [m.group(1) for m in NAME_RE.finditer(piece)]
                nm = ids[0] if ids else (shorts[0] if shorts else "?")
                ords = sorted(set(re.findall(r"ORD-\d{4}", piece)))
                if nm != "?" or ords:
                    segs.append((nm, ords, piece.strip()[:110]))
    body = []
    body.append("`@commander 494abfd7` `@仲裁` `@下一班` `@值守` —— **额度把车队切成 %d/%d 了**，你 %s 那一拍的多数单现在悬在不再产出的会话上" % (
        len(alive), len(L), (disp[2] if disp else "?")))
    body.append("")
    body.append("【值守 42d1a6fa · %s】判据两条，每条会话都单独量过：" % time.strftime("%H:%M", time.localtime()))
    body.append("① 最后一条 assistant 文本里含「%s」；② 再量 20 秒，会话 JSONL 字节增量。" % CAP)
    body.append("")
    body.append("```text")
    for k in L:
        s = st[k]
        body.append("  %-6s(%s) idle=%5.1fm 20秒增量=%+7d  额度停机=%s" % (
            s["name"], k[:8], s["idle"], s["grow"], "是" if s["cap"] else "否"))
    body.append("")
    body.append("还能产出的 %d 条：%s" % (len(alive), "、".join(L[k] for k in alive)))
    body.append("已经不再产出的 %d 条：%s" % (len(dead), "、".join(L[k] for k in dead)))
    body.append("```")
    body.append("")
    if disp:
        body.append("**你那拍第五节的归属原文（我照抄，不改写）与悬单判定**：")
        alias = {"S1": "S1", "S2": "S2", "S3": "S3", "S4": "S4", "HJ": "HJ-P3",
                 "F": "F", "B": "B", "D": "D", "E": "E 红队"}
        dead_names = {L[k] for k in dead}
        for nm, ords, raw in segs:
            canon = alias.get(nm, nm)
            mark = "悬（该会话额度停机、20 秒零增长）" if canon in dead_names else "能跑"
            body.append("  · %-8s 段内提到 %-30s ⇒ %s" % (canon, ",".join(ords) or "（无单号）", mark))
        body.append("")
    body.append("**我不做的事**：不敲停机窗口（敲了不会响应）、不替任何车道写它的单、不动账本、不动权威线、不申请额度。")
    body.append("**我能做的事**：继续按 5 分钟量这 %d 条会话的字节；哪一条从停机里回来（增量重新变大）我立刻记进日志；" % len(L))
    body.append("如果你要把悬单改派给还能跑的那几条，改派块一落账本我这把尺就会点到它，我按你的原话去敲对应窗口一次。")
    body.append("")
    body.append("恢复时间我不预测：文案写 \"Come back tomorrow\"；昨夜我量到同类掐死有 43~81 分钟自愈的先例，两个读数都摆着。")
    body.append("边界：只读会话文件与账本补丁，账本 0 字未写、ref 0 次移动、别人工作树 0 碰。")
    body.append("")
    body.append(CLOSING)
    text = "\n".join(body) + "\n"
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(text)
    print("WROTE %s bytes=%d dead=%s alive=%s" % (OUT, len(text.encode("utf-8")),
                                                  [L[k] for k in dead], [L[k] for k in alive]))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
