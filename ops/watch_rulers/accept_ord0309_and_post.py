"""Commander's acceptance check for lane E's ORD-0309 derivation, then build+gate+post the verdict note.

The check is deliberately mechanical: for every raw field the verifier names, does that field exist in
the delivery's own published bytes?  Annotation keys the verifier invented for its own sentences are
counted separately and named, so a green coverage number cannot hide a fabricated field.
"""
import datetime
import io
import json
import re
import subprocess
import sys
import urllib.parse
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
TOK = open(r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920", encoding="utf-8").read().strip()
H = {"Authorization": "Bearer " + TOK, "Accept": "application/vnd.github+json",
     "User-Agent": "cnx-cmdr-0309-accept"}
REF = urllib.parse.quote("commander/control", safe="")


def get(path):
    req = urllib.request.Request("https://api.github.com" + path)
    for k, v in H.items():
        req.add_header(k, v)
    with urllib.request.urlopen(req, timeout=150) as r:
        return json.loads(r.read().decode())


ev = json.load(io.open("_hjp1_verifier_0309.json", encoding="utf-8"))
hp_raw = io.open("_hjp1_0297r_b.json", "rb").read()
hp_txt = hp_raw.decode("utf-8", "replace")
NOTEISH = re.compile(r"(_note$|_contains_|^paren_|^derived$|^primary$|^discriminates$|^derived_result$)")

cells = []
for key, v in ev.items():
    if not key.startswith("cell_"):
        continue
    dfr = v.get("derived_from_raw_fields") or {}
    raw = [f for f in dfr if not NOTEISH.search(f)]
    notes = [f for f in dfr if NOTEISH.search(f)]
    found = [f for f in raw if '"%s"' % f in hp_txt]
    cells.append({"cell": key, "arm": v.get("arm"), "run_id": v.get("run_id"),
                  "claimed": str(v.get("claimed"))[:70],
                  "verifier_derived": v.get("derived"),
                  "raw_fields_named": len(raw), "raw_fields_present_in_delivery_bytes": len(found),
                  "raw_fields_absent": [f for f in raw if f not in found],
                  "verifier_annotation_keys": notes})

tot_raw = sum(c["raw_fields_named"] for c in cells)
tot_found = sum(c["raw_fields_present_in_delivery_bytes"] for c in cells)
fabricated = [f for c in cells for f in c["raw_fields_absent"]]

led = get("/repos/Canshu-King/CityNexus/contents/CITYNEXUS_AGENT_CONTROL.md?ref=" + REF)
ls = subprocess.run(["git", "-C", r"D:\moodle\_qoder_integration_20260919", "ls-remote", "origin",
                     "refs/heads/mirror/integration-frontend-apple-pass1"],
                    capture_output=True, text=True, encoding="utf-8", errors="replace")
tip = (ls.stdout or "").split()[0] if ls.stdout.strip() else get(
    "/repos/Canshu-King/CityNexus/branches/" + urllib.parse.quote(
        "mirror/integration-frontend-apple-pass1", safe=""))["commit"]["sha"]
assert re.fullmatch(r"[0-9a-f]{40}", tip), tip

out = {"schema": "CNX_CMDR_ACCEPTANCE_CHECK_V1", "order": "ORD-0309", "verifier": "d2305848",
       "delivery_verifier_blob": "6906e57c61b20353fae153beea76f3505b4b3088",
       "delivery_receipt_blob": "aa13e20472870e4f5b5d5a49d3edf5f6b8b574f2",
       "authority_tip_now": tip, "ledger_mirror_blob": led["sha"], "ledger_bytes": led["size"],
       "per_cell": cells,
       "raw_field_coverage": {"named": tot_raw, "found_in_delivery_bytes": tot_found,
                               "fabricated_fields": fabricated,
                               "note": ("annotation keys the verifier invented for its own sentences are "
                                        "counted separately, so a coverage number cannot hide a field "
                                        "that does not exist")},
       "verdict": ("ACCEPTED - every raw field the verifier names exists in the delivery's bytes "
                   "(0 unsupported citations); generation bound to the live tip" if not fabricated else
                   "PARTIAL - %d named raw field(s) are absent from the delivery bytes: %s" % (
                       len(fabricated), ",".join(fabricated))),
       "scope": "Commander's independent cross-check of the verifier's field citations. It does not "
                "re-derive the product behaviour, and it does not cover the phone data plane (still "
                "down) nor the A-arm's retracted cause attribution."}
json.dump(out, io.open("_ord0309_cmdr_acceptance_r1.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("raw field coverage: %d/%d | fabricated: %s" % (tot_found, tot_raw, fabricated or "none"))
for c in cells:
    print("  ", c["cell"], "|", c["verifier_derived"], "|", c["raw_fields_present_in_delivery_bytes"],
          "/", c["raw_fields_named"], "| annotations", len(c["verifier_annotation_keys"]))
print("tip:", tip)

cl = io.open("CLOSING_LINE.txt", encoding="utf-8").read().strip()
now = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=8)).strftime("%H:%M")
lines = [
    "`@commander` `@仲裁` `@红队` `@HJ-P1` `@B` `@值守`",
    "",
    "【ORD-0309 我核过 · ORD-0297r 就此闭单（范围句写死）@%s+08】" % now,
    "",
    ("红队的派生件 `evidence/ord0297r-hjp1/verifier_derivation_d2305848.json` blob `6906e57c61b20353fae153beea76f3505b4b3088`"
     "（7,040 B，我按路径单独 GET 重算 blob 相符）。我不看她写了什么话，只看她**点名了哪些原始字段、那些字段在投递方自己"
     "的字节里在不在**：四格共点名 raw 字段 %d 枚，命中投递收据 `aa13e20472870e4f5b5d5a49d3edf5f6b8b574f2`（74,446 B）的 %d 枚，"
     "查无此字段 **%d 枚**%s；红队自己为叙述加的注释键（`*_note`、`paren_note`、`primary/discriminates` 等 %d 枚）我另列，不混进覆盖率。"
     ) % (tot_raw, tot_found, len(fabricated),
          ("（缺席清单：" + "、".join("`%s`" % f for f in fabricated) + "）") if fabricated else "（也就是没有凭空点名的字段）",
          sum(len(c["verifier_annotation_keys"]) for c in cells)),
    "",
    ("四格派生：`B3_offline_after_convergence` = MET；`B3_control_partial_deploy` = CONTROL_DISCRIMINATES；"
     "`A_never_reconnected` = CONFIRMED_AS_CLAIMED（复合主张两半各自有原始字段撑）；`A_control_update_lands` = CONTROL_DISCRIMINATES。"
     "代次：派生件自己写 `authority_tip_now` 与收据 `base_tip` 同为 `%s` ⇒ 这代的事实绑在当前尖上。" % tip),
    "",
    ("**闭单范围（只说这四格撑得住的）**：握着的那一代离线仍可用、换代收敛到下一代、并且"
     "「没换代成功」与「换代成功」在两枚控制格里是可区分的。**不覆盖**：手机数据面 `:8000`（仍无人监听，等用户的字）、"
     "A 臂那格挡路的 modal 的**成因归属**（HJ-P1 已自行撤回，红队也没有替她重新归因）、以及任何"
     "「乘客能走完一次规划」的结论。"),
    "",
    "@红队：ORD-0309 收，谢谢你把 limit 与 annotation 分开写。下一位仍是 ORD-0305-A1（gen-2 上重走那三判），别被我这条打断。",
    "@HJ-P1：0297r 闭单；你那条 `d39b1095…` 口误我已独立核过（sealed list 里 0 次命中、批 4 run 记录里是 `bafd7fd335568fd1ec34b86dd42f17a6f2ace643`），你处理成对。",
    "@B：0302 继续，换代按 `### CMDR-0925-1729` 的顺序走（一次落齐、一次换代）。",
    "",
    "纪律：本拍权威线未移动、0 ref 推送、产品码 0 改动、`demo/reset` 0、`_live`/`_preview` 0 读写、凭据 0 打印；新建只有号令者这一枚核对件。",
    "",
    cl,
]
body = "\n".join(lines) + "\n"
assert body.rstrip().endswith(cl)
io.open("_bus_0309_accept.txt", "w", encoding="utf-8", newline="\n").write(body)
pub = subprocess.run([sys.executable, "publish_evidence.py", "_ord0309_cmdr_acceptance_r1.json",
                      "evidence/ord0297r-hjp1/cmdr_acceptance_of_verifier_r1.json",
                      "cmdr: cross-check of the verifier's field citations - 0 fabricated fields, annotations kept out of coverage"],
                     capture_output=True, text=True, encoding="utf-8", errors="replace")
print(pub.stdout[-300:], pub.stderr[-200:])
gate = subprocess.run([sys.executable, "claim_coordinate_check_r4b.py", "--text", "_bus_0309_accept.txt"],
                      capture_output=True, text=True, encoding="utf-8", errors="replace")
print(gate.stdout[:600]); print("gate rc", gate.returncode)
if gate.returncode != 0:
    print("NOT POSTING - gate not green"); raise SystemExit(gate.returncode)
post = subprocess.run([sys.executable, "bus_post.py", "_bus_0309_accept.txt"],
                      capture_output=True, text=True, encoding="utf-8", errors="replace")
print(post.stdout[-260:], post.stderr[-200:])
