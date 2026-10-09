# -*- coding: utf-8 -*-
"""red_shapes.py — 把写盘门在收件目录根上报的每一枚 finding 按「被咬的字符串长什么样」分类。

目的：分清两类责任——
  (a) 车道该补坐标（计数、尺寸、比率这类主张旁边确实没锚点）；
  (b) 尺可能咬到了「不是主张」的形状（命中框四元组、URL 里的端口、渲染文本里的日期）。
只读：跑门（--text 模式）与读门自己的输出；不改任何块。
"""
import glob
import io
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
LC = os.path.dirname(HERE)
INBOX = r"D:\moodle\_qoder_ledger_inbox"
DOOR = os.path.join(LC, "claim_coordinate_check_r4e.py")
OUT = os.path.join(HERE, "red_shapes.json")
HEX40 = re.compile(r"^[0-9a-f]{40}$")


def door_lines(path):
    r = subprocess.run([sys.executable, DOOR, "--text", path, "--expect-clean"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600)
    out = (r.stdout or "") + (r.stderr or "")
    toks = []
    for m in re.finditer(r"^\s*line (\d+) (\w+) (\w+) \| (.*?) \| (.*)$", out, re.M):
        toks.append({"line": int(m.group(1)), "rule": m.group(2), "code": m.group(3),
                     "token": m.group(4).strip(), "why": m.group(5).strip()})
    return r.returncode, toks, out


def shape(tok, block_lines):
    t = tok.strip().strip("`")
    if re.match(r"^\d+,\d+,\d+,\d+$", t):
        return "RECT_4元组(命中框)"
    if re.match(r"^\d{2,5}$", t) and 100 <= int(t[:3] if len(t) >= 3 else int(t)) <= 599 and len(t) == 3:
        return "三位数(形状待认，未必是状态码)"
    if re.match(r"^\d{4,5}$", t):
        return "4-5 位数字(端口/年份位形状)"
    if re.search(r"[个条次处行字分秒枚档笔]", t):
        return "带中文量词的计数"
    if re.match(r"^\d+(\.\d+)?\s*(B|KB|MB|GB|ms|s|秒|分|小时|天)$", t, re.I):
        return "带单位的尺寸/时长"
    if HEX40.match(t):
        return "完整 40 位 blob"
    if re.match(r"^[0-9a-f]{6,39}$", t):
        return "短 hex(截断坐标形状)"
    if re.match(r"^ORD-\d{4}$|^REQ-\d{4}$", t):
        return "工单号"
    if re.match(r"^\d+$", t):
        return "裸整数"
    return "其它"


def main():
    files = sorted(glob.glob(os.path.join(INBOX, "*.md")))
    all_rows = []
    per_file = {}
    for f in files:
        rc, toks, out = door_lines(f)
        text = io.open(f, encoding="utf-8", errors="replace").read().split(chr(10))
        for tk in toks:
            tk["file"] = os.path.basename(f)
            ln = tk["line"] - 1
            tk["context"] = (text[ln][:160] if 0 <= ln < len(text) else "(行号越界)")
            tk["shape"] = shape(tk["token"], text)
            all_rows.append(tk)
        per_file[os.path.basename(f)] = {"rc": rc, "n": len(toks)}
        if rc == 0:
            per_file[os.path.basename(f)]["n"] = 0
    by_shape = {}
    for tk in all_rows:
        by_shape.setdefault(tk["shape"], []).append(tk)
    total = len(all_rows)
    print("扫描 %d 枚块；门报 finding 合计 %d 枚（尺 %s）" % (len(files), total, os.path.basename(DOOR)))
    order = sorted(by_shape.items(), key=lambda kv: -len(kv[1]))
    for shp, rows in order:
        print("  %-28s %3d 枚（%.0f%%）" % (shp, len(rows), 100.0 * len(rows) / max(total, 1)))
    print("\n每类给 2 个样本（原文来自门输出与块正文，行号是块内行号）：")
    for shp, rows in order:
        print("== %s" % shp)
        for tk in rows[:2]:
            print("   %s:%d  token=`%s`  why=%s" % (tk["file"], tk["line"], tk["token"][:40], tk["why"][:40]))
            print("      上下文：%s" % tk["context"][:150])
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(json.dumps(
        {"measured_at": time.strftime("%Y-%m-%dT%H:%M:%S+08"), "door": os.path.basename(DOOR),
         "door_sha1_local": None, "blocks": len(files), "findings": total,
         "per_file": per_file,
         "by_shape": {k: len(v) for k, v in by_shape.items()},
         "rows": all_rows}, ensure_ascii=False, indent=1))
    print("\n写收据 %s" % os.path.basename(OUT))


main()
