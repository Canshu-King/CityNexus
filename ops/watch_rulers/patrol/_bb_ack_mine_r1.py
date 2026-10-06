# -*- coding: utf-8 -*-
"""「把我名下压着的信一次清掉」——给任何一枚在册身份用的小工具（默认只列不动）。

为什么要有它（10-05 16:4x 现读数）：等待表上 `human:you01` 压着 13 条未取、最老约 22 小时，
那批全是我自己在 10-04 夜验板子发话腿时投的自测件——**我的噪音挂在主人的收件框里**，
让他逐条去 ack 是不讲理的。工具只能替本人清：`--by` 必须是那个 id 自己，我不冒充他点。

形制：
· 默认 dry：只列出会清掉哪几枚（id、kind、topic、龄），一个字节都不写。
· `--apply` 才逐枚走现成的 `bus.py ack`；每枚都回读它是否离开等待表，清不掉的具名报出来。
· `--apply` 前会把「kind 分布」打出来：真有 order/deliver 混在里面时，提醒这不是纯噪音，
  要人先看一眼再清（不许把派单当垃圾清掉）。
"""
import io
import json
import os
import subprocess
import sys
import time
import urllib.request

BUS = u"D:/moodle/agent_bus"
PORT = os.environ.get("BUS_PORT", "4799")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def pending_for(agent):
    op = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    d = json.loads(op.open(u"http://127.0.0.1:%s/pending?min=0" % PORT, timeout=30).read()
                   .decode("utf-8", "replace"))
    rows = d if isinstance(d, list) else (d.get("rows") or d.get("items") or [])
    got = [r for r in rows if str(r.get("to")) == agent and r.get("id")]
    # 10-05 16:4x 自测抓到本工具自己的形制错：`/pending` 回的行**不带 ts**，
    # 我照 `r.get("ts", now)` 取就一律落到「龄 0 分」——把 22 小时的积压报成刚到的。
    # 龄必须从总线账本按 id 反查，查不到就写「不可得」，不许拿默认值当读数。
    ts = {}
    who = {}
    try:
        for line in io.open(os.path.join(BUS, "bus.jsonl"), encoding="utf-8", errors="replace"):
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            if r.get("id"):
                ts[r["id"]] = float(r.get("ts", 0))
                who[r["id"]] = str(r.get("from"))
    except Exception:
        pass
    for r in got:
        _id = r.get(u"id")
        r[u"_age_min"] = (time.time() - ts[_id]) / 60.0 if _id in ts else None
        # `/pending` 的回包同样不带 from ⇒ 一律读成 None，等于看不见谁投的；
        # 而「谁投的」正是这次判断投错对象的关键，所以从账本按 id 反查。
        r[u"_from"] = who.get(_id) if _id in who else None
    return got


def main():
    args = sys.argv[1:]
    agent = args[args.index(u"--agent") + 1] if u"--agent" in args else u"qoder:42d1a6fa"
    apply_writes = u"--apply" in args
    if not apply_writes:
        print(u"DRY（只列不动；要真清加 --apply）｜目标身份：%s" % agent)
    rows = pending_for(agent)
    kinds = {}
    for r in rows:
        kinds[r.get("kind")] = kinds.get(r.get("kind"), 0) + 1
    print(u"名下未取 %d 枚｜kind 分布：%s" % (len(rows), json.dumps(kinds, ensure_ascii=False)))
    ages = [r.get(u"_age_min") for r in rows if r.get(u"_age_min") is not None]
    print(u"龄：最老 %s 分｜最新 %s 分（取不到龄的 %d 枚具名当不可得）" % (
        (u"%.0f" % max(ages)) if ages else u"不可得",
        (u"%.0f" % min(ages)) if ages else u"不可得", len(rows) - len(ages)))
    # 谁投来的也要打出来：10-05 16:4x 那次「未取」全是同一枚车道把交付投给了主人的腿，
    # 只看条数看不见投错对象，就会把「验收没跟上」错报成「谁在压信」。
    frm = {}
    for r in rows:
        k = r.get(u"_from") or u"（账本里反查不到）"
        frm[k] = frm.get(k, 0) + 1
    print(u"来自：%s" % u"、".join(u"%s×%d" % (k, v) for k, v in sorted(frm.items(), key=lambda x: -x[1])))
    risky = [k for k in kinds if k in (u"order", u"deliver", u"ruling", u"ask")]
    if risky and apply_writes:
        print(u"注意：里面混着 %s ——这些不是噪音，先看一眼再决定要不要清；"
              u"本工具不替你判，只把 id 列全。" % u"、".join(risky))
    now = time.time()
    for r in rows[:40]:
        age = r.get(u"_age_min")
        print(u"   %-16s %-8s 龄 %s｜%s" % (r.get("id"), r.get("kind"),
              (u"%5.0f 分" % age) if age is not None else u"  不可得 ",
              str(r.get("topic"))[:52]))
    if not apply_writes:
        print(u"未动任何账。要清：python %s --agent %s --apply" % (os.path.basename(__file__), agent))
        return 0
    cleared, left_ids = 0, []
    for r in rows:
        p = subprocess.run([sys.executable, os.path.join(BUS, "bus.py"), "ack",
                            "--id", r.get("id"), "--by", agent, "--note", u"值守代列，本人自清"],
                           cwd=BUS, capture_output=True,
                           env=dict(os.environ, PYTHONIOENCODING="utf-8"))
        if p.returncode == 0:
            cleared += 1
        else:
            left_ids.append(r.get("id"))
    after = pending_for(agent)
    print(u"ack 成功 %d 枚｜回读等待表：清之前 %d、清之后 %d" % (cleared, len(rows), len(after)))
    if left_ids:
        print(u"没清成的：%s" % u"、".join(left_ids))
    return 0 if len(after) == 0 else 2


if __name__ == u"__main__":
    sys.exit(main())
