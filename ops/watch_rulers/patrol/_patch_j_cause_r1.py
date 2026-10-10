# -*- coding: utf-8 -*-
u"""J 档那条消息的成因改成**从分类器原文取**，不再手写"尾条是没回音的 tool_use"。

为什么（20:35–20:39 实测，三条独立读数）：
  哨兵 J 档 20:35:57 报「J 车道 1d64acf5 断在半路（尾条是没回音的 tool_use）」，
  可三条读数都说不是断在半路：
    ① 它自己那把分类器 `_why_stopped_r1.py` 对 1d64acf5 的判定是
       「**卡闸、等裁语、谈交付**」——**没有"断在半路"这一类**；
    ② 我的末态尺读出末三条＝tool_use → **tool_result** → text（有回音，交活型）；
    ③ 240 KB 尾窗里 tool_result 出现 20 次，排除"只读尾部看不见回音"。
  根因：`_why_stopped_r1.py` 把 1d64acf5 列进「该敲车道本人（**卡闸/断在半路**）」
  ——**两类共用一栏**；J 档那条**手写的**消息就把"卡闸"讲成了"断在半路"。

改法（只改那一句消息的成因措辞，不改阈值、不改分类器、不改归属）：
  · 分类器对该扇**没有**报"断在半路"时 ⇒ 成因写「分类器判：**卡闸/等裁语/谈交付**（非断在半路）
    ⇒ 该敲的是号令者点验收，不是叫醒这扇」。
  · 分类器**确实**报了"断在半路"时 ⇒ 才写那句"尾条是没回音的 tool_use"。
这样"断在半路"这个红只能由分类器**真的**判出来，不会被措辞凭空造出来。

怎么拿分类器原文：`mid_stalled()` 返回的是 [(id8, 分钟)]，**不带类别**；
所以这里调用 `_why_stopped_r1.py` 取那一扇的「判：…」那一行原文（它已在跑，每拍一次子进程）。
取不到 ⇒ 写「分类器判词读不到 ⇒ 成因不可判」，**不许回退到手写那句**（那正是这次假红的路）。

边界：0 次发送语义变更（alarm 仍照旧投，归属不变）；只改**成因措辞**。
"""
import ast
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "_sentinel_relay_r1.py")

OLD = u'''                msg = (u"J 车道 %s 断在半路（尾条是没回音的 tool_use）⇒ 它不会自己回来读账本，"
                       u"该敲号令者把它叫回这一手；叫醒与派单仍归他，我只把话送到。"
                       u"分钟数同 I 档：只进日志与证据输出，不进本条正文。" % id8)'''

NEW = u'''                # 成因**从分类器原文取**（20:39 装）。原来这句手写的
                # 「断在半路（尾条是没回音的 tool_use）」会在分类器只判「卡闸/等裁语」时
                # 凭空造出"断在半路"——20:35:57 对 1d64acf5 就是这样假红了一次。
                _why = why_stopped_line(id8)
                if _why is None:
                    _cause = (u"分类器判词读不到 ⇒ **成因不可判**（不回退到手写那句："
                              u"那正是 20:35 假红的路）")
                elif u"断在半路" in _why:
                    _cause = u"断在半路（尾条是没回音的 tool_use）⇒ 它不会自己回来读账本"
                else:
                    _cause = (u"分类器判：**%s**（**非断在半路**）⇒ 该敲的是号令者点验收，"
                              u"不是叫醒这一扇" % _why)
                msg = (u"J 车道 %s %s；该敲号令者把它叫回这一手；"
                       u"叫醒与派单仍归他，我只把话送到。"
                       u"分钟数同 I 档：只进日志与证据输出，不进本条正文。" % (id8, _cause))'''

FN = u'''def why_stopped_line(id8):
    u"""拿分类器 `_why_stopped_r1.py` 对这一扇的「判：…」原文。

    取不到返回 None（**不回退到手写成因**——20:35 那次假红就是手写那句造成的）。
    它每拍被调一次（子进程只读流水，秒级返回），所以只在 J 档真有候选时才问。
    """
    import subprocess
    try:
        r = subprocess.run([sys.executable, os.path.join(HERE, "_why_stopped_r1.py")],
                           capture_output=True, cwd=HERE, timeout=180,
                           env=dict(os.environ, PYTHONIOENCODING="utf-8"))
        txt = (r.stdout or b"").decode("utf-8", "replace")
    except Exception:
        return None
    for line in txt.splitlines():
        if not line.startswith(id8):
            continue
        m = re.search(u"判：(.*)$", line)
        if m:
            return m.group(1).strip()
    return None


'''


def main():
    t = io.open(SRC, encoding="utf-8", newline="").read()
    if u"why_stopped_line" in t:
        print(u"已在 ⇒ 不重复改")
        return 0
    if t.count(OLD) != 1:
        print(u"REFUSE：J 档消息锚命中 %d 次（应为 1），未写盘" % t.count(OLD))
        i = t.find(u"J 车道 %s 断在半路")
        print(u"现读那段：\n%s" % t[max(0, i - 200):i + 400])
        return 1
    new = t.replace(OLD, NEW, 1)

    # 插函数：放在第一个 def 之前
    anchor = u"def "
    idx = new.find(anchor)
    if idx < 0:
        print(u"REFUSE：找不到 def 锚，未写盘")
        return 1
    new = new[:idx] + FN + new[idx:]

    try:
        ast.parse(new)
    except SyntaxError as e:
        print(u"REFUSE：SyntaxError，未写盘：%s" % e)
        return 1
    bak = SRC + u".bak_jcause_2039"
    if not os.path.exists(bak):
        io.open(bak, "w", encoding="utf-8", newline="").write(t)
    io.open(SRC, "w", encoding="utf-8", newline="").write(new)
    print(u"已改 J 档成因取法（备份 %s）" % os.path.basename(bak))
    for l in new.splitlines():
        if u"why_stopped_line" in l or u"成因不可判" in l or u"非断在半路" in l:
            print(u"  " + l.rstrip()[:96])
    return 0


if __name__ == "__main__":
    sys.exit(main())