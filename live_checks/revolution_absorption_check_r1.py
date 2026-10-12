# -*- coding: utf-8 -*-
"""revolution 吸收进度尺：现读权威尖与对账表，报还剩几枚枝没吸收、已声明的吸收代是否真在线上。

每跑一次都重算，不读缓存：
  · 对账表每枚枝的 sha 能否从对象库取到（取不到 = 要按表内 40 位从远端救，不许默默掉）
  · absorbed_on 为空 = 未吸收
  · absorbed_on 非空时，必须是权威尖的祖先（不是祖先 = 退化，报红）

2026-10-13 加的规矩（今天咬到我一次）：**祖先判定只能在非浅仓里做**。
`D:/moodle/CityNexus` 是浅仓（`rev-parse --is-shallow-repository` 现读为 true），
浅仓在截断边界处答不出祖先，`merge-base --is-ancestor` 会对着真祖先返回非零。
这把尺那时就把「我看不到这段历史」报成「吸收代不在权威线上」，rc 从 4 跳到 9——
那是伪装成数据事故的仪器缺陷，所以：尖在哪棵读、祖先在哪棵判，分开选；
候选仓全是浅仓时本尺**不判（rc=3）**，绝不退化成 rc=9。
用法：python revolution_absorption_check_r1.py [--selftest]
退出码：0 = 对账闭合且无退化；9 = 有退化；4 = 仍有未吸收枝（推进中，不算失败）；3 = 现读数据取不到或仓库答不了祖先。
"""
import io
import os
import subprocess
import sys

GH = "git@github.com:Canshu-King/CityNexus.git"
CANDIDATES = [os.environ.get("CNX_WORK_REPO", "D:/moodle/CityNexus"),
              "D:/moodle/_qoder_integration_20260919"]
MANIFEST = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                        "..", "docs", "REVOLUTION_ABSORPTION_MANIFEST.tsv"))
TIPREF = "refs/heads/mirror/integration-frontend-apple-pass1"
WORK = CANDIDATES[0]


def git(*a):
    return subprocess.run(["git", "-C", WORK] + list(a), capture_output=True,
                          text=True, encoding="utf-8", errors="replace", timeout=900)


def is_shallow(repo):
    r = subprocess.run(["git", "-C", repo, "rev-parse", "--is-shallow-repository"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       timeout=300)
    return r.stdout.strip() == "true"


def load(path):
    lines = io.open(path, encoding="utf-8").read().splitlines()
    cols = lines[0].split("\t")
    return [dict(zip(cols, l.split("\t"))) for l in lines[1:] if l.strip()], cols


def selftest():
    """四条断言：未吸收/已声明的解析、浅仓被识别、浅仓确实答错祖先。

    最后两条是真造一棵浅克隆来测的——不造出来就等于没测，因为「浅仓答不出祖先」
    这件事只有现场复现了才拦得住下一次改错。
    """
    import shutil
    import tempfile
    bad = n = 0
    src = tempfile.mkdtemp(prefix="absorb_src_")
    dst = tempfile.mkdtemp(prefix="absorb_dst_") + "/clone"

    def sh(cwd, *a):
        return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t",
                               "-C", cwd] + list(a), capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=300)

    try:
        n += 1
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
            print("  FAIL 解析未吸收/已声明")
        os.remove(p)

        os.rmdir(dst) if os.path.isdir(dst) else None
        sh(src, "init", "-q", "--initial-branch=main", "--bare" if False else ".")
        for i in (1, 2, 3):
            io.open(os.path.join(src, "f%d.txt" % i), "w", encoding="utf-8").write("%d\n" % i)
            sh(src, "add", "-A")
            sh(src, "commit", "-q", "-m", "c%d" % i)
        first = sh(src, "rev-parse", "HEAD~2").stdout.strip()
        head = sh(src, "rev-parse", "HEAD").stdout.strip()
        n += 1
        if is_shallow(src):
            bad += 1
            print("  FAIL 全历史仓被当成浅仓")
        # 本地路径的 clone 会走「本地优化」把 --depth 吞掉（第一次自测就是这么红的），
        # 要真浅就必须走传输协议形状：file:/// 前缀。
        url = "file:///" + src.replace(os.sep, "/").lstrip("/").replace(" ", "%20")
        cl = sh(os.path.dirname(dst), "clone", "-q", "--depth=1", url, os.path.basename(dst))
        if cl.returncode:
            print("  SKIP 造不出浅克隆：%s" % (cl.stderr or "")[:100])
            bad += 1
        else:
            n += 1
            if not is_shallow(dst):
                bad += 1
                print("  FAIL depth=1 克隆没被识别为浅仓")
            n += 1
            deep = subprocess.run(["git", "-C", src, "merge-base", "--is-ancestor",
                                   first, head], capture_output=True, timeout=300).returncode
            shallow_ans = subprocess.run(["git", "-C", dst, "merge-base", "--is-ancestor",
                                          first, head], capture_output=True, timeout=300).returncode
            if deep != 0 or shallow_ans == 0:
                bad += 1
                print("  FAIL 浅仓的祖先判定没有复现出「答不出」（深=%d 浅=%d）" % (deep, shallow_ans))
    except Exception as exc:
        bad += 1
        print("SELFTEST 异常：%s" % exc)
    finally:
        shutil.rmtree(src, ignore_errors=True)
        shutil.rmtree(os.path.dirname(dst), ignore_errors=True)
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
    present = [r for r in CANDIDATES if os.path.isdir(r)]
    if not present:
        print("CHECK | 候选仓一枚都不在 %s ⇒ 不判" % CANDIDATES)
        return 3
    tip = None
    tip_repo = None
    for r in present:
        WORK = r
        globals()["WORK"] = r
        tp = git("ls-remote", "origin", TIPREF).stdout.split()
        if tp and len(tp[0]) == 40:
            tip, tip_repo = tp[0], r
            break
    if tip is None:
        print("CHECK | 权威尖取不到 ⇒ 不判")
        return 3
    hist = [r for r in present if not is_shallow(r)]
    shallow_seen = dict((r, is_shallow(r)) for r in present)
    if not hist:
        print("CHECK | 候选仓全是浅仓 %s ⇒ 祖先判定不可信，本尺不判（不当成退化）" % shallow_seen)
        return 3
    globals()["WORK"] = hist[0]
    if git("cat-file", "-e", tip + "^{commit}").returncode:
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
    print("CHECK 取数仓：尖读自 %s｜祖先判在 %s（非浅）｜浅仓标记 %s" % (
        tip_repo, hist[0], shallow_seen))
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
