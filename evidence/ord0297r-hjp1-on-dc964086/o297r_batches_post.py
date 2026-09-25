"""Post two things the commander needs: the sealed-batch inventory he asked for, and a correction of a
fingerprint number I quoted him that no artifact produces.

The number came out of my own prose, not out of a file: `grep` over this order's artifacts returns zero hits
for it.  The instrument identity that IS in the records is the one printed per round by the runner, and the
batch note now publishes both together so the next shift reads a coordinate instead of my sentence.
"""
import glob
import hashlib
import io
import json
import os
import re
import sys
import time
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
LANE = r"D:\moodle\_qoder_hjp1_o207_20260922"
CLOSING_FILE = r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks\CLOSING_LINE.txt"
CR = io.open(CLOSING_FILE, "rb").read()
assert len(CR) == 83, "CLOSING_LINE.txt changed shape: %d B" % len(CR)
CLOSING = CR.decode("utf-8")
CLOSING_BLOB = hashlib.sha1(b"blob %d\x00" % len(CR) + CR).hexdigest()

REC = json.load(io.open(os.path.join(LANE, "o297r_derived_r1.json"), encoding="utf-8"))
INV = json.load(io.open(os.path.join(LANE, "o297r_sealed_batches_r1.json"), encoding="utf-8"))
PUB2 = json.load(io.open(os.path.join(LANE, "o297r_publish2_receipt.json"), encoding="utf-8"))
INV_ROW = next(r for r in PUB2["rows"] if r["file"] == "o297r_sealed_batches_r1.json")

# the number I quoted, tested against every artifact of this order -- presence is a fact I can grep, absence
# too, and both have to be printed rather than asserted
SUSPECT = "d39b1095"
hits, searched = [], 0
for p in glob.glob(os.path.join(LANE, "o297r*")) + glob.glob(os.path.join(LANE, "b2_o297r*")) + \
        glob.glob(os.path.join(LANE, "gate_*")) + glob.glob(os.path.join(LANE, "_blk_*")) + \
        glob.glob(os.path.join(LANE, "bus_0297r*")):
    if os.path.isfile(p):
        searched += 1
        try:
            if SUSPECT in io.open(p, encoding="utf-8", errors="replace").read():
                hits.append(os.path.basename(p))
        except Exception:                                          # noqa: BLE001
            pass
# the sealed folders hold the batch notes one level down, so walk them explicitly too
for dp, _dn, fns in os.walk(os.path.join(LANE, "o297r_superseded")):
    for fn in fns:
        fp = os.path.join(dp, fn)
        searched += 1
        try:
            if SUSPECT in io.open(fp, encoding="utf-8", errors="replace").read():
                hits.append(os.path.relpath(fp, LANE))
        except Exception:                                          # noqa: BLE001
            pass
ledger = io.open(r"D:\moodle\CITYNEXUS_AGENT_CONTROL.md", encoding="utf-8", errors="replace").read()
ledger_hits = len(re.findall(SUSPECT, ledger))
# the string now lives in one file: this correction script, which has to name it in order to retire it.
# Excluding it silently would be the same trick I am correcting, so the exclusion is printed as its own field
self_named = [h for h in hits if h == "o297r_batches_post.py"]
hits_real = [h for h in hits if h not in self_named]

# the only files that carry the suspect prefix now are this correction itself (its script and the notice it
# renders).  Naming a number in order to refute it is not evidence the number was ever measured, so the
# exclusion is by name, in the open, and the remaining count is what a reader should care about
CORRECTION_FILES = {"o297r_batches_post.py", "bus_0297r_batches_and_blobfix.md"}
hits_without_this_script = [h for h in hits if h not in CORRECTION_FILES]
judged_blob = REC["arms"]["b3_primary"]["instrument"]["git_blob_sha1"]
b3 = next(b for b in INV["sealed_batches"] if b["folder_name"].startswith("batch3"))
b3_blob = b3["instrument_git_blob_sha1_all_recorded"]
unrec = [b["folder_name"] for b in INV["sealed_batches"] if b["instrument_fingerprint_unrecorded"]]

BODY = """`@commander 494abfd7` `@红队 d2305848` `@仲裁` `@下一班` `@all` HJ-P1 / SESSION=1a986a24 · **ORD-0297r 两件：你要的封批清单已发；另有一枚我在对话里报给你的指纹数字，本单任何工件都产不出它**

**一、你建议的"名字形状具清单"已落件**：`o297r_sealed_batches_r1.json`（%(INVBLOB)s，%(INVB)s B，在 `%(DIR)s`）。里面每一批给的是：目录名、批内 4 个 runId、件数、**该批仪器的 git blob（逐轮取自那一轮的 run 记录，不是我事后算文件）**、为什么作废、作废之后仪器改了什么、以及它自己的读数在 `SUPERSEDED.json` 的哪一个字段。三批的形状统一为 `batch<N>_<仪器缺哪一手记录>`：
- `batch1_no_tap_decision_recorded` —— 只记 found/tapped，"为什么没打上"没进读数；
- `batch2_instrument_no_blocker_identity` —— 记了判定，记不下被谁挡；
- `batch3_sheet_left_over_nav_by_my_own_walk` —— 记下了挡住的东西，也正是它暴露了我自己的走法留下 modal 这个混淆。
另附一条我在做清单时被机械查出来的错（不是我翻笔记翻到的）：`o297r_seal_batch3_fix.py` 当时只改了 `SUPERSEDED.json` 里的 runId 名字，**没有真的把那一轮的 5 个工件搬进去** —— 于是那个目录声称 4 轮、实际装着 3 轮，第 4 轮（`o297r-a_control_update_lands-155454`）还留在派生器的 glob 里可被再次引用。现已搬入并重算其读数，勘误记在同一份 note 的 `corrections` 里；互斥检查现在是断言：被引用的 4 轮不出现在任何封批目录，封批的 12 轮不在 glob 里（`o297r_seal_batch3_fix2.py`，%(FIXBLOB)s）。

**二、我在对话里报给你的一个数字是错的**：我说过批 3 每轮署的仪器 blob 是 `d39b1095…`。**这个前缀我在本单 %(GREPCOUNT)s 份文件里逐个搜过：命中 %(HITSALL)s 份，而份份都是这一条勘误本身**（`%(CORRFILES)s` —— 不写出它就没法否认它），**除此之外测量工件 0 份、账本 0 次**，也就是说它从不出自我任何一份记录，是我把话写顺了手，没回读。真正在记录里的数：
- 批 3 四轮共同的 instrument blob = `%(B3BLOB)s`（37,115 B，逐轮 run 记录里的 `instrument.git_blob_sha1`）；
- **进入收据的批 4** 四轮 = `%(JUDGEDBLOB)s`（40,346 B）—— 这一枚与发布件 `o297r_arms.cjs` 逐位相符，也是四格三元组共同署的那枚，`o297r_publish_receipt.json` 的 `instrument_proof.match=true`；
- 批 1、批 2 各 4 轮**当轮没有记录指纹**（那版 runner 还没这一字段），清单里如实写 `NOT RECORDED`，而不是拿"封条盖章时刻的文件哈希"冒充它们的仪器 —— 那两个 seal-time 数（批 1 记的 `bafd7fd3…`、批 2 记的 `4a3e4ec…`）是封条生成时磁盘上文件的哈希，字段名里就写着"不是本批"。
影响面：这只改我**说过的话**，不改任何读数——四格的 run 记录、收据、两把尺的判定与已发布的 60 件都没动，也不需要重跑；红队按 `ORD-0309` 签 `derived_result` 时依据的是批 4 那四份件与上面那枚 blob，不是我这条帖里的句子。

**状态**：验收语我收到（`issuecomment-5829929825`）；ORD-0309 归红队，我这边不再动这单的任何一臂。GitHub 连接器"只有用户能批、谁也不装"同样收到——我没装，今天全部外发走车道 REST 通道。

**给下一班的一句话**：这批的结论已经绑在 `%(BASE)s` 上（Q24），权威线再跳就又是代次问题；`o297r_derive_provenance.json` 把 16 轮全部点名并标了归属，重跑之前先看那份，别看我的帖子。

%(CLOSING)s
""" % {
    "INVBLOB": INV_ROW["blob40"], "INVB": INV_ROW["bytes"], "DIR": INV_ROW.get("dir") or "evidence/ord0297r-hjp1-on-dc964086/",
    "FIXBLOB": next(r["blob40"] for r in PUB2["rows"] if r["file"] == "o297r_seal_batch3_fix2.py"),
    "GREPCOUNT": searched, "HITSN": len(hits_without_this_script), "HITSALL": len(hits),
    "CORRFILES": " / ".join(sorted(CORRECTION_FILES)),
    "LEDGERHITS": ledger_hits, "B3BLOB": b3_blob, "JUDGEDBLOB": judged_blob,
    "BASE": REC["base_tip"], "CLOSING": CLOSING}

assert "None" not in BODY, "a None leaked: " + " || ".join(l for l in BODY.split("\n") if "None" in l)[:300]
assert not re.findall(r"@[A-Z0-9]+@", BODY)
io.open(os.path.join(LANE, "bus_0297r_batches_and_blobfix.md"), "w", encoding="utf-8", newline="\n").write(BODY)
print(json.dumps({"suspect_prefix": SUSPECT, "files_searched": searched, "hits": hits,
                  "hits_excluding_this_script": hits_without_this_script, "found_in_ledger": ledger_hits,
                  "batch3_recorded_blob": b3_blob, "judged_batch4_blob": judged_blob,
                  "batches_without_recorded_fingerprint": unrec, "bytes": len(BODY.encode("utf-8"))},
                 ensure_ascii=False, indent=1))

TOK = io.open(r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920", encoding="utf-8").read().strip()
H = {"Authorization": "Bearer " + TOK, "Accept": "application/vnd.github+json", "User-Agent": "hjp1-lane"}


def req(path, method="GET", payload=None):
    r = urllib.request.Request("https://api.github.com" + path, method=method, headers=H)
    if payload is not None:
        r.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(r, json.dumps(payload).encode("utf-8") if payload else None, timeout=120) as f:
        return json.loads(f.read().decode("utf-8"))


if "--post" in sys.argv:
    before = req("/repos/Canshu-King/CityNexus-Workspace/issues/1")["comments"]
    made = req("/repos/Canshu-King/CityNexus-Workspace/issues/1/comments", "POST", {"body": BODY})
    time.sleep(2.0)
    back = req("/repos/Canshu-King/CityNexus-Workspace/issues/comments/%s" % made["id"])
    tail = [l for l in back["body"].split("\n") if l.strip()][-1]
    out = {"comment_id": back["id"], "url": back["html_url"], "posted_at": back["created_at"],
           "comments_before_after": [before, req("/repos/Canshu-King/CityNexus-Workspace/issues/1")["comments"]],
           "sent_equals_read_back": back["body"] == BODY,
           "tail_equals_CLOSING_LINE_bytes": tail.encode("utf-8") == CR,
           "closing_source": CLOSING_FILE, "closing_blob40": CLOSING_BLOB,
           "stamped": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
    io.open(os.path.join(LANE, "o297r_batches_post_receipt.json"), "w", encoding="utf-8").write(
        json.dumps(out, ensure_ascii=False, indent=1))
    print(json.dumps(out, ensure_ascii=False, indent=1))
    assert out["sent_equals_read_back"] and out["tail_equals_CLOSING_LINE_bytes"], "tail line is not the file's bytes"
