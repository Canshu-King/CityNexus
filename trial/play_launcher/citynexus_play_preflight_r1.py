r"""Preflight and opener for the double-click CityNexus trial (主人自己点的这两枚 .bat 用它)。

它只做四件事，且都不写任何东西：
  1) 检查这台机器上试玩需要的东西在不在（Python 环境、node、项目树、高德键是否已在环境变量里、本地模型网关是否活着）；
  2) 检查两枚端口是不是空的（端口被别人占时启动脚本会自己拒绝，这里提前说人话）；
  3) --wait-and-open 时等启动脚本写下 READY 文件，然后打开浏览器并把地址打出来；
  4) 任何一步不满足就退出码 1，并说清缺哪一件、下一步做什么。

它从不打印任何密钥的值：高德键只看"在不在"，网关那把 key 由启动脚本自己读进子进程环境。
"""
import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

OUT = r"D:/moodle/_cmdr_v3_port_1022"
ROOT = r"D:/moodle/_cmdr_rescue_v3_1022"
PY = r"D:/moodle/CityNexus/.venv/Scripts/python.exe"
TAG = os.environ.get("HUMAN_TAG", "play")
BACKEND_PORT = int(os.environ.get("HUMAN_BACKEND_PORT", "60361"))
WEB_PORT = int(os.environ.get("HUMAN_WEB_PORT", "14461"))
READY = os.path.join(OUT, "%s_stack_ready.json" % TAG)
LAN = os.environ.get("HUMAN_LAN") == "1"
GATEWAY = "http://127.0.0.1:7863/health"


def say(line):
    print(line, flush=True)


def port_free(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.settimeout(0.6)
        return probe.connect_ex(("127.0.0.1", port)) != 0


def lan_addresses():
    """Best-effort LAN IPv4 list, read from ipconfig's own output (no third-party tool)."""
    raw = subprocess.run(["ipconfig"], capture_output=True, text=True, encoding="utf-8", errors="replace").stdout
    found = []
    for token in raw.replace("\r", "\n").split("\n"):
        for piece in token.replace("：", ":").split(":"):
            piece = piece.strip()
            if piece.count(".") == 3 and all(part.isdigit() and int(part) < 256 for part in piece.split(".")):
                if not piece.startswith("127.") and piece not in found and not piece.startswith("0."):
                    found.append(piece)
    return found


def main():
    problems = []
    if not os.path.exists(PY):
        problems.append("找不到 Python 环境：%s" % PY)
    if not os.path.isdir(os.path.join(ROOT, "backend")):
        problems.append("找不到项目后端目录：%s\\backend" % ROOT)
    if not os.path.exists(os.path.join(ROOT, "frontend", "node_modules", "vite", "bin", "vite.js")):
        problems.append("前端依赖没装：先在该机执行 npm ci（在 %s\\frontend 里）" % ROOT)
    if not (os.environ.get("CITYNEXUS_AMAP_WEB_KEY") or "").strip():
        say("提示：这台机器的环境变量里没有高德键（只查了在不在，没读值）。没有它，这一台就不向任何来源检索地点："
            "Agent 找不出真的地点，草案里每处都写「让 Agent 找这一处」，出发卡的转场核实会老实说这几处还没被认成正式地点。"
            "地图与日程仍可玩；要看到转场核实与「根据路线重新安排」，请把 CITYNEXUS_AMAP_WEB_KEY 放进用户级环境变量后重开。")
    else:
        say("检索已开：这一台会拿你的高德键向真来源查地点与转场（只读环境变量，不打印、不落盘）。")
    code = None
    try:
        with urllib.request.urlopen(GATEWAY, timeout=4) as response:
            code = response.status
    except urllib.error.HTTPError as error:
        # 404/401 still proves something answers on that port: this gateway has no /health route and
        # refuses unauthenticated probes. Saying "没答" here would send the owner off to fix a live service.
        code = error.code
        say("提示：本地模型网关在 %s 上有应答（http_status=%s，这一台没有 /health 这条路径），按活着处理。" % (GATEWAY, code))
    except Exception as error:  # noqa: BLE001
        say("提示：本地模型网关 %s 没答（%s）。Agent 对话那一块会走「服务暂时不可用」那条实话，地图与日程仍可玩。" % (GATEWAY, type(error).__name__))
    if code is not None and code >= 500:
        say("提示：本地模型网关答了 http_status=%s（服务端自己出错），Agent 那一块可能不老实回答。" % code)
    if "--wait-and-open" not in sys.argv:
        # Only the pre-launch pass may complain about occupied ports: in --wait-and-open the stack we just
        # started is supposed to own them.
        for label, port in (("后端", BACKEND_PORT), ("网页", WEB_PORT)):
            if not port_free(port):
                problems.append("%s端口 %d 已被占用：先关掉上一把试玩窗口，或改 HUMAN_%s_PORT" % (label, port, "BACKEND" if label == "后端" else "WEB"))

    if problems:
        say("")
        say("启动前有几件事不满足：")
        for item in problems:
            say("  - " + item)
        return 1

    if "--wait-and-open" not in sys.argv:
        # Clear the previous boot's marker HERE (before the server window starts), never in the waiting
        # pass: a first version deleted it while waiting and then timed out on a stack that was already up.
        if os.path.exists(READY):
            os.remove(READY)
        say("检查通过：可以用鼠标双击启动，两枚端口都是空的。")
        return 0

    deadline = time.time() + 150
    status = None
    while time.time() < deadline:
        if os.path.exists(READY):
            try:
                status = json.load(open(READY, encoding="utf-8"))
                break
            except Exception:  # noqa: BLE001
                pass
        time.sleep(2)
    if not status:
        say("等了 150 秒还没等到启动完成的消息。请看那个黑色窗口里最后几行，或把窗口里的文字发给我。")
        return 1
    url = status.get("url") or "http://127.0.0.1:%d/revolution" % WEB_PORT
    say("")
    say("好了，旅行助手已经在这台机器上跑起来了。")
    say("  这台电脑上看：  " + url)
    if LAN:
        for addr in lan_addresses():
            say("  同一 WiFi 的平板：http://%s:%d/revolution" % (addr, WEB_PORT))
        say("  平板打不开时几乎都是 Windows 防火墙拦了：用管理员身份开一个命令行，执行下面这一条再试（这条命令要你自己决定，我不替你点）：")
        say("    netsh advfirewall firewall add rule name=CityNexusTrial dir=in action=allow protocol=TCP localport=%d" % WEB_PORT)
    say("")
    say("怎么玩（三步就够）：")
    say("  1) 在最上面的框里写一句人话，例如：12 月 3 日到 12 月 4 日在北京玩两天，人均预算 800，不要太赶。")
    say("  2) 按「继续规划」，再按「开始研究」；Agent 查的时候，地图和日程照样能翻。")
    say("  3) 想改哪一天，就按「按天调整行程」；按「核实并冻结今天的转场」之后，再按「选用这份方案」。")
    say("")
    say("怎么停：关掉那个黑色窗口（或在里面按 Ctrl+C），服务就停了；数据留在 %s 里，下次双击还能接着看。" % os.environ.get("HUMAN_DB", "citynexus_v3_play_1024.db"))
    subprocess.run(["cmd", "/c", "start", "", url], check=False) if "--no-open" not in sys.argv else say("(--no-open: 这次没有真的开浏览器)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
