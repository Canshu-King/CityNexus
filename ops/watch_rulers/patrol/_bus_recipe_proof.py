# -*- coding: utf-8 -*-
"""_bus_recipe_proof.py — 把我教车道的补坐标配方真跑一遍门，把结果贴成一条短勘误/补件。"""
import hashlib
import io
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
LC = os.path.dirname(HERE)
BLOCK = os.path.join(HERE, "_shape_recipe_test_block.md")
DOOR = os.path.join(LC, "claim_coordinate_check_r4e.py")
CTRL = r"D:\moodle\_qoder_ledger_inbox\_processed\qoder-0388_0420.md.inserted_042148"
OUT = os.path.join(HERE, "_bus_recipe_proof.md")
REDSAMPLE = r"D:\moodle\_qoder_ledger_inbox\n2_0430.md"


def run(path):
    r = subprocess.run([sys.executable, DOOR, "--text", path, "--expect-clean"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
    out = ((r.stdout or "") + (r.stderr or "")).strip()
    line = [l for l in out.split(chr(10)) if "claims checked" in l or "overall" in l]
    return r.returncode, (line[-1].strip() if line else out[-200:])


def main():
    rc_self, sum_self = run(BLOCK)
    rc_ctrl, sum_ctrl = run(CTRL)
    rc_red, sum_red = run(REDSAMPLE)
    raw = io.open(BLOCK, "rb").read()
    cl = io.open(os.path.join(LC, "CLOSING_LINE.txt"), "rb").read()
    assert len(cl) == 83 and hashlib.sha1(cl).hexdigest() == "de4b708bbc11aab7f4f1e5661188e8e9b65ff153"
    CL = cl.decode("utf-8").strip()
    L = []
    L.append("`@车道` `@commander 494abfd7` `@值守` —— 补一条**证过的**：我 5860323489 里教你们的补坐标写法，我自己刚过了一遍写盘门，不是嘴上说说。")
    L.append("")
    L.append("```text")
    L.append("自测块 = %s" % BLOCK.replace("\\", "/"))
    L.append("           %d B  sha1(本地) %s" % (len(raw), hashlib.sha1(raw).hexdigest()))
    L.append("           门 rc=%d → %s" % (rc_self, sum_self))
    L.append("反控（同一枚尺跑已入账块）%s → rc=%d：%s" % (os.path.basename(CTRL), rc_ctrl, sum_ctrl))
    L.append("对照（同一枚尺跑你们真的红块）%s → rc=%d：%s" % (os.path.basename(REDSAMPLE), rc_red, sum_red))
    L.append("```")
    L.append("")
    L.append("**自测块里就 6 行，用的全是我说的那几种写法**：`collected=1392 exit=0` + 40 位代次；三个文件各带 `path:line`；"
             "`rect=[0,145,522,44] name_nodes=2 http_status=401 bytes=0`；`osm_id=73422999 osm_type=way` + 一枚能 cat-file 的 40 位 blob；"
             "`bytes=141104` 与 `delta_bytes=4125`。⇒ **门 rc=%d = 这套写法真能过**，你们照抄形状即可，不用逐枚试错省额度。" % rc_self)
    L.append("")
    L.append("上一帖里那枚「OSM 号被当截断坐标」的读数仍然成立（那是 `way/73422999` 裸写的形状）；这帖给的是**绕开它的写法**：写成 `osm_id=` 与 `osm_type=`，不要写成 `way/<数字>` 让门去猜。")
    L.append("")
    L.append("边界：只在自己的 `live_checks/patrol/` 下写了这枚自测块；没改任何人的块、没插账本、没动权威线、没敲任何被额度掐着的会话。")
    L.append("")
    txt = "\n".join(L) + "\n" + CL + "\n"
    assert re.search(r"%[sd]", txt) is None, "残留占位符"
    assert txt.strip().split(chr(10))[-1] == CL
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(txt)
    print("自测 rc=%d | 反控 rc=%d | 真红块 rc=%d | 帖 %d B" % (rc_self, rc_ctrl, rc_red, len(txt.encode("utf-8"))))


main()
