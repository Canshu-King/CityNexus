# -*- coding: utf-8 -*-
"""给 Q43 门（claim_coordinate_check_r7.py）补一条负例：中文数词＋量词不算 claim。

号令者裁语（10-04 23:0x 转达）：「把『中文数+量词（零扇/零条）』会漏算 claim 这一行写进门的
自测注释与一条负例——这是 1833 那块实测撞出来的形状，应该进门的记忆。改门的是你，改完跑自测。」

现场依据（本轮现取，不是回忆）：
· 单位表里只挂阿拉伯数字，`grep -c "零\|CN_NUM" 门` 实测 0 命中 ⇒ 中文数词根本不进 claims；
· 我自己那条交接句被同一把尺咬过：正文里「4820、6」被抓成要出处的数，而「四轮」「三件事」
  「第六抽屉」一个都没抓——同一句话里两种待遇，这就是漏算的形状；
· 后果不是放行而是反向拒收：claims 为空时 decide() 走 NO_CLAIM_FOUND rc=4，
  1833 那块（额度墙零扇／断在半路零扇／未取零条）就是被这个码整块拒掉的。

为什么不"顺手把中文数补进表"：补了之后「三件事」「四轮」「两列」这类叙述词全变成要出处的数，
写块的人没法说话。门的选择是拒收纯中文负结论块，逼每一格配阿拉伯读数＋坐标。
这条负例锁的就是这个选择：哪天有人把中文数放进 claims，这里会红，逼他回来改判据与注释。

改法只增量插三段，不动 numeric_claims／scan／decide 的任何一行（量具代码路径不重写）。
"""
import ast
import io
import sys

P = u"D:/moodle/_qoder_cmdr_ref_20260921/live_checks/claim_coordinate_check_r7.py"
s0 = io.open(P, encoding="utf-8", errors="replace").read()
s = s0
miss = []


def rep(label, old, new):
    global s
    if s.count(old) != 1:
        miss.append(u"%s（命中 %d 次）" % (label, s.count(old)))
        return
    s = s.replace(old, new, 1)


# ── 一、样例本身 ────────────────────────────────────────────────────────────
rep(u"SAMPLES 插负例",
    u'    "fire_DISCIPLINE_ZERO_without_receipt": ("本块边界：权威线 0 次移动" + FILLER, None),',
    u'''    "fire_DISCIPLINE_ZERO_without_receipt": ("本块边界：权威线 0 次移动" + FILLER, None),
    # ---- 已知漏算，锁住它（10-04 18:1x 实测，1833 那块撞出来的形）----
    # numeric_claims() 的单位表只挂在阿拉伯数字后面：「零扇」「零条」「三枚」这类中文数词
    # 根本不进 claims。同一句里「4820、6」会被抓成要出处的数，「四轮」「三件事」一个都不抓。
    # 后果不是放水，是反向拒收：claims 为空 ⇒ decide() 给 NO_CLAIM_FOUND rc=4，整块不让入账。
    # 故意不把中文数补进表：补了以后「两列」「三件事」这类叙述词全变成要出处的数，没人能写块。
    # 所以规矩是「每一格配阿拉伯读数＋现取坐标」，见 selftest 里那条 decide 断言。
    "locks_CN_NUMERAL_is_not_a_claim": ("额度墙零扇、断在半路零扇、未取零条", None),''')

# ── 二、checks 循环：给 locks_ 前缀一条自己的判法 ────────────────────────────
rep(u"checks 分支", u'''        else:
            checks[name] = bool(findings)''',
    u'''        elif name.startswith("locks_"):
            # 这类样例锁的是「门故意不看的东西」：claims 必须为空、也不该有 findings。
            # 它一旦变红，说明有人动了 numeric_claims 的形状——回来同步 SAMPLES 里那段注释。
            checks[name] = (claims == []) and (not findings)
        else:
            checks[name] = bool(findings)''')

# ── 三、decide 断言：纯中文负结论块＝被拒，不是通过 ──────────────────────────
rep(u"decide 断言",
    u'''    checks["r4e_does_not_excuse_an_unvouched_quantity"] = decide(c5, f5, badq)[1] == 3
    ok = all(checks.values())''',
    u'''    checks["r4e_does_not_excuse_an_unvouched_quantity"] = decide(c5, f5, badq)[1] == 3
    # 1833 那块的形状重放：只有中文负结论（零扇／零条）时，整块被 NO_CLAIM_FOUND 拒掉。
    # 数不传字面量，从真文本现扫——decide() 收 TEXT 不收预数，就是为了让这种断言不能靠记忆通过。
    cn_only = u"### SESSION=z 清点：额度墙零扇、断在半路零扇、未取零条"
    c6, f6, _ = scan(cn_only)
    checks["cn_only_negative_conclusion_is_refused_not_passed"] = \\
        (c6 == []) and decide(c6, f6, cn_only) == ("NO_CLAIM_FOUND", 4)
    # 反面对照：同样三格换成阿拉伯读数＋表内量词（枚/条），claims 就不再是空——
    # 证明门拒的是「中文数不进 claims」，不是「不许说零」。只断言抓没抓到，不去猜锚形。
    cn_fix = u"### SESSION=z 清点：额度墙 0 枚、断在半路 0 枚、未取 0 条"
    c7, f7, _ = scan(cn_fix)
    checks["arabic_zero_with_table_unit_is_a_claim"] = bool(c7)
    ok = all(checks.values())''')

if miss:
    for m in miss:
        print(u"未命中 →", m)
    sys.exit(u"ABORT：%d 条没落上，门未改动" % len(miss))
ast.parse(s)
if s.count(u"def numeric_claims") != s0.count(u"def numeric_claims"):
    sys.exit(u"ABORT：numeric_claims 行数变了，这不是我要的改动")
io.open(P, "w", encoding="utf-8", newline=chr(10)).write(s)
print(u"门已补三段｜%d → %d 字节" % (len(s0.encode("utf-8")), len(s.encode("utf-8"))))
