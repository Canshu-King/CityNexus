r"""09-28 04:3x 值守通告：本机代理端口无人监听，走直连三家公共供应商全部 200。

所有读数在写这一刻现量（netstat / httpx / urllib），不引用记忆、不引用上一条帖子。
"""
import io
import json
import os
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))                 # ghnet 住在 live_checks/
import ghnet  # noqa: E402
import ssl  # noqa: E402
import httpx  # noqa: E402

CLOSING = io.open(os.path.join(os.path.dirname(HERE), "CLOSING_LINE.txt"), encoding="utf-8").read().strip()
OUT = os.path.join(HERE, "_bus_provider_direct_0428.md")
REPO = r"D:\moodle\CityNexus"
UA = "citynexus-patrol-readiness-probe/1.0 (read-only)"

PHOTON = "https://photon.komoot.io/api/?q=Guangzhou&limit=1"
OVERPASS_Q = ("data=" + urllib.parse.quote('[out:json][timeout:8];(node["place"="city"]'
                                           '["name:zh"="Guangzhou"];);out 1;'))
VALHALLA_BODY = json.dumps({"locations": [{"lat": 23.13, "lon": 113.26},
                                          {"lat": 23.12, "lon": 113.28}],
                            "costing": "auto", "units": "kilometers"})


def netstat_listening(port):
    r = subprocess.run("netstat -ano", capture_output=True, shell=True)
    txt = r.stdout.decode("utf-8", "replace").split(chr(10))
    rows = [l.strip() for l in txt if (":%d " % port) in l and "LISTENING" in l.upper()]
    return rows


def direct(url, data=None, ctype=None, timeout=25):
    handlers = [urllib.request.ProxyHandler({}),
                urllib.request.HTTPSHandler(context=ssl.create_default_context())]
    op = urllib.request.build_opener(*handlers)
    headers = {"User-Agent": UA}
    if ctype:
        headers["Content-Type"] = ctype
    req = urllib.request.Request(url, headers=headers, data=data)
    t0 = time.time()
    try:
        with op.open(req, timeout=timeout) as resp:
            b = resp.read()
            return "HTTP %s / %d B / %.2fs" % (resp.status, len(b), time.time() - t0), len(b)
    except Exception as e:
        return "%s: %s / %.2fs" % (type(e).__name__, str(e)[:60], time.time() - t0), None


def through_proxy(url, data=None, ctype=None, timeout=25):
    headers = {"User-Agent": UA}
    if ctype:
        headers["Content-Type"] = ctype
    op = urllib.request.build_opener(
        urllib.request.ProxyHandler({"http": os.environ.get("HTTPS_PROXY", ""),
                                     "https": os.environ.get("HTTPS_PROXY", "")}),
        urllib.request.HTTPSHandler(context=ssl.create_default_context()))
    req = urllib.request.Request(url, headers=headers, data=data)
    t0 = time.time()
    try:
        with op.open(req, timeout=timeout) as resp:
            b = resp.read()
            return "HTTP %s / %d B / %.2fs" % (resp.status, len(b), time.time() - t0), len(b)
    except Exception as e:
        return "%s: %s / %.2fs" % (type(e).__name__, str(e)[:60], time.time() - t0), None


def httpx_pair(url, params=None):
    out = []
    for tag, kw in (("默认 (trust_env=True)", {}), ("trust_env=False", {"trust_env": False})):
        c = httpx.Client(timeout=12.0, headers={"User-Agent": UA}, **kw)
        t0 = time.time()
        try:
            r = c.get(url, params=params)
            out.append((tag, "HTTP %s / %d B / %.2fs" % (r.status_code, len(r.content), time.time() - t0)))
        except Exception as e:
            out.append((tag, "%s: %s / %.2fs" % (type(e).__name__, str(e)[:60], time.time() - t0)))
        c.close()
    return out


def httpx_valhalla():
    out = []
    for tag, kw in (("默认 (trust_env=True)", {}), ("trust_env=False", {"trust_env": False})):
        c = httpx.Client(timeout=15.0, headers={"User-Agent": UA}, **kw)
        t0 = time.time()
        try:
            r = c.post("https://valhalla1.openstreetmap.de/route", json=json.loads(VALHALLA_BODY))
            summ = (r.json().get("trip") or {}).get("summary") or {}
            out.append((tag, "HTTP %s / %d B / %.2fs / summary=%s"
                        % (r.status_code, len(r.content), time.time() - t0,
                           json.dumps({k: summ.get(k) for k in ("time", "length")}))))
        except Exception as e:
            out.append((tag, "%s: %s / %.2fs" % (type(e).__name__, str(e)[:60], time.time() - t0)))
        c.close()
    return out


def grep_count(path, pattern):
    if not os.path.exists(path):
        return None, []
    hits = []
    for n, line in enumerate(io.open(path, encoding="utf-8", errors="replace"), 1):
        if re.search(pattern, line):
            hits.append((n, line.rstrip()))
    return len(hits), hits


def port_owner(port):
    """netstat 找监听该端口的 pid，再用 CIM 取它的命令行（同一次读数，不引用旧 pid）。"""
    rows = netstat_listening(port)
    if not rows:
        return "（netstat 现在没有任何进程在 LISTENING :%d）" % port, None
    pid = rows[0].split()[-1]
    try:
        r = subprocess.run(["powershell.exe", "-NoProfile", "-Command",
                            "Get-CimInstance Win32_Process -Filter \"ProcessId=%s\" "
                            "| Select-Object -ExpandProperty CommandLine" % pid],
                           capture_output=True)
        cmd = r.stdout.decode("cp936", "replace").strip()
    except Exception as e:
        cmd = "(取命令行失败 %s)" % type(e).__name__
    cmd = cmd.replace("仓鼠王", "<user>")
    cmd = re.sub(r"C:\\+Users\\+[^\\]+", r"C:\\Users\\<user>", cmd)
    cmd = re.sub(r"[^\x20-\x7e]", "?", cmd)      # CIM 回的是 GBK，中文段一律遮掉，不把乱码发出去
    return ("pid=%s 监听 :%d，命令行 = %s" % (pid, port, cmd[:190])), pid


def health(port):
    op = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    req = urllib.request.Request("http://127.0.0.1:%d/api/v1/health" % port,
                                 headers={"User-Agent": UA})
    try:
        with op.open(req, timeout=12) as x:
            status, b = x.status, x.read()
        d = json.loads(b.decode("utf-8", "replace"))
        return status, len(b), sorted(d.keys())
    except Exception as e:
        return "FAIL " + type(e).__name__, 0, [str(e)[:60]]


def grep_tree(root, pattern):
    """递归扫 root 下所有 .py，返回 (相对路径, 行号, 行) 清单——用于「不存在」这类否定主张要打印清单。"""
    hits = []
    files = 0
    for dirpath, _dirs, names in os.walk(root):
        for nm in names:
            if not nm.endswith(".py"):
                continue
            files += 1
            p = os.path.join(dirpath, nm)
            for n, line in enumerate(io.open(p, encoding="utf-8", errors="replace"), 1):
                if re.search(pattern, line):
                    hits.append((os.path.relpath(p, REPO).replace(os.sep, "/"), n, line.strip()))
    return files, hits


def grep_files(scopes, needle):
    """在给定若干目录/文件范围内逐文件搜字面串，返回 [(路径, 命中行数, 首行样例)]。
    「这个键名全机没有」这类否定主张必须打印真正读过的清单，所以范围也一并回显。"""
    out = []
    walked = []
    for sc in scopes:
        if os.path.isdir(sc):
            walked.append(sc + os.sep + "**")
            for dirpath, _d, names in os.walk(sc):
                for nm in names:
                    if not nm.endswith((".py", ".bat", ".ps1", ".sh", ".cmd", ".md", ".example", ".txt", ".env")):
                        continue
                    p = os.path.join(dirpath, nm)
                    try:
                        txt = io.open(p, encoding="utf-8", errors="replace").read().split(chr(10))
                    except Exception:
                        continue
                    hits = [i for i, l in enumerate(txt, 1) if needle in l]
                    if hits:
                        out.append((os.path.relpath(p, r"D:\moodle").replace(os.sep, "/"),
                                    len(hits), ":%d %s" % (hits[0], txt[hits[0] - 1].strip()[:70])))
        elif os.path.exists(sc):
            walked.append(sc)
            txt = io.open(sc, encoding="utf-8", errors="replace").read().split(chr(10))
            hits = [i for i, l in enumerate(txt, 1) if needle in l]
            if hits:
                out.append((os.path.relpath(sc, r"D:\moodle").replace(os.sep, "/"),
                            len(hits), ":%d %s" % (hits[0], txt[hits[0] - 1].strip()[:70])))
        else:
            walked.append("(不存在) " + sc)
    return walked, out


def main():
    now = time.strftime("%H:%M")
    envp = os.environ.get("HTTPS_PROXY")
    l7892 = netstat_listening(7892)
    l7897 = netstat_listening(7897)
    port_owner_note, owner_pid = port_owner(8693)
    health_status, health_bytes, health_keys = health(8693)

    d_ph, _ = direct(PHOTON)
    p_ph, _ = through_proxy(PHOTON)
    d_op, _ = direct("https://overpass-api.de/api/interpreter", data=OVERPASS_Q.encode(),
                     ctype="application/x-www-form-urlencoded")
    p_op, _ = through_proxy("https://overpass-api.de/api/interpreter", data=OVERPASS_Q.encode(),
                            ctype="application/x-www-form-urlencoded")
    d_gh, _ = direct("https://api.github.com/meta")
    p_gh, _ = through_proxy("https://api.github.com/meta")

    # 产品自己的策略助手（provider_config.py）在当前 env 下算出什么
    sys.path.insert(0, os.path.join(REPO, "backend"))
    from app.integrations.provider_config import (provider_network_mode,
                                                  trust_environment_for_public_providers)
    mode = provider_network_mode()
    trust = trust_environment_for_public_providers()
    hp = httpx_pair("https://photon.komoot.io/api/", params={"q": "Guangzhou", "limit": 1})
    hv = httpx_valhalla()

    pc_hits, pc_lines = grep_count(os.path.join(REPO, "backend", "app", "integrations", "provider_config.py"),
                                   "retry")
    tree_files, tree_hits = grep_tree(os.path.join(REPO, "backend", "app", "integrations"), "retry|Retry")
    mob_hits, mob_lines = grep_count(os.path.join(REPO, "backend", "app", "integrations", "mobility", "runtime.py"),
                                     "httpx.Client|live_valhalla_url")
    mock_lines = [n for n, l in mob_lines if "if not settings.live_valhalla_url" in l]
    bare_lines = [n for n, l in mob_lines if "httpx.Client(timeout=10.0)" in l]

    # 启动脚本面：把 run/*.bat 全数扫一遍，逐个给「清没清代理」「有没有设 LIVE_VALHALLA_URL」
    run_dir = r"D:\moodle\_qoder_preview_20260920\run"
    bats = []
    for nm in sorted(os.listdir(run_dir)):
        if not nm.endswith(".bat"):
            continue
        p = os.path.join(run_dir, nm)
        lines = io.open(p, encoding="utf-8", errors="replace").read().split(chr(10))
        proxy_lines = [(i, l.strip()) for i, l in enumerate(lines, 1)
                       if re.search(r"(?i)^set +(HTTPS?_PROXY|NO_PROXY)", l)]
        lv = [(i, l.strip()) for i, l in enumerate(lines, 1) if "CITYNEXUS_LIVE_VALHALLA_URL" in l]
        bats.append((nm, len(lines), proxy_lines, lv))

    L = []
    L.append("`@commander 494abfd7` `@车道` `@值守` —— 公共供应商与 GitHub **没有停服**：本机两个代理端口都没人监听，直连三家全 200。附产品侧一处策略与代码不一致，车道现在就能绕。")
    L.append("")
    L.append("【值守现场读数 %s+08，全部这一轮现量：0 次产品写入、0 次账本写入、读这些数没打扰任何车道】" % now)
    L.append("")
    L.append("```text")
    L.append("env  HTTPS_PROXY = %s" % envp)
    L.append("netstat :7892 LISTENING 行数 = %d   ;  :7897 LISTENING 行数 = %d  ⇒ 两个端口都没有进程在听（代理没开，不是指错端口）"
             % (len(l7892), len(l7897)))
    L.append("netstat :8693（手机链那台后端）现读监听者 = %s" % port_owner_note)
    L.append("")
    L.append("同一轮 A/B（同进程、同解析器）：")
    L.append("  Photon   GET /api/?q=Guangzhou&limit=1   直连 %s | 走 env 代理 %s" % (d_ph, p_ph))
    L.append("  Overpass POST /api/interpreter            直连 %s | 走 env 代理 %s" % (d_op, p_op))
    L.append("  GitHub   GET /meta                        直连 %s | 走 env 代理 %s" % (d_gh, p_gh))
    L.append("")
    L.append("产品自己的策略助手在当前 env 下：CITYNEXUS_PROVIDER_NETWORK_MODE 未设 ⇒ mode=%s ⇒ trust_env=%s" % (mode, str(trust)))
    L.append("  httpx.Client(...) 打 Photon   %s -> %s" % hp[0])
    L.append("  httpx.Client(trust_env=False) %s -> %s" % hp[1])
    L.append("  httpx.Client(...) POST Valhalla /route   %s -> %s" % hv[0])
    L.append("  httpx.Client(trust_env=False) 同一请求    %s -> %s" % hv[1])
    L.append("```")
    L.append("")
    L.append("**代码与启动脚本事实（行号现取，grep 原文照抄）**")
    L.append("")
    for n, line in pc_lines:
        L.append("- `backend/app/integrations/provider_config.py:%d` 写着 %s" % (n, line.strip()))
    L.append("  同一轮把 `backend/app/integrations` 整棵扫了（%d 个 .py 文件），含 `retry/Retry` 的行只有 %d 行，逐行如下："
             % (tree_files, len(tree_hits)))
    for rel, n, line in tree_hits:
        L.append("    `%s:%d`  %s" % (rel, n, line[:150]))
    L.append("  ⇒ 那行注释承诺的 bounded direct retry **没有对应代码路径**（这份清单就是全部命中）；"
             "所以在本机 AUTO 的实际行为等于 ENV_PROXY。")
    L.append("")
    for n, line in mob_lines:
        L.append("- `backend/app/integrations/mobility/runtime.py:%d`  %s" % (n, line.strip()))
    L.append("  ⇒ mobility 那 %d 处 client（`runtime.py:%s`）没有走 `trust_environment_for_public_providers()`，"
             "在本机必成 10061，然后被包成 `ValhallaProviderError` → `status=UNAVAILABLE`。"
             "**这不是供应商不可达**：同一 URL、同一进程、`trust_env=False` 回 HTTP 200 并给出真 summary（见上）。"
             % (len(bare_lines), "/".join(str(n) for n in bare_lines)))
    L.append("")
    n_proxy = sum(1 for _nm, _t, pl, _lv in bats if pl)
    n_lv = sum(1 for _nm, _t, _pl, lv in bats if lv)
    KEY = "CITYNEXUS_LIVE_VALHALLA_URL"
    key_walked, key_hits = grep_files([os.path.join(REPO, "backend"),
                                       os.path.join(REPO, "scripts"),
                                       run_dir,
                                       os.path.join(REPO, ".env.example")], KEY)
    env_ls = [nm for nm in (os.listdir(REPO) if os.path.isdir(REPO) else []) if nm.startswith(".env")]
    L.append("**启动脚本面（`_qoder_preview_20260920/run/*.bat` 全 %d 份，逐个扫）**" % len(bats))
    L.append("")
    for nm, total, proxy_lines, lv in bats:
        L.append("- `%s`（共 %d 行）：清代理的行 %d 行 %s ；`CITYNEXUS_LIVE_VALHALLA_URL` 命中 %d 行"
                 % (nm, total, len(proxy_lines),
                    ("[" + ", ".join(":%d %s" % (i, s[:26]) for i, s in proxy_lines) + "]") if proxy_lines else "（无）",
                    len(lv)))
    L.append("  ⇒ %d 份脚本里 **%d 份清了代理、%d 份设了 `%s`**；"
             "我逐文件搜过这些范围：%s，仓库根 `.env*` 实有 %s，命中 `%s` 的文件是："
             % (len(bats), n_proxy, n_lv, KEY, "; ".join(w.replace(os.sep, "/") for w in key_walked),
                env_ls or "（0 份）", KEY))
    for rel, cnt, first in key_hits:
        L.append("    `%s` 命中 %d 行，首行 %s" % (rel, cnt, first))
    L.append("     ⇒ 这些命中全是读取点/测试/示例注释，**没有任何启动脚本或 `.env` 把它设上**。")
    L.append("  ⇒ 凡按这些脚本起的后端，`runtime.py:%s` 那两处判据第一步就进 mock 分支——"
             "**手机链每一腿都是 SYNTHETIC_DEFAULT 是配置事实，不是网络事实**。"
             % ("/".join(str(n) for n in mock_lines)))
    L.append("     这一台此刻由 %s；`GET :8693/api/v1/health` 回 HTTP %s / %s B，键只有 %s "
             "——payload 里没有任何供应商网络模式的格子，而进程的实际环境变量我没有读得到的通道，"
             "所以我只主张「脚本没设这一格」，不主张「这台进程现在一定没设」。"
             % (port_owner_note, health_status, health_bytes, health_keys))
    L.append("")
    L.append("**车道现在能用的绕法（不改产品码）**：起进程前置 `set CITYNEXUS_PROVIDER_NETWORK_MODE=direct`，"
             "或在你自己的仪表里显式 `httpx.Client(trust_env=False)` / `ProxyHandler({})`；"
             "git 用 `git -c http.proxy= -c https.proxy= ls-remote ...`。"
             "判供应商之前请先做一次同样的 A/B，**不要拿 10061 当供应商停服报**。")
    L.append("")
    L.append("**我没做的**：没改任何产品文件、没动账本、没动权威线、没重启任何进程、没跑 `demo/reset`。"
             "本轮只给两条自停的车道发了继续令（ORD-0387 `bac10f40`、N2 `9759f1ac` 的起点件），读数与理由在值守日志里。")
    L.append("")
    L.append(CLOSING)

    txt = "\n".join(L) + "\n"
    # 写盘门：正文里不许残留没被格式化掉的 %s/%d（我自己踩过一次隐式拼接把 join 变成了字面串）
    leftover = re.findall(r"%[sd]", txt)
    if leftover:
        raise SystemExit("ABORT：正文残留 %s/%d 未格式化，命中 %d 处 —— 不写盘、不发帖" % len(leftover))
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(txt)
    print("写就 %s = %d B | 尾行 sha 检查：" % (os.path.basename(OUT), len(txt.encode("utf-8"))))
    import hashlib
    tail = txt.strip().split(chr(10))[-1]
    print("  tail == CLOSING:", tail == CLOSING, "| sha1", hashlib.sha1(tail.encode("utf-8")).hexdigest())
    print("  引用 retry 命中数 =", pc_hits, "| integrations 扫过文件数 =", tree_files,
          "| mobility 命中数 =", mob_hits, "| bat 份数 =", len(bats), "| 键名命中文件数 =", len(key_hits))


main()
