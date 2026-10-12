# -*- coding: utf-8 -*-
"""对账表加两列体检（ORD-0620 第四节，号令者点名给屏工）：
`unique_paths` = 按 `git diff --name-status <尖> <枝>` 数出的 A（枝相对尖的新增，git 默认带重命名识别）；
`diff_files`   = 同一套 diff 的 M（同路径异字节）。两列逐行现算，既有十四列一格不改（改了就整份不写）。
同一次跑批还把「字面独有路径数」（不做改名识别）一并打在标准输出里留证：两种口径对同一枚枝可以差出几枚，
差别全在改名配对上——号令者那八行用的是前一种，本表跟他同口径。

为什么分两列：号令者裁语里定了口径——只有 unique_paths 为零才支持已盖的吸收代；
diff_files 是「线与枝各自演化之后还差多少字节」，只当体检用，不拿来否决章。
用法：
  python live_checks/revolution_absorption_columns_r1.py --selftest
  python live_checks/revolution_absorption_columns_r1.py --against <那一拍的尖>   # 与别人读数对拍
  python live_checks/revolution_absorption_columns_r1.py --apply <输出路径>        # 现尖那一代出表
退出码：0 = 全表算完；3 = 尖或表取不到；4 = 有枝的 pin 取不到；9 = 写门拒（既有列被改动或行列数变）。
"""
import argparse
import subprocess
import sys

GH_REF = "refs/heads/mirror/integration-frontend-apple-pass1"
MANIFEST = "docs/REVOLUTION_ABSORPTION_MANIFEST.tsv"
NEW_COLS = ("unique_paths", "diff_files")


def parse_table(text):
    lines = [ln for ln in text.split("\n") if ln.strip()]
    cols = lines[0].split("\t")
    rows = []
    for ln in lines[1:]:
        fields = ln.split("\t")
        fields += [""] * (len(cols) - len(fields))
        rows.append(fields)
    return cols, rows


def counts(branch, tip):
    """两棵树的字典 -> (字面独有路径数, 同路径异字节数)。字面口径不做重命名识别。"""
    unique = 0
    differ = 0
    for path, blob in branch.items():
        if path not in tip:
            unique += 1
        elif tip[path] != blob:
            differ += 1
    return unique, differ


def tally_name_status(text):
    """把 `git diff --name-status` 的原文逐行分类成 A/M/R/D 四问的计数。"""
    tally = {"A": 0, "M": 0, "R": 0, "D": 0}
    for line in text.splitlines():
        if not line.strip():
            continue
        kind = line.split("\t", 1)[0][0]
        if kind in tally:
            tally[kind] += 1
    return tally


def diff_state(git, tip, pin):
    """`git diff --name-status <尖> <枝>`：A=枝相对尖的新增（git 默认带重命名识别），
    M=同路径异字节，R=改名的配对，D=尖里有而枝没有。号令者那八行的口径就是这一套。"""
    return tally_name_status(git("diff", "--name-status", tip, pin).stdout)


def render(cols, rows, values):
    out = ["\t".join(list(cols) + list(NEW_COLS))]
    for index, row in enumerate(rows):
        out.append("\t".join(row + list(values[index])))
    return "\n".join(out) + "\n"


def guard(old_text, new_text, cols):
    """除新增两列外，前 len(cols) 列必须逐格相同；返回第一条违规说明。"""
    o = [ln for ln in old_text.split("\n") if ln.strip()]
    n = [ln for ln in new_text.split("\n") if ln.strip()]
    if len(o) != len(n):
        return "行数从 %d 变成 %d" % (len(o), len(n))
    for i, (a, b) in enumerate(zip(o, n)):
        fa, fb = a.split("\t"), b.split("\t")
        if len(fb) != len(fa) + len(NEW_COLS):
            return "第 %d 行新列数不对（%d -> %d）" % (i, len(fa), len(fb))
        for c in range(len(fa)):
            if fa[c] != fb[c]:
                return "第 %d 行的第 %d 列（%s）被改动：%r -> %r" % (i, c, cols[min(c, len(cols) - 1)], fa[c], fb[c])
    return None


def selftest():
    bad = []
    tip = {"a.py": "1", "b.py": "2", "c.py": "3"}
    branch = {"a.py": "1", "b.py": "9", "d.py": "7"}
    if counts(branch, tip) != (1, 1):
        bad.append("独有/异字节 混合形算成 %s，期望 (1, 1)" % (counts(branch, tip),))
    if counts(dict(tip), tip) != (0, 0):
        bad.append("同树应 (0, 0)，实得 %s" % (counts(dict(tip), tip),))
    if counts({"z.py": "z"}, tip) != (1, 0):
        bad.append("全新枝应 (1, 0)，实得 %s" % (counts({"z.py": "z"}, tip),))
    if counts({"a.py": "x", "b.py": "y", "c.py": "w"}, tip) != (0, 3):
        bad.append("全异字节应 (0, 3)，实得 %s" % (counts({"a.py": "x", "b.py": "y", "c.py": "w"}, tip),))
    cols = ["name", "sha", "absorbed_on"]
    # 两口径的差别要能在自检里被钉住：改名配对那三枚，字面口径算"独有"，diff 口径算"改名"
    sample = "A\tnew.py\nM\tmod.py\nR100\told.py\tmoved.py\nD\tgone.py\n"
    got = tally_name_status(sample)
    if got != {"A": 1, "M": 1, "R": 1, "D": 1}:
        bad.append("name-status 分类实得 %s，期望每问各一" % (got,))
    rename_only = "R099\tevidence/a.md\tdocs/revolution-archive/a.md\nM\tb.py\n"
    if tally_name_status(rename_only)["A"] != 0:
        bad.append("纯改名配对不该算新增")
    rows = [["枝甲", "1", ""], ["枝乙", "2", "abc"]]
    vals = [("0", "174"), ("3", "0")]
    old = "\t".join(cols) + "\n" + "\n".join("\t".join(r) for r in rows) + "\n"
    new = render(cols, rows, vals)
    if guard(old, new, cols) is not None:
        bad.append("只加两列的正常输出被写门拒了：%s" % guard(old, new, cols))
    tampered = new.replace("枝乙\t2\tabc", "枝乙\t2\tZZZ")
    if guard(old, tampered, cols) is None:
        bad.append("既有 absorbed_on 被改动竟被放行")
    dropped = "\n".join(new.split("\n")[:2]) + "\n"
    if guard(old, dropped, cols) is None:
        bad.append("少一行竟被放行")
    print("SELFTEST 格子 10，失败 %d" % len(bad))
    for line in bad:
        print("   FAIL %s" % line)
    return 1 if bad else 0


def build(repo, work):
    def git(*a, cwd=None):
        return subprocess.run(["git", "-C", cwd or repo] + list(a), capture_output=True,
                              text=True, encoding="utf-8", errors="replace", timeout=1800)
    return git


def read_tip(git, work):
    for line in git("ls-remote", "origin", GH_REF, cwd=work).stdout.splitlines():
        sha, _, ref = line.partition("\t")
        if ref == GH_REF and len(sha) == 40:
            return sha
    return None


def tree_of(git, ref):
    out = {}
    for line in git("ls-tree", "-r", "--format=%(objectname) %(path)", ref).stdout.splitlines():
        blob, _, path = line.partition(" ")
        if blob and path:
            out[path] = blob
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default="D:/moodle/_qoder_integration_20260919")
    ap.add_argument("--work", default="D:/moodle/CityNexus")
    ap.add_argument("--against", default=None, help="按指定那一代的尖算（与别人读数对拍用）")
    ap.add_argument("--apply", default=None, help="把加了新列的表写到这个路径（不动仓库里那枚）")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    git = build(args.repo, args.work)
    tip = args.against or read_tip(git, args.work)
    if not tip or git("cat-file", "-t", tip).stdout.strip() != "commit":
        print("ABORT 那一代的尖取不到：%r" % (tip,))
        return 3
    source = git("show", "%s:%s" % (tip, MANIFEST)).stdout
    if not source:
        print("ABORT 对账表取不到")
        return 3
    cols, rows = parse_table(source)
    if any(c in cols for c in NEW_COLS):
        print("ABORT 这一代的表已经有 %s 了，本尺只负责首次新增" % (NEW_COLS,))
        return 9
    tip_tree = tree_of(git, tip)
    print("那一代的尖 %s｜表内 %d 条枝｜原列 %d 枚" % (tip, len(rows), len(cols)))
    values, unreachable, zero_unique = [], [], []
    for row in rows:
        name, pin = row[0], row[1].strip()
        if git("cat-file", "-e", pin).returncode != 0:
            unreachable.append("%s（pin %s 取不到）" % (name, pin[:12]))
            values.append(("-", "-"))
            continue
        tally = diff_state(git, tip, pin)
        literal_unique, _ = counts(tree_of(git, pin), tip_tree)
        values.append((str(tally["A"]), str(tally["M"])))
        if tally["A"] == 0:
            zero_unique.append(name)
        print("%-58s unique_paths %4d｜diff_files %6d｜同代另一口径：字面独有 %4d（改名配对 %d）｜既有 absorbed_on %s"
              % (name[:58], tally["A"], tally["M"], literal_unique, tally["R"],
                 (row[cols.index("absorbed_on")] or "空")[:12]))
    print("")
    print("独有路径（A，带改名识别）为零 %d 条｜非零 %d 条｜pin 取不到 %d 条"
          % (len(zero_unique), len(rows) - len(zero_unique) - len(unreachable), len(unreachable)))
    for item in unreachable:
        print("   不可得：%s" % item)
    if args.apply:
        rendered = render(cols, rows, values)
        problem = guard(source, rendered, cols)
        if problem:
            print("ABORT 写门拒：%s" % problem)
            return 9
        with open(args.apply, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(rendered)
        print("已写出：%s（%d 行，新增列 %s）" % (args.apply, rendered.count("\n"), "、".join(NEW_COLS)))
    return 4 if unreachable else 0


if __name__ == "__main__":
    sys.exit(main())
