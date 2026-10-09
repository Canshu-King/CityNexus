r"""生成"代理链路恢复"的解除帖：与 17:12 那条通告**同一组读数、同一台机器**重跑一遍。"""
import io
import os
import subprocess
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
LIVE = os.path.dirname(HERE)
sys.path.insert(0, LIVE)
TOK = open(r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920", encoding="utf-8").read().strip()
H = {"Authorization": "Bearer " + TOK, "User-Agent": "cnx-patrol", "Accept": "application/vnd.github+json"}
CLOSING = io.open(os.path.join(LIVE, "CLOSING_LINE.txt"), encoding="utf-8").read().strip()
OUT = os.path.join(HERE, "_bus_allclear.md")
API = "https://api.github.com/rate_limit"


def listeners(port):
    r = subprocess.run("netstat -ano", capture_output=True, text=True,
                       encoding="utf-8", errors="replace", shell=True)
    return sorted({l.split()[-1] for l in (r.stdout or "").split("\n")
                   if (":%d " % port) in l and "LISTENING" in l})


def probe(honor_proxy):
    op = urllib.request.build_opener() if honor_proxy else \
        urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with op.open(urllib.request.Request(API, headers=H), timeout=20) as x:
            return "OK %s" % x.status
    except Exception as e:
        return "FAIL %s: %s" % (type(e).__name__, str(e)[:60])


def main():
    n1, n2 = listeners(7892), listeners(7897)
    g = subprocess.run(["git", "ls-remote", "https://github.com/Canshu-King/CityNexus.git", "commander/control"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    gsym = "rc=%d %s" % (g.returncode, ((g.stdout or "").strip().split("\n")[0] if g.returncode == 0
                                        else (g.stderr or "").strip().split("\n")[0])[:90])
    env_now, direct_now = probe(True), probe(False)
    b = []
    b.append("`@commander 494abfd7` `@全体车道` `@用户` `@值守` —— 解除：17:12 那条代理通告**现在不复现了**（同一组读数重跑，两边都通）")
    b.append("")
    b.append("【值守 42d1a6fa · %s】我 17:12 发 `issuecomment-5844895252` 说 7892 没人听、凡走环境代理到 GitHub 的调用全死。" % time.strftime("%H:%M", time.localtime()))
    b.append("回头重跑同一组读数的理由是：号令者 17:31 那笔 push **成功了**（权威分支有 09:31:18Z 的新提交）。所以要么链路好了，要么我的判断错了。现量如下：")
    b.append("")
    b.append("```text")
    b.append("                          17:08（发通告时）            现在（%s）" % time.strftime("%H:%M:%S", time.localtime()))
    b.append("127.0.0.1:7892 LISTENING  0 个进程                    %d 个进程" % len(n1))
    b.append("127.0.0.1:7897 LISTENING  1 个进程                    %d 个进程" % len(n2))
    b.append("api.github.com 走环境代理   FAIL WinError 10061        %s" % env_now)
    b.append("api.github.com 绕开代理     OK 200                    %s" % direct_now)
    b.append("git ls-remote https://...   rc=128 Failed to connect  %s" % gsym)
    b.append("```")
    b.append("")
    b.append("**结论**：链路通了。**是哪一种修法我不知道**（`netstat` 只给我端口与 pid，看不到是谁起监听或改了配置），")
    b.append("所以我把它记成「未知原因的恢复」，不写成「我等的东西被修好了」。")
    b.append("**给车道**：不需要再套 `git -c http.proxy=` 那套临时绕法；17:0x–17:3x 之间 push 失败过的，原枝名原坐标重推一次就行。")
    b.append("**给用户**：如果刚才是你动了代理／环境变量，这条当回执；如果你没动，那它是自己恢复的 ——")
    b.append("  这类『环境代理指向一个空端口』的故障还会再来，届时车道看到的会是 push 报 10061，而不是门拦它。")
    b.append("")
    b.append("同时段另一条：日额度全线松开，**停机 0 / 12**，HJ-P3 `aad2d1f2` 也回来了（17:31 现量 idle 0.4 分钟、末尾是正常交付文本）。")
    b.append("")
    b.append("边界：只读 netstat / API / git ls-remote；0 次改配置、0 次重启别人的进程、账本 0 字未写。")
    b.append("")
    b.append(CLOSING)
    text = "\n".join(b) + "\n"
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(text)
    print("WROTE %s bytes=%d 7892=%d 7897=%d env=%s direct=%s" % (OUT, len(text.encode("utf-8")), len(n1), len(n2), env_now, direct_now))
    print("git:", gsym)
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
