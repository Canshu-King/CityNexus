# -*- coding: utf-8 -*-
u"""第⑦格补上「Codex 窗名」：活跃 thread 不再只是一串 id，而是"CityNexus Codex Window R（派生自…）"。

为什么（20:23–20:24 实测）：这一格原来只能说「两侧对不上就不猜，要接得主人或包工头点名」。
不猜是对的，但**猜不出来**和**没查**长得一模一样——查了才知道：
  · `~/.codex/thread_history_1.sqlite` 没有标题列（表只有 thread_turns／thread_items／
    thread_history_projection_state／thread_realtime_items），所以两侧确实没有现成映射；
  · 但 thread_items 的**头十几条**里包着身份句：子窗首条 userMessage 只是 "continue"，
    身份在**上一次 `create_thread` 的 functionCallOutput** 里（父窗写给子窗的委派书），
    里面有 `<source_thread_id>` 与 `You are CityNexus Codex Window R.`。
  ⇒ 窗名拿到了。名册里仍**没有** "Window R" 这一条 ⇒ 缺口照旧，但缺口现在有名字，
    人一眼能认出是哪扇窗，不必再翻库猜。

抽窗名用 `_codex_window_id_r1.py`（只读 mode=ro）。这里只把它接进打印，不复制逻辑。
接法：子支起不来 ⇒ 该行写「窗名不可得」，**不阻塞第⑦格其余读数**（别让一件件附属品
把整格拖成不可得——那正是"两件独立的事绑进同一个 try"那一形）。
"""
import ast
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "_bb_patrol_once_r1.py")

OLD = u'''        _cx_ids = [a for a in st if a.startswith(u"codex:")]
        print(u"   名册里 codex 身份 %d 枚：%s｜两侧对不上就不猜，要接得主人或包工头点名"
              % (len(_cx_ids), u"、".join(_cx_ids) or u"无"))'''

NEW = u'''        _cx_ids = [a for a in st if a.startswith(u"codex:")]
        print(u"   名册里 codex 身份 %d 枚：%s｜两侧对不上就不猜，要接得主人或包工头点名"
              % (len(_cx_ids), u"、".join(_cx_ids) or u"无"))
        # 窗名指纹（20:24 装）：活跃 thread 不再只是一串 id。抽窗名是**附属**读数，
        # 起不来只写「窗名不可得」，不许把第⑦格其余读数一起拖成不可得。
        try:
            _w = subprocess.run([sys.executable, os.path.join(HERE, u"_codex_window_id_r1.py")],
                                cwd=HERE, capture_output=True, timeout=90,
                                env=dict(os.environ, PYTHONIOENCODING="utf-8"))
            _wt = (_w.stdout or b"").decode("utf-8", "replace")
            _names = [l.strip() for l in _wt.splitlines() if u"自报窗名：" in l]
            if _names:
                print(u"   活跃窗自报名：%s"
                      % u"；".join(x.split(u"：", 1)[1] for x in _names))
            _par = [l.strip() for l in _wt.splitlines() if u"派生自" in l]
            if _par:
                print(u"   %s" % _par[0].replace(u"派生自：", u"派生自："))
        except Exception as e:
            print(u"   窗名不可得（%s）——**不拖第⑦格其余读数**，缺口照旧按活跃 thread 数报"
                  % type(e).__name__)'''


def main():
    t = io.open(SRC, encoding="utf-8", newline="").read()
    if u"_codex_window_id_r1.py" in t:
        print(u"已在 ⇒ 不重复接")
        return 0
    if t.count(OLD) != 1:
        print(u"REFUSE：锚命中 %d 次（应为 1），未写盘" % t.count(OLD))
        i = t.find(u"_cx_ids = [a for a in st")
        print(u"现读那段：\n%s" % t[max(0, i - 200):i + 420])
        return 1
    new = t.replace(OLD, NEW, 1)
    try:
        ast.parse(new)
    except SyntaxError as e:
        print(u"REFUSE：SyntaxError，未写盘：%s" % e)
        return 1
    bak = SRC + u".bak_codexname_1224"
    if not os.path.exists(bak):
        io.open(bak, "w", encoding="utf-8", newline="").write(t)
    io.open(SRC, "w", encoding="utf-8", newline="").write(new)
    print(u"已接窗名指纹（备份 %s）" % os.path.basename(bak))
    return 0


if __name__ == "__main__":
    sys.exit(main())