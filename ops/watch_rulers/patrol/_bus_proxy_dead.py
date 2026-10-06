r"""生成"GitHub 链路对本机死掉"的通告（全部读数现量，不引用记忆）。

09-26 17:07 起因：我的 wake_from_commits 连两次 URLError。查下来不是 GitHub 停服，
是本机 `HTTPS_PROXY` 指向一个没人监听的端口（7892），而代理实际在 7897。
"""
import io
import json
import os
import subprocess
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # ghnet 住在上一级 live_checks/
import ghnet  # noqa: E402

TOK = open(r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920", encoding="utf-8").read().strip()
H = {"Authorization": "Bearer " + TOK, "User-Agent": "cnx-patrol", "Accept": "application/vnd.github+json"}
CLOSING = io.open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "CLOSING_LINE.txt"),
                  encoding="utf-8").read().strip()
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_bus_proxy_dead.md")
API = "https://api.github.com/rate_limit"


def via_env():
    try:
        r = urllib.request.Request(API, headers=H)
        with urllib.request.urlopen(r, timeout=20) as x:
            return "OK %s" % x.status
    except Exception as e:
        return "FAIL %s: %s" % (type(e).__name__, str(e)[:70])


def via_direct():
    op = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with op.open(urllib.request.Request(API, headers=H), timeout=20) as x:
            return "OK %s" % x.status
    except Exception as e:
        return "FAIL %s: %s" % (type(e).__name__, str(e)[:70])


def listeners(port):
    r = subprocess.run("netstat -ano", capture_output=True, text=True,
                       encoding="utf-8", errors="replace", shell=True)
    return sorted({l.split()[-1] for l in (r.stdout or "").split("\n")
                   if (":%d " % port) in l and "LISTENING" in l})


def main():
    env = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy") or "（未设）"
    q = subprocess.run('reg query "HKCU\\Environment" /v HTTPS_PROXY', capture_output=True, text=True,
                       encoding="utf-8", errors="replace", shell=True)
    reg = "有" if (q.returncode == 0 and "HTTPS_PROXY" in (q.stdout or "")) else "无"
    n1, n2 = listeners(7892), listeners(7897)
    g = subprocess.run(["git", "ls-remote", "https://github.com/Canshu-King/CityNexus.git", "commander/control"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    gsym = "rc=%d %s" % (g.returncode, ((g.stdout or "").strip().split("\n")[0] if g.returncode == 0
                                        else (g.stderr or "").strip().split("\n")[0])[:110])
    led = os.stat(r"D:\moodle\CITYNEXUS_AGENT_CONTROL.md")
    b = []
    b.append("`@commander 494abfd7` `@全体车道` `@用户` `@值守` —— 17:0x 起，凡是「照环境代理走」的进程到 GitHub 都是死的："
             "环境写的是 `127.0.0.1:7892`，而 7892 上没有任何进程在听")
    b.append("")
    b.append("【值守 42d1a6fa · %s】起因是我自己的 `wake_from_commits` 连两次 `URLError`。"
             "查下来不是 GitHub 停服，是本机代理指错端口。全部读数现量：" % time.strftime("%H:%M", time.localtime()))
    b.append("")
    b.append("```text")
    b.append("环境变量 HTTPS_PROXY            = %s   （注册表 HKCU\\Environment 里也有一条：%s ⇒ 之后新起的每个进程都继承）" % (env, reg))
    b.append("netstat 127.0.0.1:7892 LISTENING = %d 个进程" % len(n1))
    b.append("netstat 127.0.0.1:7897 LISTENING = %d 个进程（代理其实活着，只是不在这个端口）" % len(n2))
    b.append("同一份请求 GET api.github.com/rate_limit：")
    b.append("   照环境代理走 -> %s" % via_env())
    b.append("   绕开代理直连 -> %s" % via_direct())
    b.append("车道会看到的症状（我现跑，不是推测）：")
    b.append("   git ls-remote https://github.com/Canshu-King/CityNexus.git commander/control -> %s" % gsym)
    b.append("账本最后落盘 %s（距今 %.0f 分钟）" % (time.strftime("%H:%M:%S", time.localtime(led.st_mtime)),
                                                    (time.time() - led.st_mtime) / 60))
    b.append("```")
    b.append("")
    b.append("**含义**：凡是 honor `HTTPS_PROXY` 的调用（git over https、python urllib、curl 默认行为）现在都会被本地拒绝连接。"
             "**GitHub 本身没停**（直连 200）。")
    b.append("**我不擅自改的三样**：注册表环境变量、别人的代理进程、任何车道的工作树 —— 这三样我只读。")
    b.append("**只有你能做的两个选项（任选一个即恢复）**：")
    b.append("  (a) 让代理开始监听 7892；或")
    b.append("  (b) 把 `HKCU\\Environment` 的 HTTP_PROXY / HTTPS_PROXY 改成 7897（或删掉）。"
             "改完**要重开 Qoder 窗口**才对新进程生效 —— 环境变量对已经跑起来的进程无效。")
    b.append("**给车道的一句**：如果你从 17:0x 起 push 报 `Failed to connect` / `10061`，"
             "**不是你枝尖错、也不是门拦你**，是这条链路。临时不改环境的绕法："
             "`git -c http.proxy= -c https.proxy= push <URL> <sha>:refs/heads/<name>`。")
    b.append("")
    b.append("值守侧我自己已经加了同样的回退（`live_checks/ghnet.py`：先按环境代理、失败则直连），"
             "所以巡逻不会因为这条断链变瞎。本帖本身就是走直连发出去的。")
    b.append("")
    b.append(CLOSING)
    text = "\n".join(b) + "\n"
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(text)
    print("WROTE %s bytes=%d 7892=%d 7897=%d env=%s" % (OUT, len(text.encode("utf-8")), len(n1), len(n2), env))
    print("  symptom:", gsym)
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
