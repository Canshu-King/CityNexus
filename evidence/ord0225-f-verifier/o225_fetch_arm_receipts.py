"""取回 C 为 ORD-0225 发布的 8 件（只读 GET），逐件满 40 位回读，失败的具名记 NOT_FETCHED。

坐标来自总线 5790201618；`commander/control` 是 **CityNexus** 的分支（不是总线 Workspace 仓）。
"""
import base64
import json
import pathlib
import sys
import time
import urllib.error
import urllib.request

TOK = pathlib.Path("D:/moodle/_qoder_recovery_20260919/.api_tok_20260920").read_text(encoding="utf-8").strip()
OWNER_REPO = "Canshu-King/CityNexus"
BRANCH = "commander/control"
PREFIX = "evidence/ord0225"
OUT = pathlib.Path("D:/moodle/_qoder_f_run/o225_receipts/ord0225_c")
WANT = {  # 总线 5790201618 里 C 自报的 16 位前缀；我核的是满 40 位
    "v1_gate_receipt_Y23_a_21f1e8d.json": "e0dddec96528b306",
    "v1_gate_receipt_Y23_b_21f1e8d.json": "4152e46ecf5ba769",
    "v1_gate_receipt_Y23_c_21f1e8d.json": "583db798a14d569c",
    "v1_gate_receipt_Y123_a_21f1e8d.json": "7fecbb9189a655e9",
    "v1_gate_receipt_Y123_b_21f1e8d.json": "048d82c166aa61f6",
    "v1_gate_receipt_Y23_OFF_A1_a_21f1e8d.json": "f5771b270e3095ab",
    "v1_gate_receipt_Y23_OFF_A2_a_21f1e8d.json": "fd29667d8a03d1f2",
    "ord0225_arm_repeats_21f1e8d.json": "9a951605f09bece6",
}


def gh(path: str, tries: int = 4):
    last = ""
    for i in range(tries):
        try:
            r = urllib.request.Request("https://api.github.com" + path)
            r.add_header("Authorization", "Bearer " + TOK)
            r.add_header("User-Agent", "citynexus-lane-f")
            with urllib.request.urlopen(r, timeout=150) as x:
                return json.loads(x.read().decode("utf-8", "replace"))
        except urllib.error.HTTPError as e:
            return {"_http": e.code}
        except Exception as e:  # noqa: BLE001
            last = type(e).__name__
            time.sleep(1.5 * (i + 1))
    return {"_err": last}


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    rows, bad = [], 0
    for name, want16 in WANT.items():
        j = gh(f"/repos/{OWNER_REPO}/contents/{PREFIX}/{name}?ref={BRANCH}")
        if "_http" in j or "_err" in j:
            rows.append({"file": name, "status": f"NOT_FETCHED({j.get('_http') or j.get('_err')})"})
            bad += 1
            continue
        meta = j
        data = b""
        if meta.get("content"):
            data = base64.b64decode(meta["content"])
        elif meta.get("size", 0) > 900_000:
            b = gh(meta["git_url"].replace("https://api.github.com", ""))
            data = base64.b64decode(b.get("content", "")) if b.get("content") else b""
        import hashlib
        full = hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()
        ok = full == meta.get("sha") and full.startswith(want16)
        (OUT / name).write_bytes(data) if ok else None
        rows.append({"file": name, "status": "MATCH" if ok else "MISMATCH",
                     "remote_sha1": meta.get("sha"), "claimed16": want16,
                     "recomputed_sha1": full, "bytes": len(data)})
        if not ok:
            bad += 1
    for r in rows:
        print(f"{r['file']:44} {r['status']:12} {str(r.get('remote_sha1'))[:16]} "
              f"bytes={r.get('bytes','-')}")
    print(f"\n⇒ {len(WANT) - bad}/{len(WANT)} 件取回且满 40 位自证相等；{bad} 件不可用")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
