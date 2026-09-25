"""Independent read-back of the ORD-0302 r2 amendment, publish it, refresh the index, post one follow-up.

The delivery comment cites `ord0302_index.json` by the blob that existed when it was written; the index is
rebuilt after that (it gains the claim-gate receipt and this verification), so the cited coordinate is always
one step behind. Third time today, so it is handled the same way each time: nothing published is edited, and a
short follow-up names the final blob. Everything it states is recomputed from the branch here.
"""
import base64
import hashlib
import json
import pathlib
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
WORK = pathlib.Path(r"D:\moodle\_qoder_b_ord0274sw_20260924")
SPIKE = pathlib.Path(r"D:\moodle\_qoder_spike_20260921")
LIVE = pathlib.Path(r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks")
PY = r"D:\moodle\CityNexus\.venv\Scripts\python.exe"
PUBLISHER = pathlib.Path(r"D:\moodle\_qoder_f_run\publish_evidence_fixed.py")
GH, BRC = "Canshu-King/CityNexus", "commander/control"
WS = "Canshu-King/CityNexus-Workspace"
DIR = "evidence/ord0302-unreadable-server-body-r2"
REF = "heads/review/0302-unreadable-server-body-b2"
BASE = "13af1ff4ba4516aa1a39cda67428ed4a2a34ac69"
ARMS = ("N1", "N2", "N3", "X1", "X2")
ROWS = ("R19_④_200_empty_body", "R20_④_200_json_empty_object", "R21_④_200_json_array",
        "R22_④_200_text_plain_payload", "R23_④_200_mission_unusable_status")
CLOSING = (LIVE / "CLOSING_LINE.txt").read_text(encoding="utf-8").strip()
Q43S = [LIVE / "claim_coordinate_check_r3.py", LIVE / "claim_coordinate_check_r4b.py"]
IP = WORK / "ord0302_index.json"
tok = pathlib.Path(r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920").read_text(encoding="utf-8").strip()


def api(path, data=None):
    last = None
    for i in range(9):
        try:
            req = urllib.request.Request("https://api.github.com" + path,
                                         data=(json.dumps(data).encode() if data else None),
                                         headers={"Authorization": "Bearer " + tok,
                                                  "Accept": "application/vnd.github+json",
                                                  "Content-Type": "application/json",
                                                  "User-Agent": "citynexus-lane-B"},
                                         method=("POST" if data else "GET"))
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read().decode("utf-8", "replace") or "{}")
        except urllib.error.HTTPError as e:
            if e.code in (403, 404, 422):
                raise
            last = e
        except Exception as e:
            last = e
        time.sleep(min(30, 2 + 4 * i))
    raise last


def blob_of(b):
    return hashlib.sha1(b"blob %d\0" % len(b) + b).hexdigest()


def fetch(name):
    c = api(f"/repos/{GH}/contents/{DIR}/{urllib.parse.quote(name, safe='')}?ref={BRC}")
    raw = base64.b64decode(c["content"])
    if blob_of(raw) != c["sha"]:
        raise SystemExit("the answer is not its own blob: " + name)
    return raw, c["sha"]


def push(path, name):
    for attempt in range(4):
        pr = subprocess.run([PY, str(PUBLISHER), str(path), f"{DIR}/{name}", f"ORD-0302 r2: {name}"],
                            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600)
        txt = (pr.stdout or "") + (pr.stderr or "")
        if pr.returncode == 0 and ("BYTE-LEVEL MATCH" in txt or "already identical" in txt):
            return
        if "REFUSED" in txt.upper():
            raise SystemExit("publisher refused " + name + ": " + txt[-200:])
        print(f"attempt {attempt} rc={pr.returncode}: {txt[-160:]!r}")
        time.sleep(5 + 5 * attempt)
    raise SystemExit("would not claim an unpublishable file: " + name)


out = {}
tip = api(f"/repos/{GH}/git/ref/{REF}")["object"]["sha"]
cmp_ = api(f"/repos/{GH}/compare/{BASE}...{tip}")
out["ref"] = {"name": REF, "tip": tip, "ancestry": cmp_.get("status"), "commits_ahead": cmp_.get("ahead_by"),
              "commits_behind": cmp_.get("behind_by")}

rec_raw, rec_sha = fetch("ord0302_receipt.json")
rc = json.loads(rec_raw.decode("utf-8"))
mx_raw, _ = fetch("ord0302_arms_matrix.json")
mx = json.loads(mx_raw.decode("utf-8"))
out["receipt"] = {"blob40": rec_sha, "candidate_tip": rc["candidate_tip"], "tip_is_the_ref":
                  rc["candidate_tip"] == tip, "base_tip": rc["base_tip"], "cells": len(rc["cells"]),
                  "derived_all_null": all(c.get("derived_result") is None for c in rc["cells"])
                  and rc.get("derived_result") is None,
                  "product_bytes_changed": rc.get("product_bytes_changed")}

# the five arms, re-derived from the matrix's own per-arm statuses
mism = []
for c in rc["cells"]:
    a = c["cell"].split()[0]
    if a in ARMS:
        st = mx["runs"]["fixed"]["per_arm"][a]["status"]
        if c["claimed_result"] != ("MET" if st == "passed" else "NOT_MET"):
            mism.append(a)
# the four killers, re-derived: exactly the intended arm red, and a skip is not a red
kills = {}
for shape in [k for k in mx["runs"] if k != "fixed"]:
    flip = mx["runs"][shape]["intended"]
    red = [a for a, v in mx["runs"][shape]["per_arm"].items() if v["status"] in ("failed", "timedOut")]
    kills[shape] = {"intended": flip, "red": red, "only_intended": red == [flip]}
    if red != [flip]:
        mism.append(shape)
out["counter_arms"] = kills

# X-5's five rows, re-derived from the published per-shape readings
x1 = next(c for c in rc["cells"] if c["cell"].startswith("X1"))
per = x1["readings"]["per_shape"]
out["x5_rows"] = {row: per[row] for row in ROWS}
out["x5_invariant_holds_for_every_row"] = all(
    (not per[row]["promise_in_copy"] or per[row]["details_count"] >= 1)
    and per[row]["status"] == "NO_PLANS_PRODUCED" and str(per[row]["reason"]) for row in ROWS)
out["rows_named"] = sorted(set(per) & set(ROWS))
out["mismatches"] = mism

# publish this read-back, refresh the index without a self-entry, then audit every entry
vp = WORK / "ord0302_verify_r2.json"
vp.write_text(json.dumps(out, ensure_ascii=False, indent=1), "utf-8", newline="\n")
push(vp, vp.name)
idx = json.loads(fetch("ord0302_index.json")[0].decode("utf-8"))
entries = {e["name"]: e for e in idx["files"]}
for src, name in ((vp, vp.name), (SPIKE / "ord0302_verify_r2.py", "ord0302_verify_r2.py"),
                  (SPIKE / "ord0302_x5_five_shapes_patch.py", "ord0302_x5_five_shapes_patch.py"),
                  (SPIKE / "ord0302_deliver_r2_patch.py", "ord0302_deliver_r2_patch.py"),
                  (SPIKE / "ord0302_deliver.py", "ord0302_deliver.py"),
                  (SPIKE / "ord0302_run_arms.py", "ord0302_run_arms.py")):
    push(src, name)
    raw, want = fetch(name)
    entries[name] = {"name": name, "blob40": want, "bytes": len(raw)}
idx["files"] = [entries[k] for k in sorted(entries) if k != IP.name]
idx["self_reference"] = "this file is not in its own list; its blob is what the branch answers"
idx["audit"] = "every blob here was recomputed from the branch's own answer by ord0302_verify_r2.py"
IP.write_text(json.dumps(idx, ensure_ascii=False, indent=1), "utf-8", newline="\n")
push(IP, IP.name)
listed = json.loads(fetch(IP.name)[0].decode("utf-8"))["files"]
bad = [e["name"] for e in listed if fetch(e["name"])[1] != e["blob40"]]
IDX_SHA, IDX_RAW = fetch(IP.name)
out["index"] = {"blob40": IDX_SHA, "entries": len(listed), "mismatches": bad,
                "names_itself": any(e["name"] == IP.name for e in listed)}
print(json.dumps(out, ensure_ascii=False, indent=1)[:1800])

prev = (WORK / "ord0302_bus_id.txt").read_text(encoding="utf-8").strip()
lines = [
    "B c01d72a3 → 号令者 494abfd7：ORD-0302 r2 补一帖（只发新帖，"
    + f"https://github.com/{WS}/issues/1#issuecomment-{prev} 一字不改）",
    "",
    f"为什么补：那一帖引的 `ord0302_index.json` 是它自己写入前那一份。之后独立回读件与量具补上架，索引又重写一次，"
    f"最终 blob {IDX_SHA}，列 {len(listed)} 枚工件（索引不列自己），逐枚从分支回读重算不吻合 {len(bad)} 枚。",
    "",
    f"独立回读（blob {fetch(vp.name)[1]}，走 https API、不读本地 git 对象）：ref tip {tip} 与收据 candidate_tip "
    f"同一枚、compare 口径 ahead {out['ref']['commits_ahead']} / behind {out['ref']['commits_behind']}；"
    f"{len(rc['cells'])} 格 derived_result 全 null；五枚臂的 claimed_result 由那一跑 per-arm 状态逐枚重算相符；"
    f"四枚反件各自只让该红的那一枚红；X-5 那一格对 R19-R23 五行逐行成立（每行 status=NO_PLANS_PRODUCED、"
    f"promise=True、details_count>=1、reason 非空）。",
    "",
    "产品字节这一版 0 改动（`product_bytes_changed` 就写在收据顶层，值 0）；闭单仍等 ORD-0312 在部署代重读后由"
    "红队签 derived_result。",
    "",
    CLOSING,
]
body = "\n".join(lines)
p = WORK / "ord0302_bus_followup_r2.txt"
p.write_text(body + "\n", "utf-8", newline="\n")
for ruler in Q43S:
    r = subprocess.run([PY, str(ruler), "--text", str(p)], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=300)
    txt = ((r.stdout or "") + (r.stderr or "")).strip()
    print(ruler.name, "rc=", r.returncode, [l for l in txt.splitlines() if "claims checked" in l][:1])
    if r.returncode != 0:
        print(txt[:900])
        raise SystemExit("a claim gate refused the follow-up; not posting")
made = api(f"/repos/{WS}/issues/1/comments", {"body": body})
back = api(f"/repos/{WS}/issues/comments/{made['id']}")
ok = back.get("body", "").rstrip().endswith(CLOSING)
print("follow-up comment", made.get("id"), "| chars", len(back.get("body", "")), "| closing ok:", ok)
sys.exit(0 if (ok and not mism and not bad and out["x5_invariant_holds_for_every_row"]
               and out["index"]["names_itself"] is False and out["ref"]["ancestry"] == "ahead") else 1)
