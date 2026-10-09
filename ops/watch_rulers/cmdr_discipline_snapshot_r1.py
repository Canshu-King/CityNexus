"""The commander's own discipline snapshot for this patrol - every number is computed, none typed.

Q57=② and EVIDENCE_INTEGRITY_GATE_V1 both point the same way: a claim about my own restraint ("I did not
run demo/reset", "I printed no credential") is only worth anything if someone can recompute it.  So the
counts here come from the tools that actually ran in this hour: their source is scanned for endpoint and
secret-shaped literals, and the landing facts are re-read from git rather than copied from a stdout.
"""
import datetime
import hashlib
import io
import json
import re
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks"
TOOLS = ["post_1758_swap.py", "phone_proxy_selfanswer_r1.py", "cred_env_second_observer_r1.py",
         "publish_evidence_gated_r1.py", "merge_ledger_then_mirror_r1.py", "derive_reparent_prediction_r1.py",
         "post_note_r1.py", "gate_and_clip_r1.py"]
GIT = r"D:\moodle\CityNexus"
TIP_NOW = "13af1ff4ba4516aa1a39cda67428ed4a2a34ac69"
BASE = "5aff3722d5c36c760a424f5fea5c3a771298f9ac"


def git(*a):
    r = subprocess.run(["git"] + list(a), cwd=GIT, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=180)
    return (r.stdout or "").strip()


endpoints, secret_shapes = [], []
for t in TOOLS:
    src = io.open(HERE + "\\" + t, encoding="utf-8", errors="replace").read()
    for m in re.findall(r"(?:/api/v1|/repos|/issues)[A-Za-z0-9_./{}%-]{0,60}", src):
        endpoints.append({"tool": t, "literal": m})
    for pat in (r"ghp_[A-Za-z0-9]{20,}", r"github_pat_[A-Za-z0-9]{20,}", r"Bearer\s+[A-Za-z0-9._-]{20,}"):
        for m in re.findall(pat, src):
            secret_shapes.append({"tool": t, "matched_pattern": pat, "matched_length": len(m)})

listen = {}
ns = subprocess.run(["netstat", "-ano", "-p", "tcp"], capture_output=True, text=True,
                    encoding="utf-8", errors="replace", timeout=120)
for port in ("4781", "4782", "8000"):
    listen[port] = sum(1 for l in (ns.stdout or "").splitlines() if ":" + port in l and "LISTENING" in l.upper())

out = {
    "schema": "CNX_CMDR_DISCIPLINE_SNAPSHOT_V1",
    "at_local": (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=8)).isoformat(timespec="seconds") + "+08",
    "tool_sha1": hashlib.sha1(io.open(__file__, "rb").read()).hexdigest(),
    "landing_re_read_from_git": {
        "tip_now": git("rev-parse", TIP_NOW + "^0"), "matches_landed_value": git("rev-parse", TIP_NOW + "^0") == TIP_NOW,
        "parents": git("rev-list", "--parents", "-n1", TIP_NOW).split()[1:],
        "tree": git("rev-parse", TIP_NOW + "^{tree}"),
        "base_is_ancestor": subprocess.run(["git", "merge-base", "--is-ancestor", BASE, TIP_NOW], cwd=GIT).returncode == 0,
        "path_count_base_to_tip": len([x for x in git("diff", "--name-only", BASE, TIP_NOW).splitlines() if x]),
        "paths": git("diff", "--name-only", BASE, TIP_NOW).splitlines()},
    "endpoints_seen_in_this_hours_tools": {"count": len(endpoints), "rows": endpoints,
                                           "demo_reset_literal_hits": sum(1 for e in endpoints if "demo/reset" in e["literal"])},
    "secret_shaped_literals_in_sources": {"count": len(secret_shapes), "rows": secret_shapes[:5]},
    "listen_rows": listen,
    "how_to_recompute": ["python " + __file__.split("\\")[-1],
                         "git -C " + GIT + " rev-parse " + TIP_NOW + "^{tree}",
                         "git -C " + GIT + " merge-base --is-ancestor " + BASE + " " + TIP_NOW,
                         "git -C " + GIT + " diff --name-only " + BASE + " " + TIP_NOW,
                         "netstat -ano -p tcp"],
    "scope": "Restraint claims about my own hour. It does not certify any lane's work and is not a "
             "landing: the landing it records was read back from git inside this run.",
    "self_reported_process_error": "At 18:52 I ran the chain as `gate ; insert ; mirror` instead of gating "
            "first, so a block carrying one uncited count reached the ledger while the ruler was RED. The door "
            "is now bolted: ledger_insert_after.py runs the Q43 gate itself and refuses to write unless the "
            "block passes, with an explicit --allow-ungated escape that I have not used."}
io.open(HERE + "\\_cmdr_discipline_snapshot_1853.json", "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=1))
print("landing tip", out["landing_re_read_from_git"]["tip_now"][:12],
      "| base ancestor", out["landing_re_read_from_git"]["base_is_ancestor"],
      "| paths", out["landing_re_read_from_git"]["path_count_base_to_tip"])
print("endpoints scanned", out["endpoints_seen_in_this_hours_tools"]["count"],
      "| demo/reset literal hits", out["endpoints_seen_in_this_hours_tools"]["demo_reset_literal_hits"],
      "| secret-shaped hits", out["secret_shaped_literals_in_sources"]["count"])
print("listen", out["listen_rows"], "| tool sha1", out["tool_sha1"])
