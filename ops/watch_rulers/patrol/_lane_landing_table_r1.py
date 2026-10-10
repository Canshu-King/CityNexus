# -*- coding: utf-8 -*-
"""车道候选枝的「能不能干净落」表（只读，供号令者一次看完，不用逐枚试）。

用法：_lane_landing_table_r1.py <枝名前缀，如 map-ord>
判据分两问，绝不混说：
  A 已落=产品字节是否已与现尖逐位相同（逐文件比 blob，不比 commit 祖先——
    recut 会重父，`merge-base --is-ancestor` 会把已落的判成没落）；
  B 能不能干净落=本机 `git merge-tree --write-tree` 预测；本机没这些对象时
    改走 GitHub API compare，并具名渠道。**两条都是预测，不是落地**。
0 次 fetch、0 次写 ref、0 次动工作树。
"""
import io
import json
import os
import ssl
import subprocess
import sys
import time
import urllib.request as U

REPO = r"D:\moodle\CityNexus"
PRODUCT = ("frontend/src/", "backend/app/", "contracts/", "frontend/e2e/", "backend/tests/")
ENV = dict(os.environ)
for k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
    ENV.pop(k, None)


def sh(a, t=240):
    p = subprocess.run(a, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", env=ENV, cwd=REPO, timeout=t)
    return p.returncode, (p.stdout or "").strip(), (p.stderr or "").strip()


def api(path):
    tok = io.open(r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920", encoding="utf-8").read().strip()
    op = U.build_opener(U.ProxyHandler({}), U.HTTPSHandler(context=ssl.create_default_context()))
    r = U.Request("https://api.github.com" + path,
                  headers={"Authorization": "Bearer " + tok, "User-Agent": "cnx-patrol",
                           "Accept": "application/vnd.github+json"})
    return U.urlopen  # placeholder, unused


def api_get(path):
    tok = io.open(r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920", encoding="utf-8").read().strip()
    op = U.build_opener(U.ProxyHandler({}), U.HTTPSHandler(context=ssl.create_default_context()))
    req = U.Request("https://api.github.com" + path,
                    headers={"Authorization": "Bearer " + tok, "User-Agent": "cnx-patrol",
                             "Accept": "application/vnd.github+json"})
    return json.loads(op.open(req, timeout=120).read().decode())


def main():
    pref = sys.argv[1] if len(sys.argv) > 1 else "map-ord"
    tip = api_get("/repos/Canshu-King/CityNexus/git/ref/heads/"
                  "mirror/integration-frontend-apple-pass1")["object"]["sha"]
    print("现尖（发出/打印这一刻 API 现读）%s  @%s" % (tip, time.strftime("%H:%M:%S")))
    rc, out, err = sh(["git", "ls-remote", "origin"])
    heads = {}
    for l in out.split(chr(10)):
        if "\trefs/heads/" in l:
            s, _, n = l.partition("\t")
            n = n.strip()[len("refs/heads/"):]
            if n.startswith(pref):
                heads[n] = s
    print("前缀 %s 命中的远端枝 %d 枚" % (pref, len(heads)))
    if not heads:
        print("分母 0 ⇒ 本表不成立（可能是前缀挑错，不是车道没交）")
        return 3
    for name in sorted(heads):
        h = heads[name]
        have = sh(["git", "cat-file", "-t", h])[0] == 0 and sh(["git", "cat-file", "-t", tip])[0] == 0
        # A：这枚候选**自己改了哪些文件**，逐个与现尖的 blob 比——
        #    相同＝内容已在尖上（落过）；不同/尖上无＝尚未落地，那才是号令者要裁的面。
        #    不能直接 diff tip..head：那会把「尖比枝新」的工作也算成差异（第一版就报出 118 个假差异）。
        prod_same, prod_diff = [], []
        chanA = "本机对象库"
        if sh(["git", "cat-file", "-t", h])[0] == 0 and sh(["git", "cat-file", "-t", tip])[0] == 0:
            base = sh(["git", "merge-base", tip, h])[1]
            rc2, names, _ = sh(["git", "diff", "--name-only", base, h])
            pl = [x for x in names.split(chr(10)) if x.strip()]
            for f in pl:
                if not f.startswith(PRODUCT):
                    continue
                a = sh(["git", "rev-parse", "%s:%s" % (tip, f)])[1]
                b = sh(["git", "rev-parse", "%s:%s" % (h, f)])[1]
                if a and a == b:
                    prod_same.append(f)
                else:
                    prod_diff.append(f)
            chanA = "本机 diff(base=merge-base %s) + 逐文件 blob 对尖" % (base[:12] or "取不到")
        else:
            try:
                cmpy = api_get("/repos/Canshu-King/CityNexus/compare/%s...%s" % (tip, h))
                files = cmpy.get("files") or []
                prod_diff = [f["filename"] for f in files if f["filename"].startswith(PRODUCT)]
                chanA = "GitHub API compare（本机无对象）"
            except Exception as ex:
                print("   %-46s 头 %s 读数不可得：%s" % (name, h[:12], type(ex).__name__))
                continue
        # B：能否干净落
        if have:
            rc3, mt, mte = sh(["git", "merge-tree", "--write-tree", tip, h])
            if rc3 == 0:
                b_txt = "干净（merge-tree rc=0）"
                conf = []
            elif rc3 == 1:
                conf = [x for x in mt.split(chr(10))[1:] if x.strip()]
                b_txt = "冲突 %d 处" % max(1, len(conf))
            else:
                b_txt = "rc=%d 不可判" % rc3
                conf = []
            chanB = "本机 merge-tree 预测"
        else:
            b_txt, conf, chanB = "本机无对象 ⇒ 未测", [], "未测（不 fetch 共享仓）"
        print("   %-46s 头 %s" % (name, h[:12]))
        print("        A 本枝改到的产品面 %d 个：尖上已同 %d 个 / 未落 %d 个（渠道：%s）" % (
            len(prod_same) + len(prod_diff), len(prod_same), len(prod_diff), chanA))
        for f in prod_diff[:8]:
            print("          - 未落 " + f)
        if len(prod_diff) > 8:
            print("          …另有 %d 个未落" % (len(prod_diff) - 8))
        # C：这枚头是否已在尖的历史里；若已在，它**自己那一笔**改到的文件现在还与尖同不同
        #    ——这就是车道问的 merged==mine：已落的枝可能被后来的跳覆盖，"在历史里"不等于"我的字节还在"。
        isanc = sh(["git", "merge-base", "--is-ancestor", h, tip])[0] == 0
        rc4, own, _ = sh(["git", "show", "--name-only", "--format=", h])
        ownp = [x for x in own.split(chr(10)) if x.strip() and x.startswith(PRODUCT)]
        still, gone = [], []
        for f in ownp:
            a = sh(["git", "rev-parse", "%s:%s" % (tip, f)])[1]
            b = sh(["git", "rev-parse", "%s:%s" % (h, f)])[1]
            (still if (a and a == b) else gone).append(f)
        print("        C 头是否已在尖历史里：%s｜该头这一笔改到的产品文件 %d 个：与尖逐位相同 %d / 已被后来覆盖或尖上无 %d"
              % ("是" if isanc else "否", len(ownp), len(still), len(gone)))
        for f in gone[:5]:
            print("          ~ 已不同 " + f)
        print("        B %s（渠道：%s）" % (b_txt, chanB))
        for c in conf[:4]:
            print("          ! " + c[:120])
    print("边界：两问都是**预测**，不是落地；权威线只由号令者移动。0 fetch / 0 写 ref / 0 动工作树。")
    return 0


sys.exit(main())
