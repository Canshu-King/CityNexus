# -*- coding: utf-8 -*-
"""CMDR 02:45 line 10 ledger block - the reshaped single-source cell, with both bolts inside the writer.

Refuses to write to the inbox unless every verbatim 40-hex resolves with `git cat-file -t` and the published
coordinate ruler reads the text clean. Counts come out of the receipts named on their own lines.
"""
import io
import json
import os
import re
import subprocess
import sys
import time

WORK = r"D:\moodle\_qoder_lane_S4_0926\work\ord_anchors"
REPO = "D:/moodle/CityNexus"
LANE = "1d64acf5-3f5f-48e8-a7b4-9d7a37996edb"
GATE = r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks\claim_coordinate_check_r7.py"
CLOSING = r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks\CLOSING_LINE.txt"
INBOX = r"D:\moodle\_qoder_ledger_inbox"
ENV = dict(os.environ, HTTPS_PROXY="", HTTP_PROXY="", NO_PROXY="*")
REF = "refs/remotes/verify/blockview_cmdr0245"
ARM = "backend/tests/test_qoder_ord0296_write_deadline.py"
ART = "review/1d64acf5-g4-single-source-shape/g4_single_source_shape_r1.json"
D76 = "backend/tests/test_qoder_ord0476_checkins.py"


def load(n):
    return json.load(io.open(os.path.join(WORK, n), encoding="utf-8"))


def banner(s):
    return s.strip().strip("=").strip()


def git(*a):
    r = subprocess.run(["git", "-C", REPO] + list(a), capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env=ENV, timeout=900)
    return r.returncode, (r.stdout or "").strip()


def shelf(slug):
    for _ in range(3):
        git("fetch", "-q", "origin", "+refs/heads/commander/control:" + REF)
        rc, listing = git("ls-tree", "-r", REF, slug + "/")
        out = {}
        for line in listing.splitlines():
            parts = line.split(None, 3)
            if len(parts) == 4 and parts[1] == "blob":
                out[parts[3].rsplit("/", 1)[-1]] = parts[2]
        if out:
            return out
    raise SystemExit("ABORT: %s enumerates nothing on commander/control" % slug)


probe = load("g4_shape_probe_r1.json")
g3 = load("push_g4_floor_r3_receipt_r1.json")
shape = load("g4_single_source_shape_r1.json")
k2 = load("ord0476_gate_probe_r2.json")
d2 = load("push_ord0476_gate_receipt_r2.json")
old_pred = load("cmdr0245_landing_prediction_r1.json")
pred = load("cmdr0245_landing_prediction_r2.json")
rec = load("publish_cmdr0245_receipt_r1.json")
SH = shelf(rec["slug"])
states = {r["id"]: r for r in probe["runs"]}
kstates = {r["id"]: r for r in k2["runs"]}
CAND = {c["sha"][:12]: c for c in pred["candidates"]}
G4C, D76C = CAND[g3["candidate_commit"][:12]], CAND[d2["candidate_commit"][:12]]
P = shape["predicates_in_this_cell"]
LIVE = git("ls-remote", "--refs", "origin",
           "refs/heads/mirror/integration-frontend-apple-pass1")[1].split()[0]
own_paths = [ARM, ART, D76]
same_at_live = []
for p in own_paths:
    who = g3["candidate_commit"] if p != D76 else d2["candidate_commit"]
    on_pin = git("cat-file", "-e", "%s:%s" % (probe["tip"], p))[0] == 0
    on_live = git("cat-file", "-e", "%s:%s" % (LIVE, p))[0] == 0
    # `git rev-parse <rev>:<missing path>` answers with the commit, not an error - which is how a first
    # version of this check counted the brand-new artifact path as "drifted". Existence is asked first now.
    b_pin = git("rev-parse", "%s:%s" % (probe["tip"], p))[1] if on_pin else None
    b_live = git("rev-parse", "%s:%s" % (LIVE, p))[1] if on_live else None
    same_at_live.append({"path": p, "on_the_pin": on_pin, "on_the_live_tip": on_live,
                         "pin_blob": b_pin, "live_blob": b_live,
                         "identical_at_live": (not on_pin and not on_live) or (b_pin == b_live)})
n_same = sum(1 for r in same_at_live if r["identical_at_live"])
n_existing_same = sum(1 for r in same_at_live if r["on_the_pin"] and r["identical_at_live"])
# the same comparison done the naive way, kept so the miss in section four is a number and not a story
n_same_old_way = sum(1 for r in same_at_live
                     if git("rev-parse", "%s:%s" % (probe["tip"], r["path"]))[1]
                     == git("rev-parse", "%s:%s" % (LIVE, r["path"]))[1])
n_new_on_neither = sum(1 for r in same_at_live if not r["on_the_pin"] and not r["on_the_live_tip"])
io.open(os.path.join(WORK, "live_path_check_r1.json"), "w", encoding="utf-8").write(
    json.dumps({"pin": probe["tip"], "live": LIVE, "live_source": "git ls-remote --refs origin "
                "refs/heads/mirror/integration-frontend-apple-pass1", "paths": same_at_live,
                "identical_or_new_count": n_same}, ensure_ascii=False, indent=1))


def kf(pid):
    m = re.search(r":(\d+):", kstates[pid]["pytest"]["bitting_line"] or "")
    return m.group(1) if m else None


S = {
    "lane": LANE, "tip": probe["tip"],
    "live": git("ls-remote", "--refs", "origin",
                "refs/heads/mirror/integration-frontend-apple-pass1")[1].split()[0],
    "branch": g3["branch"], "g3": g3["candidate_commit"], "g3_commits": g3["commits_on_tip"],
    "pre_blob": probe["pre_arm_blob"], "new_blob": probe["reshaped_arm_blob"],
    "art": ART, "art_blob": SH["g4_single_source_shape_r1.json"],
    "q1_old": banner(states["Q1_same_name_other_path"]["arms"]["pre_395662e3"]["pytest"]["summary"]),
    "q1_new": banner(states["Q1_same_name_other_path"]["arms"]["reshaped"]["pytest"]["summary"]),
    "q1_new_line": re.search(r":(\d+):", states["Q1_same_name_other_path"]["arms"]["reshaped"]
                             ["pytest"]["bitting_line"] or "").group(1),
    "q0_old": banner(states["Q0_no_injection"]["arms"]["pre_395662e3"]["pytest"]["summary"]),
    "q0_new": banner(states["Q0_no_injection"]["arms"]["reshaped"]["pytest"]["summary"]),
    "q2": banner(kstates["K2_named_add"]["pytest"]["summary"]),
    "q3": banner(states["Q3_whitelist_rotted"]["arms"]["reshaped"]["pytest"]["summary"]),
    "q3_line": re.search(r":(\d+):", states["Q3_whitelist_rotted"]["arms"]["reshaped"]
                         ["pytest"]["bitting_line"] or "").group(1),
    "q4_old": banner(states["Q4_sub_floor_consumer_copy"]["arms"]["pre_395662e3"]["pytest"]["summary"]),
    "q4_new": banner(states["Q4_sub_floor_consumer_copy"]["arms"]["reshaped"]["pytest"]["summary"]),
    "q5_old": banner(states["Q5_worker_at_floor"]["arms"]["pre_395662e3"]["pytest"]["summary"]),
    "q5_new": banner(states["Q5_worker_at_floor"]["arms"]["reshaped"]["pytest"]["summary"]),
    "q6": banner(states["Q6_new_worker_below"]["arms"]["reshaped"]["pytest"]["summary"]),
    "q7": banner(states["Q7_family"]["arms"]["reshaped"]["pytest"]["summary"]),
    "wl": "、".join("`%s`" % m for m in shape["cell_brought_into_shape"]["whitelist_as_shipped"]),
    "n_states": probe["states"], "all_met": probe["all_met"],
    "k_all_met": k2["all_met"], "k_final": k2["final_test_blob"], "k_yaml": k2["yaml_tip_blob"],
    "yaml": k2["yaml_tip_blob"],
    "d76_branch": d2["branch"], "d76": d2["candidate_commit"],
    "d76_old_paths": len([c for c in old_pred["candidates"]
                          if c["sha"] == "cbcf668265d3229160cf390c024d418df126166f"][0]
                         ["paths_belonging_to_others_in_the_diff"]),
    "g3_foreign": len(G4C["paths_belonging_to_others_in_the_diff"]),
    "d76_foreign": len(D76C["paths_belonging_to_others_in_the_diff"]),
    "g3_conf": G4C["merge_tree"]["conflict_names"], "d76_conf": D76C["merge_tree"]["conflict_names"],
    "g3_root": G4C["chain_root"], "d76_root": D76C["chain_root"],
    "g3_ff": G4C["merge_tree"]["tree"], "d76_ff": D76C["merge_tree"]["tree"],
    "p_off": "%s:%s" % (ARM, P["offenders_still_the_same"]["line"]),
    "p_scale": "%s:%s" % (ARM, P["floor_is_read_live_not_written"]["line"]),
    "p_uns": "%s:%s" % (ARM, P["request_path_scale"]["line"]),
    "p_cons": "%s:%s" % (ARM, P["sub_floor_consumer_copy"]["line"]),
    "p_rot": "%s:%s" % (ARM, P["whitelist_cannot_rot"]["line"]),
    "p_wl": "%s:%s" % (ARM, shape["cell_brought_into_shape"]["whitelist_line"]["line"]),
    "b_probe": SH["g4_shape_probe_r1.json"], "b_shape": SH["g4_single_source_shape_r1.json"],
    "b_push": SH["push_g4_floor_r3_receipt_r1.json"], "b_k": SH["ord0476_gate_probe_r2.json"],
    "b_pred1": SH["cmdr0245_landing_prediction_r1.json"], "b_pred2": SH["cmdr0245_landing_prediction_r2.json"],
    "n": rec["shelf_count"], "slug": rec["slug"], "ctl": rec["control_tip_after"],
    "b_pub": SH["publish_cmdr0245_r1.py"],
    "live_same_at_live": n_same, "live_paths": len(own_paths),
    "n_existing_same": n_existing_same, "n_new_on_neither": n_new_on_neither,
    "n_same_old_way": n_same_old_way,
    "live_check": json.dumps([{k: r[k] for k in ("path", "live_blob", "identical_at_live")}
                              for r in same_at_live], ensure_ascii=False)[:60],
}

L = []
A = L.append
A("### CMDR 02:45 第 10 行按裁定收形了（车道 `%(lane)s`）：G4 的单一来源豁免不再按文件名放行，改成具名路径白名单"
  "（出厂一枚、扩容必须具名、白名单空转也算红）；在 day25 尖 `%(tip)s` 上把改前改后两代判据对着同一批注入各跑一遍，"
  "%(n_states)s 态全合期望；形制件随枝上线；裁①那一格也在同一代尖上重测并重切" % S)
A("")
A("**一、我认领的那一行（逐字）**：账本 `### CMDR 02:45 敲醒派单` 第 10 条写着 "
  "`1d64acf5`：G4 盲区尺（一千八百三十四裁定：包含式+具名扩容白名单仅限该单元格）按裁定收形，交形制件。"
  "我这轮的读数与候选都钉在 `%(tip)s`（04:18 换代那块点名的就是这一枚）。写这块时线又往前走了：现读 "
  "`%(live)s`。我名下 %(live_paths)s 枚路径在新尖上的对账：%(n_existing_same)s 枚（两枚测试文件）blob 与钉住那代逐字相同，"
  "%(n_new_on_neither)s 枚是这件全新形制件、两侧都还不存在（所以它不构成陈旧字节）。候选因此不带陈旧字节；"
  "要把链根再挪一次，点一句我就动。" % S)
A("")
A("**二、收形收在哪一格**：那一格的豁免原来是 `Path(rel).name == 「write_deadline.py」`，出现两次，"
  "**按文件名放行**——同名不同路的东西会从尺底下走过去。现在是具名路径白名单 %(wl)s，扩容只能把自己的路径写进这张表，"
  "而且表里每一枚必须自证（要么定义 accessor，要么真的内联写数）。这一格的其余半边一字未动："
  "`%(p_off)s`（第二处内联请求路径常量）、`%(p_scale)s`（量程从产品现读不写死）、`%(p_uns)s`（量程以上）、"
  "`%(p_cons)s`（18:34 那格量程以下）、新增的 `%(p_rot)s`（白名单空转）。白名单声明在 `%(p_wl)s`。" % S)
A("")
A("**三、双代对照（这轮的要点，不是单侧读数）**：同一枚注入 `backend/app/db/deep/write_deadline.py` 里写 "
  "`busy_timeout = 90000`，改前那代判据 %(q1_old)s（**洞是真的**），改后这代 %(q1_new)s，红在 `%(arm)s:%(q1_new_line)s`。"
  "对照前提取好了：无注入时两代各 %(q0_old)s / %(q0_new)s，所以这不是「一侧根本没跑」。其余各态："
  "白名单具名后同一枚注入 %(q2)s（扩容通道走得通）；具名而不自证 %(q3)s 红在 `%(arm)s:%(q3_line)s`；"
  "18:34 那格量程以下两代 %(q4_old)s / %(q4_new)s；量程以上两代 %(q5_old)s / %(q5_new)s；"
  "新增 800 毫秒 worker 两代都 %(q6)s；两枚尺整跑 %(q7)s。件 `g4_shape_probe_r1.json` blob `%(b_probe)s`，"
  "每个产品注入文件跑完都还原并与尖上 blob 逐字核过。" % dict(S, arm=ARM))
A("")
A("**四、我第一版把新判据写窄了，四格假红，具名报出来**：那条「自证」我起初只承认内联数字，"
  "而 `backend/app/db/write_deadline.py` 本体是从 settings 取数、自己不写数字——于是无注入的对照也红，"
  "连带具名扩容与整族三格一起红。改成「定义 accessor 或内联写数」二者之一即算自证之后 %(n_states)s 态全合期望。"
  "读数量没有因此改过一个字，改的是我那条新加的判据。"
  "同一只手还有第二处尺错，也在这块里改掉而不是留着：第一节那句「路径在新尖上是否还是同一枚 blob」我最初用 "
  "`git rev-parse <rev>:<路径>` 去问存在性，而那命令对不存在的路径回吐的是 commit 号、不是报错——于是我这件全新的"
  "形制件被算成「漂了」（旧切法 %(live_paths)s 枚里只认 %(n_same_old_way)s 枚）。改成先 `git cat-file -e` 问存在、"
  "再比 blob：%(n_existing_same)s 枚 blob 同值，%(n_new_on_neither)s 枚两侧都不存在，对账件 `live_path_check_r1.json`。" % S)
A("")
A("**五、形制件（订单要的就是这个）**：`%(art)s`，blob `%(art_blob)s`——机读，逐枚写着改前改后的形制、"
  "出厂白名单成员、五条判据各自的现行号、%(n_states)s 态的期望与实测、以及第三节那对双代读数。"
  "它是从读数件里生成再生成一次的，不是我另抄一份；复算命令写在件里的 `how_to_recheck`。" % S)
A("")
A("**六、裁①那一格在 day25 重测并重切**：六态在这一代尖上全合期望（件 `ord0476_gate_probe_r2.json` 的 "
  "`all_met` 字段 = %(k_all_met)s，blob `%(b_k)s`），产出的文件 blob 与我 01:53 那块引的逐字相同 `%(k_final)s`，"
  "`contracts/openapi.yaml` 仍与尖上 blob `%(yaml)s` 相同。之所以重切一枝：旧枝 `cbcf668265d3…` 对 day25 差分里"
  "带着 %(d76_old_paths)s 枚别人名下的路径——那是「切点太老」的形制而不是我改了别人的文件（"
  "`cmdr0245_landing_prediction_r1.json` blob `%(b_pred1)s` 逐枚记着）。新枝 `%(d76_branch)s` 枝头 `%(d76)s`，"
  "链根就是现尖、别人路径 %(d76_foreign)s 枚。" % S)
A("")
A("**七、两枚候选的落地形制（都还没进线）**：`%(branch)s` 枝头 `%(g3)s`（链根 `%(g3_root)s`、 %(g3_commits)s 笔、"
  "别人路径 %(g3_foreign)s 枚、只读预测树 `%(g3_ff)s` 冲突 %(g3_conf)s 行）；`%(d76_branch)s` 枝头 `%(d76)s`"
  "（链根 `%(d76_root)s`、别人路径 %(d76_foreign)s 枚、预测树 `%(d76_ff)s` 冲突 %(d76_conf)s 行）。"
  "两件在尖上的同一枚路径都还不是我这几枚 blob（`already_on_the_line` 逐枚为否），所以是要落不是已落。"
  "预测与逐枚对账件 `cmdr0245_landing_prediction_r2.json` blob `%(b_pred2)s`。按「修完自报，我落」，权威线我 0 次移动。" % S)
A("")
A("**边界**：0 产品字节（`backend/app/**` 与 `contracts/**` 每次注入后都按 blob 核回）、0 枚他人文件改动、"
  "权威线 0 移动、账本 0 直写、`demo/reset` 0 次、共享 `_preview.db` 0 次写、我这一道 0 个端口在跑。"
  "**未改善**：白名单出厂只有一枚成员，「具名扩容」这条通道仍然只有我自己走过一遍；`%(p_rot)s` 那条自证判据用的是"
  "「定义 accessor 或写内联数」二者之一，别的服务形态（比如从环境变量再包一层）不算自证，将来要落那种形态得先改这条。" % S)
A("")
A("坐标：证据 %(n)s 枚在 `commander/control` 的 `%(slug)s/`，逐枚本机字节与服务端 `ls-tree` 读回 blob 全等"
  "（回执控制尖 `%(ctl)s`）；推送回执 blob `%(b_push)s`；发布器 blob `%(b_pub)s`。写这块时权威枝现读 `%(live)s`。" % S)
A("")
closing = io.open(CLOSING, encoding="utf-8").read().strip()
A(closing)
out = "\n".join(L) + "\n"

tokens = sorted(set(re.findall(r"\b[0-9a-f]{40}\b", out)))
bad = [{"token": t, "cat_file": git("cat-file", "-t", t)[1] or "NOT_AN_OBJECT"} for t in tokens
       if git("cat-file", "-t", t)[1] not in ("commit", "tree", "blob")]
draft = os.path.join(WORK, "block_cmdr0245_r1.md")
io.open(draft, "w", encoding="utf-8", newline="\n").write(out)
if bad:
    io.open(os.path.join(WORK, "block_cmdr0245_selfcheck_r1.json"), "w", encoding="utf-8").write(
        json.dumps({"verdict": "ABORT_before_the_gate", "unresolvable": bad}, ensure_ascii=False, indent=1))
    print("ABORT: %d 40-hex token(s) do not resolve" % len(bad))
    for b in bad:
        print("   ", b["token"], b["cat_file"])
    raise SystemExit(8)

r = subprocess.run([sys.executable, GATE, "--text", draft, "--expect-clean"],
                   capture_output=True, text=True, encoding="utf-8", errors="replace",
                   env=ENV, timeout=900, cwd=os.path.dirname(GATE))
gate_ok = r.returncode == 0
stamp = time.strftime("%H%M")
target = os.path.join(INBOX, "1d64acf5_%s.md" % stamp)
io.open(os.path.join(WORK, "block_cmdr0245_selfcheck_r1.json"), "w", encoding="utf-8").write(
    json.dumps({"gate_rc": r.returncode, "gate_verdict": "GREEN" if gate_ok else "RED",
                "gate_tail": (r.stdout or "")[-900:], "tokens_checked": len(tokens),
                "block_bytes": len(out.encode("utf-8")), "delivered_to": target if gate_ok else None},
               ensure_ascii=False, indent=1))
if not gate_ok:
    print("GATE RED - the block stays a local draft, nothing written to the inbox")
    print((r.stdout or "")[-3000:])
    raise SystemExit(9)
io.open(target, "w", encoding="utf-8", newline="\n").write(out)
print(json.dumps({"delivered": target, "bytes": len(out.encode("utf-8")),
                  "tokens": len(tokens), "gate": "GREEN"}, ensure_ascii=False))
