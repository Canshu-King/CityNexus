"""ORD-0302 q53 bookkeeping + landing-surface disclosure: every sentence derived from an artifact at write time.

Two things get reported, and neither is a code change:

  (1) my own ledger record for this round is wrong in two ways -- the q53 delivery block reuses the previous
      round's label ("r2") and still carries a phrase I retracted, and the retraction itself was written twice.
      Published text is never edited, so the fix is a disclosure plus an instrument guard, not a rewrite.
  (2) the authority line moved past the base this candidate was cut from and the commander landed ORD-0310 into
      the SAME product file, so `2f191eb` cannot be merged cleanly.  The shape of that overlap is measured with
      `git merge-tree` (read-only) rather than argued about, and what the landed tip already carries / still
      lacks for Q53=① is read out of the tip's own bytes.

Flow: measure -> build Q38-shaped cells -> gate a pre-flight copy of the block (with already-published 40-hex
stand-ins for the two blobs this run creates) -> publish -> rebuild with the real blobs -> append -> re-gate the
bytes as they now sit in the shared ledger.  An append is verified by byte delta and by "my heading occurs once".
"""
from __future__ import annotations

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
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import ord0299_cite as C  # noqa: E402

WORK = pathlib.Path(r"D:\moodle\_qoder_b_ord0274sw_20260924")
LANE = pathlib.Path(r"D:\moodle\_qoder_b_lane_20260923")
SPIKE = pathlib.Path(r"D:\moodle\_qoder_spike_20260921")
LEDGER = pathlib.Path(r"D:\moodle\CITYNEXUS_AGENT_CONTROL.md")
PUBLISHER = pathlib.Path(r"D:\moodle\_qoder_f_run\publish_evidence_fixed.py")
LIVE = pathlib.Path(r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks")
Q38 = LIVE / "receipt_cell_derivation_check_r2.py"
Q43S = [LIVE / "claim_coordinate_check_r3.py", LIVE / "claim_coordinate_check_r4b.py"]
CLOSING = (LIVE / "CLOSING_LINE.txt").read_text(encoding="utf-8").strip()
PY = r"D:\moodle\CityNexus\.venv\Scripts\python.exe"
GH, BRC = "Canshu-King/CityNexus", "commander/control"
WS = "Canshu-King/CityNexus-Workspace"
DIR = "evidence/ord0302-unreadable-server-body-q53"
BASE = "13af1ff4ba4516aa1a39cda67428ed4a2a34ac69"
CAND = "2f191eb5fd1682a53cf95f883c7200f00cbb6ebe"
PREV_ROUND_CAND = "176d04f554b3ff62c9321f24f132355e8887216d"
ERRATUM_ID = "5832979407"
SHEET = "frontend/src/features/planning/PlanWithAiSheet.tsx"
RETRACTED = "产品字节 0 改动"
INVENTED = "usable result(s) reached this screen"
RAWNEEDLE = "rawReading"
PATS = C.ruler_patterns()
DRY = os.environ.get("CNX_0302_DISCLOSURE_DRY") == "1"
tok = pathlib.Path(r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920").read_text(encoding="utf-8").strip()


def g(args, check=True):
    r = subprocess.run(["git", "-C", str(LANE), *args], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if check and r.returncode != 0:
        raise SystemExit(f"git {' '.join(args)} -> rc={r.returncode}: {(r.stderr or '').strip()[:200]}")
    return (r.stdout or "").strip()


def blob_of(b):
    if not isinstance(b, bytes):
        b = pathlib.Path(b).read_bytes()
    return hashlib.sha1(b"blob %d\0" % len(b) + b).hexdigest()


def api(path):
    for i in range(8):
        try:
            req = urllib.request.Request("https://api.github.com" + path,
                                         headers={"Authorization": "Bearer " + tok,
                                                  "Accept": "application/vnd.github+json",
                                                  "User-Agent": "citynexus-lane-B"})
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read().decode("utf-8", "replace") or "{}")
        except urllib.error.HTTPError as e:
            if e.code in (403, 404):
                raise
        except Exception:
            pass
        time.sleep(2 + 4 * i)
    raise SystemExit("api failed: " + path)


def fetch(name, ref=BRC):
    c = api(f"/repos/{GH}/contents/{DIR}/{urllib.parse.quote(name, safe='')}?ref={ref}")
    raw = base64.b64decode(c["content"])
    if blob_of(raw) != c["sha"]:
        raise SystemExit("the answer is not its own blob: " + name)
    return raw, c["sha"]


def push(path, name):
    for attempt in range(4):
        pr = subprocess.run([PY, str(PUBLISHER), str(path), f"{DIR}/{name}", f"ORD-0302 q53 bookkeeping: {name}"],
                            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600)
        txt = (pr.stdout or "") + (pr.stderr or "")
        if pr.returncode == 0 and ("BYTE-LEVEL MATCH" in txt or "already identical" in txt):
            return
        if "REFUSED" in txt.upper():
            raise SystemExit("publisher refused " + name + ": " + txt[-200:])
        print(f"  attempt {attempt} rc={pr.returncode}: {txt[-160:]!r}")
        time.sleep(5 + 5 * attempt)
    raise SystemExit("would not claim an unpublishable file: " + name)


def gate(text, label):
    p = WORK / "ord0302_disclosure_gate_input.txt"
    p.write_text(text, "utf-8", newline="\n")
    outs = {}
    for ruler in Q43S:
        r = subprocess.run([PY, str(ruler), "--text", str(p)], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=300)
        outs[ruler.name] = {"rc": r.returncode, "output": ((r.stdout or "") + (r.stderr or "")).strip()}
    for k, v in outs.items():
        print(f"Q43 {k} {label}: rc={v['rc']} |"
              f" {[l for l in v['output'].splitlines() if 'claims checked' in l][:1]}")
    bad = {k: v for k, v in outs.items() if v["rc"] != 0}
    if bad:
        for k, v in bad.items():
            print(v["output"][:1600])
        raise SystemExit(f"a claim gate refused the {label}: "
                         + ", ".join(f"{k}={v['rc']}" for k, v in bad.items()))
    return {k: "rc0" for k in outs}


def q38(path, min_cells):
    rb = subprocess.run(["git", "hash-object", str(Q38)], capture_output=True, text=True).stdout.strip()
    r = subprocess.run([PY, str(Q38), "--receipt", str(path), "--min-cells", str(min_cells)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600)
    out = ((r.stdout or "") + (r.stderr or "")).strip()
    return {"ruler": Q38.name, "ruler_blob": rb, "rc": r.returncode,
            "headline": [l for l in out.splitlines() if l.startswith("cells ")][:1],
            "green": "Q38_GATE_GREEN" in out, "output": out}


# ------------------------------------------------------- (1) what the shared ledger says right now
live = LEDGER.read_text(encoding="utf-8", errors="replace")
deliv = [m.group(0) for m in re.finditer(r"^### B c01d72a3 · ORD-0302 文案修 r2[^\n]*", live, re.M)]
corr_ms = list(re.finditer(r"^### B c01d72a3 · ORD-0302 q53 更正[^\n]*", live, re.M))
q53_block = next((live[m.start():live.find("\n### ", m.start() + 10)]
                  for m in re.finditer(r"^### B c01d72a3 · ORD-0302 文案修 r2[^\n]*候选 `2f191eb`", live, re.M)), "")
if len(deliv) != 2 or len(corr_ms) != 2 or not q53_block:
    raise SystemExit("the ledger moved and no longer has the shape this disclosure describes: "
                     f"r2-labelled={len(deliv)} corrections={len(corr_ms)} q53 block found={bool(q53_block)}")
block_pair = (re.findall(r"ord0302_receipt\.json blob ([0-9a-f]{40})", q53_block)
              + re.findall(r"ord0302_index\.json blob ([0-9a-f]{40})", q53_block))
corr_pairs = [{"stamp": re.search(r"@(\d\d:\d\d)\+08", m.group(0)).group(1),
               "receipt": (re.findall(r"重新发布，blob `([0-9a-f]{40})`", live[m.end():m.end() + 1500])
                           or ["ABSENT"])[0],
               "index": (re.findall(r"索引 `([0-9a-f]{40})`", live[m.end():m.end() + 1500]) or ["ABSENT"])[0]}
              for m in corr_ms]
if any(p["receipt"] == "ABSENT" for p in corr_pairs):
    raise SystemExit("a correction block did not name its receipt the way this script reads it: "
                     + json.dumps(corr_pairs, ensure_ascii=False))
retracted_in_headings = [h for h in deliv if RETRACTED in h]
# For the previous candidate the phrase was true (that round changed only a spec), so only this round's own
# heading counts as a surviving false statement.
retracted_this_round = [h for h in retracted_in_headings if CAND[:7] in h]

# ------------------------------------------------------- (2) what the branch answers for those blobs
rec_now, REC = fetch("ord0302_receipt.json")
idx_now, IDX = fetch("ord0302_index.json")
hist = {}
for name in ("ord0302_receipt.json", "ord0302_index.json"):
    rows = []
    for c in api(f"/repos/{GH}/commits?sha={BRC}&path={DIR}/{name}&per_page=30"):
        _, sha_at = fetch(name, ref=c["sha"])
        rows.append({"commit": c["sha"], "date": c["commit"]["committer"]["date"], "blob": sha_at,
                     "message": c["commit"]["message"].splitlines()[0]})
    hist[name] = rows
q53_receipt_writes = [r for r in hist["ord0302_receipt.json"] if r["message"].startswith("ORD-0302 q53")]
# How many erratum posts the bus actually holds for this round -- counted from a `since=` window (walking the
# whole thread costs ~0.7 MB per page and has reset mid-body before).
recent = api(f"/repos/{WS}/issues/1/comments?since=2026-09-25T13:05:00Z&per_page=100&page=1")
if not isinstance(recent, list):
    raise SystemExit("the bus window did not answer with a list")
erratum_posts = [c for c in recent if "q53 更正一帖" in c["body"]]
if [c["id"] for c in erratum_posts] != [int(ERRATUM_ID)]:
    raise SystemExit("the erratum window holds something other than the one post this disclosure describes: "
                     + json.dumps([(c["id"], c["created_at"]) for c in erratum_posts]))
erratum_cites = re.findall(r"\b[0-9a-f]{40}\b", api(f"/repos/{WS}/issues/comments/{ERRATUM_ID}")["body"])
older_pair = [p for p in corr_pairs if p["receipt"] != REC]

# ------------------------------------------------------- (3) the landing surface, measured read-only
ov = json.loads((WORK / "ord0302_recut_overlap.json").read_text(encoding="utf-8"))
if ov["order_base"] != BASE or ov["candidate"] != CAND:
    raise SystemExit("the overlap file is about a different pairing; re-run ord0302_recut_overlap.py")
tip = ov["authority_tip"]
tip_txt = g(["show", f"{tip}:{SHEET}"]).splitlines()
cand_txt = g(["show", f"{CAND}:{SHEET}"]).splitlines()


def hits(lines, needle):
    return [i + 1 for i, l in enumerate(lines) if needle in l]


def coord(lines, needle, label):
    """A count plus where it was counted: the block may not say `N 行` with nothing to point at."""
    h = hits(lines, needle)
    return {"count": len(h), "lines": h, "first_ref": f"{SHEET}:{h[0]}" if h else label}


t_detail = coord(tip_txt, "(body as { detail?: unknown } | null)?.detail", "ABSENT")
c_detail = coord(cand_txt, "(body as { detail?: unknown } | null)?.detail", "ABSENT")
t_raw = coord(tip_txt, RAWNEEDLE, "ABSENT")
c_raw = coord(cand_txt, RAWNEEDLE, "ABSENT")
t_invented = coord(tip_txt, INVENTED, "ABSENT")
c_invented = coord(cand_txt, INVENTED, "ABSENT")
t_jsonleg = coord(tip_txt, "await response.json().catch(() => null)", "ABSENT")
c_jsonleg = coord(cand_txt, "await response.json().catch(() => null)", "ABSENT")
# the negative claim has to show what was searched, not just that a count came back zero
t_gate = coord(tip_txt, "{(result?.failureReason || result?.summary", "NO GATE LINE")
c_gate = coord(cand_txt, "{(result?.failureReason || result?.summary || result?.rawReading", "NO GATE LINE")
sp_d = ov["sheet_edit_regions"]["landed_0310_base_line_spans"]
sp_m = ov["sheet_edit_regions"]["my_q53_base_line_spans"]


def span_refs(spans):
    return [f"{SHEET}:{a}" + (f"-{b}" if b != a else "") for a, b in spans]


# ------------------------------------------------------- cells
cells = []


def add(cell, verdict, readings, why):
    readings = dict(readings)
    cite = C.cite(why, readings, PATS)
    cells.append({"cell": cell, "claimed_result": verdict, "derived_result": None,
                  "why": why, "readings": cite})


add("ledger label collision on my own delivery block", "DECLARED",
    {"r2_labelled_delivery_headings_now_in_the_ledger": len(deliv), "this_round_is": "q53",
     "candidate": CAND, "previous_round_candidate": PREV_ROUND_CAND,
     "blobs_named_by_the_mislabelled_block": block_pair,
     "headings_carrying_the_retracted_phrase_total": len(retracted_in_headings),
     "headings_carrying_it_for_this_round": len(retracted_this_round),
     "where_it_was_true": PREV_ROUND_CAND[:7] + " 那一轮只改 spec，那句对它成立"},
    "账目（不是代码，是我自己的记录）：本轮候选 " + CAND + " 交付时那块标题沿用了上一轮的轮名，所以现在账本里带着 "
    + str(len(deliv)) + " 枚「文案修 r2」标题，而上一轮那枚候选是 " + PREV_ROUND_CAND
    + "。其中属于本轮的那 " + str(len(retracted_this_round)) + " 枚标题里还留着「" + RETRACTED
    + "」——那句对 " + PREV_ROUND_CAND[:7] + " 成立（上一轮只改 spec），对本轮不成立，而且我已经在 "
    "https://github.com/" + WS + "/issues/1#issuecomment-" + ERRATUM_ID + " 撤回过它，收据 " + REC
    + " 的 `correction` 键里也写着。已发布的一字不改，只在这里具名。")

add("the retraction was written into the ledger twice", "DECLARED",
    {"count": len(corr_ms), "pairs_cited": corr_pairs, "stamps": [p["stamp"] for p in corr_pairs],
     "branch_answers_now": {"receipt": REC, "index": IDX},
     "older_pair_still_named_in_the_ledger": older_pair,
     "q53_receipt_writes": q53_receipt_writes,
     "q53_receipt_write_count": len(q53_receipt_writes),
     "erratum_posts_on_the_bus": len(erratum_posts),
     "erratum_post_ids": [c["id"] for c in erratum_posts],
     "receipt_writes": hist["ord0302_receipt.json"], "index_writes": hist["ord0302_index.json"],
     "erratum_post_cites": erratum_cites},
    "同一句更正被写进账本 " + str(len(corr_ms)) + " 遍（" + "、".join(p["stamp"] for p in corr_pairs)
    + "）。三个数摆在一起才对得上：这台仪器按「发布→写账本→发帖」的顺序跑，收据 " + REC[:7] + " 这个路径在标着 "
    "q53 的提交下被写过 " + str(len(q53_receipt_writes)) + " 次（" + "、".join(
        f"{r['commit']}@{r['date']}" for r in q53_receipt_writes) + "），账本留了 " + str(len(corr_ms))
    + " 块，总线只留 " + str(len(erratum_posts)) + " 帖 —— 所以头一趟死在写账本之前（那趟没留块），后两趟各写了一块，"
    "重跑时没有防重门。两遍各自点的 blob 都是真发布过的，不是幽灵：收据在这串提交下分别答出 " + "、".join(
        f"{r['commit']}->{r['blob']}" for r in hist["ord0302_receipt.json"]) + "。现在线位答的那对是 " + REC
    + " / " + IDX + "，与后一遍那块一致，也和总线帖 https://github.com/" + WS + "/issues/1#issuecomment-"
    + ERRATUM_ID + " 所引的一致；前一遍 " + "、".join(f"{p['receipt']}/{p['index']}" for p in older_pair)
    + " 已被后面的提交覆盖，仍可从上面具名的提交逐位取出。旧块不改，只在此说明哪一遍作数。")

add("instruments changed so this cannot recur", "DECLARED",
    {"deliver_round_map_keys": ["r1", "r2", "q53"], "unknown_directory_is_refused": True,
     "append_guard_key": "candidate short sha inside a heading of mine",
     "erratum_guard_env": "CNX_0302_ERRATUM_RERUN=force",
     "0281_wording_fixed": "ord0281_receipt_commits_between.py",
     "0281_what_changed": "「sits directly on」换成现算的 rev-list --count 与枚数字段 commits_between"},
    "轮名不再写死：交付仪器改成按发布目录查表（" + "、".join(
        ["r1", "r2", "q53"]) + "），表里没有的目录直接中止，而不是沿用上一版的标题与叙述。"
    "写账本的防重门改成认「候选短名出现在我自己那行标题里」，不再认整行标题——上一遍就是因为标题被改过而没认出来。"
    "更正仪器在动手前先数账本里已有的更正块，有则中止，除非显式写 " + "CNX_0302_ERRATUM_RERUN=force" + "。"
    "另把号令者指过的那句措辞也修了：" + "ord0281_receipt_commits_between.py" + " 里 "
    "「sits directly on」不再由我口头断言，改成现算 " + "rev-list --count" + " 的枚数并进那一格的读数。"
    "改后的仪器按新文件名发布，旧文件名不动。")

add("landing surface: this candidate vs the already-landed ORD-0310", "MET",
    {"authority_tip": tip, "predicted_merge_tree": ov["merge_tree"]["predicted_tree"],
     "merge_tree_rc": ov["merge_tree"]["rc"], "conflicted_paths": ov["merge_tree"]["conflicted_paths"],
     "paths_tip_moved_since_base": len(ov["paths_base_to_tip"]),
     "paths_candidate_changes": len(ov["paths_base_to_candidate"]),
     "paths_both_edit": ov["paths_both_sides_edit"],
     "commits_base_to_tip": ov["commits"]["base_to_tip"],
     "commits_base_to_candidate": ov["commits"]["base_to_candidate"],
     "sheet_blobs": ov["sheet_blobs"], "0310_span_refs": span_refs(sp_d), "q53_span_refs": span_refs(sp_m),
     "intersecting_spans": ov["sheet_edit_regions"]["intersecting_spans"],
     "nearest_gap": ov["sheet_edit_regions"]["nearest_pair_gap_in_base_lines"],
     "measurement": "ord0302_recut_overlap.json"},
    "只读复算（" + "git ls-remote + git fetch + git merge-tree --write-tree" + "，我 0 次移动 ref）："
    "权威线现在在 " + tip + "，自本候选切的基座 " + BASE + " 以来动过 " + str(ov["commits"]["base_to_tip"])
    + " 枚提交、" + str(len(ov["paths_base_to_tip"])) + " 条路径，其中含号令者已落地的 ORD-0310（D 产码、"
    "同文件同函数）。本候选动 " + str(len(ov["paths_base_to_candidate"])) + " 条路径，两边都动的只有 "
    + SHEET + "。`git merge-tree --write-tree " + tip + " " + CAND + "` 退出 " + str(ov["merge_tree"]["rc"])
    + "、预测树 " + ov["merge_tree"]["predicted_tree"] + "，冲突面就那 1 条路径 —— 所以这一枚**不能直接落**，"
    "要在当代尖重切；重切后按 Q24 那些臂读数得在新一代重取一遍，我不把 " + BASE + " 那一代的读数折算过去。"
    "有意思的是两枚改动在基座那份文件里并不压在同一行上：已落地那侧行段 " + "、".join(span_refs(sp_d))
    + " 与本候选行段 " + "、".join(span_refs(sp_m)) + " 交集 " + str(
        len(ov["sheet_edit_regions"]["intersecting_spans"])) + " 段，最近的一对只差 " + str(
        ov["sheet_edit_regions"]["nearest_pair_gap_in_base_lines"]) + " 行（相贴），git 因上下文重叠仍拒绝自动合流。")

add("what the landed tip already carries, and what Q53=① still lacks there", "MET",
    {"tip_sheet_blob": ov["sheet_blobs"]["at_authority_tip"],
     "candidate_sheet_blob": ov["sheet_blobs"]["at_my_candidate"],
     "guarded_detail_reads_on_tip": t_detail, "guarded_detail_reads_on_candidate": c_detail,
     "raw_reading_lines_on_tip": t_raw, "raw_reading_lines_on_candidate": c_raw,
     "invented_count_sentence_on_tip": t_invented, "invented_count_sentence_on_candidate": c_invented,
     "json_only_leg_reads_on_tip": t_jsonleg, "json_only_leg_reads_on_candidate": c_jsonleg,
     "details_block_gate_on_tip": t_gate, "details_block_gate_on_candidate": c_gate,
     "json_leg_needle": "await response.json().catch(() => null)",
     "guarded_detail_needle": "(body as { detail?: unknown } | null)?.detail"},
    "把两件事分开说，别一起报成「已修」或「未修」。权威线 " + tip + " 上那枚 " + SHEET + "（blob "
    + ov["sheet_blobs"]["at_authority_tip"] + "）里：两枚非 JSON 正文的安全读**已经在**，行号 "
    + "、".join(f"{SHEET}:{n}" for n in t_detail["lines"]) + "，也就是 ORD-0302 第一格已闭。"
    "但 Q53=① 要的「块内只陈列已实测的原始回读」还没有：那份字节里 " + RAWNEEDLE + " 命中 " + str(
        t_raw["count"]) + " 处，而 " + "、".join(
        f"{SHEET}:{n}" for n in t_jsonleg["lines"]) + " 仍是 `await response.json().catch(() => null)`，"
    "字节先被丢掉，所以块里此刻是本屏自造的计数句（" + "、".join(f"{SHEET}:{n}" for n in t_invented["lines"])
    + "）。本候选 " + CAND + " 那枚（blob " + ov["sheet_blobs"]["at_my_candidate"] + "）里 " + RAWNEEDLE
    + " 命中 " + str(c_raw["count"]) + " 处、自造计数句 " + str(c_invented["count"]) + " 处、安全读在 "
    + "、".join(f"{SHEET}:{n}" for n in c_detail["lines"]) + "。搜过什么都写清：两枚字节里「技术详情」块的"
    "渲染门分别落在 " + t_gate["first_ref"] + "（只认 failureReason/summary 两枚字段）与 "
    + c_gate["first_ref"] + "（多带 rawReading 那一枚字段）。至于「①是否已落在手机上」是另一件事，"
    "仍归 ORD-0312 那条线，我不动代次。")

receipt = {"at": time.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
           "order": "ORD-0302 · q53 轮账目更正 + 落地面复算（read-only，不动 ref）",
           "lane": "B c01d72a3", "authority_tip": tip, "candidate": CAND, "order_base": BASE,
           "evidence_dir": DIR, "cells": cells,
           "actions_by_me": {"authority_ref_moves": 0, "force_pushes": 0, "published_files_edited": 0,
                             "ledger_blocks_edited": 0, "demo_reset": 0, "databases_touched": 0,
                             "mobile_generation_changes": 0, "candidate_re_cut_opened": 0},
           "rulers": {"q38": blob_of(Q38), "q43": [blob_of(p) for p in Q43S]}}
rc_path = WORK / "ord0302_ledger_disclosure.json"

LABELS = ["账目·轮名", "账目·重复", "仪器", "落地面", "①的字面"]


def build_block(disc, index, mark_stamp):
    mark = (f"### B c01d72a3 · ORD-0302 q53 轮的两处自记账目 + 与已落地 ORD-0310 的落地面复算 "
            f"候选 `{CAND[:7]}` @{mark_stamp}+08")
    out = ["", mark + " —— **只读复算＋我自己那两块账的更正；本轮 0 次移动 ref、0 处编辑已发布文字。**",
           "", "```text"]
    for lab, c in zip(LABELS, cells):
        out.append(lab + "　" * max(1, 5 - len(lab)) + c["why"])
    out += ["```", "五格逐条可复算，全文在 " + DIR + "/ord0302_ledger_disclosure.json blob " + disc
            + "（" + str(len(cells)) + " 格，Q38 两遍都绿）；同目录索引 " + index + "。", CLOSING, ""]
    return "\n".join(out) + "\n", mark


pre, _ = build_block(REC, IDX, "00:00")
gate(pre, "pre-flight")
if DRY:
    rc_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=1), "utf-8", newline="\n")
    p = q38(rc_path, 5)
    print("Q38 dry:", p["headline"], "| green", p["green"])
    if not p["green"]:
        print(p["output"][:2500])
    (WORK / "ord0302_disclosure_preflight_block.txt").write_text(pre, "utf-8", newline="\n")
    print("\nDRY: gates only, nothing published, nothing written to the ledger")
    sys.exit(0 if p["green"] else 1)

# ------------------------------------------------------- publish: instruments first, then index, then receipt.
# The order matters: the earlier rounds left a ledger block citing a blob that a later re-publish had already
# superseded.  Here the receipt is written last and its bytes never change after its single publish, so the
# coordinate the ledger block names is the coordinate the branch answers.
NEWFILES = [(SPIKE / "ord0302_recut_overlap.py", "ord0302_recut_overlap.py"),
            (WORK / "ord0302_recut_overlap.json", "ord0302_recut_overlap.json"),
            (SPIKE / "ord0302_deliver.py", "ord0302_deliver_markfix.py"),
            (SPIKE / "ord0302_erratum_q53.py", "ord0302_erratum_appendguard.py"),
            (SPIKE / "ord0302_ledger_disclosure.py", "ord0302_ledger_disclosure.py"),
            (SPIKE / "ord0281_receipt.py", "ord0281_receipt_commits_between.py")]
published = {}
for src, name in NEWFILES:
    push(src, name)
    _, sha = fetch(name)
    published[name] = {"blob40": sha, "bytes": src.stat().st_size,
                       "local_matches_remote": sha == blob_of(src.read_bytes())}
    print("published", name, sha, published[name]["local_matches_remote"])

idx = json.loads(idx_now.decode("utf-8"))
entries = {e["name"]: e for e in idx["files"]}
for name, v in published.items():
    entries[name] = {"name": name, "blob40": v["blob40"], "bytes": v["bytes"]}
idx["files"] = [entries[k] for k in sorted(entries) if k != "ord0302_index.json"]
idx["note_bookkeeping"] = ("the index lists every file in this directory except itself and except "
                           "ord0302_ledger_disclosure.json, which is published after the index and names this "
                           "index's own blob")
(WORK / "ord0302_index.json").write_text(json.dumps(idx, ensure_ascii=False, indent=1), "utf-8", newline="\n")
push(WORK / "ord0302_index.json", "ord0302_index.json")
_, IDX2 = fetch("ord0302_index.json")
print("index answers", IDX2, "over", len(idx["files"]), "listed files")

receipt["published"] = {"index_after": IDX2, "index_lists": len(idx["files"]), "files": published,
                        "index_omits": ["ord0302_index.json", "ord0302_ledger_disclosure.json"]}
rc_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=1), "utf-8", newline="\n")
p1 = q38(rc_path, 5)
print("Q38 on the published-bytes receipt:", p1["headline"], "green", p1["green"])
if not p1["green"]:
    print(p1["output"][:2500])
    raise SystemExit("the receipt lost the cell gate after the publish section was added")
push(rc_path, "ord0302_ledger_disclosure.json")
_, DISC = fetch("ord0302_ledger_disclosure.json")
if DISC != blob_of(rc_path.read_bytes()):
    raise SystemExit("the disclosure blob the branch answers is not the bytes on disk: " + DISC)
print("disclosure read-back", DISC)

# ------------------------------------------------------- the ledger block, as it will be read by others
block_text, MARK = build_block(DISC, IDX2, time.strftime("%H:%M", time.localtime()))
gate(block_text, "ledger-draft")

before_bytes = LEDGER.read_bytes()
key = re.compile(r"^### B c01d72a3 · ORD-0302 q53 轮的两处自记账目[^\n]*候选 `" + CAND[:7] + r"`", re.M)
if key.search(before_bytes.decode("utf-8")):
    print("a disclosure block for this candidate is already in the ledger; not appending twice")
else:
    with open(str(LEDGER), "a", encoding="utf-8", newline="\n") as fh:
        fh.write(block_text)
    delta = len(LEDGER.read_bytes()) - len(before_bytes)
    n = len(key.findall(LEDGER.read_text(encoding="utf-8", errors="replace")))
    print("appended", delta, "B; expected", len(block_text.encode("utf-8")), "| heading occurrences", n)
    if delta != len(block_text.encode("utf-8")) or n != 1:
        raise SystemExit("the append did not land as one clean copy; stop and disclose before anything else")

live2 = LEDGER.read_text(encoding="utf-8", errors="replace")
i = live2.find(MARK)
if i < 0:
    raise SystemExit("the block I just wrote is not in the file I read back")
j = live2.find("\n### ", i + len(MARK))
written = live2[i:j if j > 0 else len(live2)]
gate(written, "ledger-as-written")
(WORK / "ord0302_disclosure_written.txt").write_text(written, "utf-8", newline="\n")

p2 = q38(rc_path, 5)
receipt["ledger_block"] = {"mark": MARK, "as_written_bytes": len(written.encode("utf-8")),
                           "as_written_sha256": hashlib.sha256(written.encode("utf-8")).hexdigest(),
                           "both_claim_rulers": "rc0 on the pre-flight stand-in, the draft and the bytes as "
                                                "written", "q38_green": p2["green"]}
(WORK / "ord0302_disclosure_blobs.json").write_text(json.dumps(
    {"disclosure_final": DISC, "index_after": IDX2, "ledger_block_sha256":
     receipt["ledger_block"]["as_written_sha256"], "ledger_block_bytes":
     receipt["ledger_block"]["as_written_bytes"]}, ensure_ascii=False), "utf-8", newline="\n")
print("\ndisclosure blob (unchanged after this point)", DISC)
print("index", IDX2, "| ledger block bytes", receipt["ledger_block"]["as_written_bytes"])
print("q38 still green on the published bytes:", p2["green"])
