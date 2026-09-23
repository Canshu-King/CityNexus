"""Mechanical envelope repair for the V1 reverse-mutation receipts (arbiter 13:32 / 15:14 / red team 16:39).

Two defects are fixed here, both by *adding new files* - no published blob is overwritten:

1. `INVALID / MISSING_REQUIRED_TOP_LEVEL_RESTORE` - the required `restore` object existed in all ten
   per-run entries but not at the top level. The arbiter's "Minimal repair" formula is applied
   literally, reading only from the run objects (nothing is typed by hand):

   attempted = all(run.restore.attempted)          restored = all(run.restore.restored)
   restored_digest_by_file[path] = the single digest, and it must equal
                                   mutation.changed_files[path].before_digest
   byte_exact_match_before = all(...)              mutant_marker_hits_after_restore = max(per-run) == 0
   post_restore_dirty_paths = union(per-run) == []

2. `claimed_result` self-declaration drift - Y123_a / Y123_b claimed `KILLED` while
   `carriers_removed = 4` (A1+A2+index+loser read-back) derives to `MULTI_CARRIER_CUTSET_KILLED`.
   Left as-is, a composite cutset reads as "there is a single-arm killer", which is exactly the shape
   B-1 exists to block. The corrected value is written under a new path, with the old number kept
   visible in `correction.was` so nothing looks edited after the fact.

`schema_version` stays `CNX_REVERSE_MUTATION_RECEIPT_V1` (this is compliance, not a new schema) and
`derivation.derived_result` / `direct_red_nodeids` / `collateral_red_nodeids` stay null for the verifier.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).parent
VERIFIER_QUOTED_SOURCE_BLOBS = {  # what the arbiter / red team actually read
    "v1_receipt_Y3_http_2ab69f2.json": "89b698678fb67538",
    "v1_receipt_Y2_http_2ab69f2.json": "5612cd30cd7944a5",
}
CLAIMED_RESULT_CORRECTIONS = {
    "v1_gate_receipt_Y123_a_21f1e8d.json": "v1_gate_receipt_Y123_a_21f1e8d_v2.json",
    "v1_gate_receipt_Y123_b_21f1e8d.json": "v1_gate_receipt_Y123_b_21f1e8d_v2.json",
}
RULING_VALUE = "MULTI_CARRIER_CUTSET_KILLED"  # arbiter Q5, 15:14, verbatim


def blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob %d\x00" % len(raw) + raw).hexdigest()


def aggregate_restore(src: dict) -> dict:
    runs = [r for r in src["mutated_runs"]["runs"] if r.get("mutated")]
    if not runs:
        raise SystemExit("no mutated runs to aggregate - refusing to invent a restore block")
    missing = [r["run_index"] for r in runs if "restore" not in r]
    if missing:
        raise SystemExit(f"runs without a restore receipt: {missing}")
    per = [r["restore"] for r in runs]
    digests: dict[str, set[str]] = {}
    for p in per:
        for path, dg in p["restored_digest_by_file"].items():
            digests.setdefault(path, set()).add(dg)
    restored_digest_by_file = {}
    for path, vals in digests.items():
        if len(vals) != 1:
            raise SystemExit(f"{path}: {len(vals)} different restored digests - not a single digest")
        restored_digest_by_file[path] = next(iter(vals))
    by_file = {c["path"]: c for c in src["mutation"]["changed_files"]}
    for path, dg in restored_digest_by_file.items():
        want = by_file.get(path, {}).get("before_digest")
        if want is None:
            raise SystemExit(f"{path}: no mutation.changed_files entry to compare the digest against")
        if dg != want:
            raise SystemExit(f"{path}: restored digest {dg[:12]} != before_digest {want[:12]}")
    marker_max = max(p["mutant_marker_hits_after_restore"] for p in per)
    dirty: list[str] = sorted({d for p in per for d in p["post_restore_dirty_paths"]})
    return {
        "attempted": all(p["attempted"] for p in per),
        "restored": all(p["restored"] for p in per),
        "restored_digest_by_file": restored_digest_by_file,
        "byte_exact_match_before": all(p["byte_exact_match_before"] for p in per),
        "mutant_marker_hits_after_restore": marker_max,
        "post_restore_dirty_paths": dirty,
        "rounds_verified": len(per),
        "aggregation": "all_mutated_runs",
        "aggregation_semantics": ("all() 覆盖 attempted/restored/byte_exact；restored_digest_by_file 取每轮一致的那一个"
                                  "并与 mutation.changed_files[path].before_digest 逐一对齐（不齐就拒绝出件）；"
                                  "marker 用 max（必须 0）；dirty 用 union（必须 []）。全部从 per-run 对象读，不手写。"),
        "derived_from_run_indices": [r["run_index"] for r in runs],
    }


def build(src_name: str, out_name: str, correction: str | None) -> dict:
    src_raw = (HERE / src_name).read_bytes()
    src = json.loads(src_raw.decode("utf-8"))
    if src.get("schema_version") != "CNX_REVERSE_MUTATION_RECEIPT_V1":
        raise SystemExit(f"{src_name} is not a V1 receipt")
    quoted = VERIFIER_QUOTED_SOURCE_BLOBS.get(src_name)
    if quoted and not blob(src_raw).startswith(quoted):
        raise SystemExit(f"{src_name} on disk is {blob(src_raw)[:16]}, not the {quoted} the verifier read")
    out = json.loads(json.dumps(src))  # deep copy; the source file is never written
    out["restore"] = aggregate_restore(src)
    prov = {"repair_kind": "envelope_only_no_remeasurement",
            "source_file": src_name, "source_git_blob_sha1": blob(src_raw),
            "source_bytes": len(src_raw),
            "source_is_untouched": True,
            "why": ("仲裁/红队读到的缺的是**信封字段**，不是实验失败：同一份 10 轮 per-run 里都有 restore。"
                    "本件只把它机械聚合到顶层，没有重跑一轮，也没有改动任何一条读数。"),
            "published_path_frozen": "旧路径与旧 blob 原样保留，本件走新路径（Q2 之后的规矩）。"}
    if correction:
        was = out["derivation"]["claimed_result"]
        carriers = out["mutation"]["carriers_removed"]
        if was != "KILLED":
            raise SystemExit(f"{src_name}: claimed_result is {was}, nothing to correct")
        out["derivation"]["claimed_result"] = RULING_VALUE
        out["derivation"]["claimed_result_note"] = (
            f"交付方自称，且已按红队 16:39 的派生修正：`carriers_removed={len(carriers)}` "
            f"（{', '.join(carriers)}）只能派生成 `{RULING_VALUE}`，不是单臂 `KILLED`。"
            "closure 仍只认 verifier 的 derived_result。")
        prov["claimed_result_correction"] = {
            "was": was, "now": RULING_VALUE,
            "carriers_removed": carriers,
            "raised_by": "red team (lane E) independent verifier, bus 5791721578, 16:39",
            "ruling": "arbiter Q5 15:14: Y123 = MULTI_CARRIER_CUTSET_KILLED，不得升格为单臂 RECEIPT_V1",
            "old_value_still_visible_in": f"evidence/ord0225/{src_name}（未覆盖）",
        }
    out["envelope_repair"] = prov
    out["repaired_at_local_clock"] = datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M%z")
    text = json.dumps(out, ensure_ascii=False, indent=2)
    if "\r" in text:
        raise SystemExit("CRLF in a published artifact")
    target = HERE / out_name
    if target.exists():
        raise SystemExit(f"{out_name} already exists - refusing to overwrite a published path")
    target.write_text(text, encoding="utf-8", newline="\n")
    return out


def main() -> int:
    jobs = [(n, n.replace(".json", "_aggregated.json"), None) for n in VERIFIER_QUOTED_SOURCE_BLOBS]
    jobs += [(s, t, "claimed_result") for s, t in CLAIMED_RESULT_CORRECTIONS.items()]
    for src, dst, corr in jobs:
        out = build(src, dst, corr)
        r = out["restore"]
        print(f"{dst}\n    from {src} ({out['envelope_repair']['source_git_blob_sha1'][:16]}…) "
              f"| restore attempted={r['attempted']} restored={r['restored']} byte_exact={r['byte_exact_match_before']} "
              f"marker={r['mutant_marker_hits_after_restore']} dirty={r['post_restore_dirty_paths']} "
              f"rounds={r['rounds_verified']}")
        print(f"    claimed={out['derivation']['claimed_result']} derived={out['derivation']['derived_result']} "
              f"| target files={list(r['restored_digest_by_file'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())