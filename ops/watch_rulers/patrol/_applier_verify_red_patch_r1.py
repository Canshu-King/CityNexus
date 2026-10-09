# -*- coding: utf-8 -*-
"""把代插腿的「插后核对」从一条会自灭的日志改成会转红、会说话的检查。

10-05 01:34 现场抓到两处（都是我自己这条腿上的）：
① 日志打了「插后核对：42d1a6fa_0133.md｜块头在账本命中 None 次（应为 1）」，然后照常
   往下走镜像、照常给号令者发「已入库」。那一拍同时没有「账本读不到」也没有
   「命中数不可得」这两行 ⇒ 这个 None 不是账本读抛的异常，而是 verify_landed 里
   `ti.get(x) or block_head(os.path.join(IBOX, x))` 那半句：块插完就被 applier 移进
   `_processed/`（实测 42d1a6fa_0133.md.inserted_013349），再去 IBOX 读标题只能读空，
   `ledger_hits(u"")` 就返回 None。触发它的精确条件我一次样本量不出来，不猜因；
   但**形状已经确定**：核对用的是「插完之后还能不能找到那个文件」，而插入的第一步
   就是把文件挪走。这条腿把「我读不到」写成了「数出来是 None」，人类看不出差别。
② 更狠的一处：本文件里从头到尾没有定义过 `hub_alarm`，而 224 行 P 档那句报警真执行
   就是 NameError——而 except 兜不住它，因为在 while 循环里。也就是说「插了块却拿不到
   镜像回执」这个最该叫人的分支，一执行就把整条腿打死，之后没人代插、也没人报。

改法（不放宽任何判据，只把「不可得」与「不为一次」都算红）：
· 标题只从插入前那一拍 `keep` 里取，不再拿插完就不存在的文件路径去猜；取不到就是红。
· 命中数不可得 ⇒ 等 5 秒重取一次（账本正被整本重写时读到空面是已知形状），仍不可得就是红。
· 任何非 1（含 None、0、≥2）⇒ 具名转红、汇总成 bad 交回调用方，调用方据此改口，
  「已入库」那句不许再说圆话。
· 补上真正的 `hub_alarm(band, id8, text)`，签名与哨兵同形，224 行那处调用不用改。
  正文刻意不带阿拉伯读数：本腿的数都在 --reprint 那份原样字节里；无出处的数会被中枢
  自己的数闸拒收（哨兵 04:52 撞过），拒了就等于没报。上报失败不许改变判定，只记一行。

用法：python _applier_verify_red_patch_r1.py            # 只预检，不写盘
      python _applier_verify_red_patch_r1.py --apply    # 落盘 + py_compile
"""
import io
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(HERE, u"_inbox_applier_r2.py")
NL = chr(10)

OLD_VERIFY = u'''def verify_landed(pairs):
    """\u63d2\u5b8c\u518d\u6570\u4e00\u904d\uff1a\u5e94\u4e3a\u4e00\u6b21\u3002\u4e0d\u7b49\u4e8e\u4e00\u6b21\u4e5f\u5177\u540d\u6253\u51fa\u6765\uff0c\u522b\u6df7\u5728\u300c\u6210\u529f\u300d\u91cc\u3002"""
    for name, title in pairs:
        say(u"\u63d2\u540e\u6838\u5bf9\uff1a%s\uff5c\u5757\u5934\u5728\u8d26\u672c\u547d\u4e2d %s \u6b21\uff08\u5e94\u4e3a 1\uff09" % (name, ledger_hits(title)))
'''

NEW_VERIFY = u'''def verify_landed(pairs):
    """插完再数一遍：应为一次。不等于一次也具名打出来，别混在「成功」里。

    10-05 01:34 抓到旧写法把「我读不到」写成「数出来是 None」，然后照常往下走：
    标题取自 `ti.get(x) or block_head(IBOX/x)`，可插入的第一步就是把块文件移进
    `_processed/`，那一拍再回 IBOX 读只能读空，`ledger_hits(u"")` 便返回 None。
    现在标题只信插入前那一拍记下的（pairs 由调用方从 keep 传进来），取不到＝红；
    命中数不可得＝等 5 秒重取一次，仍不可得＝红。**None 永远不默认成一次**。
    返回转红的块名列表，调用方据此把「已入库」那句改口。
    """
    bad = []
    for name, title in pairs:
        if not title:
            bad.append(name)
            say(u"插后核对转红：%s｜块头标题取不到 ⇒ 无法核账，按红办（不拿「没标题」当「没重复」）"
                % name)
            continue
        hit = ledger_hits(title)
        why = u""
        if hit is None:
            time.sleep(5)          # 账本正被整本重写时读到空面，是已知形状，等一手再取
            hit = ledger_hits(title)
            why = u"（重试一次仍不可得）"
        if hit != 1:
            bad.append(name)
            say(u"插后核对转红：%s｜块头在账本命中 %s 次（应为 1%s）" % (name, hit, why))
        else:
            say(u"插后核对：%s｜块头在账本命中 1 次（应为 1）" % name)
    if bad:
        hub_alarm(u"R", u"verify",
                  u"代插腿插完再数命中，有块头转红：要么标题取不到、要么命中数不可得、"
                  u"要么不为一次。这一拍的入账不可证，别按「已入库」办；逐枚名单与原因都在"
                  u"本腿日志的转红行里，随附证据那份原样字节是本拍出处。")
    return bad
'''

OLD_CALL = u'''                    verify_landed([(x, ti.get(x) or block_head(os.path.join(IBOX, x))) for x in ins])'''

NEW_CALL = u'''                    bad = verify_landed([(x, ti.get(x) or u"") for x in ins])'''

OLD_TELL = u'''                    tell_cmdr(ins, note + u"\uff1b\u63d2\u524d\u547d\u4e2d\u4e3a\u96f6\u3001\u63d2\u540e\u9010\u679a\u6838\u5bf9\u89c1\u672c\u65e5\u5fd7", tally_line)'''

NEW_TELL = u'''                    note += (u"\uff1b但插后核对有转红的（标题取不到／命中数不可得／不为一次），"
                             u"逐枚原因见本腿红行，R 档 alarm 已投" if bad
                             else u"\uff1b插前命中为零、插后逐枚核对每枚都只命中一次")
                    tell_cmdr(ins, note, tally_line)'''

OLD_HEAD = u'''def tell_cmdr(landed_names, verdict, tally_line):'''

NEW_HEAD = u'''def hub_alarm(band, id8, text):
    """报红的同一时刻往 BB 机投一枚 alarm：日志红只有我回来才看得见，中枢那条号令者会读。

    为什么这里要自己有一份：本文件以前直接调了 hub_alarm（P 档那句镜像回执缺失的报警），
    却从没定义或导入过它——那个分支真执行就是 NameError，而它在 while 循环里、没有
    except 兜着，于是「最该叫人的那一刻」恰好把腿自己打死。签名与哨兵那份同形
    （band, id8, text），旧调用点不用改。
    正文刻意不带阿拉伯读数：本腿的数都在 --reprint 那份原样字节里，正文里的数必须与
    证据同源才算数（哨兵 04:52 撞过：无出处的数被中枢拒收⇒这条腿永远投不出去）。
    上报失败不许改变判定，只记一行——红该红还是该红。
    """
    topic = u"applier:%s:%s:%s" % (band, time.strftime("%m%d"), id8)
    try:
        cmd = [sys.executable, os.path.join(BUS, "bus.py"), "send",
               "--from", FROM, "--to", CMDR, "--kind", "alarm",
               "--topic", topic, "--body", text,
               "--evidence", u"本拍原文|python \\"%s\\" --reprint" % SELF]
        q = subprocess.run(cmd, capture_output=True, cwd=BUS, timeout=90,
                           env=dict(os.environ, PYTHONIOENCODING="utf-8"))
        out = (q.stdout or b"").decode("utf-8", "replace")
        ok = (u'"id"' in out) and q.returncode == 0
        say(u"BB 机 alarm %s（%s）%s" % (u"已投" if ok else u"没投出去", topic,
            u"" if ok else (out[:120] or (q.stderr or b"").decode("utf-8", "replace")[:120])))
        return ok
    except Exception as e:
        say(u"BB 机 alarm 抛错（%s）：%s" % (topic, e))
        return False


def tell_cmdr(landed_names, verdict, tally_line):'''

OLD_CONST = u'''CLOSING = os.path.join(LIVE, u"CLOSING_LINE.txt")'''

NEW_CONST = u'''CLOSING = os.path.join(LIVE, u"CLOSING_LINE.txt")
FROM = u"qoder:42d1a6fa"
CMDR = u"qoder:494abfd7"'''

EDITS = [(u"hub_alarm 那两处收件人常量", OLD_CONST, NEW_CONST),
         (u"补上 hub_alarm 本体", OLD_HEAD, NEW_HEAD),
         (u"verify_landed 改成会转红", OLD_VERIFY, NEW_VERIFY),
         (u"调用方只从插前 keep 取标题", OLD_CALL, NEW_CALL),
         (u"通报措辞随核对结果改口", OLD_TELL, NEW_TELL)]


def main():
    apply_writes = "--apply" in sys.argv[1:]
    raw = io.open(TARGET, encoding="utf-8").read()
    if u"def hub_alarm(" in raw:
        print("ALREADY PATCHED — 本文件已有 hub_alarm，不重复打")
        return 0
    bad = []
    for label, old, new in EDITS:
        c = raw.count(old)
        print("%-26s 锚命中 %d 次" % (label, c))
        if c != 1:
            bad.append(label)
    if bad:
        print("ABORT：%s 锚不是唯一命中 ⇒ 未写盘" % u"、".join(bad))
        return 3
    if not apply_writes:
        print("DRY：预检通过，未写盘（要落盘加 --apply）")
        return 0
    for label, old, new in EDITS:
        raw = raw.replace(old, new, 1)
    io.open(TARGET, "w", encoding="utf-8", newline=NL).write(raw)
    p = subprocess.run([sys.executable, "-m", "py_compile", TARGET], capture_output=True)
    out = (p.stdout or b"").decode("utf-8", "replace") + (p.stderr or b"").decode("utf-8", "replace")
    print("WROTE %s bytes｜py_compile rc=%d %s" % (os.path.getsize(TARGET), p.returncode,
                                                  out[-200:].replace(NL, " ")))
    return 0 if p.returncode == 0 else 4


if __name__ == "__main__":
    sys.exit(main())
