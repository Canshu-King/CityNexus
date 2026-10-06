# -*- coding: utf-8 -*-
"""K 档（等模型回包）的三眼自测：命中、不可得、按天幂等。

为什么要有它：K 档是 04 日 00:4x 新加的，判据来自**另一枚进程**（那块人看的板）。
跨进程的档位最容易出两种假绿：板子死了整格当绿、以及 alarm 没投出去却记进重账（今天 06:55 就栽过一次）。
所以这三眼都必须真跑，不许只看代码。取不到数就 REFUSE 非零退。
"""
import importlib.util
import io
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def load(what, env=None):
    old = dict(os.environ)
    for k, v in (env or {}).items():
        os.environ[k] = v
    spec = importlib.util.spec_from_file_location(what + "_selftest", os.path.join(HERE, what + ".py"))
    m = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(m)
    finally:
        os.environ.clear()
        os.environ.update(old)
    return m


def main():
    red, green = [], []
    S = load("_sentinel_relay_r1")

    # 眼一：真板子答话 ⇒ 要么列出卡住的扇，要么明确 0 扇；两种都算尺活着
    k = S.board_k()
    if k is None:
        red.append(u"眼一：真板子没答话（K 档此刻不可用）")
    else:
        green.append(u"眼一：板子答了，等模型回包 >=%d 分的 %d 扇：%s"
                     % (int(S.K_MODEL_MIN), len(k), u"、".join(i for i, _a in k) or u"（无）"))
        if any(a < S.K_MODEL_MIN for _i, a in k):
            red.append(u"眼一：清单里混进了没到档的扇 ⇒ 门槛没生效")
        if any(i in S.J_EXCLUDE for i, _a in k):
            red.append(u"眼一：号令者/我这扇被列进来了（J_EXCLUDE 没复用）")

    # 眼二：板子死了 ⇒ 必须返回 None（不可得），绝不能返回空表当绿
    dead = load("_sentinel_relay_r1", {"SR_BOARD": "http://127.0.0.1:1/api/fleet"})
    kd = dead.board_k()
    if kd is None:
        green.append(u"眼二：板子不答时 K 档写「不可得」而不是 0 扇（不是单向致盲）")
    else:
        red.append(u"眼二：板子死了却回了 %r ⇒ 会把读不到当绿" % (kd,))

    # 眼三：K 的红要能触发早退集合（前缀「K 」），且 alarm 没投出去时不许记进重账
    probe = u"K 车道 abcdef12 那一轮的工包结果已回来、模型没出下一句"
    got = [x for x in S.actionable([probe, u"A 别的红"] ) if x.startswith(u"K ")]
    if got:
        green.append(u"眼三：K 的红在「我这班动得了」集合里（会早退交人，不会闷在日志里）")
    else:
        red.append(u"眼三：K 的红被 actionable 漏掉了 ⇒ 整夜不会叫人")
    huboff = load("_sentinel_relay_r1", {"SR_HUB_OFF": "1"})
    st, topic = huboff.try_alarm(u"K", "abcdef12", probe)
    if st == u"skip":
        green.append(u"眼三·补：SR_HUB_OFF=1 时返回 skip（调用方据此**不记**进重账，下一轮还会再试）")
    else:
        red.append(u"眼三·补：hub 关着却返回 %r ⇒ 可能被当成已投递而记进重账" % (st,))

    # 眼四：L 档（掉线）真板子答话 ⇒ 返回二元组，清单里都得到档且不混进号令者/我自己
    drop, unreg = S.board_l()
    if drop is None:
        red.append(u"眼四：L 档没答话（板子活着却取不到？）")
    elif any(a < S.L_DROP_MIN for _i, a, _u in drop) or any(i in S.J_EXCLUDE for i, _a, _u in drop):
        red.append(u"眼四：L 清单里混进到不了档或被排除的扇：%s" % u"、".join(i for i, _a, _u in drop))
    else:
        green.append(u"眼四：L 档答了，掉线 >=%d 分的 %d 扇：%s｜未接 BB 机 %d 扇：%s"
                     % (int(S.L_DROP_MIN), len(drop), u"、".join(i for i, _a, _u in drop) or u"（无）",
                        len(unreg or []), u"、".join(i for i, _a in unreg) or u"（无）"))

    # 眼五：板子死了 ⇒ L 也必须「不可得」，不能空表当绿
    ldead = dead.board_l()
    if ldead == (None, None):
        green.append(u"眼五：板子不答时 L 档写「不可得」而不是 0 扇")
    else:
        red.append(u"眼五：板子死了 L 却回了 %r" % (ldead,))

    # 眼六：L 的红要能触发早退集合
    lprobe = u"L 车道 abcdef12 末条是平台错误回话（实测 22 分）"
    if [x for x in S.actionable([lprobe, u"A 别的红"]) if x.startswith(u"L ")]:
        green.append(u"眼六：L 的红在「我这班动得了」集合里（会早退交人）")
    else:
        red.append(u"眼六：L 的红被 actionable 漏掉 ⇒ 整夜不会叫人")

    # 眼七：M 档（alarm 投出仍未取）——直调要拿到三元组，且到档的那条要能具名到收件人
    mu = S.bus_unread_alarms()
    if mu is None:
        red.append(u"眼七：M 档取不到账（BB 机账读不到？）")
    elif not (isinstance(mu, tuple) and len(mu) == 3) or (mu[0] and not mu[2]):
        red.append(u"眼七：M 档形制不对：%r" % (mu,))
    else:
        green.append(u"眼七：M 档答了——到档未取的 alarm %d 条，最老 %d 分，收件人：%s"
                     % (mu[0], mu[1], u"、".join(mu[2]) or u"（无）"))

    # 眼八：账读不到时 M 必须「不可得」，不能空表当绿
    bad = load("_sentinel_relay_r1")
    bad.M_BUS = u"D:/moodle/__no_such_dir__"
    if bad.bus_unread_alarms() is None:
        green.append(u"眼八：账读不到时 M 档写「不可得」而不是 0 条")
    else:
        red.append(u"眼八：账读不到 M 却回了数 ⇒ 会把断链读成健康")

    # 眼九：M 的红要能触发早退集合
    mprobe = u"M BB 机上有 1 条 alarm 到档仍未被取（最老 73 分）"
    if [x for x in S.actionable([mprobe, u"A 别的红"]) if x.startswith(u"M ")]:
        green.append(u"眼九：M 的红在「我这班动得了」集合里")
    else:
        red.append(u"眼九：M 的红被 actionable 漏掉 ⇒ 断链整夜没人管")

    print(u"sentinel_K_selftest 于 %s" % time.strftime("%m-%d %H:%M:%S"))
    for x in green:
        print(u"   绿：" + x)
    for x in red:
        print(u"   红：" + x)
    print(u"⇒ %s（红 %d 枚）" % (u"K_SELFTEST_GREEN" if not red else u"REFUSED", len(red)))
    return 0 if not red else 1


if __name__ == "__main__":
    sys.exit(main())
