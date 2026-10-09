#!/usr/bin/env python3
"""Publish the 17:1x-17:2x chain-recovery + generation-switch batch through the GIT write path.

Rows are (local file, evidence path).  Nothing here deletes or overwrites a published path (Q57):
every remote path below is new; the 17:18 red preflight is published as-is, because the red is the
instrument's stale HTTPS_PROXY, and that reading is evidence too.
"""
import json
import os
import subprocess
import sys

ROOT = "D:/moodle/_qoder_cmdr_ref_20260921/live_checks"
MIR = os.path.join(ROOT, "cmdr_git_mirror_r1.py")
MSG = "commander 1725: phone chain recovered (4 hops detached), switch to b6a8ea5c gate-green + phone-side readback"

ROWS = [
    ("_preflight_b6a8ea5_1719.json", "evidence/cmdr-chain-recovery-1715/preflight_red_stale_proxy_env_1719.json"),
    ("_preflight_b6a8ea5_1721.json", "evidence/cmdr-chain-recovery-1715/preflight_ready_to_switch_1721.json"),
    ("receipts/preflight_0926_171938.json", "evidence/cmdr-chain-recovery-1715/preflight_receipt_0926_171938.json"),
    ("_deploy_b6a8ea5_1722.log", "evidence/cmdr-chain-switch-b6a8ea5c-1720/deploy_overall_green_1722.txt"),
    ("_phone_chain_1720.json", "evidence/cmdr-chain-switch-b6a8ea5c-1720/phone_side_probe_1720.json"),
    # Absolute paths: the first pass used "../run/...", which resolves against THIS file's
    # directory, not the preview tree, so 7 rows published nothing and read back MISSING.
    ("D:/moodle/_qoder_preview_20260920/run/preview_db_state_1716.json", "evidence/cmdr-chain-recovery-1715/preview_db_state_1716.json"),
    ("D:/moodle/_qoder_preview_20260920/run/_desk_note_head_1716.txt", "evidence/cmdr-chain-recovery-1715/desk_note_head_1716.txt"),
    ("D:/moodle/_qoder_preview_20260920/run/cmdr_hop1_backend.bat", "evidence/cmdr-chain-recovery-1715/hop1_backend_8693.bat"),
    ("D:/moodle/_qoder_preview_20260920/run/cmdr_hop2_preview.bat", "evidence/cmdr-chain-recovery-1715/hop2_vite_preview_4781.bat"),
    ("D:/moodle/_qoder_preview_20260920/run/cmdr_hop3_proxy.bat", "evidence/cmdr-chain-recovery-1715/hop3_auth_proxy_4782.bat"),
    ("D:/moodle/_qoder_preview_20260920/run/cmdr_hop4_tunnel.bat", "evidence/cmdr-chain-recovery-1715/hop4_cloudflared.bat"),
    ("D:/moodle/_qoder_preview_20260920/run/cmdr_hop1_1710.err.log", "evidence/cmdr-chain-recovery-1715/hop1_boot_log.txt"),
]


def one(local, remote):
    p = os.path.join(ROOT, local.replace("/", os.sep))
    if not os.path.isfile(p):
        return {"local": local, "path": remote, "verdict": "MISSING"}
    r = subprocess.run([sys.executable, MIR, "--file", p,
                        "--repo-path", remote, "--branch", "commander/control",
                        "--message", MSG],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=900)
    out = (r.stdout or "") + (r.stderr or "")
    row = {"local": local, "path": remote, "rc": r.returncode, "tail": out.strip().splitlines()[-2:]}
    for line in out.splitlines():
        line = line.strip()
        if line.startswith("{") and line.endswith("}"):
            try:
                j = json.loads(line)
                row.update({"blob": j.get("readback_blob"), "bytes": j.get("readback_size"),
                            "commit": j.get("pushed_commit"), "byte_equal": j.get("byte_equal")})
            except Exception:
                pass
    row["verdict"] = "OK" if row.get("byte_equal") else ("ALREADY" if r.returncode == 0 else "FAIL")
    print("%-8s %-66s %s" % (row["verdict"], remote, (row.get("blob") or "")[:12]))
    return row


def main():
    rows = [one(a, b) for a, b in ROWS]
    bad = [r for r in rows if r["verdict"] not in ("OK", "ALREADY")]
    print("\nrows=%d ok=%d not-ok=%d" % (len(rows), len(rows) - len(bad), len(bad)))
    json.dump(rows, open(os.path.join(ROOT, "_publish_1725_result.json"), "w", encoding="utf-8"),
              indent=1, ensure_ascii=False)
    for r in bad:
        print("FAIL", r["path"], r.get("tail"))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
