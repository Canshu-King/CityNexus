# -*- coding: utf-8 -*-
u"""删掉第⑦格那条按**数差**算的旧缺口行——它与新判据自相矛盾。

矛盾长什么样（20:26 现读打出来的）：
  新行：**推广缺口 1 扇（窗名在名册里没有同名身份）**：CityNexus Codex Window R
  旧行：推广缺口：活跃 thread 比在册 codex 身份多 **0 枚**
两行并排，谁看都要愣一下。旧行是数差（新窗数 − 在册数），**数相等不等于同一扇**：
一枚已接的 bbfix1 ＋ 一枚未接的 Window R，减出来正好 0。
两个互相抵消的错谓词比一个更危险——所以旧行必须走，不能"留着当参考"。

改成：只留接入件那半句（它有用：看的人要知道去哪拿可粘的文本），缺口数一律由新判据给。
"""
import ast
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "_bb_patrol_once_r1.py")

OLD = u'''        # 10-05 16:3x 把这格从「只报缺口」升级成「缺口 + 出口」：看巡逻的人不该再去别处问「那要怎么接」。
        # 件里写的是 join 一条做完「注册＋认领＋读信」，以及数闸的规矩（带数必须带出处）。
        # 仍不假装认得出人：thread 号与名册之间没有映射，这里只数枚数，不编身份。
        _gap = cx["active_threads_90m"] - len(_cx_ids)
        print(u"   推广缺口：活跃 thread 比在册 codex 身份多 %d 枚｜接入件（可直接粘）："
              u"D:/moodle/agent_bus/INVITE_CODEX.txt" % _gap)'''

NEW = u'''        # 10-05 16:3x 把这格从「只报缺口」升级成「缺口 + 出口」：看巡逻的人不该再去别处问「那要怎么接」。
        # 20:27 把**数差**那半句删了：它与上面的「按窗名判缺口」自相矛盾（数相等≠同一扇），
        # 两个互相抵消的错谓词比一个更危险。缺口数一律由窗名判据给；这里只留出口那半句。
        print(u"   接入件（可直接粘）：D:/moodle/agent_bus/INVITE_CODEX.txt")'''


def main():
    t = io.open(SRC, encoding="utf-8", newline="").read()
    if u"_gap = cx[" not in t:
        print(u"旧那行已在（要么已删，要么形状不同）⇒ 先看现读再动")
        i = t.find(u"推广缺口：活跃 thread")
        if i < 0:
            print(u"现读里没有那条，已删过")
            return 0
        print(t[max(0, i - 300):i + 300])
        return 1
    if t.count(OLD) != 1:
        print(u"REFUSE：锚命中 %d 次（应为 1），未写盘" % t.count(OLD))
        return 1
    new = t.replace(OLD, NEW, 1)
    try:
        ast.parse(new)
    except SyntaxError as e:
        print(u"REFUSE：SyntaxError，未写盘：%s" % e)
        return 1
    bak = SRC + u".bak_dropnumgap_1227"
    if not os.path.exists(bak):
        io.open(bak, "w", encoding="utf-8", newline="").write(bak and t)
    io.open(SRC, "w", encoding="utf-8", newline="").write(new)
    print(u"已删数差那行（备份 %s）" % os.path.basename(bak))
    return 0


if __name__ == "__main__":
    sys.exit(main())