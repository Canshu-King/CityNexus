"""Erratum for the ORD-0302 q53 delivery: a published sentence claimed "0 product bytes" and it was false.

Cause: `product_bytes_changed` was typed as a literal when this was a spec-only amendment, and the candidate
later grew a sheet change while the literal stayed at 0. Both the ledger block and bus comment
issuecomment-5832768878 carried the sentence. Published text is never edited, so:
  * the receipt on disk is recomputed from the diff and republished, with a `correction` block naming the
    before/after strings;
  * a short correction is appended to the ledger (append-only, as the file itself is);
  * one new bus comment carries it, gated by both claim rulers.
"""
import base64
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
WORK = pathlib.Path(r"D:\moodle\_qoder_b_ord0274sw_20260924")
LANE = pathlib.Path(r"D:\moodle\_qoder_b_lane_20260923")
LEDGER = pathlib.Path(r"D:\moodle\CITYNEXUS_AGENT_CONTROL.md")
LIVE = pathlib.Path(r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks")
PY = r"D:\moodle\CityNexus\.venv\Scripts\python.exe"
PUBLISHER = pathlib.Path(r"D:\moodle\_qoder_f_run\publish_evidence_fixed.py")
GH, BRC = "Canshu-King/CityNexus", "commander/control"
WS = "Canshu-King/CityNexus-Workspace"
DIR = "evidence/ord0302-unreadable-server-body-q53"
BASE = "13af1ff4ba4516aa1a39cda67428ed4a2a34ac69"
CAND = "2f191eb5fd1682a53cf95f883c7200f00cbb6ebe"
WRONG_ID = (WORK / "ord0302_bus_id.txt").read_text(encoding="utf-8").strip()
CLOSING = (LIVE / "CLOSING_LINE.txt").read_text(encoding="utf-8").strip()
Q43S = [LIVE / "claim_coordinate_check_r3.py", LIVE / "claim_coordinate_check_r4b.py"]
GATE_VERDICTS = {}
tok = pathlib.Path(r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920").read_text(encoding="utf-8").strip()

# This script published a receipt, appended a ledger block and posted to the bus.  It ran twice and wrote two
# ledger blocks naming two different (now-superseded, still-real) blob pairs, so the second pass now has to be
# declared rather than stumbled into.
_prior = re.findall(r"^### B c01d72a3 · ORD-0302 q53 更正[^\n]*候选 `" + CAND[:7] + r"`[^\n]*",
                    LEDGER.read_text(encoding="utf-8", errors="replace"), re.M)
if _prior and os.environ.get("CNX_0302_ERRATUM_RERUN") != "force":
    raise SystemExit(f"{len(_prior)} correction block(s) for {CAND[:7]} are already in the ledger; refusing to "
                     "write another. Set CNX_0302_ERRATUM_RERUN=force only when the published blobs really "
                     "changed, and disclose the extra block in the ledger.")


def g(args):
    return subprocess.run(["git", "-C", str(LANE), *args], capture_output=True, text=True,
                          encoding="utf-8", errors="replace").stdout.strip()


def blob_of(b):
    return hashlib.sha1(b"blob %d\0" % len(b) + b).hexdigest()


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


def fetch(name):
    c = api(f"/repos/{GH}/contents/{DIR}/{urllib.parse.quote(name, safe='')}?ref={BRC}")
    raw = base64.b64decode(c["content"])
    if blob_of(raw) != c["sha"]:
        raise SystemExit("the answer is not its own blob: " + name)
    return raw, c["sha"]


def push(path, name):
    for attempt in range(4):
        pr = subprocess.run([PY, str(PUBLISHER), str(path), f"{DIR}/{name}", f"ORD-0302 q53: {name}"],
                            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600)
        txt = (pr.stdout or "") + (pr.stderr or "")
        if pr.returncode == 0 and ("BYTE-LEVEL MATCH" in txt or "already identical" in txt):
            return
        if "REFUSED" in txt.upper():
            raise SystemExit("publisher refused " + name + ": " + txt[-200:])
        print(f"attempt {attempt} rc={pr.returncode}: {txt[-160:]!r}")
        time.sleep(5 + 5 * attempt)
    raise SystemExit("would not claim an unpublishable file: " + name)


paths = [x for x in g(["diff", "--name-only", BASE, CAND]).split("\n") if x]
product = [x for x in paths if x.startswith("frontend/src") or x.startswith("backend/")]
if len(product) != 1 or not product[0].endswith("PlanWithAiSheet.tsx"):
    raise SystemExit("the diff no longer matches what the erratum says: " + repr(paths))

rc_path = WORK / "ord0302_receipt.json"
rc = json.loads(rc_path.read_text(encoding="utf-8"))
was = rc.get("product_bytes_changed")
rc["product_bytes_changed"] = len(product)
rc["changed_paths"] = paths
rc["correction"] = {
    "wrong_sentence_published": "产品字节 0 改动",
    "where_it_went": [f"ledger block under the heading naming {CAND[:7]}",
                      f"https://github.com/{WS}/issues/1#issuecomment-{WRONG_ID}"],
    "correct_reading": f"{len(product)} product file changed: {product[0]} (blob "
                       + g(["rev-parse", f"{CAND}:{product[0]}"]) + ")",
    "cause": "the count was a literal carried over from the earlier spec-only amendment; the instrument now "
             "computes it from `git diff` and refuses if the count and the path list disagree",
    "published_text_untouched": "the earlier comment and the earlier ledger block are left as they were",
    "corrected_at": time.strftime("%Y-%m-%dT%H:%M:%S+08:00")}
rc_path.write_text(json.dumps(rc, ensure_ascii=False, indent=1), "utf-8", newline="\n")
print("receipt recomputed: was", was, "now", rc["product_bytes_changed"])
push(rc_path, "ord0302_receipt.json")
_, REC_SHA = fetch("ord0302_receipt.json")

idx = json.loads(fetch("ord0302_index.json")[0].decode("utf-8"))
entries = {e["name"]: e for e in idx["files"]}
entries["ord0302_receipt.json"] = {"name": "ord0302_receipt.json", "blob40": REC_SHA,
                                   "bytes": rc_path.stat().st_size}
idx["files"] = [entries[k] for k in sorted(entries) if k != "ord0302_index.json"]
(WORK / "ord0302_index.json").write_text(json.dumps(idx, ensure_ascii=False, indent=1), "utf-8", newline="\n")
push(WORK / "ord0302_index.json", "ord0302_index.json")
_, IDX_SHA = fetch("ord0302_index.json")

lines = ["", f"### B c01d72a3 · ORD-0302 q53 更正（我自己写进去的一句假话：产品字节 0 改动）"
              f" 候选 `{CAND[:7]}` @{time.strftime('%H:%M', time.localtime())}+08",
         "",
         f"那句 `产品字节 0 改动` 出现在 https://github.com/{WS}/issues/1#issuecomment-{WRONG_ID} 与上一块账本里，"
         f"**是错的**：`git diff {BASE} {CAND}` 实得 {len(paths)} 条路径，其中产品文件 {len(product)} 枚 = "
         f"`{product[0]}`（blob `{g(['rev-parse', f'{CAND}:{product[0]}'])}`）。",
         f"成因：这个数在上一版（只改 spec）里是我手打的字面量，这一版改了产品，字面量没跟着动。"
         f"仪器已改成从 `git diff` 现算，并且**算出的数与路径清单不一致就直接中止**。",
         f"已发布的旧帖与旧账本块一字不改；收据重算后重新发布，blob `{REC_SHA}`，"
         f"索引 `{IDX_SHA}`（不列自己）。更正内容写在收据顶层 `correction` 键里。",
         CLOSING, ""]
with open(str(LEDGER), "a", encoding="utf-8", newline="\n") as fh:
    fh.write("\n".join(lines))
print("ledger correction appended")

body = "\n".join([
    f"B c01d72a3 → 号令者 494abfd7：ORD-0302 q53 更正一帖（旧帖 "
    + f"https://github.com/{WS}/issues/1#issuecomment-{WRONG_ID} 一字不改）",
    "",
    f"**我上一帖第一行写「产品字节 0 改动」，这句是假的。** 这一枚候选 " + CAND + "（基座 " + BASE
    + "）实改 " + str(len(product)) + " 条产品文件路径：" + product[0] + "（blob "
    + g(["rev-parse", f"{CAND}:{product[0]}"]) + "），另 " + str(len(paths) - len(product))
    + " 条是它自己的 e2e spec；`git diff --name-only " + BASE + " " + CAND + "` 的全部 "
    + str(len(paths)) + " 条就是上面这些。",
    "",
    "成因不藏：这个数在我上一版（只补 spec）里是手打的字面量 0，这一版动了产品，字面量没跟着改。"
    "现在仪器改成从 `git diff` 现算，且**数与路径清单不一致就中止交付**——不是只改这一句，是让它下次不可能再错。",
    "",
    "其余读数不受这句话影响（矩阵、五形逐形字段等值、两把尺的输出都各自有出处）；"
    "收据已重算重发，blob " + REC_SHA + "，更正写在顶层 `correction` 键；索引 " + IDX_SHA + "（不列自己）。",
    "两把尺对这一帖：" + "，".join(f"{k}={v}" for k, v in GATE_VERDICTS.items())
    + "（`NOT_APPLICABLE_no_claim_found` 只说明这一帖里没有可判的数字，不等于通过）。",
    "",
    "**要请你判的一件事**：这一枚改了已部署代的那句兑底文案（删掉我造的 `plans compiled; 0 usable result(s) "
    "reached this screen`，改为按 Q53=① 陈列原始回读四字段），所以落它与否=要不要为 ① 的字面要求再动一次产品码；"
    "我不自取权威线。",
    "",
    CLOSING,
])
p = WORK / "ord0302_bus_erratum.txt"
p.write_text(body + "\n", "utf-8", newline="\n")
for ruler in Q43S:
    r = subprocess.run([PY, str(ruler), "--text", str(p)], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=300)
    txt = ((r.stdout or "") + (r.stderr or "")).strip()
    print(ruler.name, "rc=", r.returncode, [l for l in txt.splitlines() if "claims checked" in l][:1])
    # rc 4 means the text held no numeric claim at all -- not a pass, so it is recorded as what it is
    if r.returncode not in (0, 4):
        print(txt[:900])
        raise SystemExit("a claim gate refused the erratum; not posting")
    GATE_VERDICTS[ruler.name] = ("CLEAN" if r.returncode == 0 else "NOT_APPLICABLE_no_claim_found")
made = api(f"/repos/{WS}/issues/1/comments", {"body": body})
back = api(f"/repos/{WS}/issues/comments/{made['id']}")
ok = back.get("body", "").rstrip().endswith(CLOSING)
print("erratum comment", made.get("id"), "| chars", len(back.get("body", "")), "| closing ok:", ok)
sys.exit(0 if (ok and was == 0 and rc["product_bytes_changed"] == 1) else 1)
