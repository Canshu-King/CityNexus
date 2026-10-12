# -*- coding: utf-8 -*-
"""revolution 对账盖章尺（ORD-0607 新增尺；不改现有任何一枚尺的字节）：
逐条现算「这枚枝自己改过哪些文件」与「其中几成今天已在权威尖上按同一枚字节存在」，
把对账表的 carried 与 absorbed_on 填成有主、可重放的读数。

判据（每条枝各算一次，全部现读；不读缓存，也不信表里既有的数）：
  · TIP  = 现尖，从 GitHub 的 refs/heads/mirror/integration-frontend-apple-pass1 现取；
  · BASE = `git merge-base TIP <pin>`：这枚枝与线上真正的分叉点（表里 fork 那列只用来对账，不参与判据）；
  · OWN  = 枝的树里 <path,blob> 与 BASE 的树不同的路径集（这枚枝自己的改动，含新增与修改）；
  · ON   = OWN 里今天在 TIP 上仍是同一枚 blob 的路径（字节级吸收；同路径不同内容不算）；
  · carried = "YES n/m"（n==m 且 m>0）｜"PART n/m"（0<n<m）｜"NO 0/m"（n==0 且 m>0）｜"NONE 0/0"（OWN 空）
    ——YES/NO 沿用表里既有词，比例是这次新添的读数；
  · absorbed_on = 只有这把尺自己算出全量在线（YES）才新盖，盖的是「把这些路径写成这枚字节的最新一枚线上提交」，
    盖之前必须 `merge-base --is-ancestor` 通过；表里已有的合法章一律原样保留——这把尺不许擦别人的章。
写门：--apply 之前逐列对账，除 carried 与 absorbed_on 之外任何一列变动都整份不写。
退出码：0 = 全表算完且每条都有判据；4 = 有枝取不到 pin 或求不出分叉点，或有退化警示；
3 = 现尖或表本身取不到；9 = 写门拒（改动面越界）。
"""
import argparse
import subprocess
import sys

GH_REF = "refs/heads/mirror/integration-frontend-apple-pass1"
MUTABLE = ("carried", "absorbed_on")


def classify(m, n):
    if m == 0:
        return "NONE 0/0"
    if n == m:
        return "YES %d/%d" % (n, m)
    if n == 0:
        return "NO 0/%d" % m
    return "PART %d/%d" % (n, m)


def guard(old_text, new_text, cols):
    """除 MUTABLE 之外的列一格都不许变；返回第一条违规说明，干净返回 None。"""
    o = [ln for ln in old_text.split("\n") if ln.strip()]
    n = [ln for ln in new_text.split("\n") if ln.strip()]
    if len(o) != len(n):
        return "行数从 %d 变成 %d" % (len(o), len(n))
    for i, (a, b) in enumerate(zip(o, n)):
        fa, fb = a.split("\t"), b.split("\t")
        if len(fa) != len(fb):
            return "第 %d 行列数不等" % i
        for c, name in enumerate(cols):
            if name not in MUTABLE and fa[c] != fb[c]:
                return "第 %d 行的 %s 列被改动（%r -> %r）" % (i, name, fa[c], fb[c])
    return None


def parse_table(text):
    lines = [ln for ln in text.split("\n") if ln.strip()]
    cols = lines[0].split("\t")
    rows = []
    for ln in lines[1:]:
        fields = ln.split("\t")
        fields += [""] * (len(cols) - len(fields))
        rows.append(dict(zip(cols, fields)))
    return cols, rows


def selftest():
    cases = [
        ((0, 0), "NONE 0/0"), ((5, 5), "YES 5/5"), ((5, 0), "NO 0/5"),
        ((5, 2), "PART 2/5"), ((6490, 6313), "PART 6313/6490"),
    ]
    bad = []
    for args, want in cases:
        got = classify(*args)
        if got != want:
            bad.append("classify%s = %s，期望 %s" % (args, got, want))
    cols = ["name", "sha", "carried", "verdict", "absorbed_on"]
    base = "\n".join(["\t".join(cols), "a\t1\tNO\tTO_ABSORB\t", "b\t2\t\tTO_ABSORB\t"]) + "\n"
    good = "\n".join(["\t".join(cols), "a\t1\tPART 2/5\tTO_ABSORB\tdeadbeef",
                      "b\t2\tNO 0/3\tTO_ABSORB\t"]) + "\n"
    if guard(base, good, cols) is not None:
        bad.append("只改两列本该放行，却被写门拒了")
    stealing = good.replace("b\t2\tNO 0/3\tTO_ABSORB", "b\t2\tNO 0/3\tDONE")
    if guard(base, stealing, cols) is None:
        bad.append("改动 verdict 列竟被放行")
    shorter = "\n".join(good.split("\n")[:2]) + "\n"
    if guard(base, shorter, cols) is None:
        bad.append("少写一行竟被放行")
    padded = "\t".join(cols) + "\n" + "a\t1\n"
    try:
        _, rows = parse_table(padded)
        if rows[0]["absorbed_on"] != "":
            bad.append("尾部空列补齐失败")
    except Exception as exc:
        bad.append("尾部空列补齐抛错：%s" % exc)
    print("SELFTEST 格子 %d，失败 %d" % (len(cases) + 4, len(bad)))
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


def last_commit_writing(git, tip, path, blob):
    found = git("log", "-1", "--format=%H", tip, "--", path).stdout.strip()
    if len(found) != 40:
        return None
    return found if git("rev-parse", "%s:%s" % (found, path)).stdout.strip() == blob else None


def stamp_candidate(git, tip, own, branch_tree):
    newest = None
    for path in sorted(own):
        commit = last_commit_writing(git, tip, path, branch_tree[path])
        if commit is None:
            return None
        if newest is None:
            newest = commit
        elif git("merge-base", "--is-ancestor", newest, commit).returncode == 0:
            newest = commit
        else:
            return None
    return newest


def run(git, tip, cols, rows, tip_tree, apply_path, source_text):
    full, partial, noneed, unreachable, regress, kept = [], [], [], [], [], []
    for row in rows:
        name, pin = row["name"], row["sha"].strip()
        if git("cat-file", "-e", pin).returncode != 0:
            unreachable.append("%s（pin %s 取不到）" % (name, pin[:12]))
            continue
        base = git("merge-base", tip, pin).stdout.strip()
        if len(base) != 40:
            unreachable.append("%s（merge-base 求不出）" % name)
            continue
        base_tree, branch_tree = tree_of(git, base), tree_of(git, pin)
        own = {p: b for p, b in branch_tree.items() if base_tree.get(p) != b}
        on = [p for p, b in own.items() if tip_tree.get(p) == b]
        m, n = len(own), len(on)
        carried = classify(m, n)
        stamp = ""
        if carried.startswith("YES"):
            cand = stamp_candidate(git, tip, own, branch_tree)
            if cand and git("merge-base", "--is-ancestor", cand, tip).returncode == 0:
                stamp = cand
            else:
                regress.append("%s 全量在线但盖代取不到（不新盖）" % name)
        old = row.get("absorbed_on", "").strip()
        if old:
            if git("merge-base", "--is-ancestor", old, tip).returncode != 0:
                regress.append("%s 表里既有 absorbed_on %s 不是现尖祖先" % (name, old[:12]))
            else:
                stamp = old
                kept.append(name)
        row["_carried"], row["_absorbed_on"] = carried, stamp
        if carried.startswith("YES"):
            full.append(name)
        elif carried.startswith("PART") or carried.startswith("NO"):
            partial.append(name)
        else:
            noneed.append(name)
        print("%-58s 自改 %5d｜在线上 %5d｜carried %-15s｜absorbed_on %s"
              % (name[:58], m, n, carried, stamp[:12] if stamp else "-"))
    print("")
    print("分布：全量在线上 %d 条｜部分或未吸收 %d 条｜无自改 %d 条｜数据不可得 %d 条"
          % (len(full), len(partial), len(noneed), len(unreachable)))
    print("既有章原样保留 %d 条（这把尺不擦别人的章）" % len(kept))
    for item in unreachable:
        print("   不可得：%s" % item)
    for line in regress:
        print("   警示：%s" % line)
    if apply_path:
        out = ["\t".join(cols)]
        for row in rows:
            body = dict(row)
            for c in MUTABLE:
                body[c] = row["_" + c]
            out.append("\t".join(body[c] for c in cols))
        rendered = "\n".join(out) + "\n"
        problem = guard(source_text, rendered, cols)
        if problem:
            print("ABORT 写门拒：%s" % problem)
            return 9
        with open(apply_path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(rendered)
        print("已写出盖章副本：%s（%d 行，只动 %s 两列）" % (apply_path, len(out), "、".join(MUTABLE)))
    return 4 if (unreachable or regress) else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default="D:/moodle/_qoder_integration_20260919")
    ap.add_argument("--work", default="D:/moodle/CityNexus")
    ap.add_argument("--apply", default=None, help="把盖好章的表写到这个路径（不动仓库里那枚）")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    git = build(args.repo, args.work)
    tip = read_tip(git, args.work)
    if tip is None:
        print("ABORT 现尖取不到")
        return 3
    source = git("show", "%s:docs/REVOLUTION_ABSORPTION_MANIFEST.tsv" % tip).stdout
    if not source:
        print("ABORT 对账表取不到")
        return 3
    cols, rows = parse_table(source)
    print("现尖 %s｜表内 %d 条枝｜列 %d 枚" % (tip, len(rows), len(cols)))
    return run(git, tip, cols, rows, tree_of(git, tip), args.apply, source)


if __name__ == "__main__":
    sys.exit(main())
