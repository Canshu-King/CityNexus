# -*- coding: utf-8 -*-
"""代插腿「插后核对会转红」这一手的真输入自测（不动权威账本、不投真报警）。

四形各一，都是 10-05 01:34 那拍真会出现的形状，用临时账本 + 临时日志跑：
甲 命中一次 ⇒ 绿，且不许报警（负对照：防我把红门槛放低成"每次都红"）
乙 命中零次 ⇒ 红（重复入账的另一半：插没插进去）
丙 标题取不到 ⇒ 红（旧代码正是这里读出 None 的）
丁 账本读不到 ⇒ 重试一次仍不可得 ⇒ 红，且必须写明"不可得"而不是当成 0

再加两格结构性检查：hub_alarm 现在真在本文件里定义过（旧代码 224 行调用的是一个不存在的名字，
一执行就 NameError 打死整条腿），且它的形参是 (band, id8, text)——P 档那个旧调用点没改过，
签名不同就会当场炸。
"""
import importlib.util
import inspect
import io
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(HERE, u"_inbox_applier_r2.py")

spec = importlib.util.spec_from_file_location("apl_selftest", TARGET)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

tmp = tempfile.mkdtemp(prefix="apl_verify_")
LOG = os.path.join(tmp, "leg.log")
LED = os.path.join(tmp, "ledger.md")
m.LOG = LOG
m.LEDGER = LED

ALARMS = []
REAL_ALARM = m.hub_alarm              # 先留真身，签名那两格要拿它来量
m.hub_alarm = lambda band, id8, text: ALARMS.append((band, id8, text))


def ledger(lines):
    io.open(LED, "w", encoding="utf-8", newline=chr(10)).write(lines)


def logtail():
    return io.open(LOG, encoding="utf-8").read()


res = []


def check(name, got, want):
    ok = got == want
    res.append(ok)
    print("%-58s %s" % (name, "PASS" if ok else "FAIL got=%r want=%r" % (got, want)))
    return ok


# ── 甲：命中一次 ⇒ 绿，不报警 ──────────────────────────────────────────────
ledger(u"### A 块头\n正文\n")
ALARMS[:] = []
bad = m.verify_landed([(u"A.md", u"A 块头")])
check(u"甲 命中一次 ⇒ 不进红名单", bad, [])
check(u"甲 绿的时候不许投报警（负对照）", ALARMS, [])
check(u"甲 绿行保持旧日志形制（巡逻那格还在读它）",
      u"插后核对：A.md｜块头在账本命中 1 次" in logtail(), True)

# ── 乙：命中零次 ⇒ 红 + 报警 ───────────────────────────────────────────────
ledger(u"### 别的块\n")
ALARMS[:] = []
bad = m.verify_landed([(u"B.md", u"B 块头")])
check(u"乙 命中零次 ⇒ 进红名单", bad, [u"B.md"])
check(u"乙 红 ⇒ 投一枚 R 档", [a[0] for a in ALARMS], [u"R"])
check(u"乙 红行写明命中次数", u"块头在账本命中 0 次" in logtail(), True)

# ── 丙：标题取不到 ⇒ 红，且不拿「没标题」当「没重复」 ──────────────────────
ALARMS[:] = []
bad = m.verify_landed([(u"C.md", u"")])
check(u"丙 标题为空 ⇒ 进红名单", bad, [u"C.md"])
check(u"丙 红行写明「标题取不到」", u"块头标题取不到" in logtail(), True)

# ── 丁：账本读不到 ⇒ 重试一次仍不可得 ⇒ 红（绝不当 0、更不当 1） ────────────
m.LEDGER = os.path.join(tmp, "does_not_exist.md")
ALARMS[:] = []
bad = m.verify_landed([(u"D.md", u"D 块头")])
check(u"丁 读不到账本 ⇒ 进红名单", bad, [u"D.md"])
check(u"丁 红行写明「重试一次仍不可得」", u"重试一次仍不可得" in logtail(), True)

# ── 戊：结构——hub_alarm 真存在、签名对得上旧调用点 ─────────────────────────
raw = io.open(TARGET, encoding="utf-8").read()
check(u"戊 本文件里 hub_alarm 有定义（旧代码只有调用）", raw.count(u"def hub_alarm("), 1)
check(u"戊 hub_alarm 形参 = band/id8/text（与哨兵同形）",
      list(inspect.signature(REAL_ALARM).parameters), [u"band", u"id8", u"text"])
check(u"戊 真身来自被改的这个模块（不是导入错文件）",
      REAL_ALARM.__module__ == u"apl_selftest", True)
check(u"戊 P 档那句旧调用未改、名字现在能解析", raw.count(u"hub_alarm(u\"P\", u\"mirror\""), 1)
check(u"戊 R 档调用点已就位", raw.count(u"hub_alarm(u\"R\", u\"verify\""), 1)
check(u"戊 旧那句「插完之后回 IBOX 读标题」已断掉", raw.count(u"block_head(os.path.join(IBOX, x))"), 0)

print(u"\n临时目录：%s" % tmp)
n = sum(1 for x in res if x)
print(u"%d/%d 过" % (n, len(res)))
sys.exit(0 if n == len(res) else 1)
