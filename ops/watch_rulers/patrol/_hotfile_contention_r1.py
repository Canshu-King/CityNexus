# -*- coding: utf-8 -*-
"""值守 08:46 · 热文件争用尺（只读；给落地顺序用）。

号令者 08:27 那块原话：「**词典这一枚文件已经连续咬过 ORD-0418、ORD-0436 两单**……
词典文件是我当前的串行点」。他一轮要过十几枚候选，顺序错了就是 ABORT + 让车道 rebase，
一条车道一次 rebase 就是几十分钟与一整个回合。所以这把尺每次跳前量三件事：
  ① 每条在线 `review/*` 枝的头改了哪几枚**热文件**（`LocaleContext.tsx` / `styles.css` / `V8Experience.tsx`）；
  ② 该枝对现尖 `git merge-tree` 的只读预测（干净 / 冲突几枚）；
  ③ 该枝比现尖落后几笔（`rev-list --count`），用来分辨「旧代枝」与「在跑的枝」。
只报每枝**最新那一代**（`-rN` 取最大 N），旧代枝列在一起当历史，免得把已弃用的枝当争用源。
"""
import os
import re
import subprocess
import sys

REPO = r"D:/moodle/CityNexus"
ENV = dict(os.environ, HTTPS_PROXY="", PYTHONIOENCODING="utf-8")
HOT = {"frontend/src/i18n/LocaleContext.tsx": "词典",
       "frontend/src/styles.css": "styles.css",
       "frontend/src/app/V8Experience.tsx": "V8Experience"}
RECR = re.compile(r"^refs/heads/review/(.*?)(?:-r(\d+))?$")


def run(*a):
    r = subprocess.run(list(a), capture_output=True, text=True, encoding="utf-8",
                       errors="replace", cwd=REPO, env=ENV)
    return r.returncode, ((r.stdout or "") + (r.stderr or "")).strip()


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    rc, ls = run("git", "-c", "http.proxy=", "-c", "https.proxy=", "ls-remote", "origin")
    if rc:
        print("ls-remote 取不到：%s" % ls[:200])
        return 1
    remote = {}
    for line in ls.split("\n"):
        if "\t" in line:
            sha, ref = line.split("\t", 1)
            remote[ref.strip()] = sha.strip()
    tip = remote.get("refs/heads/mirror/integration-frontend-apple-pass1", "")
    print("现尖 %s；review/* %d 枚" % (tip[:12], sum(1 for k in remote if k.startswith("refs/heads/review/"))))
    # 同一族枝只取最大 -rN
    fams = {}
    for ref, sha in remote.items():
        m = RECR.match(ref)
        if not m:
            continue
        fam, n = m.group(1), int(m.group(2) or 1)
        if fam not in fams or n > fams[fam][0]:
            fams[fam] = (n, ref, sha)
    hot_fams, clean = [], 0
    for fam, (n, ref, sha) in sorted(fams.items()):
        rc2, mb = run("git", "merge-base", tip, sha)
        if rc2:
            continue
        rc3, files = run("git", "diff", "--name-only", "%s..%s" % (mb, sha))
        fl = [x for x in files.split("\n") if x.strip()]
        hits = [HOT[h] for h in HOT if h in fl]
        rc4, behind = run("git", "rev-list", "--count", "%s..%s" % (sha, tip))
        if hits:
            hot_fams.append((fam, n, sha[:8], hits, behind.strip()))
        else:
            clean += 1
    FRESH = 60   # 落后这么多笔以内才算「下一两跳真的会去落的」；更老的是旧代，只计数
    # 关键一条（08:55 实测出来的）：`merge-tree rc=0` 不等于能落。复切器 `cmdr_recut_r1.py`
    # 的判据是「合完要逐字节等于车道自己那份」，所以某枚热文件在 **base 之后两侧都改过** 时，
    # 即使完全不冲突也会被 ABORT（ORD-0436 的 `-r2` 就是这个形状，我差点用 merge-tree 的绿去报平安）。
    def recut_risk(sha, mb, files):
        risky = []
        for f, tag in HOT.items():
            if f not in files:
                continue
            _, base_b = run("git", "rev-parse", "%s:%s" % (mb, f))
            _, lane_b = run("git", "rev-parse", "%s:%s" % (sha, f))
            _, tip_b = run("git", "rev-parse", "%s:%s" % (tip, f))
            if not base_b or not lane_b or not tip_b:
                risky.append((tag, "取不到 blob"))
            elif base_b != lane_b and base_b != tip_b and lane_b != tip_b:
                risky.append((tag, "两侧都改过 base ⇒ 复切大概率 ABORT"))
            elif base_b != lane_b:
                risky.append((tag, "只有一侧改过 ⇒ 可干净合"))
        return risky

    live = [x for x in hot_fams if x[4].isdigit() and int(x[4]) <= FRESH]
    old = [x for x in hot_fams if x not in live]
    print("不碰热文件的枝族 %d 个；碰热文件的 %d 个，其中**下一两跳真会碰到的** %d 个："
          % (clean, len(hot_fams), len(live)))
    for fam, n, sha, hits, behind in sorted(live, key=lambda x: -len(x[3])):
        rc2, mb = run("git", "merge-base", tip, sha)
        rc3, files = run("git", "diff", "--name-only", "%s..%s" % (mb, sha)) if mb else (1, "")
        fl = [x for x in files.split("\n") if x.strip()]
        risk = recut_risk(sha, mb, fl)
        print("   %-46s -r%-2d 头 %s 落后 %s 笔  %s"
              % (fam[:46], n, sha[:8], behind, "；".join("%s：%s" % (a, b) for a, b in risk) or "—"))
    print("   （旧代 %d 个：落后 >%d 笔，只计数不列，避免把已弃用的枝当争用源）" % (len(old), FRESH))
    print("\n落地顺序建议（不替你决定，只是数出来的）：先落不碰词典的，"
          "再落碰词典的；同文件多枝时，后落的必然要 rebase。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
