# -*- coding: utf-8 -*-
"""值守 13:22 · 曝光面前置尺（只读）：每枚待落候选相对现尖会不会**新增**曝光格。

为什么做这件事：号令者 11:27 那块立了新规矩——「凡候选里有新增产品文件且门走过曝光面，
落地前必须自己对该文件跑一次尺并把 `cells_total` 记进账本」，而且他同一轮就是用这把尺拦下 ORD-0437 的
（tip 12 格 vs cand 14 格，集合差新增 2 格 ⇒ 退回不手合）。现在队列里躺着 8 枚候选、现尖已一小时没动，
他逐枚自跑要花时间。我这边用**同一把尺、同一个调用形**（`--ref <rev> --path <树内路径>`，
尺身份 = blob `d3f66ce9fecd0790981a4fcdeb5e36b1c0fd10f2`，与 `preflight_and_land_r5.py:43` 钉的那枚逐字相同）
先算一遍，把「哪几枚不会新增曝光格」摊出来。

边界与诚实条款：
- 尺自己的口径写在输出里：`per-file: no module graph is built here`（跨文件 helper 在一枚文件内是不透明的），
  所以我这个数是**逐枚文件对比的集合差**，不等于门在整棵树上的判语；门的实判仍归他那一跑。
- 只比候选**自己改过的** frontend/src 文件（没改的文件不可能新增格），每枚候选最多比 6 枚，超出的具名报「未比」。
"""
import json
import os
import re
import subprocess
import sys

REPO = r"D:\moodle\CityNexus"
LC = r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks"
RULER = os.path.join(LC, "ui_exposure_taint_ast_r7b.cjs")
TIPREF = "refs/heads/mirror/integration-frontend-apple-pass1"
RULER_BLOB = "d3f66ce9fecd0790981a4fcdeb5e36b1c0fd10f2"
ENV = dict(os.environ, HTTP_PROXY="", HTTPS_PROXY="")
PER_CAND = int(sys.argv[1]) if len(sys.argv) > 1 else 6


def sh(args, t=600, cwd=REPO):
    p = subprocess.run(args, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", cwd=cwd, env=ENV, timeout=t)
    return p.returncode, ((p.stdout or "") + (p.stderr or "")).strip()


def cells(rev, path):
    """跑尺，返回该文件在这一尖的 cell id 集合。

    尺的退出码语义（13:27 从 `ui_exposure_taint_ast_r7b.cjs:2155-2165` 读出来，不是我猜的）：
      0 = 正常出 JSON（`verdict` 里再分有没有格）；2 = 用法错；4 = **`git show <rev>:<path>` 取不到这个路径**，
      此时它自己发 `verdict=REFUSED, reason=… did not resolve`。
    ⇒ 4 不能当「读数不全」，它是「这一侧没有这枚文件」：车道新增的文件就属于这种，
      对侧（现尖）没有 ⇒ 这一枚的差集应当按空集算，并具名标出来。
    """
    p = subprocess.run(["node", RULER, "--ref", rev, "--path", path], capture_output=True,
                       text=True, encoding="utf-8", errors="replace", cwd=REPO, env=ENV, timeout=300)
    # 只用 stdout 解析：尺的拒绝件是打在 stdout 上的合法 JSON，而 stderr 里可能跟着 TS/Node 的杂讯，
    # 把两条流拼一起会让 json.loads 失败（13:29 我就这么把 5 枚读成了「取不到读数」）。
    rc, out = p.returncode, (p.stdout or "")
    i = out.find("{")
    body = out[i:] if i >= 0 else ""
    j = None
    if body:
        try:
            j = json.loads(body)
        except Exception:
            j = None
    if rc == 4:
        v = (j or {}).get("verdict", "")
        if v == "REFUSED":
            return set(), "该侧无此路径（尺 REFUSED：did not resolve）"
        return None, "尺退 4 且解析不出拒绝件：%s / stderr %s" % (out[:100], (p.stderr or "")[:100])
    if rc != 0 or j is None:
        return None, "尺退 %s：%s" % (rc, out[:120])
    cs = j.get("cells") or []
    return set(c.get("cell_id") or c.get("cell_identity", "?") for c in cs), j.get("verdict", "?")


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    rc, ident = sh(["git", "hash-object", os.path.join(LC, "ui_exposure_taint_ast_r7b.cjs")])
    print("尺身份 `git hash-object` = %s（门里钉的应为 %s）⇒ %s"
          % (ident[:40], RULER_BLOB, "同一把" if ident.startswith(RULER_BLOB[:12]) else "**不是同一把，别用我的数**"))
    if not ident.startswith(RULER_BLOB[:12]):
        return 2
    rc, o = sh(["git", "ls-remote", "origin", TIPREF])
    tip = (o.split() or [""])[0]
    print("现尖 `%s`" % tip[:40])

    # 候选名单：现读远端 review/*，只取近 150 分钟动过、且不在现尖上的族
    now = __import__("time").time()
    rc, ro = sh(["git", "ls-remote", "origin", "refs/heads/review/*"])
    heads = []
    for line in ro.split("\n"):
        if "\t" not in line:
            continue
        s, r = line.split("\t", 1)
        name = r.strip().replace("refs/heads/review/", "")
        if name.startswith(("cmdr-", "CMDR-")):
            continue
        ct = sh(["git", "show", "-s", "--format=%ct", s])[1].split("\n")[0]
        if not ct.isdigit() or now - int(ct) > 150 * 60:
            continue
        if sh(["git", "merge-base", "--is-ancestor", s, tip])[0] == 0:
            continue
        heads.append((name, s))
    # 同族取最新一代
    fam = {}
    for name, s in heads:
        m = re.match(r"^(.*?)(?:-r(\d+))?$", name)
        n = int(m.group(2) or 1)
        if m.group(1) not in fam or n > fam[m.group(1)][0]:
            fam[m.group(1)] = (n, name, s)
    # 13:32 修的一处判据错：`merge-base --is-ancestor 头 现尖` 会把**已落地**的候选读成未落地——
    # 复切器落地时是把枝重挂成新提交（`cmdr-recut-*`），车道原来那枚头因此不在现尖的祖先链上。
    # 所以「在不在线上」要按复切器自己的口径量：该枝改过的每一枚文件，字节是否已等于现尖那一份。
    def on_line(head, mb, files):
        bm, tm = {}, {}
        for rev, store in ((head, bm), (tip, tm)):
            rcx, ox = sh(["git", "ls-tree", "-r", rev])
            for line in ox.split("\n"):
                if "\t" not in line:
                    continue
                meta, path = line.split("\t", 1)
                parts = meta.split()
                if len(parts) == 3 and parts[1] == "blob":
                    store[path.strip()] = parts[2]
        diff = []
        for f in files:
            if bm.get(f, "") != tm.get(f, ""):
                diff.append(f)
        return diff

    real, already = [], []
    for f, (n, name, sha) in sorted(fam.items()):
        rcx, mb = sh(["git", "merge-base", tip, sha])
        rcy, fl = sh(["git", "diff", "--name-only", "%s..%s" % (mb, sha)])
        fs = [x for x in fl.split("\n") if x.strip()]
        d = on_line(sha, mb, fs)
        if not d:
            already.append((name, sha[:12], len(fs)))
        else:
            real.append((name, sha[:12], len(d), fs))
    if already:
        print("按字节量**已经在线上**（只是车道原头不是现尖祖先，被祖先判据误报成候选）%d 枚：%s"
              % (len(already), ", ".join("%s(%s,差0/%d枚)" % (x[0][:30], x[1], x[2]) for x in already[:10])))
    fam = dict((k, v) for k, v in fam.items() if v[1] in [x[0] for x in real])
    print("近 150 分钟动过、按字节**确有未落地差**、同族取最新一代的候选 %d 枚" % len(fam))

    safe, risky, partial = [], [], []
    for f, (n, name, sha) in sorted(fam.items()):
        rc2, mb = sh(["git", "merge-base", tip, sha])
        rc3, fl = sh(["git", "diff", "--name-only", "%s..%s" % (mb, sha)])
        prod = [x for x in fl.split("\n") if x.strip().startswith("frontend/src")]
        if not prod:
            safe.append((name, sha[:12], "0 枚 frontend/src 文件（纯证据/后端件）", 0, []))
            continue
        grown, seen, errs = set(), 0, []
        for p in prod[:PER_CAND]:
            hc, hv = cells(sha, p)
            tc, tv = cells(tip, p)
            if hc is None or tc is None:
                errs.append("%s：%s" % (p.split("/")[-1], (hv if hc is None else tv)))
                continue
            seen += 1
            grown |= (hc - tc)
        note = "比了 %d/%d 枚 frontend/src" % (seen, len(prod))
        if len(prod) > PER_CAND:
            note += "（其余 %d 枚未比，具名：`_landing_plan_r1.py`）" % (len(prod) - PER_CAND)
            partial.append(name)
        if grown:
            risky.append((name, sha[:12], len(grown), note, sorted(grown)[:3]))
        elif errs:
            risky.append((name, sha[:12], -1, note + "；有取不到读数的文件：" + "; ".join(errs)[:120], ["读数不全"]))
        else:
            safe.append((name, sha[:12], note, 0, []))
    print("\n**不会新增曝光格（按逐枚文件集合差）%d 枚**：" % len(safe))
    for name, s, note, _, _ in safe:
        print("  OK %-46s 头 %s  %s" % (name[:46], s, note[:80]))
    print("\n**会新增 / 或读数不全 %d 枚**：" % len(risky))
    for name, s, k, note, ids in risky:
        print("  !! %-46s 头 %s %s  %s  例：%s" % (name[:46], s, ("新增 %d 格" % k) if k >= 0 else "有文件取不到读数（不当安全，也不当新增）", note[:70], "; ".join(x[:60] for x in ids)))
    print("\n未比满的候选 %d 枚：%s" % (len(partial), ", ".join(x[:34] for x in partial[:8])))
    print("边界：只读（node 尺跑 `git show` 取 blob，不动工作树）；0 次写、0 次落地、0 次动权威线。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
