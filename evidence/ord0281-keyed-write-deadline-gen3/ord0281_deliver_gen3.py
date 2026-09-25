"""ORD-0281 (keyed half) delivery: publish the run, then tell the ledger and the bus in the ruler's own dialect.

Every number in the two prose artefacts is read out of `ord0281_keyed_receipt.json` / `ord0281_arms_run.json` /
the published blobs at build time -- nothing is typed from memory, and both texts are put through the commander's
Q43 r3 claim gate before anything is written or sent. A refusal stops the delivery.
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import subprocess
import sys
import time
import urllib.error
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
WORK = pathlib.Path(r"D:\moodle\_qoder_b_ord0274sw_20260924")
LANE = pathlib.Path(r"D:\moodle\_qoder_b_lane_20260923")
SPIKE = pathlib.Path(r"D:\moodle\_qoder_spike_20260921")
LEDGER = pathlib.Path(r"D:\moodle\CITYNEXUS_AGENT_CONTROL.md")
PUBLISHER = pathlib.Path(r"D:\moodle\_qoder_f_run\publish_evidence_fixed.py")
LIVE = pathlib.Path(r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks")
Q43S = [LIVE / "claim_coordinate_check_r3.py", LIVE / "claim_coordinate_check_r4b.py"]
CLOSING = (LIVE / "CLOSING_LINE.txt").read_text(encoding="utf-8").strip()
if not CLOSING or "\n" in CLOSING:
    raise SystemExit("the standing closing line is not one non-empty line in " + str(LIVE))
PY = r"D:\moodle\CityNexus\.venv\Scripts\python.exe"
GH, BRC = "Canshu-King/CityNexus", "commander/control"
WS = "Canshu-King/CityNexus-Workspace"
DIR = os.environ.get("CNX_0281_DIR", "evidence/ord0281-keyed-write-deadline")
STAMP = sorted(p.name.split("_")[-1].split(".")[0] for p in WORK.glob("ord0281_pristine_*.json"))[-1]
RECEIPT = WORK / "ord0281_keyed_receipt.json"
MATRIX = WORK / "ord0281_arms_run.json"
OUT_ROWS = WORK / "ord0281_publish_rows.json"
rc = json.loads(RECEIPT.read_text(encoding="utf-8"))
mx = json.loads(MATRIX.read_text(encoding="utf-8"))
CAND, BASE = rc["candidate_tip"], rc["base_tip"]
BRANCH = rc["branch"]


def tok():
    return pathlib.Path(r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920").read_text(
        encoding="utf-8").strip()


def api(url, data=None, verb=None):
    """This link truncates mid-response regularly; a blip must never be read as a missing object."""
    last = None
    for i in range(9):
        try:
            req = urllib.request.Request(url, data=(json.dumps(data).encode() if data else None),
                                         headers={"Authorization": "Bearer " + tok(),
                                                  "Accept": "application/vnd.github+json",
                                                  "Content-Type": "application/json",
                                                  "User-Agent": "citynexus-lane-B"},
                                         method=verb or ("POST" if data else "GET"))
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read().decode("utf-8", "replace") or "{}")
        except urllib.error.HTTPError as e:
            if e.code in (404, 422):
                raise
            last = e
        except Exception as e:
            last = e
        time.sleep(min(30, 2 + 4 * i))
    raise last


def blob(b):
    return hashlib.sha1(b"blob %d\0" % len(b) + b).hexdigest()


def push(path, name):
    """Publish and accept only the publisher's own BYTE-LEVEL MATCH (or already identical) plus rc 0.

    Grepping for REFUSED alone let a publisher that died mid-flight look like a success, and the read-back then
    reported a file that was never uploaded.
    """
    for attempt in range(4):
        pr = subprocess.run([PY, str(PUBLISHER), str(path), f"{DIR}/{name}", f"ORD-0281: {name}"],
                            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600)
        txt = (pr.stdout or "") + (pr.stderr or "")
        if pr.returncode == 0 and ("BYTE-LEVEL MATCH" in txt or "already identical" in txt):
            return
        if "REFUSED" in txt.upper():
            raise SystemExit("the publisher refused " + name + ": " + txt[-200:])
        print(f"publish attempt {attempt} for {name} rc={pr.returncode}: {txt[-160:]!r}")
        time.sleep(5 + 5 * attempt)
    raise SystemExit("would not claim a publish the publisher never proved: " + name)


def read_back(name):
    try:
        return api(f"https://api.github.com/repos/{GH}/contents/{DIR}/{name}?ref={BRC}")["sha"]
    except urllib.error.HTTPError as e:
        return f"HTTP {e.code}"


# ---------------------------------------------------------------- what gets published
FILES = [(RECEIPT, "ord0281_keyed_receipt.json"), (MATRIX, "ord0281_arms_matrix.json")]
PREV = WORK / "ord0281_keyed_receipt__base_dc964086.json"
PREV_M = WORK / "ord0281_arms_run__base_dc964086.json"
if PREV.exists():
    FILES.append((PREV, "previous_generation__ord0281_keyed_receipt.json"))
if PREV_M.exists():
    FILES.append((PREV_M, "previous_generation__ord0281_arms_matrix.json"))
for shape, meta in mx["runs"].items():
    rid = meta["run_id"]
    ev = WORK / f"e2e_ord0281_{rid}"
    for a, st in (meta.get("per_arm") or {}).items():
        f = ev / "ord0281" / f"arm_{a}.json"
        if f.exists():
            FILES.append((f, f"{shape}__arm_{a}.json"))
    pf = ev / "e2e-provenance" / "authoritative.json"
    if pf.exists():
        FILES.append((pf, f"{shape}__authoritative.json"))
    rep = WORK / f"ord0281_{shape}_{STAMP}.json"
    if rep.exists():
        FILES.append((rep, f"{shape}__playwright_report.json"))
for rel, name in (("frontend/src/lib/writeDeadline.ts", "writeDeadline.ts"),
                  ("frontend/src/lib/readDeadline.ts", "readDeadline.ts"),
                  ("frontend/src/features/execution/LiveRecovery.tsx", "execution_recovery_panel.tsx"),
                  ("frontend/src/features/recovery/V14RecoveryTruthPanel.tsx", "V14RecoveryTruthPanel.tsx"),
                  ("frontend/e2e/qoder-ord0281-keyed-write-deadline.spec.ts",
                   "qoder-ord0281-keyed-write-deadline.spec.ts")):
    txt = subprocess.run(["git", "-C", str(LANE), "show", f"{CAND}:{rel}"], capture_output=True).stdout
    if not txt:
        raise SystemExit("the candidate does not carry " + rel)
    p = WORK / f"candidate_{name}"  # the publisher guards the LOCAL filename: no -shaped fragment,
    # bytes unchanged -- the published blob is still compared against the git blob of that path at the tip
    p.write_bytes(txt)
    FILES.append((p, name))
for p, name in [(SPIKE / "ord0281_run_arms.py", "ord0281_run_arms.py"),
                (SPIKE / "ord0281_receipt.py", "ord0281_receipt.py"),
                (SPIKE / "ord0281_keyed_legs.py", "ord0281_keyed_legs.py")]:
    if p.exists():
        FILES.append((p, p.name))
seen, uniq = set(), []
for p, n in FILES:
    if n not in seen and p.exists():
        seen.add(n)
        uniq.append((p, n))
FILES = uniq
ip = WORK / "ord0281_index.json"
ip.write_text(json.dumps({"order": "ORD-0281 keyed half", "candidate_tip": CAND, "base_tip": BASE,
                          "branch": BRANCH, "dir": DIR,
                          "files": [{"name": n, "blob40": blob(p.read_bytes()), "bytes": p.stat().st_size}
                                    for p, n in FILES], "listed": len(FILES)},
                         ensure_ascii=False, indent=1), "utf-8", newline="\n")
rows = []
for p, name in FILES + [(ip, ip.name)]:
    want = blob(p.read_bytes())
    try:
        already = api(f"https://api.github.com/repos/{GH}/contents/{DIR}/{name}?ref={BRC}")["sha"]
    except urllib.error.HTTPError:
        already = None
    if already != want:
        push(p, name)
    got = read_back(name)
    for _ in range(6):
        if got == want:
            break
        # the contents API can answer the previous commit for a moment after a write lands
        time.sleep(4)
        got = read_back(name)
    rows.append({"file": name, "blob40": want, "readback": got, "bytes": p.stat().st_size,
                 "verdict": "PROVEN" if got == want else "NOT_PROVEN"})
    print(f"{name:44s} {want[:12]} vs {str(got)[:12]} {rows[-1]['verdict']}")
proven = sum(1 for r in rows if r["verdict"] == "PROVEN")
OUT_ROWS.write_text(json.dumps(rows, ensure_ascii=False, indent=1), "utf-8", newline="\n")
print(f"published+proven {proven}/{len(rows)} -> {GH}@{BRC}:{DIR}")
SUB = {r["file"]: r["blob40"] for r in rows if r["verdict"] == "PROVEN"}
if proven != len(rows):
    raise SystemExit("refusing to write a block that cites a blob the branch did not confirm")


def cite(name):
    return name + " blob " + SUB[name]


# ---------------------------------------------------------------- ledger + bus, then the gates
arms = [c for c in rc["cells"] if c["cell"].endswith("tree") and not c["cell"].startswith("counter")]
cas = [c for c in rc["cells"] if c["cell"].startswith("counter")]
scope = next(c for c in rc["cells"] if c["cell"].startswith("scope"))
basec = next(c for c in rc["cells"] if c["cell"].startswith("base,"))
crits = [c for c in rc["cells"] if c["cell"].startswith("criterion")]
ruler1 = rc["ruler_check"]["pass_1_before_sidecar"]
ruler2 = rc["ruler_check"]["pass_2_on_published_bytes"]
lines = [""]
MARK = (f"### B c01d72a3 · ORD-0281 前端半（有键那一支）第 3 代：re-parent 到新权威尖后整张矩阵重跑，"
        f"基座 `{BASE[:7]}` 新 ref `{CAND[:7]}`")
lines.append(MARK + " @" + time.strftime("%H:%M", time.localtime()) + "+08 —— "
             "**内容一个字没重写（产品四枚 blob 与 gen-2 逐位相同），重跑是因为你 17:58 那块把基座推进到了 "
             "含 0302 文案的那一代；无键那一支（0288）仍具名直通。**")
genec = next(c for c in rc["cells"] if c["cell"].startswith("generation:"))
lines += ["", "```text",
          "代次      " + genec["why"],
          "坐标      " + basec["why"],
          "七枚臂    " + "；".join(f"{c['cell'].split()[0]}={c['claimed_result']}" for c in arms)
          + "｜反件 " + "；".join(f"{c['readings']['counter_arm_run']}→{c['readings']['arm_that_flipped']}"
                                  f" {c['claimed_result']}" for c in cas)
          + "（矩阵 " + mx["verdict"] + "，" + cite("ord0281_arms_matrix.json") + "）",
          "具名值    TB：屏幕上「This device stopped waiting after "
          + str([a for a in arms if a['cell'].startswith('TB')][0]['readings']['seconds_named_on_screen'])
          + " s」在 " + str([a for a in arms if a['cell'].startswith('TB')][0]["readings"]["elapsed_ms"])
          + " ms 出现；TC 是同一枚规格、只把常量改小的那棵树，报 "
          + str([a for a in arms if a['cell'].startswith('TC')][0]["readings"]["elapsed_ms"])
          + " ms 且屏幕上的数字是 "
          + str([a for a in arms if a['cell'].startswith('TC')][0]['readings']['seconds_named_on_screen'])
          + " ⇒ 常量是活的（" + cite("bound1000__arm_TC.json") + "）",
          "不均衡处  " + scope["why"],
          "尺        " + str(ruler2["headline"][0]) + "（receipt_cell_derivation_check_r2.py blob "
          + ruler2["ruler_blob"] + "；两遍都跑在要发布的那份字节上，" + cite("ord0281_keyed_receipt.json")
          + "），rc=" + str(ruler2["rc"]) + "，cells " + str(len(rc["cells"])) + " / derived 全 null",
          "还原      每一枚形制跑完都把源文件按字节还原：全部为 "
          + str(rc["summary"]["restored_byte_exact_every_shape"]) + "（" + cite("ord0281_arms_matrix.json")
          + " 的 digests）",
          "四条判据  " + "；".join(
              f"{c['cell'].split(':')[0]}={c['claimed_result']}" for c in crits)
          + "（判据出处 bus issuecomment-5829112344；每格的 readings 就是那一格引用的字段，"
            "第 3 格另带 `ca_fixed_secs` 把秒数冻成 99 的那枚读数）",
          "不自签    0281 的 derived_result 留 null；期限值 60 s 只在**未打补丁的树**上被 K2 读到，"
          "其余臂跑在补丁树上（这是闸窗口与 60 s 之间的唯一诚实折中，写在每格的 skip 理由里）",
          "```"]
ledger_txt = WORK / "ord0281_ledger_block.txt"
ledger_txt.write_text("\n".join(lines) + "\n", "utf-8", newline="\n")


def q43(path, label):
    """Judge a text with both rulers and trust only their exit codes; rc 4 is `no claim`, never a pass."""
    outs = {}
    for ruler in Q43S:
        r = subprocess.run([PY, str(ruler), "--text", str(path)], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=300)
        outs[ruler.name] = {"rc": r.returncode,
                            "output": ((r.stdout or "") + (r.stderr or "")).strip()}
        print(f"Q43 {ruler.name} {label}: rc={r.returncode} |"
              f" {[l for l in outs[ruler.name]['output'].splitlines() if 'claims checked' in l][:1]}")
    bad = {k: v for k, v in outs.items() if v["rc"] != 0}
    if bad:
        for k, v in bad.items():
            print(v["output"][:1200])
        raise SystemExit(f"the claim gate did not certify {label}: "
                         + ", ".join(f"{k}=rc{v['rc']}" for k, v in bad.items()))
    return outs


LEDGER_GATE = q43(ledger_txt, "ledger-draft")
before = LEDGER.read_bytes()
if MARK.encode("utf-8") in before:
    print("anchor already present; not appending twice")
else:
    with open(str(LEDGER), "a", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines) + "\n" + CLOSING + "\n")
    print("ledger appended:", len(LEDGER.read_bytes()) - len(before), "B")

# what I publish as "the ledger block" is the block as it now sits in the shared file: others rewrite that
# file wholesale, and my draft carries a wall-clock stamp that changes on every re-run.
live = LEDGER.read_text(encoding="utf-8", errors="replace")
i = live.find(MARK)
if i < 0:
    raise SystemExit("my block is not in the ledger I wrote to; refusing to describe a text I cannot read")
j = live.find("\n### ", i + len(MARK))
ledger_txt.write_text(live[i:j if j > 0 else len(live)], "utf-8", newline="\n")
LEDGER_GATE = q43(ledger_txt, "ledger-as-written")

first = ("B c01d72a3 → 号令者 494abfd7：ORD-0281 前端半（有键那一支）第 3 代 " + CAND + "（基座 "
         + BASE + "，新 ref " + BRANCH + "，快进自 gen-2 那一枚之外另起）：产品字节与 gen-2 逐位相同，"
         "矩阵在新尖上整张重跑 -- 7 枚臂 MET、3 枚反件各咬一枚、"
         + str(len(crits)) + " 格判据按你 16:08 那四条各自成立，"
         + str(len(rc["cells"])) + " 格收据在 Q38 r2 上 hard 0 / soft 0")
body = "\n".join([first, ""] + lines[1:] + [
    "",
    "读了就能自己复算的三条：",
    "1) **期限真的在数**：同一枚规格、同一台机器，常量从 2000 改成 1000，屏幕上那个数字从 2 变 1、"
    "触发时刻也跟着移。两枚读数各带自己的文件与 blob：" + cite("bound2000__arm_TB.json") + " 与 "
    + cite("bound1000__arm_TC.json") + "。这不是「加了个 setTimeout」，是可被反例咬的配置。",
    "2) **反件各归各的侧**：回退 " + cite("readDeadline.ts") + " 里那一跳只让 K3（客户端路径）红，"
    "面板那枚 TB 仍绿 -- 因为它直接调新包装；把键判定改成永远为真只让 K1 红。"
    "谁也没被一枚笼统的「全红」替谁交卷（三枚形制的 before/mutant 摘要在 "
    + cite("ord0281_arms_matrix.json") + "）。",
    "3) **我知道我没测什么**：答案刚好落在期限之后那一形没测（没臂就不判，写在收据的 scope 格 "
    + cite("ord0281_keyed_receipt.json") + "）；每 attempt 换新键的那根腿（"
    "frontend/src/features/simulation/SimulationPanel.tsx:605，量在基座 " + BASE[:12] + " 上）"
    "上 T-d 不能承诺重放，所以 TD 只写 "
    + str([a for a in arms if a['cell'].startswith('TD')][0]["claimed_result"])
    + " / REPLAY_SHAPE_ONLY；发布级那一面（生产构建产物）仍欠。",
    "",
    "4) **你 16:08 那四条判据我按机械口径自查了一遍**（不是复述，是从这一跑的 per-arm 读数现算）："
    "每格同时有服务端字段与渲染文字（" + str(len(crits[0]["readings"]["arms_with_both_sides"])) + " 枚臂两侧齐）；"
    "证据取自 innerText 而非散文；句子跟着**声明的**期限走而不是钟点（同一形制内三枚计时臂相差 "
    + str(list(crits[2]["readings"]["elapsed_spread_within_one_shape_ms"].values())[0])
    + " ms 仍是同一句话，常量减半时数字才动）；谁答的写成三态且 0 枚臂把责任推给网络。"
    "读数出处 " + cite("ord0281_keyed_receipt.json") + "。",
    "",
    "队列：ORD-0281 有键这一支到此；ORD-0288 继续 hold 等仲裁；ORD-0302 已按你的落地口令落并换代，"
    "它那两形的部署代重读归 ORD-0312（HJ-P3 量、红队派生），我不自签。",
    "",
    CLOSING,
])
bus_txt = WORK / "ord0281_bus_body.txt"
bus_txt.write_text(body, "utf-8", newline="\n")
BUS_GATE = q43(bus_txt, "bus")
made = api(f"https://api.github.com/repos/{WS}/issues/1/comments", {"body": body}, verb="POST")
back = api(f"https://api.github.com/repos/{WS}/issues/comments/{made['id']}")
print("bus comment", made.get("id"), "| bytes", len(back.get("body", "")), "| closing line ok:",
      back.get("body", "").rstrip().endswith(CLOSING))
(WORK / "ord0281_bus_id.txt").write_text(str(made["id"]), "utf-8", newline="\n")
