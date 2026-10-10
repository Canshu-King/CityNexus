"""谁的活已经落到账本、但人还在睡觉？

号令者写 verdict 时不会去叫醒车道，冷车道也不会自己重读账本 —— 今晚这条失效模式
（`### CMDR-0925-2229` 点名 E 要 a4，E 从 22:12 起就没动过）就是靠这个脚本提前发现的。

判据：账本里**最新那块**的落盘时间 > 某条会话的最后落盘时间，且那块点名了它
⇒ 打一条 WAKE_CANDIDATE。只报不动手：敲不敲由值守的会话判断（具名等待不敲）。

用法：python pending_check.py
"""
import glob
import io
import json
import os
import re
import sys
import time

LEDGER = r"D:\moodle\CITYNEXUS_AGENT_CONTROL.md"
HERE = os.path.dirname(os.path.abspath(__file__))
BASE = r"C:\Users\仓鼠王\.qoder\projects\D--moodle"
LANES = {
    "494abfd7": "号令者",
    "8ccd71d8": "F",
    "aad2d1f2": "HJ-P3",
    "e345b9d6": "D",
    "c01d72a3": "B",
    "d2305848": "E",
    # 09-26 凌晨号令者新开的工具车道（03:21 才发现我名册写死、漏了它们）
    "a17ae861": "S3",
    "8e094dec": "S1",
    "d9e2c9ae": "S2",
    "1d64acf5": "S4", "352ef353": "N1", "9759f1ac": "N2"}
# 号令者在块里点名车道时用的几种写法
PATTERNS = {
    "F": [r"8ccd71d8", r"(?<![A-Za-z0-9])F\b", r"@F\b"],
    "B": [r"c01d72a3", r"(?<![A-Za-z0-9])B\b", r"@B\b"],
    "D": [r"e345b9d6", r"(?<![A-Za-z0-9])D\b", r"@D\b"],
    "E": [r"d2305848", r"红队", r"(?<![A-Za-z0-9])E\b"],
    "HJ-P3": [r"aad2d1f2", r"HJ-P3"],
    "S1": [r"8e094dec", r"S1-q64sweep", r"(?<![A-Za-z0-9])S1\b"],
    "S2": [r"d9e2c9ae", r"S2-hermes-port", r"(?<![A-Za-z0-9])S2\b"],
    "S3": [r"a17ae861", r"状态板", r"(?<![A-Za-z0-9])S3\b"],
    "S4": [r"1d64acf5", r"ast-taint", r"(?<![A-Za-z0-9])S4\b"],
}


def last_write(key):
    p = glob.glob(os.path.join(BASE, key + "*.jsonl"))
    if not p:
        return 0.0
    return max(os.stat(x).st_mtime for x in p)


GRACE_MIN = 20.0


def decide(named, lane_mtime, ledger_mtime, now, min_idle=8.0, block_nominal=None):
    """判据本体。抽出来是为了能双向自检：
    正控 = 点名 + 账本更新 + 空闲够久 -> 必须报；反控 = 少任意一个条件 -> 必须不报。
    （不做"历史回放"：会话 JSONL 只有当前 mtime，回放出来的 idle 是假的。）

    block_nominal = 那块标题里 `CMDR-MMDD-HHMM` 换算出的秒。09-26 07:26 被自己咬了一口：
    账本 mtime 会因为**别人**插块而前进，我当时拿它当"有新字给她"的证据，把 S1 报成了候选 ——
    而她 07:14 刚交完 ORD-0339，点名她那块其实是 03:35 的旧字，她早看过并回过了。
    ⇒ 文件 mtime 只证明"账本动过"，不证明"那块是新的"。再加一道：她最后一次落盘必须不晚于
    那一块的名义时间（宽 GRACE_MIN 分钟，容作者写块时的时钟抖动）。"""
    idle = (now - lane_mtime) / 60.0
    if not named or idle < min_idle or lane_mtime >= ledger_mtime:
        return False
    if block_nominal is not None:
        return lane_mtime < block_nominal + GRACE_MIN * 60.0
    return True


def nominal_seconds(head, now):
    """块头 `CMDR-MMDD-HHMM` -> 本地秒；跨年时回退到 now 的前一年。解析不出就回 None（宁可退回旧判据）。"""
    m = re.search(r"CMDR-(\d{2})(\d{2})-(\d{2})(\d{2})", head)
    if not m:
        return None
    mm, dd, hh, mi = (int(m.group(i)) for i in (1, 2, 3, 4))
    year = time.localtime(now).tm_year
    try:
        t = time.mktime((year, mm, dd, hh, mi, 0, 0, -1, -1))
    except Exception:
        return None
    if t > now + 3 * 3600:                      # 明年同号 -> 差了一年
        try:
            t = time.mktime((year - 1, mm, dd, hh, mi, 0, 0, -1, -1))
        except Exception:
            return None                         # 回退到超出可表示范围（自检里 1970 年就撞到过）
    return t


PING_STATE = os.path.join(HERE, "wake_pings.json")
COOLDOWN_MIN = 40.0


def in_cooldown(pinged_at, now):
    """我多久之前刚敲过她。规则来自"一条车道一轮只发一条，发完就等"——
    敲第二遍就是噪声，且会把她的回合挤掉。"""
    if not pinged_at:
        return False
    return (now - float(pinged_at)) / 60.0 < COOLDOWN_MIN


def load_pings():
    try:
        return json.load(io.open(PING_STATE, encoding="utf-8"))
    except Exception:
        return {}


def record_ping(key, block):
    d = load_pings()
    d[key] = {"at": time.time(), "at_str": time.strftime("%H:%M:%S"), "block": block}
    json.dump(d, io.open(PING_STATE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("PING_RECORDED %s block=%s" % (key, block))
    return 0


def selftest():
    now = 1_000_000.0
    ledger = now - 600.0                     # 账本 10 分钟前落的
    cases = [
        ("正控 点名+账本更新+idle 15m", decide(True, now - 900, ledger, now), True),
        ("反控 没点名", decide(False, now - 900, ledger, now), False),
        ("反控 账本不比她新（她自己刚写过）", decide(True, now - 60, ledger, now), False),
        ("反控 idle 只有 2 分钟", decide(True, now - 120, ledger, now), False),
        ("正控 冷却判定：30 分钟前敲过 -> 在冷却内", in_cooldown(now - 1800, now), True),
        ("反控 冷却判定：55 分钟前敲过 -> 不在冷却内", in_cooldown(now - 3300, now), False),
        ("反控 冷却判定：从没敲过 -> 不在冷却内", in_cooldown(None, now), False),
        ("正控 块头排序：offset 小不等于最新（0335 在前、0510 在后）",
         newest_block([(100, "### CMDR-0926-0335 x"), (9000, "### CMDR-0926-0510 y")])[2] == "### CMDR-0926-0510 y", True),
        ("反控 跨日排序：0926-0010 应新于 0925-2359",
         newest_block([(0, "### CMDR-0925-2359 a"), (5000, "### CMDR-0926-0010 b")])[2] == "### CMDR-0926-0010 b", True),
        ("反控 全是无时间戳的块 -> 不选", newest_block([(0, "### 没有编号")]) is None, True),
        # 09-26 07:26 的假候选：账本因别人插块前进，但点名她那块是 03:35 的旧字
        ("正控 块名义时间新于她落盘 -> 报", decide(True, now - 900, now - 600, now, block_nominal=now - 900), True),
        ("反控 她在块名义时间+20 分钟之后又落过盘 -> 不报（03:35 的旧块）",
         decide(True, now - 900, now - 600, now, block_nominal=now - 3.6 * 3600), False),
        ("正控 宽限以内（块比名义时间晚 10 分钟）-> 仍报",
         decide(True, now - 900, now - 600, now, block_nominal=now - 1500), True),
        ("反控 名义时间解析不出 -> 不因它误杀（退回 mtime 判据）",
         decide(True, now - 900, now - 600, now, block_nominal=None), True),
        ("正控 块头时间换算：用真表针，0926 那枚应落在现在 ±1 天内",
         abs(nominal_seconds("### CMDR-0926-0735", time.time()) - time.time()) < 86400, True),
        ("反控 跨年回退：12 月的块在 1 月不算成明年",
         nominal_seconds("### CMDR-1231-2359", time.time()) < time.time(), True),
    ]
    bad = 0
    for name, got, want in cases:
        ok = (got == want)
        print("  %-40s got=%-5s want=%-5s %s" % (name, got, want, "OK" if ok else "FAIL"))
        bad += 0 if ok else 1
    print("selftest %s (%d/%d)" % ("PASS" if bad == 0 else "FAIL", len(cases) - bad, len(cases)))
    return 1 if bad else 0


def quota_dead_keys():
    """被日额度掐死的车道 —— 对它们敲门只会浪费剩下的额度。"""
    try:
        import quota_check as qc
    except Exception:
        return set()
    out = set()
    for key in LANES:
        ps = glob.glob(os.path.join(BASE, key + "*.jsonl"))
        if not ps:
            continue
        try:
            t = qc.last_assistant(max(ps, key=os.stat))
        except Exception:
            continue
        if qc.is_quota_dead(t):
            out.add(key)
    return out


def record_decline(key, block):
    """把"我已经看过这块并判定不敲"记下来。否则同一块会整夜反复报警，
    而重复报警的最后下场一定是被人忽略——那才是真的漏。"""
    d = load_pings()
    e = d.setdefault(key, {})
    e["declined_block"] = block
    e["declined_at"] = time.time()
    e["declined_at_str"] = time.strftime("%H:%M:%S")
    json.dump(d, io.open(PING_STATE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("DECLINE_RECORDED %s block=%s" % (key, block[:56]))
    return 0


def newest_block(blocks):
    """blocks: [(offset, header_line)]。账本**按作者分块插入**，offset 顺序不等于时间顺序
    （09-26 06:00 我差点用 blocks[0] 当"最新"，结果 04:05 / 05:0x 的块排在 0335 后面被我看漏）。
    ⇒ 只能解析块头里的 `CMDR-MMDD-HHMM` 再按它排。"""
    best = None
    for off, head in blocks:
        m = re.search(r"CMDR-(\d{2})(\d{2})-(\d{2})(\d{2})", head)
        if not m:
            continue
        key = (int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4)))
        if best is None or key > best[0]:
            best = (key, off, head)
    return best


def main():
    if "--selftest" in sys.argv:
        return selftest()
    if "--pinged" in sys.argv:
        i = sys.argv.index("--pinged")
        key = sys.argv[i + 1]
        block = sys.argv[i + 2] if i + 2 < len(sys.argv) else "?"
        return record_ping(key, block)
    if "--declined" in sys.argv:
        i = sys.argv.index("--declined")
        s = io.open(LEDGER, encoding="utf-8", errors="replace").read()
        m = re.search(r"(?m)^### CMDR-[0-9]{4}-\d{4}[^\n]*", s)
        block = sys.argv[i + 2] if i + 2 < len(sys.argv) else (m.group(0) if m else "?")
        return record_decline(sys.argv[i + 1], block)
    if not os.path.exists(LEDGER):
        print("LEDGER_MISSING")
        return 1
    st = os.stat(LEDGER)
    s = io.open(LEDGER, encoding="utf-8", errors="replace").read()
    blocks = [(m.start(), m.group(0)) for m in re.finditer(r"(?m)^### CMDR-[0-9]{4}-\d{4}[^\n]*", s)]
    if not blocks:
        print("NO_CMDR_BLOCKS")
        return 1
    picked = newest_block(blocks)
    if not picked:
        print("NO_PARSEABLE_BLOCK_HEADER")
        return 1
    off, head = picked[1], picked[2]
    after = [o for o, _h in blocks if o > off]
    nxt = min(after) if after else off + 9000
    body = s[off:nxt]
    now = time.time()
    nom = nominal_seconds(head, now)
    print("newest block %s | ledger mtime %s | %d blocks" % (
        head[:64], time.strftime("%H:%M:%S", time.localtime(st.st_mtime)), len(blocks)))
    hits = 0
    pings = load_pings()
    dead = quota_dead_keys()
    for key, name in LANES.items():
        if name == "号令者":
            continue
        lw = last_write(key)
        idle = (now - lw) / 60.0
        pats = PATTERNS.get(name, [name])
        named = any(re.search(p, body) for p in pats)
        aged_out = bool(named) and nom is not None and lw >= nom + GRACE_MIN * 60.0
        if key in dead:
            print("  %-6s(%s) idle=%5.1fm QUOTA_DEAD —— 被日额度掐死，敲门无效，不列为候选" % (name, key, idle))
            continue
        if decide(named, lw, st.st_mtime, now, block_nominal=nom):
            if pings.get(key, {}).get("declined_block") == head and lw < st.st_mtime:
                print("  DECLINED %s(%s) idle=%.1fm —— 同一块 %s 我已判过不敲（欠的是别人的动作），换块才会重新报" % (
                    name, key, idle, head[:34]))
                continue
            if in_cooldown(pings.get(key, {}).get("at"), now):
                print("  SUPPRESSED %s(%s) idle=%.1fm —— %s 已敲过（%s），冷却 %d 分钟内不敲第二遍" % (
                    name, key, idle, pings[key]["at_str"], pings[key].get("block"), COOLDOWN_MIN))
                continue
            print("  WAKE_CANDIDATE %s(%s) idle=%.1fm —— 最新块点名了她，而账本(%s)晚于她最后落盘(%s)" % (
                name, key, idle, time.strftime("%H:%M:%S", time.localtime(st.st_mtime)),
                time.strftime("%H:%M:%S", time.localtime(lw))))
            hits += 1
        else:
            tag = "" if not named else ("  aged_out=她在该块之后又落过盘，视为已读" if aged_out else "")
            print("  %-6s(%s) idle=%5.1fm named_in_newest=%s%s" % (name, key, idle, "Y" if named else "n", tag))
    print("candidates=%d | 块名义时间=%s" % (
        hits, "?" if nom is None else time.strftime("%m-%d %H:%M", time.localtime(nom))))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
