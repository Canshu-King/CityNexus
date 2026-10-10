# -*- coding: utf-8 -*-
u"""第⑦格推广缺口改按**窗名**判，不按活跃 thread 数 − 在册身份数。

为什么（20:25 现读打出来的矛盾）：
  活跃窗自报名 = CityNexus Codex Window R，派生自 01a0c796；
  名册里 codex 身份 = codex:bbfix1；
  而那格仍打「推广缺口：活跃 thread 比在册 codex 身份多 **0 枚**」。
  ⇒ **数量相等被读成"缺口为零"**，可这是两扇不同的窗：
  bbfix1 10-04 19:0x 交过真 deliver（已接上），Window R 是 20:xx 才活跃的另一个窗（未接）。
  一枚已接 + 一枚未接 = 数都是 1，减出来 0。**两个互相抵消的错谓词比一个更危险**。

改法：缺口 = 「活跃窗自报名」里**在名册 codex 身份里找不到同名**的枚数。
  · 窗名读不到 ⇒ 这一格写「窗名不可得，缺口按未知报，不按 0 报」。
  · 名册里没有任何窗名可比（现读就是如此：只有 bbfix1）⇒ 缺口 = 活跃窗数，并点名是哪扇窗。
判据仍**不猜身份**：只报"这扇窗的名字在名册里没有"，不自动把它注册成 codex:xxx。
"""
import ast
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "_bb_patrol_once_r1.py")

OLD = u'''            _par = [l.strip() for l in _wt.splitlines() if u"派生自" in l]
            if _par:
                print(u"   %s" % _par[0].replace(u"派生自：", u"派生自："))
        except Exception as e:'''

NEW = u'''            _par = [l.strip() for l in _wt.splitlines() if u"派生自" in l]
            if _par:
                print(u"   %s" % _par[0])
            # 缺口按**窗名**判（20:25 装）：原来按「活跃 thread 数 − 在册身份数」，
            # 会把「一枚已接的 bbfix1 ＋ 一枚未接的 Window R」减成 0 —— 数量对上≠接上了。
            _win = []
            for x in _names:
                _v = x.split(u"：", 1)[1].strip()
                if _v and not _v.startswith(u"**"):
                    _win.append(_v)
            if _win:
                _hit = [w for w in _win if any(w.lower() in a.lower() for a in _cx_ids)]
                _miss = [w for w in _win if w not in _hit]
                if _miss:
                    print(u"   **推广缺口 %d 扇（窗名在名册里没有同名身份）**：%s"
                          % (len(_miss), u"、".join(_miss)))
                    print(u"      名册现有：%s｜要接得主人或包工头点名，我不据窗名自动注册"
                          % (u"、".join(_cx_ids) or u"无"))
                else:
                    print(u"   按窗名对：活跃窗 %s 都能在名册里找到同名身份 ⇒ 缺口 0 枚" % u"、".join(_win))
            else:
                print(u"   **窗名不可读 ⇒ 推广缺口按未知报，不按 0 报**"
                      u"（原来那条「多 N 枚」是数差，不是缺口）")
        except Exception as e:'''


def main():
    t = io.open(SRC, encoding="utf-8", newline="").read()
    if u"按窗名对" in t or u"推广缺口 %d 扇" in t:
        print(u"已在 ⇒ 不重复改")
        return 0
    if t.count(OLD) != 1:
        print(u"REFUSE：锚命中 %d 次（应为 1），未写盘" % t.count(OLD))
        i = t.find(u"_par = [l.strip()")
        print(u"现读那段：\n%s" % t[max(0, i - 300):i + 500])
        return 1
    new = t.replace(OLD, NEW, 1)
    try:
        ast.parse(new)
    except SyntaxError as e:
        print(u"REFUSE：SyntaxError，未写盘：%s" % e)
        return 1
    bak = SRC + u".bak_gapbyname_1225"
    if not os.path.exists(bak):
        io.open(bak, "w", encoding="utf-8", newline="").write(bak and t)
    io.open(SRC, "w", encoding="utf-8", newline="").write(new)
    print(u"缺口判据已改按窗名（备份 %s）" % os.path.basename(bak))
    return 0


if __name__ == "__main__":
    sys.exit(main())