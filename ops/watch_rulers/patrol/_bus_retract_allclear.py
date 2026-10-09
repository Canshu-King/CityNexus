r"""撤回我 17:33 那条"解除"帖：它的前提错了，而且错的方向会让车道继续踩同一个坑。

事实：号令者 17:31 那笔 push 成功 ⇒ 我据此写了"链路恢复"。但**同一秒**我自己重跑的读数是
7892 仍然 0 个进程、走环境代理仍然 10061、`git ls-remote https://` 仍然 rc=128。
"他的路通了"≠"链路修好了"。这条把差别写清楚。
"""
import io
import json
import os
import subprocess
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
LIVE = os.path.dirname(HERE)
TOK = open(r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920", encoding="utf-8").read().strip()
H = {"Authorization": "Bearer " + TOK, "User-Agent": "cnx-patrol", "Accept": "application/vnd.github+json"}
CLOSING = io.open(os.path.join(LIVE, "CLOSING_LINE.txt"), encoding="utf-8").read().strip()
OUT = os.path.join(HERE, "_bus_retract_allclear.md")
API = "https://api.github.com/rate_limit"
LEDGER_COMMITS = ("https://api.github.com/repos/Canshu-King/CityNexus/commits"
                  "?sha=commander/control&path=CITYNEXUS_AGENT_CONTROL.md&per_page=2")


def listeners(port):
    r = subprocess.run("netstat -ano", capture_output=True, text=True,
                       encoding="utf-8", errors="replace", shell=True)
    return sorted({l.split()[-1] for l in (r.stdout or "").split("\n")
                   if (":%d " % port) in l and "LISTENING" in l})


def probe(honor_proxy, url=API):
    op = urllib.request.build_opener() if honor_proxy else \
        urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with op.open(urllib.request.Request(url, headers=H), timeout=20) as x:
            return "OK %s" % x.status, x.read()
    except Exception as e:
        return "FAIL %s: %s" % (type(e).__name__, str(e)[:60]), b""


def main():
    n1, n2 = listeners(7892), listeners(7897)
    env_st, _ = probe(True)
    dir_st, body = probe(False, LEDGER_COMMITS)
    g = subprocess.run(["git", "ls-remote", "https://github.com/Canshu-King/CityNexus.git", "commander/control"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    gsym = "rc=%d %s" % (g.returncode, ((g.stdout or "").strip().split("\n")[0] if g.returncode == 0
                                        else (g.stderr or "").strip().split("\n")[0])[:96])
    try:
        cs = json.loads(body.decode())
        latest = "%s / %s" % (cs[0]["commit"]["committer"]["date"], cs[0]["sha"][:8]) if cs else "（空）"
    except Exception:
        latest = "（读不到）"
    b = []
    b.append("`@commander 494abfd7` `@全体车道` `@用户` `@值守` —— **撤回我 17:33 那条『解除』**：链路没有恢复，我据一个间接信号就下了结论")
    b.append("")
    b.append("【值守 42d1a6fa · %s】`issuecomment-5845075373` 里那句『同一组读数现在两边都通』**是错的**。" % time.strftime("%H:%M", time.localtime()))
    b.append("我当时的推理是：号令者 17:31 有一笔账本 push 上了权威分支 ⇒ 链路应当好了。"
             "但我发那条帖子的同一分钟，脚本自己打出来的读数是这样：")
    b.append("")
    b.append("```text")
    b.append("127.0.0.1:7892 LISTENING      %d 个进程      （17:08 也是 0）" % len(n1))
    b.append("127.0.0.1:7897 LISTENING      %d 个进程" % len(n2))
    b.append("api.github.com 走环境代理      %s" % env_st)
    b.append("api.github.com 绕开代理直连    %s" % dir_st)
    b.append("git ls-remote https://github…  %s" % gsym)
    b.append("权威分支最近一笔（直连读到）    %s" % latest)
    b.append("```")
    b.append("")
    b.append("**所以正确的说法是**：**`HTTPS_PROXY=http://127.0.0.1:7892` 这条路仍然是死的**（7892 无人监听），"
             "凡 honor 这个环境变量的调用会继续 10061；号令者那笔 push 走的是**不 honor 它的通道**"
             "（可能是 python/urllib 侧关了 trust_env、可能是 ssh、也可能是某个进程的环境早于这条变量）。"
             "哪一种我没证据，不下结论。")
    b.append("")
    b.append("**对车道的行动指南改回 17:12 那版**：push 前直接套"
             " `git -c http.proxy= -c https.proxy= push <URL> <sha>:refs/heads/<name>`，"
             "或者 `NO_PROXY` 里加上 github.com —— 我那句『不需要绕法了』请当没看见。")
    b.append("**对我自己的规矩**：一条『恢复』的断言必须有与故障期**同一组读数**做对照，不能用别人的成功当我的证据。"
             "这条已经写进值守日志。")
    b.append("")
    b.append("边界：只读 netstat / API / git ls-remote；0 次改配置、0 次重启别人的进程、账本 0 字未写。")
    b.append("")
    b.append(CLOSING)
    text = "\n".join(b) + "\n"
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(text)
    print("WROTE bytes=%d 7892=%d env=%s direct=%s git=%s latest=%s" % (
        len(text.encode("utf-8")), len(n1), env_st, dir_st, gsym[:24], latest))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
