r"""单写者收件箱的**实测等待时长**，分「已插入」与「还压着」两列。

09-26 07:07 我在总线上报了 "d-e345b9d6_0605 已等 81 分钟 vs 15 分钟 SLA"，
那句是真的但**不完整**：它只量了最老的一枚，没量同期有没有别人也在等。
07:31 再看 `_processed/` 才发现 S1(0710→07:16:20)、B(0723→07:25:20)、S2(0655→06:55:55)
都在几分钟内过了闸 —— 也就是说这不是全局积压，是**选择性**的。
判据：文件名 `<lane>_<HHMM>.md.inserted_<HHMMSS>` 两侧都是量出来的，不靠记忆。
"""
import io
import os
import re
import sys
import time

ROOT = r"D:\moodle\_qoder_ledger_inbox"
SLA_MIN = 15.0
BASE = re.compile(r"^(?P<lane>.+?)_(?P<wm>\d{2})(?P<wh>\d{2})\.md")
INS = re.compile(r"\.inserted_(?P<h>\d{2})(?P<m>\d{2})(?P<s>\d{2})$")
SUP = re.compile(r"\.superseded_by_(?P<by>.+)$")
TODAY = time.localtime()


def hm(day, hour, minute, sec=0):
    """块名只带 HHMM/HHMMSS ⇒ 日期取今天；若算出来在未来，判成昨天跨日。"""
    t = time.mktime((TODAY.tm_year, TODAY.tm_mon, TODAY.tm_mday, hour, minute, sec, 0, -1, -1))
    return t


def wait_of(name, ins_mtime):
    """哪个时间是哪个量，09-26 07:33 用两枚自打架的读数量出来的：
    · 文件 **mtime = 作者写它的那一刻**（Windows rename 保留 mtime，所以移进 `_processed/` 不改它）。
    · 唯一有插入时刻的就是文件名尾标 `.inserted_HHMMSS`，但它**不带日期**。
    第一版我拿 mtime 当插入、把 HHMM 写成日期反推 ⇒ `cmdr_0645` 被算成 1439.7 分钟，
    实际是写于 06:44:40、尾标 06:45:03 ⇒ 23 秒。方向弄反会造出整天级别的假红。
    ⇒ written := mtime；inserted := 尾标落到"不早于 written 的那一天"。跨日时如实标 CROSS-DAY。"""
    b = BASE.match(name)
    i = INS.search(name)
    if not b or not i:
        return None
    lt = time.localtime(ins_mtime)
    written = ins_mtime
    ins = time.mktime((lt.tm_year, lt.tm_mon, lt.tm_mday,
                       int(i.group("h")), int(i.group("m")), int(i.group("s")), 0, -1, -1))
    delta = (ins - written) % 86400.0        # 尾标不带日期：取"不早于 written 的那一天"
    mins = delta / 60.0
    cross = mins > 12 * 60.0                 # 超过 12 小时 ⇒ 可能是多天，按可疑单列
    return mins, b.group("lane"), written, written + delta, cross


def selftest():
    """两枚反件都来自 07:32 那次自打架：把方向弄反会造出整天级的假红/假绿。"""
    base = time.mktime((2026, 9, 26, 6, 44, 40, 0, -1, -1))     # mtime = 作者写于 06:44:40
    cases = [
        ("反控 尾标只比 mtime 晚 23 秒 -> 0.4 分钟，不是 1439",
         round(wait_of("cmdr_0645.md.inserted_064503", base)[0], 1), 0.4),
        ("正控 尾标早于 mtime（同一分钟线之前写的）-> 判成跨天并标 CROSS",
         [(r[0] > 700, r[4]) for r in (wait_of("e-x_0715.md.inserted_064100", base),)], [(True, True)]),
        ("反控 缺尾标 / 缺写入标 -> 不参加统计", [wait_of("notes.md", base), wait_of("a_9999.md", base)], [None, None]),
    ]
    bad = 0
    for name, got, want in cases:
        ok = (got == want)
        print("  %-52s got=%-14s want=%-14s %s" % (name, got, want, "OK" if ok else "FAIL"))
        bad += 0 if ok else 1
    print("selftest %s (%d/%d)" % ("PASS" if bad == 0 else "FAIL", len(cases) - bad, len(cases)))
    return 1 if bad else 0


def main():
    if "--selftest" in sys.argv:
        return selftest()
    now = time.time()
    root = [f for f in os.listdir(ROOT) if f.endswith(".md") and os.path.isfile(os.path.join(ROOT, f))]
    pend = sorted(root, key=lambda f: os.stat(os.path.join(ROOT, f)).st_mtime)
    print("== 还压着（root）==")
    for f in pend:
        st = os.stat(os.path.join(ROOT, f))
        mins = (now - st.st_mtime) / 60.0
        b = BASE.match(f)
        wm = "%s:%s" % (b.group("wm"), b.group("wh")) if b else "?"
        print("  %-34s 写入标 %s | 落盘 %s | 已等 %5.1f 分钟 %s" % (
            f, wm, time.strftime("%H:%M:%S", time.localtime(st.st_mtime)), mins,
            "OVER-SLA" if mins > SLA_MIN else ""))
    if not pend:
        print("  (空)")
    proc = os.path.join(ROOT, "_processed")
    names = sorted(os.listdir(proc), key=lambda f: os.stat(os.path.join(proc, f)).st_mtime)
    rows = [w for w in (wait_of(n, os.stat(os.path.join(proc, n)).st_mtime) for n in names) if w]
    cross = [r for r in rows if r[4]]
    print("\n== 最近 12 枚已插入：mtime(作者写) -> 尾标(插入，无日期，取不早于写的那天) ==")
    for (mins, lane, written, ins, _c) in rows[-12:]:
        print("  %-18s %s -> %s  = %6.1f 分钟 %s" % (
            lane, time.strftime("%m-%d %H:%M:%S", time.localtime(written)),
            time.strftime("%H:%M:%S", time.localtime(ins)), mins,
            "OVER-SLA" if mins > SLA_MIN else "within"))
    sup = [n for n in names[-12:] if SUP.search(n)]
    print("  (同窗口被作者自己重发取代: %d 枚)" % len(sup))
    print("  读数>12 小时的枚数=%d /%d（尾标跨多天会被我低估，单列不当结论）" % (len(cross), len(rows)))
    if rows:
        vals = sorted(r[0] for r in rows)
        n = len(vals)
        recent = [r[0] for r in rows[-20:]]
        print("\n== 全量 _processed=%d 枚：等待分钟 中位=%.1f p90=%.1f 最大=%.1f ==" % (
            n, vals[n // 2], vals[min(n - 1, int(n * 0.9))], vals[-1]))
        print("== 最近 %d 枚（今晚这段）：中位=%.1f 最大=%.1f 超 SLA=%d/%d ==" % (
            len(recent), sorted(recent)[len(recent) // 2], max(recent),
            sum(1 for v in recent if v > SLA_MIN), len(recent)))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
