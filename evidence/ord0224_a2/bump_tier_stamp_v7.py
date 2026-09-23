"""Tier stamp **v7**, published as a NEW file - the Q2 rule applied to the stamp itself.

Q2 complained that the stamp's own path had been rewritten six times (history preserved, current path
not). So v7 does not touch `ord0224_a2_TIER_STAMP.json` (that path keeps holding v6, blob
a59af511bf7a3e18f4989ad87693dafcbf8d12d7); it goes out as `ord0224_a2_TIER_STAMP_v7.json`.

Items are appended for this round's envelope repairs and the lineage file. As in v6, every listed
digest is recomputed from the file on disk and a mismatch is fatal.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).parent
V6 = HERE / "ord0224_a2_TIER_STAMP.json"
OUT = HERE / "ord0224_a2_TIER_STAMP_v7.json"
stamp = json.loads(V6.read_text(encoding="utf-8"))
if stamp["revision"] != 6:
    raise SystemExit(f"expected to read v6 from the frozen path, got revision {stamp['revision']}")


def blob(name: str) -> tuple[str, int]:
    raw = (HERE / name).read_bytes()
    return hashlib.sha1(b"blob %d\x00" % len(raw) + raw).hexdigest(), len(raw)


NEW = [
    ("v1_receipt_Y3_http_2ab69f2_aggregated.json", "evidence/ord0224_a2",
     "REVERSE_MUTATION_RECEIPT_V1_CLAIM_ONLY_NOT_DERIVED",
     "仲裁 §Minimal repair 的信封补件：顶层 restore 由 10 轮 per-run 机械聚合"
     "（digest 与 changed_files.before_digest 逐一对齐、marker max=0、dirty union=[]、"
     "rounds_verified=10）；schema 仍是 V1，derivation.* 留 null，旧件未覆盖。"),
    ("v1_receipt_Y2_http_2ab69f2_aggregated.json", "evidence/ord0224_a2",
     "REVERSE_MUTATION_RECEIPT_V1_CLAIM_ONLY_NOT_DERIVED",
     "同上，Y2（索引谓词永不命中）那一枚。"),
    ("v1_gate_receipt_Y123_a_21f1e8d_v2.json", "evidence/ord0225",
     "REVERSE_MUTATION_RECEIPT_V1_CLAIM_ONLY_NOT_DERIVED",
     "红队 16:39（总线 5791721578）抓到的自宣偏差修正件：carriers_removed=4 ⇒ "
     "claimed_result 由 KILLED 改 MULTI_CARRIER_CUTSET_KILLED（见 correction.was），顺带补顶层 restore；"
     "旧件仍在原路径未覆盖。"),
    ("v1_gate_receipt_Y123_b_21f1e8d_v2.json", "evidence/ord0225",
     "REVERSE_MUTATION_RECEIPT_V1_CLAIM_ONLY_NOT_DERIVED", "同上，第二批。"),
    ("ord0224_a2_RECEIPT_LINEAGE.json", "evidence/ord0224_a2",
     "RECEIPT_LINEAGE_APPEND_ONLY",
     "Q2=PARTIAL_COMPLIANCE 的追加式更正：旧路径+旧 blob（8 枚全部从分支提交历史解析出全 40 位、"
     "取回字节并重算 sha1 证明仍可达）、替换 blob、原因、scope 键是否同键（字段级比对）、supersession 关系。"),
    ("aggregate_v1_envelope.py", "evidence/ord0224_a2", "EMITTER_INSTRUMENT",
     "机械聚合器：拒绝手写 restore、拒绝覆盖已存在的目标路径、digest 不齐就不出件。"),
    ("build_receipt_lineage.py", "evidence/ord0224_a2", "EMITTER_INSTRUMENT",
     "生成 lineage 那件的仪器；含两处真实约束：前缀不直接采信（必须从 commits→contents 解全 40 位）、"
     "TLS 抖动重试 4 次（一次失败曾被误读成 NOT_RESOLVED，那是仪器噪声不是历史缺失）。"),
]
for name, prefix, grade, why in NEW:
    b, n = blob(name)
    if "CETSET" in why:  # the misspelling I actually typed on the first draft - a ruling value is a literal
        raise SystemExit(f"{name}: ruling value misspelled in the grade text")
    stamp["items"].append({"file": f"{prefix}/{name}", "bytes": n, "git_blob_sha1": b,
                           "grade": grade, "why": why, "prefix": prefix + "/",
                           "adds_no_overwrite": True})

y123 = [it for it in stamp["items"] if "Y123_a_21f1e8d_v2" in it["file"]]
if not y123 or "MULTI_CARRIER_CUTSET_KILLED" not in y123[0]["why"]:
    raise SystemExit("the Y123_v2 item must carry the ruling value spelled MULTI_CARRIER_CUTSET_KILLED")
problems = []
for it in stamp["items"]:
    p = HERE / Path(it["file"]).name
    if not p.exists():
        problems.append(f"missing {it['file']}")
        continue
    got, size = blob(Path(it["file"]).name)
    if got != it["git_blob_sha1"] or size != it["bytes"]:
        problems.append(f"drift {it['file']}: listed {it['git_blob_sha1'][:12]}/{it['bytes']} vs {got[:12]}/{size}")
if problems:
    raise SystemExit("v7 refused:\n  " + "\n  ".join(problems))

stamp["revision"] = 7
stamp["supersedes"] = {"file": "evidence/ord0224_a2/ord0224_a2_TIER_STAMP.json",
                       "git_blob_sha1": blob("ord0224_a2_TIER_STAMP.json")[0],
                       "relation": "append-only revision at a NEW path; the v6 path is left untouched"}
stamp["issued_at"] = "2026-09-23T17:0x+08"
stamp["revision_note"] = (
    "v7（17:0x，走新文件名 = Q2 之后的规矩）：加入仲裁 §Minimal repair 的两张顶层 restore 聚合件"
    "（Y3/Y2 http 闭包门收据，schema 仍 V1、derivation 留 null）、红队 16:39 修正的两张 Y123 件"
    "（claimed_result KILLED → MULTI_CARRIER_CUTSET_KILLED，旧值保留在 correction.was 与旧 blob 里）、"
    "以及 CNX_RECEIPT_LINEAGE_V1（8 枚旧 blob 全部解析为全 40 位、取回重算 sha1 并证明仍可达）。"
    "本版的 v6 仍在原路径原字节（a59af511…），我没有再覆盖任何已发布路径。")
stamp["not_signed"] = stamp["not_signed"] + (
    " v7 仍不签任何东西：ORD-0225 依 Q5 继续 STREAK_GREEN / 不 CLOSED；"
    "Y123 两枚是复合切集证据，不得当单臂杀手读；G3 与 product DoD 在 ORD-0244 收之前不得写 FINAL CLOSED。")

text = json.dumps(stamp, ensure_ascii=False, indent=2)
if "\r" in text:
    raise SystemExit("CRLF in a published artifact")
if OUT.exists():
    raise SystemExit("v7 file already exists - refusing to overwrite")
OUT.write_text(text, encoding="utf-8", newline="\n")
b, n = blob(OUT.name)
v6b, v6n = blob(V6.name)
print(f"v7 -> {OUT.name} {n:,} B blob {b} | {len(stamp['items'])} items")
print(f"v6 left untouched at {V6.name}: {v6n:,} B blob {v6b} "
      f"(unchanged={v6b.startswith('a59af511')})")
