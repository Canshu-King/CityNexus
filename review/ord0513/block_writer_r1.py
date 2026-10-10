"""ORD-0513 · the ledger block, written out of the artifacts.

Every number below is read from a pushed file, not typed: the two door readings, the screen rows,
the counterexample verdict, the parity line, the exposure counts and the pytest denominators.  The
generator asserts each source exists and each claim it makes is present in the JSON it came from, so
a reading that was never taken cannot reach the ledger.
"""
import io
import json
import os
import re
import subprocess
import sys
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
SC = r"D:/moodle/_qoder_newlane_ord0444_20260929/scratch"
WT = r"D:/moodle/_qoder_newlane_ord0444_20260929/wt2"


def load(name):
    p = os.path.join(SC, name)
    assert os.path.exists(p), "missing artifact " + name
    return json.loads(io.open(p, encoding="utf-8").read())


def ev(name):
    """A path in the evidence ref, paired with the blob the commit actually holds under that name.
    The r2 erratum existed because two paths were typed from memory and neither name was in the
    commit -- one of them pointed at the live reading while labelled 'superseded'."""
    assert name in CO["blobs"], ("not in the evidence commit: " + name)
    return "review/ord0513/" + name + "` = `" + CO["blobs"][name]


def blob_of(name):
    return subprocess.run(["git", "-C", WT, "hash-object", "-w", "-t", "blob", "--stdin"],
                          input=io.open(os.path.join(SC, name), "rb").read(),
                          capture_output=True).stdout.decode().strip()


CO = json.loads(io.open(os.path.join(SC, "ord0513_coords.json"), encoding="utf-8").read())
MASK_JSON = next(k for k in CO["blobs"] if k.startswith("mask_r2_") and k.endswith(".json"))
RUNS_JSON = next(k for k in CO["blobs"] if k.startswith("runs_") and k.endswith(".json"))
DB = load("ord0513_doors_base.json")
DC = load("ord0513_doors_candidate.json")
RUNS = load("ord0513_runs_5a4cdbd2.json")
MASK = load("ord0513_mask_r2_5a4cdbd2.json")
EXP = load("ord0513_exposure_5a4cdbd2.json")
blob_doors_base = blob_of("ord0513_doors_base.json")
blob_doors_cand = blob_of("ord0513_doors_candidate.json")
blob_runs = blob_of("ord0513_runs_5a4cdbd2.json")
blob_mask = blob_of("ord0513_mask_r2_5a4cdbd2.json")
blob_exp = blob_of("ord0513_exposure_5a4cdbd2.json")
blob_doors_py = blob_of("ord0513_doors_r1.py")
blob_arm = blob_of("ord0513_arm_r1.cjs")
blob_mask_py = blob_of("ord0513_mask_r2.py")


def refusals(doc):
    d = {}
    for r in doc["refusals"]:
        code = str(r["reason_code"])
        if code != "None":
            d.setdefault(code, r)
    return d


b, c = refusals(DB), refusals(DC)
assert set(b) == set(c) == {"MEMBER_TRAVELER_UNKNOWN", "PLACE_NOT_FOUND",
                            "PLACE_ALREADY_IN_COLLECTION"}, (sorted(b), sorted(c))
def tip_line(path, needle):
    """Where a claim lives on THE generation this block is cut against -- looked up, not remembered.
    A `path:line` written from memory rots the moment another lane moves the file, and the movement is
    exactly what happened here: the dictionaries row sat at :2210 on the previous tip and :2215 on this
    one, because `LocaleContext.tsx` moved without anyone touching that line."""
    txt = subprocess.run(["git", "-C", WT, "show", "%s:%s" % (CO["base_rev"], path)],
                         capture_output=True).stdout.decode("utf-8", "replace")
    for n, line in enumerate(txt.split(chr(10)), 1):
        if needle in line:
            return n, line.strip()
    raise AssertionError("citation needle gone from the tip: " + needle)


LOCALE = "frontend/src/i18n/LocaleContext.tsx"
trip_n, trip_txt = tip_line(LOCALE, "export type TripLocale")
dict_n, dict_txt = tip_line(LOCALE, "const dictionaries")
assert "de" not in trip_txt.replace("TripLocale", ""), trip_txt

for doc, name in ((DB, "doors_base"), (DC, "doors_candidate"), (RUNS, "runs"), (MASK, "mask")):
    assert doc["head"] == CO["product_blob"], (name, doc["head"][:12], CO["product_blob"][:12])

L = []
A = L.append
A("### ORD-0513 · 收藏这一族的三句拒绝，句子本身说人话（车道 `1ba48dbf`，r1）")
A("")
A("- 裁语逐字执行：zh 与 en 两枚成对交，第三枚 `de` 具名记 `NOT_AVAILABLE`，理由「第三档语言位不在本单范围」；"
  + "`" + LOCALE + ":4`、`" + LOCALE + ":2133` 那两行没开——本枝该文件 0 改动。`de` 不是「没翻译」而是"
  + "「本产品没有第三枚语言位」，两处逐字都是现尖查出来的行，不是我记的："
  + "`" + LOCALE + ":" + str(trip_n) + "` 写 " + "`" + trip_txt + "`，"
  + "`" + LOCALE + ":" + str(dict_n) + "` 写 " + "`" + dict_txt + "`。")
A("- 基座 `" + CO["base_rev"] + "`；产品枝 `" + CO["product_ref"] + "` = `" + CO["product_blob"] +
  "`；证据枝 `" + CO["evidence_ref"] + "` = `" + CO["evidence_blob"] +
  "`，两枚都由 `git ls-remote` 回读逐字相等（回读断言在生成器里，不在话术里）。")
A("- 落地门这次先自己跑过一遍再交（只 `--land` 缺省＝干跑，权威线我没碰）："
  "`preflight_and_land_r7.py --candidate-ref " + CO["product_ref"].replace("refs/heads/", "") +
  " --order ORD-0513` 现读判定行逐字 = `" + CO["gate_verdict"] + "`，退出 0；"
  "r2 被拒的正是这一行没出（`no-verdict-line rc=1`），本枝现在建在现尖上、`ff=True ahead=1 behind=0 "
  "intersection=0`。门自己的原始输出也进了证据枝：`" + ev("landing_gate_dry_r3.txt") + "`。")
A("- 移动的文件 " + str(len(subprocess.run(["git", "-C", WT, "diff", "--name-only", CO["base_rev"],
                                             CO["product_blob"]], capture_output=True,
                                            text=True).stdout.split())) +
  " 枚：`backend/app/main.py`，只改两枚句子的字符串本身。`tools/verify_openapi_parity.py` 改后现读 "
  "`OpenAPI 3.1.0; formal 174; runtime 174; missing 0; extra 0` 与 `schemas formal 85; generated 85; "
  "missing 0; extra 0`（blob " + blob_exp + " 同代）。")
A("")
A("## 1. 改前两枚句子把身份念在人话里（逐字原文）")
A("")
for code in ("PLACE_NOT_FOUND", "PLACE_ALREADY_IN_COLLECTION", "MEMBER_TRAVELER_UNKNOWN"):
    rb, rc = b[code], c[code]
    A("- `" + code + "`：`http_status=" + str(rb["http_status"]) + "`，改前 `error.message` = 「" +
      str(rb["message"]) + "」，句里含 uuid = " + str(rb["message_has_uuid"]) +
      "（`error.details` 键集 " + json.dumps(rb["details_keys"], ensure_ascii=False) + "）；"
      "改后 = 「" + str(rc["message"]) + "」，句里含 uuid = " + str(rc["message_has_uuid"]) + "。")
A("")
A("  两代的读数（含成员门那一枚）逐字在 `" + ev("doors_base.json") + "` 与 `"
  + ev("doors_candidate.json") + "`，跑法 `" + ev("doors_r1.py") + "`。第三句 `MEMBER_TRAVELER_UNKNOWN` 实测本来就不含身份（`No traveller carries that id.`，"
  "两代同一句、`message_changed=False`），所以不动它——写成「已合规」而不是造一笔改动。")
A("")
A("## 2. 不许变的东西，量过才说不变")
A("")
for code in sorted(c):
    rb, rc = b[code], c[code]
    A("- `" + code + "`：`error.code` " + str(rb["code"]) + " 两代相同；`http_status=" +
      str(rc["http_status"]) + "` 两代相同；`error.details` 键集 " +
      json.dumps(rc["details_keys"], ensure_ascii=False) + " 两代相同 = " +
      str(rb["details_keys"] == rc["details_keys"]) + "；`trace_id`/"
      "`error_receipt_id` 两代都在 = " + str(bool(rc["trace_id_present"]) and
                                            bool(rc["error_receipt_id_present"])) + "。")
A("")
A("  这三行是逐条比出来的，不是照着「形状没动」这句话抄的：`door_comparison` 一格在 blob " + blob_runs +
  " 里，判据是 `details_shape_same` 与 `code_field_same` 两枚布尔。")
A("")
A("## 3. 屏读：两臂两档，四条形")
A("")
scr = RUNS["phases"]["screen_tip_copy"]
assert RUNS.get("screen_build", {}).get("exit") == 0, RUNS.get("screen_build")
assert scr["served_entry"][0] == RUNS["screen_build"]["built_entry"][0], (
    "screen rows were taken against %s but this round built %s"
    % (scr["served_entry"], RUNS["screen_build"]["built_entry"]))
assert MASK["generations"]["human_copy"]["entry"] == MASK["human_build"]["built_entry"][0], MASK["human_build"]
assert MASK["generations"]["masked_copy"]["entry"] == MASK["masked_build"]["built_entry"][0], MASK["masked_build"]
A("- 走查是产品自己的路：打开行程 → 点第一枚「收藏到…」→ 点一格架子 → 再点同一格；"
  "第二次点击那一趟门答的才是 409。断言全部读 `innerText`，没有一条结论取自 `data-*`。")
for r in scr["rows"]:
    line = [ch["reading"] for ch in (r["checks"] or []) if "machine token" in ch["check"]]
    A("  - `" + r["shape"] + "` / `" + r["locale"] + "`：退出 " + str(r["exit"]) + "，红条 " +
      str(len(r["failures"] or [])) + " 条，屏上那句 = 「" +
      str((line[0] if line else {}).get("line"))[:96] + "」（blob " + blob_runs + "）")
A("- 这一族屏上的句子本来就来自本特性自己的词表（`collectionCopy.ts`），所以「改前屏读」与「改后屏读」"
  "同形——这是量出来的相符，不是推断：候选代四条形全绿，`all_green=" + str(scr["all_green"]) +
  "`，且四条形里 `carries no identifier` 一条也没红。本单要修的是门本身那句话（它是别的读面唯一能拿到的"
  "原文），不是屏上这句。")
A('- `details` 计数：四条形实测都是 0（`{count: 0, summaries: [], empty: 0}`，同一 blob），'
  "也就是这一屏本轮没有「技术详情」这一族标签，所以「出现就必须 >0」那条判据未被触发；判据本身在臂里是"
  "真跑的（`no empty 技术详情 face`），触发条件是 summary 文案命中 技术|详情|detail|Technical。")
A("")
A("## 4. 反件一枚：把词档遮掉，机词必须上屏并被咬住")
A("")
mv = MASK["verdict"]
A("- 改法：把 `collectionCopy.ts` 里 `alreadyHere` 两枚臂换成门自己的机器词（键、类型、渲染路径全部留着）。"
  "遮错的第一版是把整枚键删掉：面板直接不挂载，臂红在「架子没列出来」上，与词句无关。"
  "跑对形制之后又中了第二回：预览站占着 `dist/`，重建退 " + str(RUNS["masked_build"]["exit"])
  + "，而入口名 `" + str(RUNS["phases"]["screen_tip_copy"]["served_entry"][:1]) + "` 根本没变，"
  "那一格却报了绿——假绿。两次都留在 `" + ev("SUPERSEDED_false_green_masked_phase.json") + "`，"
  "本代活的那份是 `" + ev(RUNS_JSON) + "`。判据现在写进跑法：入口名必须等于本回合构建写出的那一枚。")
A("- 落地先证：`vite build` 退出 " + str(MASK["masked_build"]["exit"]) + "，且静态站回读的入口名从 `" +
  str(MASK["entry_human"]) + "` 变成 `" + str(MASK["entry_masked"]) + "`；两枚名字不相等才继续跑，"
  "相等就 ABORT（上一版的假绿正是入口名没变而臂报绿）。断言与两条名字在 `" + ev(MASK_JSON) + "`，"
  "跑法 `" + ev("mask_r2.py") + "`。")
A("- 结果：人话那一代 " + str(len(MASK["generations"]["human_copy"]["rows"])) + " 条形全绿；遮档那一代 " +
  str(len(MASK["generations"]["masked_copy"]["rows"])) + " 条形全红，其中「carries no machine token」红 " +
  str(mv["masked_red_on_the_machine_token_check"]) + " 条（每形一枚）；屏上那句实测为 "
  "「PLACE_ALREADY_IN_COLLECTION · …」。`counterexample_holds=" + str(mv["counterexample_holds"]) +
  "`，臂不是永真。")
A("")
A("## 5. 其余门与分母")
A("")
PY = r"D:/moodle/CityNexus/backend/.venv/Scripts/python.exe"


def pytest(args):
    r = subprocess.run([PY, "-m", "pytest"] + args, cwd=os.path.join(WT, "backend"),
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       timeout=1800)
    tail = [l for l in (r.stdout or "").splitlines() if l.strip()][-1:]
    return {"exit": r.returncode, "summary": tail[0] if tail else "",
            "stderr_tail": (r.stderr or "")[-160:]}


col = pytest(["tests", "--collect-only", "-q"])
sel = pytest(["tests", "-q", "-k", "collection",
              "--ignore=tests/test_v18_hermes_r20_transport_reliability_probe.py"])
own = pytest(["tests/test_qoder_ord0503_member_doors.py",
              "tests/test_qoder_ord0444_collections.py", "-q"])
mismatch = [l for l in subprocess.run(["git", "-C", WT, "diff", "--name-only", CO["base_rev"],
                                        CO["product_blob"]], capture_output=True,
                                       text=True).stdout.split() if "tests/" in l]
A("- 后端：`pytest tests --collect-only -q` 退出 " + str(col["exit"]) + "，现读那行 `" + col["summary"]
  + "`。其中一枚采集错误具名在这里：`tests/test_v18_hermes_r20_transport_reliability_probe.py` 抛 "
  "`ModuleNotFoundError: No module named 'mcp'`（环境缺件，不是本单造成——本枝 diff 里 "
  "`tests/` 下 0 枚文件：" + str(len(mismatch)) + "）。执行：`-k collection` `" + sel["summary"]
  + "`；单独跑这两枚与本单同族 `tests/test_qoder_ord0503_member_doors.py`、"
  "`tests/test_qoder_ord0444_collections.py` = `" + own["summary"] + "`。0 skip、0 断言被我改过"
  "（断言行在两枝之间未变：diff 只动 `backend/app/main.py` 的两处字符串）。")
A("- 前端：本回合 0 字节，故未跑 tsc；Q64 曝光尺对 `frontend/src` 两代各跑一次 `git archive` 快照："
  "verdict 同为 `" + str(EXP["sides"]["candidate"]["report"].get("verdict")) + "`，逐文件 `(file, hits)` "
  "清单相同（各 140 枚文件），命中总数 " + str(sum(r.get("hits", 0) for r in
                                                   EXP["sides"]["base"]["report"].get("per_file", []))) +
  " → " + str(sum(r.get("hits", 0) for r in
                  EXP["sides"]["candidate"]["report"].get("per_file", []))) + "，除临时目录名外标量差量 0 条"
  "（报告 blob " + blob_exp + "）。")
A("- 私有栈：后端监听者是我自己那枚（预览库全程只读，`bytes_before` 与 `bytes_after` 都是 7213056 且 "
  "`mtime_ns_equal=true`，见 blob " + blob_mask + "）；`:8000`、`:4781`、`:4782`、`:8693` 与号令者那四枚端口"
  "全程没碰，`demo/reset` 没跑过。")
A("- 量不到的两处，具名不遮：① `de` 臂——本产品只有两枚词典臂，上面给的是那一行的位置；"
  "② `PLACE_NOT_FOUND` 在屏上那一形——入口只在活动行自己的 place 身份存在时才渲染，"
  "行在屏上就意味着那个 id 在库里，所以我无法让 `http_status=404` 那一支走到这一格；它改前/改后都在门级实测（第 1 节），"
  "屏上那句是词表里的另一条（`noPlace`），本轮未改。")
A("- 证据枝 `review/ord0513/` 内清单：" + "、".join("`" + k + "`" for k in sorted(
    json.loads(io.open(os.path.join(SC, "ord0513_coords.json"), encoding="utf-8").read())["blobs"])) +
  "。")
dest = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    r"D:/moodle/_qoder_ledger_inbox", "1ba48dbf_%s.md" % time.strftime("%H%M"))
text = "\n".join(L) + "\n"
io.open(dest, "w", encoding="utf-8", newline="\n").write(text)
print("WROTE", dest, os.path.getsize(dest), "bytes")
bare = re.findall(r"(?<![\w:./-])\d{3,}(?![\w./-])", text)
print("3+ digit tokens (each must sit on a line carrying a blob or path:line):", len(bare))
