r"""额度恢复探测：谁从"限流回复"里回来了。

09-26 夜里量到的形状：停在日额度的会话，**末尾一条 assistant 就是那句额度文案**，且 JSONL 不再增长。
所以"回来"= 那之后又出现一条**不是额度文案的** assistant（或整段被续写）。
判据只用文件本身，不看 runtimeState（它会在冻死时仍报 running）。
状态存 recover_watch_state.json：{车道id: {"size": 上次字节数, "capped": 上次是否停机}}
"""
import glob
import io
import json
import re
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = r"C:\Users\仓鼠王\.qoder\projects\D--moodle"
STATE = os.path.join(HERE, "recover_watch_state.json")
CAP = "daily usage limit for Chat"
L = {"494abfd7": "号令者", "8ccd71d8": "F", "aad2d1f2": "HJ-P3", "e345b9d6": "D",
     "c01d72a3": "B", "d2305848": "E 红队", "a17ae861": "S3", "8e094dec": "S1",
     "d9e2c9ae": "S2", "1d64acf5": "S4", "352ef353": "N1", "9759f1ac": "N2",
         "be19052c": "道tokens", "8e5245f0": "道0369", "e4f3490f": "道0370"}



KNOWN = {
    "4033270f": "道0383","494abfd7": "号令者", "8ccd71d8": "F", "aad2d1f2": "HJ-P3", "e345b9d6": "D",
         "c01d72a3": "B", "d2305848": "E 红队", "a17ae861": "S3", "8e094dec": "S1",
         "d9e2c9ae": "S2", "1d64acf5": "S4", "352ef353": "N1", "9759f1ac": "N2",
         "be19052c": "道tokens", "8e5245f0": "道0369", "e4f3490f": "道0370"}
ME = "42d1a6fa"
NON_PROJECT = {"a6b95d59"}   # 平板 DSH 部署会话，不在包工头的工作流里（09-28 01:43 核过首条与末条）
LANE_RE = re.compile(r"车道 ([A-Za-z0-9][A-Za-z0-9\-]{0,6})")
ORDER_RE = re.compile(r"(?:新工单|ORDER|ORD-) ?(ORD-\d{4})")


def discover(max_age_h=16.0):
    """名册不能手写：09-26 一夜号令者新开 N1/N2/N3 三条，我手写名册两次漏人。
    ⇒ 现扫 projects/D--moodle/*.jsonl（排除我自己），近 max_age_h 小时有落盘的都算车道；
      名字从首条 user 里的「车道 X」取，取不到就退回 KNOWN，再退回 id 前 8 位。"""
    now = time.time()
    cache = {}
    try:
        cache = json.load(io.open(STATE, encoding="utf-8")).get("_names", {})
    except Exception:
        pass
    found = {}
    for p in glob.glob(os.path.join(BASE, "*.jsonl")):
        key = os.path.basename(p)[:8]
        if key == ME or key in NON_PROJECT:
            continue
        st = os.stat(p)
        if now - st.st_mtime > max_age_h * 3600:
            continue
        nm = cache.get(key) or KNOWN.get(key)
        if not nm:
            nm = None                           # 先别拿 id 当名字，得先证明这条会话是本项目的
            try:
                for rec in io.open(p, encoding="utf-8", errors="replace").read().split(chr(10))[:80]:
                    try:
                        d = json.loads(rec)
                    except Exception:
                        continue
                    m = d.get("message") or {}
                    if m.get("role") != "user":
                        continue
                    c = m.get("content")
                    txt = (" ".join(x.get("text", "") for x in c if isinstance(x, dict))
                           if isinstance(c, list) else str(c))
                    mm = LANE_RE.search(txt)
                    if mm:
                        nm = mm.group(1)
                        break
                    mo = ORDER_RE.search(txt)
                    if mo:                      # 09-28 夜班：新车道的第一条指令里没有"车道 X"，只有工单号
                        nm = "道" + mo.group(1)[4:]
                        break
                    if "CityNexus" in txt:
                        nm = key
                        break
            except Exception:
                pass
        if not nm:
            continue                            # 不是本项目车道 ⇒ 不进名册，也不会有人替我去敲它
                                                # （09-28 01:43 就是这么排掉 `a6b95d59` 的：那是平板 DSH 部署会话）
        found[key] = nm
    cache.update(found)
    try:
        old = {}
        try:
            old = json.load(io.open(STATE, encoding="utf-8"))
        except Exception:
            old = {}
        old["_names"] = cache
        json.dump(old, io.open(STATE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    except Exception:
        pass
    return found


def probe(key):
    p = max(glob.glob(os.path.join(BASE, key + "*.jsonl")), key=os.stat)
    st = os.stat(p)
    last = ""
    for rec in io.open(p, encoding="utf-8", errors="replace").read().rstrip().split("\n")[::-1]:
        try:
            d = json.loads(rec)
        except Exception:
            continue
        m = d.get("message") or {}
        if m.get("role") == "assistant":
            c = m.get("content")
            last = (" ".join(x.get("text", "") for x in c if isinstance(x, dict))
                    if isinstance(c, list) else str(c)).strip()
            break
    return {"size": st.st_size, "mtime": st.st_mtime, "capped": CAP in last,
            "last_kind": ("cap" if CAP in last else ("empty" if not last else "text"))}


def load():
    try:
        return json.load(io.open(STATE, encoding="utf-8"))
    except Exception:
        return {}


def main():
    now = time.time()
    prev = load()
    cur = {}
    recovered, dead, working = [], [], []
    L = discover()
    for k, nm in sorted(L.items(), key=lambda kv: kv[1]):
        s = probe(k)
        cur[k] = s
        old = prev.get(k)
        idle = (now - s["mtime"]) / 60.0
        if s["capped"]:
            dead.append("%s(%s idle %.0fm)" % (nm, k, idle))
        elif old and old.get("capped"):
            recovered.append("%s(idle %.1fm, 末尾已是正常回复)" % (nm, idle))
        elif idle <= 6:
            working.append("%s %.1fm" % (nm, idle))
        else:
            working.append("%s %.0fm?" % (nm, idle))
        if old and not s["capped"] and not old.get("capped"):
            d = s["size"] - old["size"]
            if d > 200000:
                recovered.append("%s 自上次 +%.1f MB（在写）" % (nm, d / 1e6))
    cur["_names"] = load().get("_names", {})     # 名字缓存要跟着写回去，否则每次跑都忘一次名册
    json.dump(cur, io.open(STATE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("[%s] 在写/可动: %s" % (time.strftime("%H:%M:%S", time.localtime(now)), "、".join(working) or "无"))
    print("  仍停机: %s" % ("、".join(dead) or "无"))
    if recovered:
        print("  >>> 回来了: %s" % "、".join(recovered))
    print("  合计 停机 %d / %d 条会话" % (len(dead), len(L)))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
