# -*- coding: utf-8 -*-
"""重启正式 hub（:4799）→ 具名作废两枚死地址 → 负对照证它真拦得住。

号令者裁语：「点①（确认作废，从名册摸掉）…作废地址 = file:nightwatch 与 codex:laneE7。
摸掉前把那 4 条信的内容摘要写进你下一块。」摘要已在 1833 那块入账（含 codex:laneE7 那枚
装着 ORD-0544 唯一裁定的 ack），所以这里只做"摸掉 + 拦后续"。

四步都要读数，不接受"我敲过了"：
① 重启：只认 LISTENING 的 PID；起完真回连 /agents 拿 200 才算活；
② forget：逐枚要 200（已作废的再跑给 404，脚本认作幂等，不当失败）；
③ 负对照：真发一条到已作废地址 ⇒ 必须被拒，且拒因里要有「已被具名作废」和经手人；
   它回 201 就是没拦住（那才是这次交付的失败态）；
④ 回读 state.json 的 forgotten 段与 forget.log 尾行，证明痕迹真落盘了。
"""
import io
import json
import os
import re
import subprocess
import sys
import time
import urllib.request

PORT = 4799
ROOT = u"D:/moodle/agent_bus"
PY = sys.executable
DETACHED = 0x00000008
NEW_GROUP = 0x00000200
DEAD = [u"file:nightwatch", u"codex:laneE7"]
REASON = (u"号令者 10-04 裁：这两条腿已停（文件腿值守地址与 Codex 旧实例），"
          u"名册摸掉；压着的信已逐封摘要入账本（含 ORD-0544 唯一裁定那枚 ack）")


def listening():
    out = subprocess.check_output(["netstat", "-ano", "-p", "TCP"]).decode("utf-8", "replace")
    pids = []
    for ln in out.splitlines():
        if (u"127.0.0.1:%d" % PORT) in ln and "LISTENING" in ln.upper():
            m = re.search(r"(\d+)\s*$", ln.strip())
            if m:
                pids.append(int(m.group(1)))
    return sorted(set(pids))


def get(path):
    return json.loads(urllib.request.urlopen("http://127.0.0.1:%d%s" % (PORT, path), timeout=8)
                      .read().decode("utf-8", "replace"))


def main():
    before = listening()
    print(u"① 改前听 :%d 的：%s" % (PORT, before or u"（无）"))
    for pid in before:
        subprocess.call(["taskkill", "/PID", str(pid), "/T", "/F"],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1.2)
    if listening():
        sys.exit(u"ABORT：taskkill 后仍有进程听 :%d（%s）⇒ 不重复起，免得两个 hub 抢一本账"
                 % (PORT, listening()))
    log = open(os.path.join(ROOT, "_hub.out.log"), "ab", buffering=0)
    p = subprocess.Popen([PY, os.path.join(ROOT, "bus_hub.py")], cwd=ROOT,
                         env=dict(os.environ, PYTHONIOENCODING="utf-8"),
                         stdout=log, stderr=subprocess.STDOUT,
                         creationflags=DETACHED | NEW_GROUP, close_fds=True)
    for i in range(30):
        time.sleep(0.5)
        try:
            agents = get("/agents")
            break
        except Exception as e:
            if i == 29:
                sys.exit(u"起了 15 秒仍连不上 hub：%s ⇒ 看 _hub.out.log" % e)
    print(u"   已起 pid %d｜回连 /agents 拿到 %d 枚在册｜持有者 %s"
          % (p.pid, len(agents), listening()))
    if listening() != [p.pid]:
        print(u"   注意：端口持有者与新起 pid 不一致（可能有看门狗同时起了）")

    print(u"② 具名作废：")
    for aid in DEAD:
        r = subprocess.run([PY, os.path.join(ROOT, "bus.py"), "forget", "--id", aid,
                            "--by", u"qoder:42d1a6fa", "--reason", REASON],
                           cwd=ROOT, capture_output=True,
                           env=dict(os.environ, PYTHONIOENCODING="utf-8"))
        txt = r.stdout.decode("utf-8", "replace")
        held = u"?"
        m = re.search(r'"held_undelivered":\s*(\d+)', txt)
        if m:
            held = m.group(1)
        dup = u"名册里没有" in txt
        print(u"   %s｜rc=%d｜摸掉时压着未取 %s 条%s"
              % (aid, r.returncode, held, u"（已在作废名单，幂等）" if dup else u""))
        if r.returncode not in (0, 2) and not dup:
            print(u"   输出：", txt[:400])

    print(u"③ 负对照（真发一条到已作废地址，必须被拒）：")
    r = subprocess.run([PY, os.path.join(ROOT, "bus.py"), "send", "--from", u"qoder:42d1a6fa",
                        "--to", DEAD[0], "--kind", u"note",
                        "--topic", u"forget-probe-" + str(int(time.time())),
                        "--body", u"这条不该进账"],
                       cwd=ROOT, capture_output=True, env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    txt = r.stdout.decode("utf-8", "replace")
    blocked = (r.returncode != 0) and (u"已被具名作废" in txt)
    print(u"   rc=%d｜被具名拒回=%s" % (r.returncode, blocked))
    m = re.search(u"已被具名作废[^\"\\\\]{0,120}", txt)
    print(u"   拒因（逐字截一段）：", (m.group(0) if m else txt[:200]))
    if not blocked:
        sys.exit(u"FAIL：写门没拦住往已作废地址发信 ⇒ 这次交付不算成")

    print(u"④ 痕迹回读：")
    st = json.loads(io.open(os.path.join(ROOT, "state.json"), encoding="utf-8").read())
    fg = st.get("forgotten") or {}
    print(u"   state.json 的 forgotten 段有 %d 枚：%s" % (len(fg), u"、".join(fg.keys())))
    for aid, e in fg.items():
        print(u"     %s｜by=%s｜压着未取 %s 条｜理由前 24 字：%s"
              % (aid, e.get("by"), e.get("held_undelivered"), (e.get("reason") or u"")[:24]))
    tail = io.open(os.path.join(ROOT, "forget.log"), encoding="utf-8").read().strip().splitlines()[-2:]
    for ln in tail:
        print(u"   forget.log：", ln[:150])
    print(u"HUB_FORGET_APPLIED")


if __name__ == "__main__":
    main()
