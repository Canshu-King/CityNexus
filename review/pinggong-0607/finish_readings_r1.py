# -*- coding: utf-8 -*-
"""把交块要的三份读数补齐并落进枝内：一、按 carried 列从交付后的对账表直接分桶（最有主的来源）；
二、几条被点名引用的枝在判据读数件里的真实行号；三、最新那一拍的头与形状。"""
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
TREE = "D:/moodle/_qoder_pinggong_0588"
REPO = "D:/moodle/_qoder_integration_20260919"
BARE = "D:/moodle/CityNexus"
OUT = TREE + "/review/pinggong-0607/"
HEAD = subprocess.run(["git", "-C", TREE, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()


def git(*a, cwd=REPO):
    return subprocess.run(["git", "-C", cwd] + list(a), capture_output=True, text=True,
                          encoding="utf-8", errors="replace").stdout


# 一、从交付后那枚表直接分桶
table = git("show", "%s:docs/REVOLUTION_ABSORPTION_MANIFEST.tsv" % HEAD)
rows = [ln.split("\t") for ln in table.split("\n") if ln.strip()][1:]
carried_counts, ratio_buckets = {}, {"九成以上": 0, "五到九成": 0, "一到五成": 0, "不足一成": 0, "零": 0}
for r in rows:
    carried = r[12]
    carried_counts[carried.split()[0]] = carried_counts.get(carried.split()[0], 0) + 1
    if "/" in carried:
        n, m = carried.split()[1].split("/")
        frac = float(n) / float(m) if float(m) else 0.0
        key = "零" if frac == 0 else "九成以上" if frac >= 0.9 else "五到九成" if frac >= 0.5 \
            else "一到五成" if frac >= 0.1 else "不足一成"
        ratio_buckets[key] += 1
lines = ["来源：交付后的 `docs/REVOLUTION_ABSORPTION_MANIFEST.tsv` 第 13 列（carried）逐条数出来",
         "表内数据行 %d 条" % len(rows),
         "carried 词形分布：%s" % "｜".join("%s %d 条" % (k, v) for k, v in sorted(carried_counts.items())),
         "按「自己的改动里已在线上几成」分桶：%s" % "｜".join("%s %d 条" % (k, v) for k, v in ratio_buckets.items()),
         "absorbed_on 非空 %d 条" % len([r for r in rows if r[14].strip()])]
open(OUT + "carried_distribution.txt", "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
print("\n".join(lines))

# 二、被点名引用的枝在判据读数件里的真行号
run = open(OUT + "stamp_final_run.txt", encoding="utf-8").read().split("\n")
want = ["r6-h11-r61-prep", "r77-recovery", "r38-rebase", "taskbooks"]
hits = []
for w in want:
    for number, line in enumerate(run, start=1):
        if w in line and "carried" in line:
            hits.append("%s -> %d: %s" % (w, number, line.strip()[:120]))
            break
open(OUT + "named_row_lines.txt", "w", encoding="utf-8", newline="\n").write("\n".join(hits) + "\n")
print("\n".join(hits))

# 三、最新那一拍的形状
tip = git("ls-remote", "origin", "refs/heads/mirror/integration-frontend-apple-pass1", cwd=BARE).split("\t")[0]
shape = ["现尖 %s" % tip, "枝尖 %s" % HEAD]
for label, cwd in (("bare", REPO), ("GitHub", BARE)):
    shape.append("READBACK %s：%s" % (label, git("ls-remote", "origin", "refs/heads/review/pinggong-0607-r1",
                                                 cwd=cwd).strip()))
shape.append("先人位：%s" % git("rev-list", "--left-right", "--count", "%s...%s" % (tip, HEAD)).strip())
shape.append("合流预测：%s" % git("merge-tree", "--write-tree", tip, HEAD).splitlines()[0][:60])
shape.append("工作树未登记改动 %d 处" % len([l for l in git("status", "--porcelain", cwd=TREE).split("\n") if l.strip()]))
shape.append("本枝相对现尖改动面 %d 枚" % len([l for l in git("diff", "--name-only", "%s...%s" % (tip, HEAD)).split("\n") if l.strip()]))
open(OUT + "branch_shape2.txt", "w", encoding="utf-8", newline="\n").write("\n".join(shape) + "\n")
print("\n".join(shape))
