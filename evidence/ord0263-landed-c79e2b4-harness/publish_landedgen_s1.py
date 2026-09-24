"""ORD-0263 landed-generation close-out, segment 1: ship the pre-reboot originals before doing anything else.

The box blue-screened between 02:2x and 02:3x and cut both my face and my instrument processes. Two of the five
readings I had already taken on the landed bundle exist only as dialog text plus these files, so the first act
after the reboot is to publish the surviving originals (surface receipt, the two never-closing origin side logs,
the junk-200 log, the face launcher) rather than to continue measuring.

Nothing here is re-derived or "reconstructed from memory": these are the byte files that were on disk, and each
row's verdict comes from its own GET read-back. The note records which readings the reboot interrupted, so the
later seven-cell table can be read as a fresh post-reboot pass with this one as its predecessor rather than as a
silently merged mixture of the two.
"""
from __future__ import annotations

import base64
import hashlib
import importlib.util
import json
import subprocess
import sys
import time
from pathlib import Path

BASE = Path(r"D:\moodle\_qoder_harness_ord0254")
PUBLISHER = Path(r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks\publish_evidence.py")
API, BRANCH = "Canshu-King/CityNexus", "commander/control"
REPO_DIR = "evidence/ord0263-landed-c79e2b4-harness"
OUT = BASE / "ord0263_landedgen_segment1_index.json"
MSG = ("ORD-0263 HARNESS d291c9dc: segment 1 - pre-reboot originals on the landed generation c79e2b4 "
       "(face receipt, never-closing origin side logs, junk-200 log, launcher)")

FILES = ["ord0263_landedgen_reboot_note.md",
         "ord0263_close_surface_receipt.json",
         "tools/run_disk_face.py",
         "ord0263_origin_state_answered_health.log",
         "ord0263_origin_state_fully_silent.log",
         "ord0263_junk_html.log"]


def blob40(d: bytes) -> str:
    return hashlib.sha1(b"blob %d\x00" % len(d) + d).hexdigest()


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    spec = importlib.util.spec_from_file_location("cmdr_publish", PUBLISHER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    rows = []
    for name in FILES:
        lp = BASE / name
        if not lp.is_file():
            rows.append({"local_file": name, "verdict": "MISSING_LOCAL_FILE"})
            print("  MISSING ", name)
            continue
        data = lp.read_bytes()
        local = blob40(data)
        rp = f"{REPO_DIR}/{Path(name).name}"
        st = subprocess.run([sys.executable, str(PUBLISHER), str(lp), rp, MSG],
                            capture_output=True, text=True, encoding="utf-8", errors="replace")
        out = ((st.stdout or "") + (st.stderr or "")).strip()
        time.sleep(1.5)
        code, meta = mod.call("GET", f"/repos/{API}/contents/{rp}?ref={BRANCH}")
        if code == 200 and isinstance(meta, dict) and meta.get("content"):
            rb = base64.b64decode(meta["content"])
            agree = blob40(rb) == local and len(rb) == len(data)
            rows.append({"local_file": name, "repo_path": rp, "bytes": len(data), "blob40": local,
                         "readback_status": code, "readback_bytes": len(rb),
                         "readback_blob40": blob40(rb),
                         "verdict": "PROVEN" if agree else "BLOB_DIFFERS",
                         "publisher_rc": st.returncode})
            print(f"  {'PROVEN ' if agree else 'DIFFERS'} {Path(name).name:48s} {len(data):>7,} B {local[:16]}")
        else:
            rows.append({"local_file": name, "repo_path": rp, "bytes": len(data), "blob40": local,
                         "readback_status": str(code), "verdict": "PUBLISHED_UNPROVEN",
                         "publisher_rc": st.returncode,
                         "publisher_tail": out.splitlines()[-1][:190] if out else ""})
            print(f"  UNPROVEN {name}: {code} :: {out.splitlines()[-1][:150] if out else ''}")

    ruler = (BASE / "tools/ord0263_verifier_v3.py").read_bytes()
    proven = sum(1 for r in rows if r["verdict"] == "PROVEN")
    idx = {"at": time.strftime("%Y-%m-%dT%H:%M:%S+08:00", time.localtime()),
           "what": "ORD-0263 landed-generation close-out - segment 1: pre-reboot originals",
           "lane": "HARNESS d291c9dc",
           "interruption": {"event": "blue screen + reboot 02:2x-02:3x", "my_face_and_instruments": "all gone",
                            "ports_after_reboot": "4411-4417 and 8411 all free (netstat read after reboot)",
                            "readings_taken_before_the_reboot": ["S1", "S2", "S4", "S3", "S5/200+HTML"],
                            "readings_not_reached_before_the_reboot": ["S5/200+empty", "S5/200+not_json"],
                            "policy_i_adopted": "re-take the whole table on a fresh post-reboot face and "
                                                "report the two passes side by side; nothing from before the "
                                                "reboot is merged silently into the after-the-reboot table"},
           "subject": "landed generation c79e2b4f4efe414dba22a071a7136ae10b5c84aa as served from disk "
                      "(index.html refs only assets/index-ChOTTCvB.js, 1,245,203 B sha256/16 "
                      "2d56a79632efc0c6; v10-sw.js 2,055 B sha256/16 88a7d980b3ffcbd6 which differs from the "
                      "previous generation's e63d7421eda34093, so the re-spin is distinguishable; "
                      "manifest.webmanifest 314 B; the previous bundle index-Cpy_jhEg.js is still on disk "
                      "per DEPLOY_BUNDLE_RETENTION)",
           "ruler_under_test_unchanged_so_far": {"file_bytes": len(ruler),
                                                 "blob40": blob40(ruler),
                                                 "promised": "e9a4188f63e27bbbf8bfed35adfd554b9e8641d9",
                                                 "match": blob40(ruler) ==
                                                     "e9a4188f63e27bbbf8bfed35adfd554b9e8641d9"},
           "commander_contract_for_this_cell": {
               "close_conditions": ["(1) the four earlier cells do not regress on this generation",
                                    "(2) V5 GREEN for all three shapes",
                                    "(3) the raw capture shows, per shape, a dedicated non-catch-all reason - "
                                     "any shape really landing UNKNOWN_FAILURE blocks closing"],
               "self_limiting_sentence_that_must_appear_verbatim_in_my_close_text":
                   "UNKNOWN_FAILURE prohibition = contractually satisfied by direct landed-generation "
                   "observations; v3 has no dedicated UNKNOWN_FAILURE mutation killer; verifier coverage "
                   "debt transferred to instrument maintenance.",
               "ruler_changes_this_round": "none - no v4, no killer added (arbiter 5800456557); the missing "
                                           "mutation killer is recorded as verifier coverage debt, not as a "
                                           "product blocker"},
           "previous_landing_receipt_from_commander":
               "commander/control:evidence/ord0263-landing-c79e2b4/LANDED_RECEIPT_c79e2b4.json "
               "blob 5201a28b2da737e18bda9cba1b7f3653352d3e6a 6,299 B",
           "files_requested": len(FILES), "proven_by_40char_readback": proven,
           "not_proven": [r["local_file"] for r in rows if r["verdict"] != "PROVEN"],
           "old_paths_touched": [], "rows": rows}
    OUT.write_text(json.dumps(idx, ensure_ascii=False, indent=1), "utf-8", newline="\n")
    data = OUT.read_bytes()
    local = blob40(data)
    rp = f"{REPO_DIR}/{OUT.name}"
    subprocess.run([sys.executable, str(PUBLISHER), str(OUT), rp,
                    "ORD-0263 HARNESS d291c9dc: landed-generation segment 1 index"],
                   capture_output=True, text=True, encoding="utf-8", errors="replace")
    time.sleep(1.5)
    code, meta = mod.call("GET", f"/repos/{API}/contents/{rp}?ref={BRANCH}")
    rb = base64.b64decode(meta["content"]) if code == 200 and isinstance(meta, dict) and meta.get("content") else b""
    ok_idx = blob40(rb) == local
    print(f"  {'PROVEN ' if ok_idx else 'UNPROVEN'} {OUT.name} {len(data):,} B {local[:16]}")
    print(f"segment 1: PROVEN {proven}/{len(FILES)} plus the index: {ok_idx}")
    return 0 if proven == len(FILES) and ok_idx else 4


if __name__ == "__main__":
    raise SystemExit(main())
