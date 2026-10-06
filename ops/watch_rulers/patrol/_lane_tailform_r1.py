# -*- coding: utf-8 -*-
u"""流水末态尺：给一扇车道，报末三条对话节点（形态＋几���前）＋能不能敲门。

为什么要有它（20:11 第三次踩时间戳形状）：今晚我为同一件事写过三个探针，三次都栽在**同一处**——
Qoder 的 jsonl 里 `timestamp` 有两种形状：整数 epoch **毫秒**（1791286362177）与
ISO 字符串（2026-10-06T12:10:11.518Z），还有的节点**没有**这个键。
每次现写一个就崩一次 ⇒ 固化成一把尺，所有车道都用它。

判「该不该敲」只看末态形态（这是交接稿五·三十三/四十九那条结论）：
  末条 assistant tool_use 而**没有**更晚的 tool_result ⇒ 断在半路（该敲）
  末条 assistant text/thinking　　　　⇒ 交活型停着（**不该敲**，等下一单）
  末条距今 < 阈值　　　　　　　　　　 ⇒ 在写（不该敲）

用法：python _lane_tailform_r1.py 0afdb49b 8ac89982 [...]
"""
import datetime
import io
import json
import os
import sys
import time

D = os.path.join(os.path.expanduser("~"), ".qoder", "projects", "D--moodle")


def to_epoch(ts):
    u"""两种形状都认：int/float（毫秒或秒）、ISO 串、空。取不到返回 None（不猜）。"""
    if ts is None or ts == "":
        return None
    if isinstance(ts, (int, float)):
        v = float(ts)
        if v > 1e11:          # 毫秒
            v /= 1000.0
        elif v < 1e8:         # 秒数都不像（太小），当不可判
            return None
        return v
    s = str(ts)
    try:
        t = datetime.datetime.fromisoformat(s.replace("Z", "+00:00"))
        if t.tzinfo is None:
            t = t.replace(tzinfo=datetime.timezone.utc)
        return t.timestamp()
    except Exception:
        return None


def dialogue_nodes(pre):
    u"""只收有 role 或 content 的节点——active-leaf/runtime-config 那类脚手架节点不算（20:00 实测）。"""
    hits = [f for f in os.listdir(D) if f.startswith(pre) and f.endswith(".jsonl")]
    if not hits:
        return None
    out = []
    for line in io.open(os.path.join(D, hits[0]), encoding="utf-8", errors="replace"):
        line = line.strip()
        if not line:
            continue
        try:
            n = json.loads(line)
        except Exception:
            continue
        m = n.get("message")
        if isinstance(m, dict) and (m.get("role") or m.get("content")):
            out.append(n)
    return out


def shape(m):
    c = m.get("content")
    if isinstance(c, str):
        return u"text(%d 字)" % len(c)
    if isinstance(c, list):
        ks = []
        for b in c:
            t = (b or {}).get("type")
            ks.append(t + (u":" + (b or {}).get("name", u"") if t == "tool_use" else u""))
        return u"、".join(ks) or u"(空)"
    return u"(无 content)"


def verdict(nodes, now):
    last = nodes[-1]
    m = last["message"]
    role = m.get("role")
    sh = shape(m)
    if role == "user" and u"tool_result" in sh:
        return u"工具回包中（上一拍敲过工具）", False
    if role != "assistant":
        return u"末条不是 assistant（%s）" % role, False
    if u"tool_use" in sh:
        has_reply = any(shape((n.get("message") or {})) .find(u"tool_result") >= 0
                        for n in nodes[:-1][-5:])
        if not has_reply:
            return u"**断在半路**：末条 tool_use 且近五条无 tool_result", True
        return u"tool_use 已回音", False
    return u"**交活型停着**：末条是 %s" % sh, False


def main():
    pres = sys.argv[1:]
    if not pres:
        print(u"用法：python _lane_tailform_r1.py <id8> [<id8>…]")
        return 1
    now = time.time()
    for pre in pres:
        nodes = dialogue_nodes(pre)
        if nodes is None:
            print(u"【%s】jsonl 不在 %s" % (pre, D))
            continue
        print(u"【%s】对话节点 %d" % (pre, len(nodes)))
        for n in nodes[-3:]:
            m = n["message"]
            sec = to_epoch(n.get("timestamp"))
            age = u"%.0f 分前" % ((now - sec) / 60.0) if sec else u"时刻不可判"
            print(u"   %-10s %-34s %s" % (m.get("role"), shape(m), age))
        v, knock = verdict(nodes, now)
        print(u"   ⇒ %s" % v)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())