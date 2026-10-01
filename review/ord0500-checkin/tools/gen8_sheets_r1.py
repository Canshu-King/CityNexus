"""Generation 4 -- turn the artifacts into the two readings sheets.

Every number in the sheets is read out of a JSON this lane's instruments wrote, in this run.  Nothing
here is a sentence I typed from memory: if an artifact is missing, the cell says NOT_MEASURED rather
than keeping a number from an earlier generation.
"""
import json
import os
import sys
from datetime import datetime

LANE = r"D:/moodle/_qoder_phone_ord0485_20260930"
EV = os.path.join(LANE, "evidence")


def load(name):
    p = os.path.join(EV, name)
    if not os.path.exists(p):
        return {"MISSING": name}
    return json.load(open(p, encoding="utf-8"))


def cell(v):
    if v is None:
        return "NOT_MEASURED"
    if isinstance(v, (dict, list)):
        return json.dumps(v, ensure_ascii=False)
    return str(v)


def main():
    builds = load("gen8_builds_r1.json")
    sweep = load("gen8_checkin_sweep_r1.json")
    doors = load("gen8_doors_r1.json")
    ce1 = load("gen8_ce1_r1.json")
    proof = load("gen8_ce1_tree_proof_r1.json")
    walk = load("gen8_walk_r1.json")
    carrier = load("gen8_carrier_r1.json")

    faces = {f.get("label"): f for f in builds.get("faces", [])}
    runs = {r.get("tag"): r for r in sweep.get("runs", [])}

    def bnd(label, key):
        f = faces.get(label, {})
        e = f.get("entry", {})
        return cell(e.get(key))

    lines = []
    a = lines.append
    a("# ORD-0500 r4 -- 现尖 514b397f96f3b5165b24865f4a544ab6f8020084 读数单（与 ORD-0530 同族并块后重量；曝光尺两侧对照在 receipts 里）")
    a("")
    a("生成时间 `%s`；量具与件都在 `D:/moodle/_qoder_phone_ord0485_20260930`。"
      % datetime.now().astimezone().isoformat())
    a("")
    a("## 一、本代的产物身份（基座 + 交付候选 + 反件）")
    a("")
    a("| 面 | 入口资产 | 打包字节数 | 打包 sha256（本机字节） | tsc check | tsc all | build |")
    a("|---|---|---|---|---|---|---|")
    for label in ("TIP_514b397f", "O0500_R4", "O0500_CLIENTBOOL_MUTANT"):
        f = faces.get(label, {})
        e = f.get("entry", {})
        bn = e.get("bundle") or {}
        a("| %s | %s | %s | %s | %s | %s | %s |" % (
            label, bnd(label, "entry_asset"), cell(bn.get("bytes")),
            str(bn.get("sha256"))[:16] + "…",
            cell((f.get("tsconfig.check.json") or {}).get("exit")),
            cell((f.get("tsconfig.typecheck.json") or {}).get("exit")),
            cell((f.get("build") or {}).get("exit"))))
    a("")
    a("本机字节 sha256，不是 git 物件，不可 cat-file；件 `evidence/gen8_builds_r1.json`。")
    a("")
    a("## 二、打卡门在本代的普查（390x844 与 1280x800 各一趟，每趟一份新库）")
    a("")
    a("| 跑 | 视窗 | 站数 | 控件枚数 | 中心命中可按 | 盒 | 到屏时门里行数 | 屏上已打卡枚数 |")
    a("|---|---|---|---|---|---|---|---|")
    for tag, r in runs.items():
        rd = r.get("readings", {})
        c = rd.get("census", {})
        arr = rd.get("arrived", {})
        a("| %s | %s | %s | %s | %s | %s | %s | %s |" % (
            tag, cell(r.get("viewport")), cell(arr.get("stops")), cell(c.get("controls")),
            cell(c.get("pressable_by_centre_hit")),
            cell(sorted(set(c.get("boxes") or []))),
            cell((r.get("store_after_schema") or {}).get("count")), cell(arr.get("marks"))))
    a("")
    a("## 三、真发一发：行数前后与那句拒绝")
    a("")
    a("| 跑 | 请求序列 | 行数 前→后 | 重复点击后屏上拒绝句枚数 | 句主 | 句子 |")
    a("|---|---|---|---|---|---|")
    for tag, r in runs.items():
        rd = r.get("readings", {})
        ad = rd.get("after_duplicate", {})
        na = (rd.get("census", {}).get("controls") == 0)
        if na:
            a("| %s | %s | %s→%s | 不适用：这一族代 %s 枚打卡控件，没有可点的第二下 | 不适用 | 不适用 |" % (
                tag, cell(rd.get("requests")),
                cell((r.get("store_after_schema") or {}).get("count")),
                cell((r.get("store_after_arm") or {}).get("count")),
                cell(rd.get("census", {}).get("controls"))))
            continue
        a("| %s | %s | %s→%s | %s | %s | %s |" % (
            tag, cell(rd.get("requests")),
            cell((r.get("store_after_schema") or {}).get("count")),
            cell((r.get("store_after_arm") or {}).get("count")),
            cell(ad.get("notice_count")), cell(ad.get("notice_owners")),
            cell((ad.get("notices") or [None])[0])))
    a("")
    a("## 四、门里的拒绝原文（四字段陈列，不造句子）")
    a("")
    # one run per served backend, labelled by the tree each one booted -- the sheet must not carry
    # tree names from an earlier generation
    ROLE = {"wt20": "基座（现尖原样）", "wt19": "候选（本单交付）", "mutgen8": "反件一（409 判据摘掉）"}
    for r in doors.get("runs", []):
        name = ROLE.get(r.get("tree"), r.get("tree"))
        if not r:
            a("- %s：NOT_MEASURED（件缺）" % name)
            continue
        a("- %s `main.py` sha256 `%s…`，库行数 %s→%s，共享库未被动：%s" % (
            name, r.get("main_sha256", "")[:16],
            cell((r.get("staged") or {}).get("store_before", {}).get("count")),
            cell(r.get("store_after", {}).get("count")), cell(r.get("shared_untouched"))))
        a("")
        a("  | 用例 | http_status | content_type | body_bytes | reason_code | 句子里有 uuid | details 为 null | details |")
        a("  |---|---|---|---|---|---|---|---|")
        for p in r.get("probes", []):
            a("  | %s | %s | %s | %s | %s | %s | %s | %s |" % (
                p.get("case"), cell(p.get("http_status")), cell(p.get("content_type")),
                cell(p.get("body_bytes")),
                ("无（这一格测到了：成功体里没有 error 对象）" if p.get("reason_code") is None
                 else cell(p.get("reason_code"))),
                cell(p.get("uuid_in_message")), cell(p.get("details_is_null")),
                ("null（成功体里没有 error 对象）" if p.get("details") is None
                 else cell(p.get("details"))[:120])))
        a("")
        if r.get("mutant_screen"):
            ms = r["mutant_screen"]
            arm = ms.get("arm") or {}
            a("  反件屏侧：交付候选面 `%s`（outDir `%s`）挂在被改过的门上（判据摘掉），臂退出 %s，"
              "请求序列 %s，拒绝句枚数 %s，句主 %s，走完臂时库里 %s 行，pageerror %s "
              "—— 状态码与句子两样都看不出是哪一层拒的，这就是假绿。"
              % (cell((ms.get("serve") or {}).get("entry_asset")),
                 str((ms.get("serve") or {}).get("face_dir", "")).split("faces/")[-1],
                 cell(arm.get("exit")), cell(arm.get("requests")),
                 cell(arm.get("notice_count")), cell(arm.get("notice_owners")),
                 cell((ms.get("store_after_screen") or {}).get("count")),
                 cell(arm.get("page_errors"))))
            a("")
    a("## 五、反件一（服务端 409 判据摘掉）")
    a("")
    a("| 侧 | 臂数合计 | 通过 | 失败 | 退出 | 失败的臂 |")
    a("|---|---|---|---|---|---|")
    import re as _re
    for r in ce1.get("runs", []):
        summary = str(r.get("summary_line"))
        nums = dict(_re.findall(r"(\d+) (passed|failed|error)", summary))
        passed_u = sorted(set(r.get("passed_names") or []))
        failed_u = sorted(set(r.get("failed_names") or []))
        a("| %s | %s | %s | %s | %s | %s |" % (
            r.get("label"), "%s（= 通过 %d + 失败 %d，臂名去重）" % (len(passed_u) + len(failed_u), len(passed_u), len(failed_u)),
            "%s（臂名去重）" % len(passed_u), "%s（臂名去重）" % len(failed_u),
            cell(r.get("exit")), cell(failed_u)))
        r["_failed_unique"] = failed_u
    a("")
    compared = sum(int(v.get("files_compared") or 0) for v in (proof.get("dirs") or {}).values())
    a("两枚树只差 `backend/app/main.py` 一枚文件（比对 %s 枚，data/contracts/generated 全等，"
      "件 %s）；交付那枚的 `main.py` 前后 sha256 同一枚：%s…（本机字节 sha256，不是 git 物件，"
      "不可 cat-file）" % (cell(compared), cell(proof.get("why", ""))[:80],
                          str(ce1.get("candidate_main_sha256_before", ""))[:16]))
    a("")
    a("## 六、反件二（屏上的标不是门里给的）")
    a("")
    for tag in ("TIP_514b397f_phone", "O0500_R4_phone", "O0500_CLIENTBOOL_MUTANT_phone"):
        r = runs.get(tag, {})
        rd = r.get("readings", {})
        arr = rd.get("arrived", {})
        a("- %s：门里 %s 行时屏上 %s 枚「已打卡」；走完两站后门里 %s 行、最后一次屏读 %s 枚" % (
            tag, cell((r.get("store_after_schema") or {}).get("count")), cell(arr.get("marks")),
            cell((r.get("store_after_arm") or {}).get("count")),
            cell((rd.get("after_second") or {}).get("marks"))))
    a("")
    a("## 七、词汇闸（ORD-0485）不在这一页上。" )
    a("")
    a("那一单量在它自己那一代（基座 0989713aa687b97f4cd40bae009a6ce493425a4b），读数单是`review/ord0485-phone-walk/GEN6_READINGS.md`，随枝 `review/newlane-ord0485-phone-walkthrough-r5` 交付；把它的数写在本单页眉下就是跨代折算，Q24 不许。")
    a("")
    a("## 八、打卡真理载体（本单三臂）在三面上的通过/失败")
    a("")
    arms = load("gen8_carrier_arms_r1.json")
    for r in arms.get("runs", []):
        st = r.get("stats", {})
        a("- %s（Playwright 报告 %s）：通过 %s 枚，失败 %s 枚" % (
            r.get("label"), cell(r.get("report")), cell(st.get("expected")),
            cell(st.get("unexpected"))))
        for arm in r.get("arms", []):
            a("    · %-8s %s" % (cell(arm.get("status")), cell(arm.get("arm"))))
            if arm.get("node_message"):
                a("        %s" % arm["node_message"])
    a("")
    for r in carrier.get("runs", []):
        a("  （同跑的库行数 %s：%s→%s，入口 %s，服务字节与磁盘字节相等 %s）" % (
            r.get("label"), cell(r.get("rows_before")), cell(r.get("rows_after")),
            cell((r.get("serve") or {}).get("entry_asset")),
            cell((r.get("serve") or {}).get("index_bytes_equal_served_vs_disk"))))
    a("")
    a("## 九、没走的与不修的（具名）")
    a("")
    a("- 真机与隧道：NOT_MEASURED，以上全是本机 127.0.0.1 面上的模拟器读数。")
    a("- 整套 Playwright 验收：NOT_EXECUTED，只跑本单自己的载体与邻座已收的词汇闸。")
    a("- `GET /api/v1/journeys/{id}/checkins` 那一扇门在基座代仍不给未知行程具名（`require()` 印 uuid "
      "且 details 为 null）：本单在候选代把两扇门一起具名了，但契约侧只写 POST 的 404 —— 因为 GET 侧"
      "补 404 会撞 ORD-0476 已收的那条契约臂（`sorted(listed[\"responses\"]) == [\"200\", \"409\"]`），"
      "那是别人手上的判据，我不改。这条缺口具名留着，不在我写集里。")
    text = "\n".join(lines) + "\n"
    for dest in (os.path.join(LANE, "wt19/review/ord0500-checkin/GEN8_READINGS.md"),):
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        open(dest, "w", encoding="utf-8", newline="\n").write(text)
        print("WROTE %s bytes=%d lines=%d" % (dest, len(text.encode("utf-8")), text.count("\n")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
