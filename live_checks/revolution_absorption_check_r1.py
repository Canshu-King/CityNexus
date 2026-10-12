# -*- coding: utf-8 -*-
"""revolution 吸收进度尺：现读权威尖与对账表，报还剩几枚枝没吸收、已声明的吸收代是否真在线上。

每跑一次都重算，不读缓存：
  · 对账表每枚枝的 sha 能否从对象库取到（取不到 = 要按表内 40 位从远端救，不许默默掉）
  · absorbed_on 为空 = 未吸收
  · absorbed_on 非空时，必须是权威尖的祖先（不是祖先 = 退化，报红）
用法：python revolution_absorption_check_r1.py
退出码：0 = 对账闭合且无退化；9 = 有退化；4 = 仍有未吸收枝（推进中，不算失败）；3 = 现读数据取不到。
"""
import io
import os
import subprocess
import sys

GH = "git@github.com:Canshu-King/CityNexus.git"
WORK = os.environ.get("CNX_WORK_REPO", "D:/moodle/CityNexus")
MANIFEST = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                        "..", "docs", "REVOLUTION_ABSORPTION_MANIFEST.tsv"))
TIPREF = "refs/heads/mirror/integration-frontend-apple-pass1"


def git(*a):
    return subprocess.run(["git", "-C", WORK] + list(a), capture_output=True,
                          text=True, encoding="utf-8", errors="replace", timeout=900)


def load(path):
    lines = io.open(path, encoding="utf-8").read().splitlines()
    cols = lines[0].split("\t")
    return [dict(zip(cols, l.split("\t"))) for l in lines[1:] if l.strip()], cols


def selftest():
    cases = [("空 absorbed_on 算未吸收", load, "ok")]
    n = len(cases)
    bad = 0
    try:
        p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_absorb_selftest.tsv")
        io.open(p, "w", encoding="utf-8", newline="").write(
            "name\tsha\tabsorbed_on\n"
            "x\t" + "0" * 40 + "\t\n"
            "y\t" + "1" * 40 + "\t" + "2" * 40 + "\n")
        rows, _ = load(p)
        unre = [r["name"] for r in rows if not r.get("absorbed_on", "").strip()]
        done = [r for r in rows if r.get("absorbed_on", "").strip()]
        if unre != ["x"] or len(done) != 1:
            bad += 1
        os.remove(p)
    except Exception as exc:
        bad += 1
        print("SELFTEST 异常：%s" % exc)
    return n, bad


def main():
    if "--selftest" in sys.argv:
        n, bad = selftest()
        print("ABSORB-SELFTEST assertions=%d failures=%d" % (n, bad))
        return 0 if bad == 0 else 9
    if not os.path.exists(MANIFEST):
        print("CHECK | 对账表读不到：%s ⇒ 不判" % MANIFEST)
        return 3
    rows, cols = load(MANIFEST)
    tp = git("ls-remote", "origin", TIPREF).stdout.split()
    if not tp or len(tp[0]) != 40:
        print("CHECK | 权威尖取不到 ⇒ 不判")
        return 3
    tip = tp[0]
    if git("cat-file", "-e", tip + "^{commit}").returncode != 0:
        git("fetch", "-q", GH, "+" + TIPREF + ":refs/tmp/absorb_tip")
        tip = git("rev-parse", "refs/tmp/absorb_tip").stdout.strip()
        if len(tip) != 40:
            print("CHECK | fetch 后仍取不到现尖 ⇒ 不判")
            return 3
    unre = [r for r in rows if not r.get("absorbed_on", "").strip()]
    done = [r for r in rows if r.get("absorbed_on", "").strip()]
    lost = [r["name"] for r in rows if git("cat-file", "-e", r["sha"]).returncode != 0]
    regress = []
    for r in done:
        on = r["absorbed_on"].strip()
        if len(on) != 40:
            regress.append("%s:absorbed_on 不是四十位(%s)" % (r["name"], on[:12]))
            continue
        if git("cat-file", "-e", on).returncode != 0:
            regress.append("%s:吸收代取不到对象" % r["name"])
        elif git("merge-base", "--is-ancestor", on, tip).returncode != 0:
            regress.append("%s:吸收代不在权威线上" % r["name"])
    print("revolution 吸收进度尺 | 权威尖 %s" % tip[:12])
    print("CHECK 对账表 %d 枚枝 | 已挂吸收代 %d | 未吸收 %d | 枝对象取不到 %d" % (
        len(rows), len(done), len(unre), len(lost)))
    if lost:
        print("CHECK 需按表内 sha 从远端救回：%s" % ", ".join(lost[:6]))
    if regress:
        print("CHECK 退化：%s" % ", ".join(regress[:6]))
        return 9
    if unre:
        print("CHECK 未吸收面按 verdict 分：TO_ABSORB %d｜CARRIED_BY_REP %d" % (
            len([r for r in unre if r.get("verdict") == "TO_ABSORB"]),
            len([r for r in unre if r.get("verdict") == "CARRIED_BY_REP"])))
        return 4
    print("CHECK 对账闭合：表内每枚枝都有在权威线上的吸收代，且无退化")
    return 0


if __name__ == "__main__":
    sys.exit(main())
