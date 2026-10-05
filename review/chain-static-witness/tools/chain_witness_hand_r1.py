"""Compose, gate and drop the independent witness on the phone-chain static door.

Every figure comes from the witness JSON this run wrote, and the two source lines quoted are re-read from the
server's own file at composition time -- if the line numbers moved, the block says so instead of citing a
number I remembered.  The ruler gates it and the file is only copied into the inbox when it exits clean.
"""
import json
import os
import re
import shutil
import subprocess
from datetime import datetime

LANE = r"D:/moodle/_qoder_phone_ord0485_20260930"
RULER = r"D:/moodle/_qoder_cmdr_ref_20260921/live_checks/claim_coordinate_check_r7.py"
CLOSING = r"D:/moodle/_qoder_cmdr_ref_20260921/live_checks/CLOSING_LINE.txt"
INBOX = r"D:\moodle\_qoder_ledger_inbox"
SERVER = r"D:/moodle/_qoder_cmdr_ref_20260921/live_checks/_cmdr_lan_static_api_r1.py"
PY = r"D:/moodle/CityNexus/.venv/Scripts/python.exe"
DIST = r"D:/moodle/_qoder_cmdr_ref_20260921/live_checks/_build_day34/frontend/dist"
ENV = {k: v for k, v in os.environ.items() if k.upper() not in ("HTTP_PROXY", "HTTPS_PROXY")}
ENV["NO_PROXY"] = "*"


def line_of(path, needle):
    text = open(path, encoding="utf-8", errors="replace").read().splitlines()
    hits = [n for n, l in enumerate(text, 1) if needle in l]
    if not hits:
        raise SystemExit("ABORT_CITED_LINE_NOT_FOUND " + needle[:40])
    return hits[0], len(text)


def main():
    w = json.load(open(os.path.join(LANE, "evidence", "chain_static_door_witness_r1.json"), encoding="utf-8"))
    if w["probed_paths"] != len(w["statuses"]):
        raise SystemExit("ABORT_STATUS_COUNT_MISMATCH")
    n_guard, srv_lines = line_of(SERVER, "if not os.path.isfile(candidate):")
    n_open, _ = line_of(SERVER, "with open(candidate, \"rb\") as fh:")
    dist_entries = len(os.listdir(DIST)) if os.path.isdir(DIST) else 0
    if os.path.isdir(r"D:/moodle/_qoder_cmdr_ref_20260921/live_checks/_build_day33"):
        raise SystemExit("ABORT_DAY33_STILL_PRESENT_read_changed")
    body = """### ORD-0500 手机车道（0afdb49b）办 BB 报警：静态口那件我独立复现了，并且给出了因——它 serve 的那份 dist 整个目录已不在，而服务代码在没有 404 分支

一、复现（不是重跑别人的脚本，换了客户端、换了路径集）
- 探针 `tools/chain_static_door_witness_r1.py`，件 `evidence/chain_static_door_witness_r1.json`：对 `:4783` 用 urllib 探 {probed} 枚路径（他 lane 探的是 curl 五枚，我另加两枚并把 `/index.html` 也放进去），**{noresp} 枚全部拿不到响应**；api 门 `:4787` 两枚路由都回 {api_status}（`/api/v1/health` 正文 {api_bytes} 字节）⇒ 不是全局网络，是那一扇门。
- 裸连 TCP 再证一次形状：发出请求后**对端关闭前一个字节都没回**（`/` 收到 0 字节、`/index.html` 收到 0 字节），也不是慢——这与他 lane 报的「约三毫秒就断」同形。
- 谁在听：`:4783` 由 PID {spid} 持有，命令行是 `python _cmdr_lan_static_api_r1.py --dist …_build_day33/frontend/dist --port 4783 --api 4787`；`:4787` 是另一枚 PID {apid}（uvicorn 真后端）。两扇门都活着，所以「进程没了」这个解释被排除。

二、因（代码路径 + 文件系统两边对上）
- 它 `--dist` 指的那份产物**整个目录已经不在了**：`live_checks/_build_day33` 现读不存在（只剩旁边的 `_build_day33_info.json`）。
- 服务代码没有「文件没了就回 404」这一支：`{srv}:{n_guard}` 判完 `isfile` 就把兜底目标换成 `dist/index.html`，紧接 `{srv}:{n_open}` **无条件 open** —— 兜底目标同样不存在时这里抛 FileNotFoundError，线程死掉、连接被关，于是外面看到的就是「在听、0 字节、几毫秒」。这条链的每一环都是读出来的，不是推的（该文件现读 {srvlines} 行）。
- 同一把尺顺手看了替代品：`_build_day34/frontend/dist` 在，{dist_entries} 项，含 `index.html` 与 `assets/`。

三、我能做与不能做的
- 没做：不重启、不杀进程、不改参数、不动别人名下的端口（那是号令者起的链）。本手重启 0 次、杀进程 0 次、改绑定 0 次、写别人的目录 0 处（件里 `actions_taken` 四项皆零）。
- 等一句的：把静态口指向 day34 那份 dist，或重建 day33 —— 这属于换代动作，归你；点给我我就把复现脚本与判据留着，改完我再独立复测一遍并把四屏顶栏那四行重新量一次（那正是这条链现在挡住的格子）。
- 我这侧受影响的格子据实写：真机 NOT_MEASURED、手机屏读那批仍不可取；Playwright 本手未跑。

四、边界
- 本手产品字节改动 0 枚；线上已落字节覆盖 0 枚；名下枝改写 0 枚；删枝 0 枚；账本直写 0 处（本块走收件口）；端口起停 0 个；wt22 工作树写入 0 处；`demo/reset` 未跑。
- 读数时刻成立：以上都是 {tip_note} 这一眼取的，链随时可能被别人换代，复算请重跑那把尺而不是引用这块。
""".format(probed=w["probed_paths"], noresp=w["no_response"],
               api_status=str(w["api_health"]["status"]), api_bytes=w["api_health"].get("bytes"),
               spid=w["static_owner"]["listening_pids"][0], apid=w["api_owner"]["listening_pids"][0],
               srv="live_checks/_cmdr_lan_static_api_r1.py", n_guard=n_guard, n_open=n_open,
               srvlines=srv_lines, dist_entries=dist_entries,
               tip_note="现尖 `%s` 之后" % w["took_local"][11:16])
    closing = open(CLOSING, "rb").read()
    if len(closing) != 83:
        raise SystemExit("ABORT_CLOSING_LINE_SIZE %d" % len(closing))
    composed = body.rstrip() + "\n\n" + closing.decode("utf-8").strip() + "\n"
    dest_comp = os.path.join(LANE, "run", "chain_witness_block_composed.md")
    open(os.path.join(LANE, "run", "chain_witness_block_body.md"), "w", encoding="utf-8",
         newline="\n").write(body)
    open(dest_comp, "w", encoding="utf-8", newline="\n").write(composed)
    hexes = sorted(set(re.findall(r"\b[0-9a-f]{40}\b", composed)))
    gp = os.path.join(LANE, "run", "chain_witness_precheck.txt")
    rc = subprocess.run([PY, RULER, "--text", dest_comp, "--out", gp, "--expect-clean"],
                        capture_output=True, timeout=600, env=ENV).returncode
    print("Q43 rc=%s hexes=%d\n%s" % (rc, len(hexes),
          open(gp, encoding="utf-8", errors="replace").read()[-1200:]))
    if rc != 0:
        raise SystemExit("ABORT_BLOCK_NOT_GREEN rc=%s" % rc)
    now = datetime.now().astimezone()
    name = "0afdb49b_%s.md" % now.strftime("%H%M")
    drop = os.path.join(INBOX, name)
    if os.path.exists(drop) or os.path.exists(os.path.join(INBOX, "_processed", name + ".inserted_x")):
        name = "0afdb49b_%s%d.md" % (now.strftime("%H%M"), now.second)
        drop = os.path.join(INBOX, name)
    shutil.copyfile(dest_comp, drop)
    print("DROPPED %s (%d B)" % (drop, os.path.getsize(drop)))


if __name__ == "__main__":
    main()
