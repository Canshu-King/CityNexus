# -*- coding: utf-8 -*-
"""裁语前的现算：把「挂代口径」与「内容口径」在同一代尖上一次摊开。

只读：不 fetch 除必要之外的东西，不写任何文件。取不到的枝尖就点名报缺，不许当成零。
"""
import subprocess
import sys

WORK = "D:/moodle/CityNexus"
TIPREF = "refs/heads/mirror/integration-frontend-apple-pass1"
TSV = "docs/REVOLUTION_ABSORPTION_MANIFEST.tsv"


def g(*a):
    return subprocess.run(["git", "-C", WORK] + list(a), capture_output=True,
                          text=True, encoding="utf-8", errors="replace", timeout=900)


def main():
    tip = g("ls-remote", "origin", TIPREF).stdout.split()
    if not tip or len(tip[0]) != 40:
        raise SystemExit("现读尖失败")
    tip = tip[0]
    tsv = g("show", "%s:%s" % (tip, TSV)).stdout
    if not tsv.strip():
        raise SystemExit("对账表在这枚尖上取不到")
    cols = tsv.splitlines()[0].split("\t")
    i_abs, i_sha = cols.index("absorbed_on"), cols.index("sha")
    rows = [l.split("\t") for l in tsv.splitlines()[1:] if l.strip()]
    stamped = [r for r in rows if len(r) > i_abs and r[i_abs].strip()]
    print("tip=%s rows=%d stamped=%d unstamped=%d" % (tip[:12], len(rows), len(stamped),
                                                      len(rows) - len(stamped)))
    if len(stamped) == 0:
        raise SystemExit("无盖章行，本尺无事可做")
    print("%-46s %-13s %6s %6s %6s %s" % ("枝名", "吸收代前12", "新增", "改动", "删除", "枝尖可取"))
    tot_am = 0
    for r in stamped:
        name, sha, on = r[0], r[i_sha], r[i_abs]
        if g("cat-file", "-e", sha + "^{commit}").returncode:
            g("fetch", "-q", "--depth=1", "origin", sha)
        ok = g("cat-file", "-e", sha + "^{commit}").returncode == 0
        if not ok:
            print("%-46s %-13s %s" % (name[:46], on[:12], "枝尖取不到（不当零）"))
            continue
        out = g("diff", "--name-status", tip, sha).stdout.splitlines()
        add = len([l for l in out if l.startswith("A")])
        mod = len([l for l in out if l.startswith("M")])
        dele = len([l for l in out if l.startswith("D")])
        anc = g("merge-base", "--is-ancestor", on, tip).returncode == 0
        tot_am += add + mod
        print("%-46s %-13s %6d %6d %6d %s 祖先于尖=%s" % (name[:46], on[:12], add, mod, dele,
                                                        "可取", "是" if anc else "否"))
    print("八条合计 新增+改动 = %d 枚；内容口径下这些枝全为未吸尽" % tot_am)
    return 0


if __name__ == "__main__":
    sys.exit(main())
