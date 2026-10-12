# -*- coding: utf-8 -*-
"""ORD-0619（给地图工）：把两个口径分成两列各写判据，并带一条反控。

为什么不直接改 live_checks/revolution_absorption_stamp_r1.py：那枚文件现在尖上的 blob 是
953c16517a64b4fa685031550e324569430bfdb0，等于 refs/heads/review/屏工-0607-r1 里的同一枚，
而地图工-0607-r1 的那枚是 5b32787772b70a324930d580dfd0fcaddeee7019，没落线。
裁语把归属记错了；覆盖别人已落地的交付、或再造一枚同能力的尺，都不是这条单要的。
所以本件只做两件事：(1) 按裁语的判据把两个口径算成两列；(2) 带一条故意造的反控，
证明「仍有独有路径 ⇒ 拒绝盖章」与「独有路径为零 ⇒ 可盖章」两种读数都落进带日期的读数件。

口径（逐枚现算，全部对现尖，不读表里既有的数）：
  unique_paths = 枝里有、尖上没有的路径数（`git diff --name-status <尖> <枝尖>` 里状态 A 那些）；
  diff_files   = 两边都有、字节不同的路径数（状态 M，含 R 的重命名对）；
  可盖章 = unique_paths 为零（裁语第二条的判据），不为零一律留空，不看 diff_files。

本尺**不写对账表**：只读，输出落 `live_checks/patrol/_absorption_calibers_<日期>.tsv`。
退出码：0 = 两列都算出且反控按预期拒盖；9 = 反控没被拒（尺失效）；3 = 现读取不到。
"""
import datetime
import os
import re
import shutil
import subprocess
import sys
import tempfile

WORK = os.environ.get("CNX_WORK_REPO", "D:/moodle/CityNexus")
TIPREF = "refs/heads/mirror/integration-frontend-apple-pass1"
MANIFEST_REL = "docs/REVOLUTION_ABSORPTION_MANIFEST.tsv"
COLS = ("name sha fork ahead behind prod test doc other artifact mod_total mod_real "
        "carried verdict absorbed_on").split()
NEG_BRANCH = "refs/local/ditu-0619-negctl"


def git(*a):
    p = subprocess.run(["git", "-C", WORK] + list(a), capture_output=True)
    return p.returncode, p.stdout.decode("utf-8", "replace")


def git_rc(*a):
    return subprocess.run(["git", "-C", WORK] + list(a), capture_output=True).returncode


def calibers(tip, sha):
    rc, out = git("diff", "--name-status", tip, sha)
    if rc != 0:
        return None, None, None
    uniq = diffs = renamed = 0
    for ln in out.splitlines():
        parts = ln.split("\t")
        if len(parts) < 2:
            continue
        st = parts[0][0]
        if st == "A":
            uniq += 1          # 枝里有、尖里没有 = 独有路径
        elif st == "M":
            diffs += 1         # 两边都有、字节不同 = 与尖不同文件（裁定的 174 就是这个口径）
        elif st in ("R", "C"):
            renamed += 1       # 路径改名：既不算独有路径，也不算同路径异字节，单列摆着不藏
    return uniq, diffs, renamed


def main():
    argv = [a for a in sys.argv[1:]]
    pinned = ""
    if "--tip" in argv:
        k = argv.index("--tip")
        if k + 1 >= len(argv):
            print("RC3 --tip 后面要跟一枚 40 位")
            return 3
        pinned = argv[k + 1]
        del argv[k:k + 2]
        if not re.fullmatch(r"[0-9a-f]{40}", pinned or ""):
            print("RC3 --tip 不是 40 位十六进制")
            return 3
    rc, out = git("ls-remote", "origin", TIPREF)
    live = out.split("\n")[0].split("\t")[0].strip() if out else ""
    tip = pinned or live
    if not re.fullmatch(r"[0-9a-f]{40}", tip or ""):
        print("RC3 ls-remote failed")
        return 3
    if pinned:
        print("PINNED tip=%s (live tip is %s, same=%s)" % (tip, live, pinned == live))
    rc, raw = git("show", "%s:%s" % (tip, MANIFEST_REL))
    if not raw.strip():
        print("RC3 manifest unreadable on %s" % tip)
        return 3
    lines = [l for l in raw.split("\n") if l.strip()]
    hdr = lines[0].split("\t")
    if hdr != COLS:
        print("RC3 manifest header changed: %s" % hdr)
        return 3
    rows = [dict(zip(COLS, (l.split("\t") + [""] * 15)[:15])) for l in lines[1:]]

    print("tip=%s branches=%d" % (tip, len(rows)))
    recs = []
    for r in rows:
        u, d, rn = calibers(tip, r["sha"])
        if u is None:
            recs.append(dict(r, unique_paths=-1, diff_files=-1, renamed=-1,
                         stamp="UNREADABLE", basis=""))
            continue
        stamp = "ELIGIBLE" if u == 0 else "REFUSED"
        recs.append(dict(r, unique_paths=u, diff_files=d, renamed=rn, stamp=stamp, basis=tip))

    # ---- controls. Everything here runs on a THROWAWAY index (GIT_INDEX_FILE): the shared
    # index of D:/moodle/CityNexus belongs to whichever lane is mid-flight and must not be touched.
    neg_note = []
    tmpdir = tempfile.mkdtemp(prefix="ditu0619_")
    try:
        ienv = dict(os.environ, GIT_INDEX_FILE=os.path.join(tmpdir, "idx"))
        def git_i(*a):
            p = subprocess.run(["git", "-C", WORK] + list(a), capture_output=True, env=ienv)
            return p.returncode, p.stdout.decode("utf-8", "replace").strip()
        payload = os.path.join(tmpdir, "uniquename.txt")
        with open(payload, "w", encoding="utf-8") as fh:
            fh.write("ORD-0619 negative control: a path the authoritative tip does not have.\n")
        bo = git("hash-object", "-w", "--no-filters", payload)[1].strip()
        if git_i("read-tree", tip)[0] == 0 and git_i(
                "update-index", "--add", "--cacheinfo",
                "100644,%s,ops/ditu0619_negative_control_uniquename.txt" % bo)[0] == 0:
            tree = git_i("write-tree")[1]
            cmt = git_i("commit-tree", tree, "-p", tip, "-m",
                        "negative control: ORD-0619 ruler must refuse to stamp")[1]
            if re.fullmatch(r"[0-9a-f]{40}", cmt or ""):
                u2, d2, _r2 = calibers(tip, cmt)
                neg_note.append(("negative", cmt, u2, d2,
                                 "REFUSED" if (u2 or 0) > 0 else "STAMPED(bug!)"))
        u3, d3, _r3 = calibers(tip, tip)
        neg_note.append(("positive", tip, u3, d3, "ELIGIBLE" if u3 == 0 else "REFUSED"))
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    ctrl_ok = bool(neg_note) and neg_note[0][2] and neg_note[0][2] > 0 and neg_note[0][4] == "REFUSED" \
        and neg_note[1][4] == "ELIGIBLE"
    elig = [x for x in recs if x["stamp"] == "ELIGIBLE"]
    print("独有路径为零（可盖章）=%d  仍有独有路径（一律留空）=%d" % (len(elig), len(recs) - len(elig)))
    for x in sorted(elig, key=lambda y: y["name"]):
        print("   %-56s unique_paths=%d diff_files=%d renamed=%d %s" % (
            x["name"][:56], x["unique_paths"], x["diff_files"], x["renamed"],
            x["absorbed_on"].strip()[:12] or "-"))
    print("反控=%s 通过=%s" % (neg_note, ctrl_ok))

    day = datetime.datetime.now().strftime("%Y%m%d")
    if not argv:
        print("RC3 必须显式给输出目录（不往共享工作树里写）")
        return 3
    out_dir = argv[0]
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "_absorption_calibers_%s.tsv" % day)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("branch\tsha\tunique_paths\tdiff_files\trenamed\tstamp_eligible\tabsorbed_on_in_table\t"
                 "judgement\tbasis_tip\n")
        for x in sorted(recs, key=lambda y: (y["unique_paths"], y["name"])):
            fh.write("%s\t%s\t%d\t%d\t%d\t%s\t%s\t%s\t%s\n" % (
                x["name"], x["sha"], x["unique_paths"], x["diff_files"], x["renamed"], x["stamp"],
                x["absorbed_on"].strip() or "-",
                "独有路径=%d｜与尖不同=%d｜改名=%d；判据：只有独有路径为零才可盖章" % (x["unique_paths"], x["diff_files"], x["renamed"]), tip))
        for kind, sha, u, d, verdict in neg_note:
            fh.write("CONTROL-%s\t%s\t%s\t%s\t0\t%s\t-\t反控：故意造一枚仍有独有路径的枝，尺必须拒盖；"
                     "零独有路径的必须可盖\t%s\n" % (kind, sha, u, d, verdict, tip))
        fh.write("# totals rows=%d eligible=%d refused=%d control_passed=%s tip=%s\n" % (
            len(recs), len(elig), len(recs) - len(elig), ctrl_ok, tip))
    print("WROTE %s" % path)
    if not ctrl_ok:
        print("RC9 反控没通过，尺不可信")
        return 9
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
