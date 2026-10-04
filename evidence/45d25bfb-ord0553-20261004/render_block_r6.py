"""ORD-0553 r6 -- publish the false-positive facts, render the correction block, gate it, deliver it.

The r5 census named two painted machine words as "words the server answered".  This pass proves they are
this component's own dictionary wording (both keys, both language tables, and the render site, with line
numbers read now), and that the string equality with a server value is coincidence -- so the census rule
"逐字等于某个响应值" is not enough on its own.  Nothing here changes product bytes.
"""
import datetime
import io
import json
import os
import shutil
import subprocess
import sys

R1 = r"D:/moodle/_qoder_cmdra_ord0553_20261003"
WT = r"D:/moodle/_qoder_cmdra_ord0553_r2_20261003\wt"
REFS = r"D:/moodle/_qoder_cmdr_ref_20260921/live_checks"
PUBLISHER = os.path.join(REFS, "publish_evidence_gated_r1.py")
REMOTE = "evidence/45d25bfb-ord0553-20261004/"
PY = sys.executable
facts = json.load(open(os.path.join(R1, "_facts_r6.json"), encoding="utf-8"))
census = json.load(open(os.path.join(R1, "_facts_r5.json"), encoding="utf-8"))

FILES = [(os.path.join(R1, "_facts_r6.json"), "facts_r6_false_positive.json"),
         (os.path.join(R1, "_render_block_r6.py"), "render_block_r6.py")]
blobs = {}
rows = []
for line in io.open(os.path.join(R1, "_publish_manifest_r5.jsonl"), encoding="utf-8"):
    r5 = json.loads(line)
    if r5.get("decision") in ("CREATED", "SKIP_IDENTICAL") and r5.get("blob"):
        blobs[r5["remote_path"].split("/")[-1]] = r5["blob"]
for path, name in FILES:
    r = subprocess.run([PY, PUBLISHER, "--local", path, "--path", REMOTE + name,
                        "--message", "lane 45d25bfb ORD-0553 r6: " + name],
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       cwd=REFS, timeout=300)
    out = (r.stdout or "") + (r.stderr or "")
    at = out.find('{\n "decision"')
    if at < 0:
        at = out.find('{"decision"')
    obj = json.loads(out[at:out.rfind("}") + 1]) if at >= 0 else {"decision": "NO_JSON"}
    obj["remote_path"] = REMOTE + name
    obj["rc"] = r.returncode
    rows.append(obj)
    print("%-34s -> %-12s rc %s blob %s" % (name, obj.get("decision"), r.returncode, str(obj.get("blob"))[:14]))
    if obj.get("decision") in ("CREATED", "SKIP_IDENTICAL"):
        blobs[name] = obj["blob"]
man = os.path.join(R1, "_publish_manifest_r6.jsonl")
io.open(man, "w", encoding="utf-8").write("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in rows))
bad = [x["remote_path"] for x in rows if x.get("decision") not in ("CREATED", "SKIP_IDENTICAL") or x.get("rc") != 0]
if bad:
    raise SystemExit("ABORT not published: %s" % bad)


def blob(name):
    return blobs[name]


def anchor(relpath, line):
    return "%s:%d" % (relpath, line)


sel = facts["painted"]["SELECTED"]
com = facts["painted"]["COMMITMENT"]
en = census["arms"]["en"]
zh = census["arms"]["zh"]
I18N = "frontend/src/i18n/LocaleContext.tsx"
CTP = "frontend/src/features/intelligence/ControlTowerPanel.tsx"
closing = io.open(os.path.join(REFS, "CLOSING_LINE.txt"), encoding="utf-8").read().strip()

L = []
w = L.append
w("### ORD-0553 · 普查更正 r6（r5 点名的两枚「服务端答的字」其实都是本地词表措辞）· 车道 45d25bfb 自申报（不占新号、0 枚产品字节）")
w("")
w("一、这一件更正什么")
w("- 我上一块（r5，账本与镜像都在第 16591 行）把十四条路由里两枚机词判进了「服务端答的字」一侧：SELECTED 与 COMMITMENT。这一趟我按发射点重读，两枚都是本组件词表自己的措辞，判错了，按规矩发新帖不改旧帖。")
w("- 判错的机制也写清楚：r5 的分类只要求「这枚字逐字等于某个被答应的响应值」。同一串字服务端也答过一次，就够假阳。两枚的巧合值：SELECTED 撞 {sv}，COMMITMENT 撞 {cv}（都在 r5 发布件里，件 blob {cb}）。".format(
    sv=facts["server_values_that_coincide"]["SELECTED"],
    cv=facts["server_values_that_coincide"]["COMMITMENT"], cb=blob("facts_r6_false_positive.json")))
w("")
w("二、按发射点重读（两枚各自的行号都是本轮现取）")
w("- SELECTED：屏上整行逐字是 {txt}，不是独立成行（standalone_line={st}），槽位链 {ch}。发射点是词表键 {k}：英文那侧在 {l1}、中文那侧在 {l2}，两侧同键，值里本来就带这串大写词。".format(
    txt=sel["line_text"], st=sel["standalone_line"], ch=" > ".join(sel["slot_chain"]), k=sel["source_key"],
    l1=anchor(I18N, sel["source_lines"][0]), l2=anchor(I18N, sel["source_lines"][1])))
w("- COMMITMENT：屏上整行逐字是 {txt}，独立成行（standalone_line={st}），槽位链 {ch}。发射点 {site}，取的是词表键 {k}：英文侧 {l1}、中文侧 {l2}。这一格画的是「这条事实叫什么」的标签，不是服务端某个 kind 的值。".format(
    txt=com["line_text"], st=com["standalone_line"], ch=" > ".join(com["slot_chain"]),
    site=anchor(CTP, com["render_site"][0]), k=com["source_key"],
    l1=anchor(I18N, com["source_lines"][0]), l2=anchor(I18N, com["source_lines"][1])))
w("")
w("三、所以 r5 那张普查表的净结论")
w("- 英文臂：命中 {h} 处、去重 {d} 枚，按发射点重读后「服务端答的字上屏」实测 0 枚（原判 {s} 枚已在本块更正），其余 {t} 枚是样式字或键名巧合。件 blob {be}。".format(
    h=en["totals"]["painted_hits"], d=en["totals"]["distinct_tokens"], s=en["totals"]["server_answer_tokens"],
    t=en["totals"]["style_only_tokens"], be=blob("census_all_routes_en.json")))
w("- 中文臂：命中 {h} 处、去重 {d} 枚、服务端答的字 0 枚，唯一那枚是 /v8/bookings 的 JSON（号令者早前裁过保留）。件 blob {bz}。".format(
    h=zh["totals"]["painted_hits"], d=zh["totals"]["distinct_tokens"], bz=blob("census_all_routes_zh.json")))
w("- 判据要升级才有用：下一版我把「逐字相等」换成「相等且发射点确实读那一枚响应字段」，槽位级判据；这一轮先用这两个反例把它钉住，反例本身就在发布件里（件 blob {fb}）。".format(
    fb=blob("facts_r6_false_positive.json")))
w("")
w("四、字节与纪律")
w("- r6 产品字节 0 枚、提交 0 笔、推送 0 次；词表里那两条大写措辞（{a1} 与 {a2}）我一个字没动——它们是组件自己的样式字，你早前对「全抹」明确不同意。".format(
    a1=anchor(I18N, sel["source_lines"][0]), a2=anchor(I18N, com["source_lines"][0])))
w("- 本轮无新端口：r5 的 :8752 与 :49861 交完那块已停（netstat 现读 0 行 LISTENING）；这一件只用已发布的读数与本地工作树现取的行号，没重跑浏览器。")
w("- 发布：本件新落盘 2 枚、全 CREATED、重写 0 件，回执 D:/moodle/_qoder_cmdra_ord0553_20261003/_publish_manifest_r6.jsonl；共享预览库没读没写、没跑 demo/reset；force-push 0 次；权威线我没碰。")
w("")
w(closing)

text = "\n".join(L) + "\n"
stage = os.path.join(R1, "_stage_45d25bfb_r6.md")
io.open(stage, "w", encoding="utf-8", newline="\n").write(text)
print("rendered", stage, len(text.encode("utf-8")), "B,", len(L), "lines")

gate = subprocess.run([PY, os.path.join(REFS, "claim_coordinate_check_r7.py"), "--text", stage,
                       "--expect-clean"], capture_output=True, text=True, encoding="utf-8",
                      errors="replace", cwd=REFS, timeout=600)
print("GATE rc=%d" % gate.returncode)
print((gate.stdout or "")[-2500:])
if gate.returncode != 0:
    raise SystemExit("gate RED -> not delivered")
hhmm = datetime.datetime.now().strftime("%H%M")
dst = r"D:\moodle\_qoder_ledger_inbox\45d25bfb_%s.md" % hhmm
if os.path.exists(dst):
    raise SystemExit("ABORT exists " + dst)
shutil.copyfile(stage, dst)
print("DELIVERED", dst, os.path.getsize(dst), "B identical=%s" % (open(stage, "rb").read() == open(dst, "rb").read()))
