"""Read back the branch and assert the one thing Q2 was about: nothing previously published moved.

Two tables, both checked against `GET /contents/<path>?ref=commander/control`:

* `MUST_BE_UNCHANGED` - every path+blob the arbiter or lane F already derived from. If any of these
  reads back different, this round broke the ruling and the script exits non-zero.
* `NEW_THIS_ROUND` - the additive files, each asserted to exist with the digest computed locally.

A 401/404/SSL hiccup is reported as UNPROVEN, never as a mismatch (that distinction has bitten this
lane before), and the exit code separates "proven equal" from "could not look".
"""
from __future__ import annotations

import hashlib
import json
import urllib.error
import urllib.request
from pathlib import Path

TOK = open(r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920", encoding="utf-8").read().strip()
H = {"Authorization": f"Bearer {TOK}", "Accept": "application/vnd.github+json", "User-Agent": "lane-c-readback"}
HERE = Path(__file__).parent
MUST_BE_UNCHANGED = {
    "evidence/ord0224_a2/v1_receipt_Y3_http_2ab69f2.json": "89b698678fb67538a3efaa9ccca35cd9ff731f05",
    "evidence/ord0224_a2/v1_receipt_Y2_http_2ab69f2.json": "5612cd30cd7944a5ed81c4ba92ff1c27994f4ea1",
    "evidence/ord0225/v1_gate_receipt_Y123_a_21f1e8d.json": "7fecbb9189a655e9dd448ed6ec64441cacad0200",
    "evidence/ord0225/v1_gate_receipt_Y123_b_21f1e8d.json": "048d82c166aa61f6f44473dc225fa7d4f36b5511",
    "evidence/ord0224_a2/ord0224_a2_TIER_STAMP.json": "a59af511bf7a3e18f4989ad87693dafcbf8d12d7",
    "evidence/ord0224_a2/mutant_rounds_Y3_http_2ab69f2.json": "091b692280f59944d5686b1afe35ba255d38eed8",
    "evidence/ord0224_a2/mutant_rounds_Y2_http_2ab69f2.json": "49eec1e31a18b375e4cc5b277c60446c67047648",
}
NEW_THIS_ROUND = {
    "evidence/ord0224_a2/v1_receipt_Y3_http_2ab69f2_aggregated.json": "v1_receipt_Y3_http_2ab69f2_aggregated.json",
    "evidence/ord0224_a2/v1_receipt_Y2_http_2ab69f2_aggregated.json": "v1_receipt_Y2_http_2ab69f2_aggregated.json",
    "evidence/ord0225/v1_gate_receipt_Y123_a_21f1e8d_v2.json": "v1_gate_receipt_Y123_a_21f1e8d_v2.json",
    "evidence/ord0225/v1_gate_receipt_Y123_b_21f1e8d_v2.json": "v1_gate_receipt_Y123_b_21f1e8d_v2.json",
    "evidence/ord0224_a2/ord0224_a2_RECEIPT_LINEAGE.json": "ord0224_a2_RECEIPT_LINEAGE.json",
    "evidence/ord0224_a2/aggregate_v1_envelope.py": "aggregate_v1_envelope.py",
    "evidence/ord0224_a2/build_receipt_lineage.py": "build_receipt_lineage.py",
    "evidence/ord0224_a2/ord0224_a2_TIER_STAMP_v7.json": "ord0224_a2_TIER_STAMP_v7.json",
    "evidence/ord0224_a2/bump_tier_stamp_v7.py": "bump_tier_stamp_v7.py",
}


def head(path: str, tries: int = 4):
    import time
    last = None
    for k in range(tries):
        req = urllib.request.Request("https://api.github.com/repos/Canshu-King/CityNexus/contents/"
                                     + path + "?ref=commander/control")
        for a, b in H.items():
            req.add_header(a, b)
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                d = json.loads(r.read().decode())
                return "200", d.get("sha"), d.get("size"), None
        except urllib.error.HTTPError as e:
            return str(e.code), None, None, e.read().decode("utf-8", "replace")[:90]
        except Exception as e:  # noqa: BLE001
            last = f"{type(e).__name__}: {e}"[:90]
            time.sleep(2 * (k + 1))
    return "TRANSIENT", None, None, last


def local_digest(name: str) -> tuple[str, int]:
    raw = (HERE / name).read_bytes()
    return hashlib.sha1(b"blob %d\x00" % len(raw) + raw).hexdigest(), len(raw)


def main() -> int:
    for path, want in MUST_BE_UNCHANGED.items():
        local = HERE / Path(path).name
        if not local.exists():
            raise SystemExit(f"no local copy of {path} to cross-check the expectation against")
        lb, _ = local_digest(Path(path).name)
        if not lb.startswith(want):
            raise SystemExit(f"expectation for {path} is not what the local bytes say: "
                             f"listed {want} vs measured {lb} (never quote a digest you did not read)")
    bad, unproven, ok = [], [], 0
    print("--- 已发布路径必须一字不变 ---")
    for path, want in MUST_BE_UNCHANGED.items():
        st, sha, size, err = head(path)
        verdict = "UNPROVEN" if st != "200" else ("EQUAL" if str(sha).startswith(want) and len(want) == 40
                                                  else ("EQUAL(prefix)" if str(sha).startswith(want) else "CHANGED"))
        if verdict == "CHANGED":
            bad.append(f"{path}: now {sha}, must be {want}")
        elif st != "200":
            unproven.append(f"{path}: GET {st} {err}")
        else:
            ok += 1
        print(f"  {verdict:12s} {path} blob={str(sha)[:16]} size={size}")
    print("--- 本轮新增（每件的本地摘要与远端逐一比） ---")
    for path, name in NEW_THIS_ROUND.items():
        lb, ln = local_digest(name)
        st, sha, size, err = head(path)
        if st != "200":
            unproven.append(f"{path}: GET {st} {err}")
            verdict = "UNPROVEN"
        elif sha == lb and size == ln:
            verdict, ok = "BYTE-LEVEL MATCH", ok + 1
        else:
            verdict = "MISMATCH"
            bad.append(f"{path}: remote {sha}/{size} vs local {lb}/{ln}")
        print(f"  {verdict:17s} {path} blob={str(sha)[:16]} size={size} (local {ln} B)")
    print(json.dumps({"proven": ok, "changed_or_mismatch": bad, "unproven": unproven,
                      "note": "UNPROVEN 只说明这一次没看到，不等于内容错了；CHANGED 才是违约"}, ensure_ascii=False))
    return 4 if bad else (6 if unproven else 0)


if __name__ == "__main__":
    raise SystemExit(main())
