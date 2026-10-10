"""夜巡自机：量转写字节增量判"在不在干活"，比 runtimeState 可靠。

用法：python patrol_watch.py [轮数] [每轮间隔秒]
默认 2 轮 / 每轮 270s（一次调用约 9 分钟，覆盖一个观察窗口）。
每轮输出一行读数并追加到同目录 PATROL_LOG.md。
"""
import os, sys, time, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

BASE = r"C:\Users\仓鼠王\.qoder\projects\D--moodle"
LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "PATROL_LOG.md")
LANES = {
    "aad2d1f2": "HJ-P3 手机模拟",
    "d2305848": "红队 E",
    "e345b9d6": "夜间 UI D",
    "8ccd71d8": "面板 B",
    "c01d72a3": "地图 C",
    "494abfd7": "包工头",
}
ERRS = ("Sorry, something went wrong", "The request could not be completed",
        "连接已中断", "消息发送超时")


def stat(key):
    for f in os.listdir(BASE):
        if f.startswith(key) and f.endswith(".jsonl"):
            p = os.path.join(BASE, f)
            s = os.stat(p)
            return s.st_size, s.st_mtime, p
    return 0, 0, None


def tail_text(path, n=60000):
    if not path:
        return ""
    with open(path, "rb") as fh:
        fh.seek(max(0, os.path.getsize(path) - n))
        return fh.read().decode("utf-8", "replace")


def last_assistant_text(path, n=400000):
    """只看**最后一条 assistant 正文**。整段尾部一起扫会把值守自己门铃里
    引用的错误串（『The request could not be completed』）读成车道报错 —— 04:33 实测误报过一次。"""
    if not path:
        return ""
    size = os.path.getsize(path)
    with open(path, "rb") as fh:
        fh.seek(max(0, size - n))
        chunk = fh.read().decode("utf-8", "replace")
    out = ""
    for line in chunk.split("\n"):
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            import json
            o = json.loads(line)
        except Exception:
            continue
        m = o.get("message") or {}
        if m.get("role") != "assistant":
            continue
        c = m.get("content")
        if isinstance(c, list):
            for x in c:
                if isinstance(x, dict) and x.get("type") == "text" and x.get("text"):
                    out = x["text"].strip().replace("\n", " ")
    return out



def one_round(idx, gap):
    before = {k: stat(k)[0] for k in LANES}
    time.sleep(gap)
    now = time.time()
    rows, stuck, parked = [], [], []
    for k, name in LANES.items():
        size, mtime, path = stat(k)
        age = now - mtime if mtime else -1
        delta = size - before[k]
        at = last_assistant_text(path)
        err = next((e for e in ERRS if e in at[-1200:]), "")
        if delta > 0:
            flag = "干活"
        elif err:
            flag = "死尾"
        else:
            flag = "收尾/等待"
        if delta == 0 and age > 400:
            if err:
                stuck.append(f"{k}({name},{age:.0f}s/{err})")
            else:
                parked.append(f"{k}({name},{age:.0f}s) 尾句:{at[-90:]}")
        rows.append(f"{k} {name}: {flag} Δ{delta:+d}B {age:.0f}s前{(' 错:'+err) if err else ''}")
    stamp = time.strftime("%m-%d %H:%M:%S", time.localtime(now))  # 本机时区已经是 +08，不要再加 8 小时
    line = f"- 自机 {stamp} +08 ｜ " + " ｜ ".join(rows)
    if stuck:
        line += "\n  **需救援（死回合占位）**: " + ", ".join(stuck)
    if parked:
        line += "\n  收尾待验收（**不要催、不要掐**，等包工头验收或它等的依赖跑完）: " + "; ".join(parked)
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8", newline="\n") as f:
        f.write(line + "\n")
    return stuck



def main():
    rounds = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    gap = int(sys.argv[2]) if len(sys.argv) > 2 else 270
    for i in range(rounds):
        one_round(i, gap)


if __name__ == "__main__":
    main()
