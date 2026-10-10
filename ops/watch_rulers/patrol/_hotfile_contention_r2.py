# -*- coding: utf-8 -*-
"""值守 09:58 · 争用尺 r2：把「三侧互异」从只看热文件扩到**该枝自己动过的每一枚文件**。

为什么改版：r1 只对三枚热文件（词典 / `styles.css` / `V8Experience`）算三侧 blob。
09:56 我把 `a68b0631` 的 `backend/app/main.py` 也量了一遍，才发现这条判据跟文件名无关——
复切器 `cmdr_recut_r1.py` 要的是「合完逐字节等于车道自己那份」，**任何**一枚文件
在 base 之后两侧都改过都会 ABORT。只看热文件会漏报（r1 就把 ORD-0445 那类
「只动注册表 + 新建目录」的枝当成无风险）。

判据（与 r1 同一套，只是覆盖面变大）：
  base == tip != lane ⇒ 只车道一侧改过 ⇒ 预测可干净合
  base != tip 且 lane != tip 且 base != lane ⇒ 两侧都改过 ⇒ 预测复切 ABORT
`git ls-tree -r` 每枚 rev 只跑一次并缓存（逐文件 `rev-parse` 在 Windows 上会把一把尺变成十分钟）。

边界：这是**只读预测**（ls-remote / ls-tree / merge-base），门的实判归 `--apply` 那一跑。
"""
import os
import re
import subprocess
import sys

REPO = r"D:/moodle/CityNexus"
ENV = dict(os.environ, HTTP_PROXY="", HTTPS_PROXY="")
TIPREF = "refs/heads/mirror/integration-frontend-apple-pass1"
HOT = {"frontend/src/i18n/LocaleContext.tsx": "词典",
       "frontend/src/styles.css": "styles.css",
       "frontend/src/app/V8Experience.tsx": "V8Experience",
       "frontend/src/design-tokens.css": "design-tokens",
       "backend/app/main.py": "main.py"}
RECR = re.compile(r"^refs/heads/review/(.*?)(?:-r(\d+))?$")
FRESH = 60          # 落后这么多笔以内才算「下一两跳真会去落的」
CACHE = {}


def run(*a):
    p = subprocess.run(list(a), capture_output=True, text=True, encoding="utf-8",
                       errors="replace", cwd=REPO, env=ENV, timeout=900)
    return p.returncode, ((p.stdout or "") + (p.stderr or "")).strip()


def tree_map(rev):
    """rev -> {path: blob40}，一枚 rev 只跑一次。"""
    if rev in CACHE:
        return CACHE[rev]
    rc, out = run("git", "ls-tree", "-r", rev)
    m = {}
    if rc == 0:
        for line in out.split("\n"):
            # 默认形："<mode> blob <sha>\t<path>"
            if "\t" not in line:
                continue
            meta, path = line.split("\t", 1)
            parts = meta.split()
            if len(parts) == 3 and parts[1] == "blob" and re.match(r"^[0-9a-f]{40}$", parts[2]):
                m[path.strip()] = parts[2]
    CACHE[rev] = m
    return m


def classify(b, l, t):
    """三侧 blob（缺位 = 空串）→ None（无争用）或 (标签, 说明)。

    10:14 修的一处假报：上一版只要「车道改过 且 现尖改过」就报风险，于是把
    **两侧改到同一字节**（改动已经落地）那一种也抓成红——实测在 `Q-ord0441-token-ladder-r2`
    上就假报了两枚（它的 `design-tokens.css`/`styles.css` 在现尖 `574f2e37…` 上已经等于它那一份）。
    复切要的是「合完逐字节等于车道自己那份」，所以真正的争用形是
    **车道改过、现尖也改过、而且两侧结果互不相同**（`l != t`）。
    """
    if l == t:
        return None                      # 结果已一致：要么已落地，要么两侧同写
    lane_changed = (l != b)
    tip_changed = (t != b)
    if not (lane_changed and tip_changed):
        return None
    if b == "":
        return ("两侧各自新建同一枚路径（内容不同）",)
    if l == "":
        return ("车道删/移，现尖又改成别的",)
    if t == "":
        return ("现尖删/移，车道又改成别的",)
    return ("三侧互异",)


def _selftest():
    ok = True
    cases = [
        # (base, lane, tip, 期望是否报风险)
        ("A", "B", "A", False),   # 只车道一侧改过 ⇒ 可干净合
        ("A", "A", "C", False),   # 只现尖改过（车道没动）⇒ 不算争用
        ("A", "B", "C", True),    # 两侧都改过且结果不同 ⇒ 预测 ABORT
        ("A", "B", "B", False),   # 两侧改到**同一字节**（改动已落地）⇒ 10:14 的假报形，必须不报
        ("", "B", "B", False),    # 两侧各自新建但内容相同 ⇒ 无争用
        ("", "B", "C", True),     # 两侧各自新建同一枚路径、内容不同
        ("", "B", "", False),     # 纯新增（base/tip 都没有）⇒ 无争用
        ("A", "", "C", True),     # 车道删、现尖改成别的
        ("A", "B", "", True),     # 车道改、现尖删
        ("A", "A", "A", False),   # 三侧相同
    ]
    for b, l, t, want in cases:
        got = classify(b, l, t) is not None
        if got != want:
            ok = False
            print("  !! 分类自测不过：base=%s lane=%s tip=%s 期望风险=%s 实得=%s" % (b, l, t, want, got))
    # ls-tree 解析自测：现尖必须能取到词典这枚路径的 40 位
    return ok


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    if not _selftest():
        print("分类器自测不过 ⇒ 不报数（宁可不出这张表，也不出一张错的）")
        return 2
    rc, ls = run("git", "ls-remote", "origin")
    if rc:
        print("ls-remote 取不到：%s" % ls[:200])
        return 1
    remote = {}
    for line in ls.split("\n"):
        if "\t" in line:
            sha, ref = line.split("\t", 1)
            remote[ref.strip()] = sha.strip()
    tip = remote.get(TIPREF, "")
    if not re.match(r"^[0-9a-f]{40}$", tip):
        print("现尖取不到")
        return 1
    tt = tree_map(tip)
    # 解析自证（两通道同读一枚）：ls-tree 表里词典这枚必须与 `rev-parse tip:path` 逐字相等，
    # 否则说明我的 ls-tree 解析式错了，整张表都不该出。
    df = "frontend/src/i18n/LocaleContext.tsx"
    rcx, xrow = run("git", "rev-parse", "%s:%s" % (tip, df))
    xrow = xrow.split("\n")[0].strip()
    if not tt or tt.get(df, "") != xrow:
        print("ls-tree 解析与 rev-parse 不一致（表里 %s / rev-parse %s，条目 %d 枚）⇒ 不报数"
              % (tt.get(df, "缺"), xrow[:40], len(tt)))
        return 2
    fams = {}
    for ref, sha in remote.items():
        m = RECR.match(ref)
        if not m:
            continue
        fam, n = m.group(1), int(m.group(2) or 1)
        if fam not in fams or n > fams[fam][0]:
            fams[fam] = (n, ref, sha)
    live = []
    for fam, (n, ref, sha) in sorted(fams.items()):
        rc2, mb = run("git", "merge-base", tip, sha)
        if rc2 or not re.match(r"^[0-9a-f]{40}$", mb):
            continue
        rc3, behind = run("git", "rev-list", "--count", "%s..%s" % (sha, tip))
        if not behind.isdigit() or int(behind) > FRESH:
            continue
        rc4, files = run("git", "diff", "--name-only", "%s..%s" % (mb, sha))
        live.append((fam, n, ref, sha, mb, int(behind),
                     [x for x in files.split("\n") if x.strip()]))
    print("现尖 %s；review/* %d 枚；**落后 <=%d 笔的活枝 %d 枚**（逐枚对它自己动过的每一枚文件算三侧）"
          % (tip[:12], sum(1 for k in remote if k.startswith("refs/heads/review/")), FRESH, len(live)))
    risky = 0
    for fam, n, ref, sha, mb, behind, files in sorted(live, key=lambda x: -len(x[6])):
        bt = tree_map(mb)
        lt = tree_map(sha)
        both, lane_only = [], []
        for f in files:
            # 缺位用空串表示「这一侧没有这枚文件」，这样新增/删除也走同一条式子。
            c = classify(bt.get(f, ""), lt.get(f, ""), tt.get(f, ""))
            if c:
                both.append((f, c[0]))
            elif bt.get(f, "") != lt.get(f, ""):
                lane_only.append(f)
        parts = []
        for f, why in both:
            h = HOT.get(f)
            parts.append("%s：%s" % ("%s（%s）" % (f, h) if h else f, why))
        tag = "；".join(parts)
        risky += 1 if both else 0
        print("  %-44s -r%-2d 头 %s 落后 %2d 笔  动 %2d 枚｜单侧改过 %d 枚｜**两侧都改过 %d 枚**%s"
              % (fam[:44], n, sha[:8], behind, len(files), len(lane_only), len(both),
                 " ← " + (tag[:220] if both else "")))
    print("小结：活枝 %d 枚，其中**预测复切会 ABORT**（至少一枚文件两侧都改过）%d 枚。"
          % (len(live), risky))
    print("边界：只读预测（ls-remote / ls-tree / merge-base / rev-list），门的实判归 `--apply`；"
          "本尺 0 次写、0 次落地、0 次动权威线。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
