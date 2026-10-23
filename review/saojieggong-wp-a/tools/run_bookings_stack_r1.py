# -*- coding: utf-8 -*-
"""一条命令内：起我自己的私有栈 -> 跑票夹取景器 -> 收栈（扫街工 WP-A′）。

形制照 CMDR 简报 §3/§6 与 脉搏工 那把尺公开的做法，但三条安全线是我自己的：
  甲 端口只认 LISTENING——TIME_WAIT 带的是 PID 0，把它算成"被占"会误 abort，
     把"有人睡在那"算成"空闲"则会量到邻居。
  乙 起来之后还要验它服务的是我这棵树：从盘上抽 styles.css 的单行令牌声明逐条在响应里找。
  丙 不碰受保护端口 :8000/:4781/:4782/:8693 与共享库 _preview.db；数据是 _cmdr_demo_1013/demo.db
     的只读副本（简报 §6 写明那条链是取景条件，不是产品事实）。
用法: run_bookings_stack_r1.py <arm> <front_port>
"""
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.request

TREE = r"D:/moodle/_cmdr_saojieggong_1016/tree"
WORK = r"D:/moodle/_cmdr_saojieggong_1016"
PY = r"D:/moodle/CityNexus/.venv/Scripts/python.exe"
SRC_DB = r"D:/moodle/_cmdr_demo_1013/demo.db"
MY_DB = os.path.join(WORK, "demo_saojieggong.db")
PROTECTED = ("8000", "4781", "4782", "8693")


def listening(port):
    out = subprocess.run("netstat -ano", shell=True, capture_output=True, text=True).stdout
    return [ln for ln in out.splitlines()
            if ("127.0.0.1:%s " % port) in ln and "LISTENING" in ln]


def served_is_mine(front):
    """验的是 styles.css（本单改的文件），不是 cn-pulse.css。"""
    disk = open(os.path.join(TREE, "frontend", "src", "styles.css"), encoding="utf-8").read()
    cands = [ln.strip() for ln in disk.splitlines()
             if ln.strip().startswith(".v8-booking") or ln.strip().startswith(".v9-inbox")]
    sample = cands[:6]
    if len(sample) < 3:
        return False, "盘上只抽到 %d 条规则，尺不够" % len(sample)
    try:
        with urllib.request.urlopen("http://127.0.0.1:%s/src/styles.css" % front, timeout=20) as r:
            body = r.read().decode("utf-8", "replace")
        hit = sum(1 for s in sample if s in body)
        return hit >= max(3, len(sample) - 1), "sampled=%d hit=%d bytes=%d" % (len(sample), hit, len(body))
    except Exception as exc:
        return False, str(exc)[:90]


def main():
    arm = sys.argv[1] if len(sys.argv) > 1 else "armA"
    front = sys.argv[2] if len(sys.argv) > 2 else "4720"
    back = str(int(front) + 4000)
    if front in PROTECTED or back in PROTECTED:
        print("ABORT 撞受保护端口"); return 8
    for p in (front, back):
        busy = listening(p)
        if busy:
            print("ABORT port %s 已 LISTENING（%d 行）——绝不量邻居，也绝不清它" % (p, len(busy)))
            print("   " + busy[0].strip())
            return 5
    print("preflight: ports %s/%s LISTENING 为空" % (front, back), flush=True)
    if not os.path.isfile(SRC_DB):
        print("ABORT 找不到 %s" % SRC_DB); return 8
    shutil.copyfile(SRC_DB, MY_DB)
    for ext in ("-wal", "-shm"):
        if os.path.exists(MY_DB + ext):
            os.remove(MY_DB + ext)
    print("数据＝%s 的只读副本 → %s（%d 字节）" % (SRC_DB, MY_DB, os.path.getsize(MY_DB)), flush=True)

    env = dict(os.environ)
    env["CITYNEXUS_DATABASE_URL"] = "sqlite:///" + MY_DB.replace("\\", "/")
    env["CITYNEXUS_AI_ENABLED"] = "false"
    env["PYTHONIOENCODING"] = "utf-8"
    bk = subprocess.Popen([PY, "-X", "utf8", "-m", "uvicorn", "app.main:app",
                           "--host", "127.0.0.1", "--port", back],
                          cwd=os.path.join(TREE, "backend"), env=env,
                          stdout=open(os.path.join(WORK, "uvicorn_%s.log" % back), "ab"),
                          stderr=subprocess.STDOUT)
    fe = dict(env); fe["CITYNEXUS_BACKEND_PORT"] = back
    vt = subprocess.Popen(["node", "node_modules/vite/bin/vite.js", "--port", front,
                            "--host", "127.0.0.1", "--strictPort"],
                          cwd=os.path.join(TREE, "frontend"), env=fe,
                          stdout=open(os.path.join(WORK, "vite_%s.log" % front), "ab"),
                          stderr=subprocess.STDOUT)
    rc = 1
    try:
        deadline = time.time() + 90
        up = False
        while time.time() < deadline:
            probe = subprocess.run(["node", "-e",
                                    "require('http').get('http://127.0.0.1:%s/',r=>{process.exit(0)}).on('error',()=>process.exit(1))" % front],
                                   shell=False)
            if probe.returncode == 0:
                up = True; break
            time.sleep(2)
        print("stack_up=%s front=%s back=%s" % (up, front, back), flush=True)
        if not up:
            print("栈没起来——拒绝打印任何数"); return 4
        mine, info = served_is_mine(front)
        print("served_from_my_tree=%s (%s)" % (mine, info), flush=True)
        if not mine:
            print("ABORT :%s 上服务的不是我这棵树，数会是别人的" % front); return 6
        r = subprocess.run([PY if False else "node",
                            os.path.join(WORK, "tools", "capture_bookings_r1.cjs"), arm],
                           cwd=WORK, capture_output=True, text=True,
                           encoding="utf-8", errors="replace",
                           env=dict(os.environ, SAOJIE_FRONT=front))
        print(r.stdout[-3000:], flush=True)
        if r.stderr.strip():
            print("STDERR " + r.stderr[-500:], flush=True)
        rc = r.returncode
    finally:
        for p in (vt, bk):
            try:
                p.terminate()
            except Exception:
                pass
        time.sleep(3)
        for p in (vt, bk):
            if p.poll() is None:
                p.kill()
        print("stack torn down (rc=%d)" % rc, flush=True)
    return rc


if __name__ == "__main__":
    sys.exit(main())
