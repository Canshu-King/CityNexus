# -*- coding: utf-8 -*-
u"""终值单第 2 格：把"取尖"与"拉 commits 列表"拆成两段，别让一格拖累另一格。

成因（10-06 17:18 实跑夜班终值尺发现）：那一格里两次 API 调用被绑在**同一个 try** 里——
先取尖（成功了，`sha` 已经拿到、`tip_line` 已赋值），紧接着拉 100 条 commits；
第二次响应体大到读不完就 `IncompleteRead(322868 bytes read, 63581 more expected)`，
异常把整块打回 `tip_line = "读数不全"`，于是**明明已经取到的 40 位尖被一起抹掉了**，
终值单那一格整夜空着（今晚 23:20 那档本来还会再空一次）。

修法（只动这一格）：
  一、取尖与拉 commits 各包各的 try：取尖成功就落定；commits 拉不到只写「窗口内提交读数不全」，
     尖那一半照旧是真值。
  二、兜底：两次 API 都失败时，用 `git ls-remote` 现读同一枝（清代理），
     至少把尖保住——第 2 格补件那一路就是这么拿到完整 40 位的，它证明这条路可靠。
判据一处没改：拉不到 commits 时**不许编窗口内提交数**，写"读数不全"。

跑法：python _patch_verdict_tip_isolation_r1.py --check / 直接跑
"""
import ast
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
T = os.path.join(HERE, "night_verdict_r2.py")

OLD = u'''    req2 = urllib.request.Request("https://api.github.com/repos/%s/commits?sha=%s&per_page=100" % (PROD, sha),
                                  headers={"Authorization": "token " + tok, "Accept": "application/vnd.github+json",
                                           "User-Agent": "night-verdict"})
    cs = json.loads(op.open(req2, timeout=60).read().decode())
    n = 0
    for c in cs:
        src = c.get("commit") or c
        ad = (src.get("author") or {}).get("date") or ""
        try:
            e = time.mktime(time.strptime(ad, "%Y-%m-%dT%H:%M:%SZ")) - time.timezone
        except Exception:
            continue
        if e_frm <= e <= e_cap:
            n += 1
            sub_by_hour[time.strftime("%H", time.localtime(e))] = sub_by_hour.get(time.strftime("%H", time.localtime(e)), 0) + 1
    tip_line += "；窗口内提交 %d 笔（%s）" % (n, "、".join("%s 时 %d" % (h, k) for h, k in sorted(sub_by_hour.items())) or "无")
except Exception as exc:
    tip_line = "API 读数不全：%s: %s" % (exc.__class__.__name__, str(exc)[:90])'''

NEW = u'''    # 10-06 17:2x 修：下面这次 commits 列表**单独**一个 try。
    # 原来它跟"取尖"共用一个 try，第二次调用读不完（IncompleteRead 322868/63581）就把整块打回
    # "读数不全"，连已经取到的 40 位尖一起抹掉 ⇒ 终值单这一格整夜空着。
    # 现在：尖保住，拉不到列表只让"窗口内提交"那一小段写不可得（不许编数）。
    try:
        req2 = urllib.request.Request("https://api.github.com/repos/%s/commits?sha=%s&per_page=100" % (PROD, sha),
                                      headers={"Authorization": "token " + tok, "Accept": "application/vnd.github+json",
                                               "User-Agent": "night-verdict"})
        cs = json.loads(op.open(req2, timeout=60).read().decode())
        n = 0
        for c in cs:
            src = c.get("commit") or c
            ad = (src.get("author") or {}).get("date") or ""
            try:
                e = time.mktime(time.strptime(ad, "%Y-%m-%dT%H:%M:%SZ")) - time.timezone
            except Exception:
                continue
            if e_frm <= e <= e_cap:
                n += 1
                sub_by_hour[time.strftime("%H", time.localtime(e))] = sub_by_hour.get(time.strftime("%H", time.localtime(e)), 0) + 1
        tip_line += "；窗口内提交 %d 笔（%s）" % (n, "、".join("%s 时 %d" % (h, k) for h, k in sorted(sub_by_hour.items())) or "无")
    except Exception as exc:
        tip_line += "；窗口内提交读数不全：%s: %s（尖是上头 API 现读的真值）" % (
            exc.__class__.__name__, str(exc)[:70])
except Exception as exc:
    # 兜底：连尖都没取到 ⇒ 用 ls-remote 现读同一枝，把尖保住。
    # 这条路是 `_night_tip_local_r1.py` 每晚都在走的那条（17:18 实跑拿到完整 40 位），不是新假设。
    _lr = subprocess.run(["git", "-C", "D:/moodle/CityNexus", "ls-remote", "origin",
                          "refs/heads/mirror/integration-frontend-apple-pass1"],
                         capture_output=True, timeout=180,
                         env=dict(os.environ, GIT_TERMINAL_PROMPT="0", HTTP_PROXY="", HTTPS_PROXY=""))
    _sha = ((_lr.stdout or b"").decode("utf-8", "replace").split() or [""])[0]
    tip_line = ("%s（ls-remote 兜底现读；API 读数不全：%s: %s）" % (_sha, exc.__class__.__name__, str(exc)[:60])
                if len(_sha) == 40 else
                "API 与 ls-remote 都读不到尖：%s: %s ⇒ 这一格不可得，不许拿旧值充数"
                % (exc.__class__.__name__, str(exc)[:90]))'''


def main():
    t = io.open(T, encoding="utf-8").read()
    if u"ls-remote 兜底现读" in t:
        print("已装过（文件里有 ls-remote 兜底），不重复写")
        return 0
    n = t.count(OLD)
    if n != 1:
        print("REFUSE：那段锚命中 %d 次，要 1 次 ⇒ 未写盘" % n)
        return 1
    new = t.replace(OLD, NEW)
    ast.parse(new)
    if "--check" in sys.argv:
        print("--check：锚逐字命中一次、替换后 ast 过（未写盘）")
        return 0
    io.open(T, "w", encoding="utf-8", newline="\n").write(new)
    print("已写 night_verdict_r2.py：取尖与拉 commits 拆开＋ls-remote 兜底")
    return 0


if __name__ == "__main__":
    sys.exit(main())
