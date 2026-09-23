"""Build `ord0224_a2_RECEIPT_LINEAGE.json` - the append式 scope-correction Q2 asked for (arbiter 15:14).

Q2's verdict was PARTIAL_COMPLIANCE: history was preserved (old blobs still resolvable) but the
*current content of published paths* had been replaced, while the arbiter's and lane F's re-derivations
cite the old numbers. This file is the missing link, and it does not take anyone's word for the old
coordinates:

  * every old blob sha is recovered from the branch's own commit history (a 16-hex prefix quoted in a
    message is not a coordinate), by walking `GET /commits?path=…&sha=commander/control` and reading
    the blob for that path at each commit;
  * each recovered blob is then fetched from `GET /git/blobs/<full-sha>` and re-hashed, so "still
    reachable" is a measured 200 + sha1 equality, not an assertion;
  * the difference between old and new content is computed from the two byte strings (keys added,
    fields changed), so the stated reason describes what actually differs rather than what I remember
    doing.

Published paths are frozen from now on: revisions go out under `..._v2.json` / `..._aggregated.json`
style names, which is also why this revision of the tier stamp is published as a NEW file.
"""
from __future__ import annotations

import hashlib
import json
import urllib.error
import urllib.request
from pathlib import Path

TOK = open(r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920", encoding="utf-8").read().strip()
REPO = "Canshu-King/CityNexus"
BRANCH = "commander/control"
HDRS = {"Authorization": f"Bearer {TOK}", "Accept": "application/vnd.github+json",
        "User-Agent": "cnx-lane-c-lineage"}
HERE = Path(__file__).parent

# prefix quoted to me (arbiter / commander / tier stamp) -> the path whose history must name it
QUOTED = {
    "evidence/ord0224_a2/mutant_rounds_Y3_http_2ab69f2.json": ["2650cd5a17c85f7b"],
    "evidence/ord0224_a2/mutant_rounds_Y2_http_2ab69f2.json": ["bf72437f4d6f3eba"],
    "evidence/ord0224_a2/ord0224_a2_TIER_STAMP.json": ["5ca7356ccaacc97b", "6ff6b0d824bbf906",
                                                       "fb3e250c4451e3cf", "e7c0b1600165462c",
                                                       "512aca2bf2a1f488"],
    "evidence/ord0225/xproc_v1_gate_receipt.py": ["0e7bf4174400c2f8"],
}
REASONS = {
    "evidence/ord0224_a2/mutant_rounds_Y3_http_2ab69f2.json": (
        "同一 scope 键上又跑了一批，并把新批次写到了旧路径：新文件多了 self_clean（每轮具名临时库 + 受审自清），"
        "control_round 随之不同。本 entry 的 diff 还量出一件旧缺陷：旧 blob 的顶层 sha 只有 28 个字符"
        "（`2ab69f20adf783a6f288580129e3`，被截断），新版是完整 40 位；tree / node / run_shape 两版一致，"
        "所以替换件与旧件是同一 scope 键，不是换了一棵树。旧 blob 是仲裁与 F 复算时读的那一份。"),
    "evidence/ord0224_a2/mutant_rounds_Y2_http_2ab69f2.json": (
        "同上：Y2（索引谓词永不命中）那批也一样被同路径升版覆盖了。"),
    "evidence/ord0224_a2/ord0224_a2_TIER_STAMP.json": (
        "分级戳按 revision 递增、一直在同一路径上覆盖（v1→v6）。这是 Q2 判 PARTIAL_COMPLIANCE 的第三条： "
        "每一版的 blob 都还能取到，但路径当前内容换过。从 v7 起改为**每版一个新文件名**。"),
    "evidence/ord0225/xproc_v1_gate_receipt.py": (
        "本轮我自己抓到并自报的那件：新仪器 PUT 复用了已发布路径，覆盖了六枚 ORD-0225 收据引用的字节。"),
}
REPLACED_BY = {  # where the *old bytes* now live under a frozen, self-describing name
    "evidence/ord0225/xproc_v1_gate_receipt.py": "evidence/ord0225/xproc_v1_gate_receipt_pre_provenance_0e7bf417.py",
}


def api(path: str, tries: int = 4):
    """Transient TLS resets are routine on this line; a single failed read must not become a
    NOT_RESOLVED claim about history that is in fact there (that is how false absences get made)."""
    last = None
    for k in range(tries):
        req = urllib.request.Request("https://api.github.com" + path)
        for kk, vv in HDRS.items():
            req.add_header(kk, vv)
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return r.status, json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8", "replace")[:200]  # a real 4xx/5xx is not retried
        except Exception as e:  # noqa: BLE001
            last = f"{type(e).__name__}: {e}"
            __import__("time").sleep(2 * (k + 1))
    return "TRANSIENT_AFTER_RETRIES", (last or "")[:200]


def blob_sha(raw: bytes) -> str:
    return hashlib.sha1(b"blob %d\x00" % len(raw) + raw).hexdigest()


def history(path: str) -> list[dict]:
    """Every blob this path has held on the branch, newest first, with the commit that produced it."""
    st, commits = api(f"/repos/{REPO}/commits?path={path}&sha={BRANCH}&per_page=100")
    if not isinstance(commits, list):
        return [{"error": f"commits listing for {path}: {st} {str(commits)[:120]}"}]
    out = []
    for c in commits:
        sha = c["sha"]
        st2, meta = api(f"/repos/{REPO}/contents/{path}?ref={sha}")
        out.append({"commit": sha[:12], "commit_date": (c.get("commit", {}).get("author", {}) or {}).get("date"),
                    "message": (c.get("commit", {}).get("message", "") or "").splitlines()[0][:90],
                    "blob_at_that_commit": meta.get("sha") if isinstance(meta, dict) else f"GET_{st2}"})
    return out


def prove_reachable(full_sha: str) -> dict:
    st, data = api(f"/repos/{REPO}/git/blobs/{full_sha}")
    if not isinstance(data, dict):
        return {"reachable": False, "status": str(st), "detail": str(data)[:120]}
    import base64
    raw = base64.b64decode(data.get("content", "")) if data.get("content") else b""
    back = blob_sha(raw) if raw else None
    return {"reachable": True, "status": 200, "size_reported": data.get("size"),
            "bytes_fetched": len(raw), "sha1_of_fetched_bytes": back,
            "sha_matches": back == full_sha if back else None,
            "note": ("sha1 自己按取回字节重算；不等就说明我拿到的不是那个对象" if back != full_sha else "一致")}


def diff_fields(old_raw: bytes, new_raw: bytes) -> dict:
    try:
        o, n = json.loads(old_raw.decode("utf-8")), json.loads(new_raw.decode("utf-8"))
    except Exception:  # noqa: BLE001  (a .py instrument has no field shape)
        return {"not_applicable": "两份字节不是 JSON（仪器文件），只比摘要与大小"}
    if not isinstance(o, dict) or not isinstance(n, dict):
        return {"not_applicable": "顶层不是对象"}
    d = {"keys_only_in_old": sorted(set(o) - set(n)), "keys_only_in_new": sorted(set(n) - set(o)),
         "top_level_keys_whose_value_changed": sorted(k for k in set(o) & set(n) if o[k] != n[k])}
    # the question Q2 actually asks: is the replacement the SAME scope key, or a different one wearing
    # the same filename? Answered from the two files, not from memory.
    if {"sha", "node", "run_shape"} <= (set(o) | set(n)):
        d["scope_key_same_as_old"] = {k: o.get(k) == n.get(k) for k in ("sha", "tree", "node", "run_shape")}
        d["scope_key_old"] = {k: o.get(k) for k in ("sha", "tree", "node", "run_shape")}
        d["scope_key_new"] = {k: n.get(k) for k in ("sha", "tree", "node", "run_shape")}
        d["verdict_fields"] = {"old": o.get("verdict"), "new": n.get("verdict")}
    return d


def main() -> int:
    entries = []
    for path, prefixes in QUOTED.items():
        hist = history(path)
        local = HERE / Path(path).name
        cur_raw = local.read_bytes() if local.exists() else b""
        found = []
        for pre in prefixes:
            hit = next((h for h in hist if str(h.get("blob_at_that_commit", "")).startswith(pre)), None)
            if not hit:
                found.append({"quoted_prefix": pre, "resolved": None,
                              "error": "该路径的提交历史里找不到这个前缀 ⇒ 不编造，报 NOT_RESOLVED"})
                continue
            full = hit["blob_at_that_commit"]
            proof = prove_reachable(full)
            old_raw = b""
            if proof.get("reachable") and proof.get("bytes_fetched"):
                import base64
                st3, data3 = api(f"/repos/{REPO}/git/blobs/{full}")
                if isinstance(data3, dict) and data3.get("content"):
                    old_raw = base64.b64decode(data3["content"])
            found.append({"quoted_prefix": pre, "resolved_full_sha1": full, "commit": hit["commit"],
                          "commit_date": hit["commit_date"], "commit_message": hit["message"],
                          "old_bytes": len(old_raw), "reachability": proof,
                          "diff_vs_current_published_bytes": diff_fields(old_raw, cur_raw) if old_raw else None,
                          "restored_under_a_frozen_name": REPLACED_BY.get(path)})
        entries.append({
            "published_path": path,
            "reason_for_the_replacement": REASONS[path],
            "scope": {"arm": Path(path).name,
                      "target_nodeid_or_stamp": (
                          "evidence 分级戳（不是收据）" if "TIER_STAMP" in path else
                          "instrument（不是收据）" if path.endswith(".py") else
                          "closure door: backend/tests/test_qoder_g3_xproc_http.py::"
                          "test_g3_xproc_two_uvicorn_workers_over_http_share_one_operation, single-node")},
            "history_on_the_branch_newest_first": hist,
            "quoted_old_blobs": found,
            "current_content_at_that_path": {"local_bytes": len(cur_raw),
                                             "local_git_blob_sha1": blob_sha(cur_raw) if cur_raw else None},
            "supersession_relation": ("supersedes(旧 blob 仍可寻址，路径当前内容 = 新版本；"
                                      "旧号未消失，只是不再是该路径的当前内容)"),
        })
    out = {
        "kind": "CNX_RECEIPT_LINEAGE_V1",
        "issued_for": "Q2 = PARTIAL_COMPLIANCE（history preserved YES / same published path unchanged NO）",
        "arbitration_source": "arbiter 13:32 与 15:14；commander 转达（总线 5789505851 = Q2 递仲裁那一贴）",
        "session": "8c66aa92",
        "generated_at_local_clock": __import__("datetime").datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M%z"),
        "how_the_old_numbers_were_recovered": (
            "消息里给我的 16 位前缀不直接采信：先用 GET /commits?path=<p>&sha=commander/control 列出该路径在"
            "分支上的每次提交，再对每个提交 GET /contents/<p>?ref=<commit> 读出**当时**那枚 blob 的全 40 位，"
            "与前缀对上后去 GET /git/blobs/<full> 取回字节并重算 sha1。取不到就写 NOT_RESOLVED，不补全。"),
        "entries": entries,
        "additive_files_this_round": {
            "note": "以下新文件**不替换**任何旧内容：旧路径与旧 blob 原样在位。",
            "files": [
                {"file": "evidence/ord0224_a2/v1_receipt_Y3_http_2ab69f2_aggregated.json",
                 "derived_from": "evidence/ord0224_a2/v1_receipt_Y3_http_2ab69f2.json",
                 "source_blob": blob_sha((HERE / "v1_receipt_Y3_http_2ab69f2.json").read_bytes()),
                 "source_blob_quoted_by_verifier": "89b698678fb67538a3efaa9ccca35cd9ff731f05",
                 "why": "仲裁 §Minimal repair：顶层 restore 从 10 轮 per-run 机械聚合"},
                {"file": "evidence/ord0224_a2/v1_receipt_Y2_http_2ab69f2_aggregated.json",
                 "derived_from": "evidence/ord0224_a2/v1_receipt_Y2_http_2ab69f2.json",
                 "source_blob": blob_sha((HERE / "v1_receipt_Y2_http_2ab69f2.json").read_bytes()),
                 "source_blob_quoted_by_verifier": "5612cd30cd7944a5ed81c4ba92ff1c27994f4ea1",
                 "why": "同上"},
                {"file": "evidence/ord0225/v1_gate_receipt_Y123_a_21f1e8d_v2.json",
                 "derived_from": "evidence/ord0225/v1_gate_receipt_Y123_a_21f1e8d.json",
                 "source_blob": blob_sha((HERE / "v1_gate_receipt_Y123_a_21f1e8d.json").read_bytes()),
                 "why": "红队 16:39（总线 5791721578）：carriers_removed=4 ⇒ claimed_result 从 KILLED "
                        "改 MULTI_CARRIER_CUTSET_KILLED；顺带补顶层 restore"},
                {"file": "evidence/ord0225/v1_gate_receipt_Y123_b_21f1e8d_v2.json",
                 "derived_from": "evidence/ord0225/v1_gate_receipt_Y123_b_21f1e8d.json",
                 "source_blob": blob_sha((HERE / "v1_gate_receipt_Y123_b_21f1e8d.json").read_bytes()),
                 "why": "同上"},
            ],
        },
        "go_forward_rule": ("已发布路径冻结：任何改版一律新文件名（`..._v2.json` / `..._aggregated.json` / "
                            "戳按版本 `..._v7.json`）。这条也解释了为什么本版分级戳本身走新路径。"),
    }
    for f in out["additive_files_this_round"]["files"]:
        if not (HERE / Path(f["derived_from"]).name).exists():
            raise SystemExit(f"lineage cites a missing source: {f['derived_from']}")
        if blob_sha((HERE / Path(f["derived_from"]).name).read_bytes()) != f["source_blob"]:
            raise SystemExit(f"source blob drift for {f['derived_from']}")
        q = f.get("source_blob_quoted_by_verifier")
        if q and q != f["source_blob"]:
            raise SystemExit(f"the verifier quoted {q} but disk holds {f['source_blob']} - not the same file")
    # fail-closed: never emit a lineage file that asserts something unmeasured
    proved = 0
    for e in entries:
        for f in e["quoted_old_blobs"]:
            full = f.get("resolved_full_sha1")
            if not full:
                raise SystemExit(f"{e['published_path']}: quoted prefix {f['quoted_prefix']} did not resolve "
                                 "- refusing to publish a lineage with a hole in it")
            r = f["reachability"]
            if not r.get("reachable") or r.get("sha_matches") is not True:
                raise SystemExit(f"{full[:16]}: not proven reachable+sha-equal ({str(r)[:120]})")
            proved += 1
    text = json.dumps(out, ensure_ascii=False, indent=2)
    if "\r" in text:
        raise SystemExit("CRLF in a published artifact")
    target = HERE / "ord0224_a2_RECEIPT_LINEAGE.json"
    if target.exists():
        raise SystemExit("lineage file exists - refusing to overwrite a published path")
    target.write_text(text, encoding="utf-8", newline="\n")
    for e in entries:
        got = [(f["quoted_prefix"], (f.get("resolved_full_sha1") or "NOT_RESOLVED")[:12],
                f["reachability"].get("sha_matches"))
               for f in e["quoted_old_blobs"]]
        print(f"{e['published_path']}\n    history {len(e['history_on_the_branch_newest_first'])} commits | "
              f"quoted {got}\n    current {e['current_content_at_that_path']['local_git_blob_sha1'][:16] if e['current_content_at_that_path']['local_git_blob_sha1'] else '-'}")
    print(f"-> {target.name} {target.stat().st_size:,} B blob {blob_sha(target.read_bytes())}")
    print(f"    old blobs resolved + re-hashed + proven reachable: {proved}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
