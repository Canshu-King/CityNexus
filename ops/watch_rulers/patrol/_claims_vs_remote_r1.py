# -*- coding: utf-8 -*-
"""值守 07:15 · 落地前把每枚待插块的「枝 + 40 位」申报逐枚对远程回读（全只读）。

为什么做：07:12 收件箱 12 分钟里从 1 枚涨到 10 枚，号令者那一轮从 06:49 起还没写完账本，
他一轮读几十块时最容易漏的就是「块里写的枝尖与远程不一样」。这里只做一件事：
  ① `git fetch`（只读）后，把块里出现的每个 `refs/heads/...` 与它同段出现的 40 位配成一对，
     用一次 `git ls-remote origin` 的真实返回值核对；
  ② 块里出现的每一枚逐字 40 位，用 `git cat-file -e` 看它到底存不存在（对象库已 fetch）。
不判内容、不改字、不写账本。命中不一致就具名报，由我决定是否把原话送进那条车道。
"""
import io
import os
import re
import glob
import subprocess as sp
import sys

INBOX = r"D:/moodle/_qoder_ledger_inbox"
REPO = r"D:/moodle/CityNexus"
ENV = dict(os.environ, HTTPS_PROXY="", PYTHONIOENCODING="utf-8")
REF = re.compile(r"refs/heads/[A-Za-z0-9._/-]+")
HEX40 = re.compile(r"\b[0-9a-f]{40}\b")
GATE = re.compile(r"^[A-Za-z0-9._-]+_[0-9]{4}\.md$")


def sh(*args):
    r = sp.run(list(args), capture_output=True, text=True, encoding="utf-8",
               errors="replace", cwd=REPO, env=ENV)
    return r.returncode, (r.stdout or ""), (r.stderr or "")


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    rc, out, err = sh("git", "fetch", "origin", "--prune")
    print(("git fetch origin --prune rc=%d %s" % (rc, (err or "")[:120])).strip())
    rc, ls, err = sh("git", "ls-remote", "origin")
    remote = {}
    for line in ls.split("\n"):
        if "\t" in line:
            sha, ref = line.split("\t", 1)
            remote[ref.strip()] = sha.strip()
    print("ls-remote 一次取到 %d 枚 ref（后面全部用它，不再打网络）" % len(remote))
    TIP_REF = "refs/heads/mirror/integration-frontend-apple-pass1"
    tip = remote.get(TIP_REF, "")
    print("现尖 %s" % (tip[:40] or "取不到"))

    files = [p for p in sorted(glob.glob(os.path.join(INBOX, "*.md")))
             if GATE.match(os.path.basename(p))]
    print("待插块 %d 枚（按命名门）\n" % len(files))

    problems = 0
    notes = 0
    for p in files:
        f = os.path.basename(p)
        text = io.open(p, encoding="utf-8", errors="replace").read()
        refs = sorted(set(REF.findall(text)))
        hexes = sorted(set(HEX40.findall(text)))
        bad_ref, missing_obj, documented_del, declared, stale = [], [], [], [], []
        land = {}
        for r in refs:
            got = remote.get(r)
            # 只认「紧贴申报」：ref 名与 40 位之间不超过 60 字，且中间出现 =／头／尖 之一。
            # 早先我用「同段所有 40 位」比，结果把 merge-base、tree id、别的枝头全算成不符 —— 58 处假红。
            for m in re.finditer(re.escape(r) + r"[`\s]{0,3}(?:头|尖|＝|=)[^\n]{0,40}?\b([0-9a-f]{40})\b", text):
                c = m.group(1)
                if got is None:
                    if re.search(r"--delete[^\n]{0,80}" + re.escape(r.split("/")[-1]), text):
                        documented_del.append((r, c))
                    else:
                        bad_ref.append((r, c, "REF_NOT_ON_REMOTE 且块内没有 --delete 的记录"))
                elif c != got:
                    # 现尖一直在前移：块里那枚「开工现尖/基点」若是当前头的祖先，就是**基线过时**，
                    # 不是假申报（07:33 我先把这一形当红报过一次，s4_0721 那枚即此例）。
                    if sh("git", "merge-base", "--is-ancestor", c, got)[0] == 0:
                        stale.append((r, c, got))
                    else:
                        bad_ref.append((r, c, "!= remote 实为 " + got))
        # 落地预测：这块申报的每条 review/* 枝，对现尖只读预测能不能干净落
        for r in refs:
            got = remote.get(r)
            if not got or not r.startswith("refs/heads/review/"):
                continue
            rc2, out2, _e2 = sh("git", "merge-tree", "--write-tree", tip, got)
            cf = sorted(set(re.findall(r"^\d+ [0-9a-f]+ \d+	(.+)$", out2, re.M)))
            land[r.split("/")[-1]] = (rc2, cf)
        for h in hexes:
            if sh("git", "cat-file", "-e", h)[0] == 0:
                continue
            # 与门同口径：它自己那一行写明不可取回（本机 sha1／非 blob／不在对象库…）就不是缺陷，只算声明
            DECL = (r"本机 sha1|文件 sha1|内容 sha1|sha1 (?:over|of) bytes|本地字节重算|"
                    r"从未入 git|未入 git|不在对象库|非 blob|不是 blob|不可 cat-file|故意不可取回")
            line_has_decl = any(h in l and re.search(DECL, l) for l in text.split("\n"))
            if line_has_decl:
                declared.append(h)
            else:
                missing_obj.append(h)
        n = len(bad_ref) + len(missing_obj)
        problems += n
        notes += len(documented_del) + len(declared) + len(stale)
        flag = "OK " if n == 0 else "!! "
        print("%s%-22s refs=%d 40位=%d 申报不符=%d 未声明取不到=%d 已声明/已删记录=%d"
              % (flag, f, len(refs), len(hexes), len(bad_ref), len(missing_obj), len(declared) + len(documented_del)))
        for r, c, why in bad_ref:
            print("      枝 %s 块内紧贴申报 %s；%s" % (r, c[:12] + "…", why))
        for h in missing_obj:
            print("      40 位 %s 在 fetch 之后仍 cat-file 不到" % (h[:12] + "…"))
        for r, c2, g in stale:
            print("      基线过时（非假申报）%-46s 块内 %s… 现尖已 %s…" % (r[:46], c2[:8], g[:8]))
        for name, (rc2, cf) in land.items():
            print("      落地对现尖 %-44s rc=%d %s" % (
                name[:44], rc2, "可干净落" if rc2 == 0 else "冲突 %d 枚: %s" % (len(cf), ", ".join(x.split("/")[-1] for x in cf[:4]))))
    print("\n合计实质不一致 %d 处；另有 %d 处是块自己写明的『推错枝名后 --delete 删掉』，不算缺陷"
          % (problems, notes))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
