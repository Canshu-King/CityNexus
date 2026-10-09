# -*- coding: utf-8 -*-
u"""第四栋楼 · 第一格：清点我名下所有尺的坐标现状——哪些是本机路径（取不回）、哪些已可 cat-file。

图纸（账本 `## ORDERS` 段，23:0x 号令者派单）：
  「把你名下所有尺的读数出处，都改成权威线上真实可取回的那个对象（把尺本体随块推上枝、
    块里改引枝上的提交），并给尺的每一类读数配一条『该红的那一次』的反例臂。」

这一格只做**清点**：出一张表，逐把尺说清「它引用了几个本机坐标 / 几个可取回坐标」。
不清点就动手改 = 又一轮猜（今晚我已经猜错好几次）。

口径（写下来，下一班照这个量）：
  · **本机坐标**：`D:/moodle…`、`D:\\moodle…`、`~/.qoder…`、`~/…`、`C:/Users…` 开头的路径，
    以及 `某个.py:行号` 这种**只在本机存在**的文件行号 ⇒ 交出去别人取不回。
  · **可取回坐标**：40 位 sha（能 `git cat-file`）、`refs/heads/…`、blob id、
    以及 `某文件.py:行号` 但那个文件**已入 git**（⇒ 行号可 cat-file 定位）。
  · **可推**：这枝归我带、我能把新文件推上去 ⇒ 这是"改成可取回"的手段。

输出：`_coordinate_audit_1.json`（机器读）+ 一张给人看的表（stdout）。
"""
import io
import json
import os
import re
import subprocess
import time

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "_coordinate_audit_1.json")

LOCAL_PAT = re.compile(r"(?:[A-Za-z]:[\\/]moodle|[A-Za-z]:[\\/]Users|~[\\/])")
SHA40 = re.compile(r"\b[0-9a-f]{40}\b")
FILELINE = re.compile(r"([\w./\\-]+\.(?:py|md|bat|txt|json|jsonl)):(\d+)")
REFS = re.compile(r"refs/heads/[\w./-]+")
REPO = r"D:\moodle\CityNexus"
TIP = "refs/remotes/origin/mirror/integration-frontend-apple-pass1"


def tracked_paths():
    r = subprocess.run(["git", "ls-tree", "-r", "--name-only", TIP],
                       cwd=REPO, capture_output=True, timeout=180)
    if r.returncode != 0:
        return None
    return set(r.stdout.decode("utf-8", "replace").splitlines())


def main():
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    tracked = tracked_paths()
    print(u"现读 %s｜权威镜枝 %s" % (now, TIP))
    if tracked is None:
        print(u"REFUSE：读不到权威树的路径表，本格不许出手（没有基准就量不出差别）")
        return 1
    print(u"权威树里 %d 枚路径可作可取回坐标的落点" % len(tracked))

    rows = []
    for f in sorted(os.listdir(HERE)):
        if not (f.endswith(".py") or f.endswith(".md") or f.endswith(".bat")):
            continue
        p = os.path.join(HERE, f)
        try:
            t = io.open(p, encoding="utf-8", errors="replace").read()
        except Exception:
            continue
        loc = len(LOCAL_PAT.findall(t))
        sha = len(SHA40.findall(t))
        refs = len(REFS.findall(t))
        fl = FILELINE.findall(t)
        # 这一行引用的文件，若在权威树里 ⇒ 可 cat-file；否则取不回
        retrievable = sum(1 for name, _ln in fl
                          if any(x.endswith(name) or name.endswith(x) for x in tracked))
        rows.append({"file": f, "local_paths": loc, "sha40": sha, "refs": refs,
                     "file_line": len(fl), "file_line_retrievable": retrievable})
        rows[-1]["unretrievable"] = max(0, len(fl) - retrievable)

    tot_local = sum(r["local_paths"] for r in rows)
    tot_sha = sum(r["sha40"] for r in rows)
    tot_unretr = sum(r["unretrievable"] for r in rows)
    print()
    print(u"%-46s %6s %5s %6s %8s %9s"
          % (u"文件", u"本机路径", u"40位", u"refs", u"行号引用", u"取不回的"))
    for r in sorted(rows, key=lambda x: -(x["local_paths"] + x["unretrievable"]))[:20]:
        print(u"%-46s %6d %5d %6d %8d %9d"
              % (r["file"][:46], r["local_paths"], r["sha40"], r["refs"],
                 r["file_line"], r["unretrievable"]))
    print()
    print(u"合计：本机路径当坐标 **%d** 处｜可取回的 40 位 **%d** 处｜取不回的 file:行 **%d** 处"
          % (tot_local, tot_sha, tot_unretr))
    print(u"（分母＝本目录 %d 个 .py/.md/.bat 文件）" % len(rows))

    with io.open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps({"at": now, "tip": TIP, "tracked_paths": len(tracked),
                             "totals": {"local_paths": tot_local, "sha40": tot_sha,
                                        "unretrievable": tot_unretr},
                             "rows": rows}, ensure_ascii=False, indent=1))
    print(u"已写 %s" % os.path.basename(OUT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())