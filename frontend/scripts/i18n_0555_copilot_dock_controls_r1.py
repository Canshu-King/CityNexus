"""Two controls for the ORD-0555 delivery.

1. Negative control: corrupt one dictionary value my arm guards, run the arm, require a
   non-zero exit naming that key, then restore byte-for-byte and re-run for green.
2. Provenance control: run the repo's own shipped parity gate against the BASE tip's
   LocaleContext in a scratch tree, so "that gate is red" is measured as pre-existing
   rather than asserted.
"""
import hashlib
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TREE = os.path.dirname(ROOT)
DICT = os.path.join(ROOT, "frontend", "src", "i18n", "LocaleContext.tsx")
ARM = os.path.join(ROOT, "frontend", "scripts", "i18n_0555_copilot_dock_arm_r1.py")
SHIPPED = os.path.join(ROOT, "frontend", "scripts", "i18n_detail_parity_r1.py")
EVIDENCE = json.load(open(os.path.join(ROOT, "frontend", "scripts",
                                       "i18n_0555_copilot_dock_move_evidence_r1.json"),
                          encoding="utf-8"))
TIP = EVIDENCE["base_tip"]
STOPPING = [r for r in EVIDENCE["items"] if r["key"] == "agent.stopping"][0]
SALTED = '  "agent.stopping": "%s",\n' % STOPPING["en"]
CORRUPT = '  "agent.stopping": "%s ",\n' % STOPPING["en"]
OUT = os.path.join(ROOT, "frontend", "scripts", "i18n_0555_copilot_dock_controls_r1.json")


def run(cmd, cwd=None):
    p = subprocess.run(cmd, cwd=cwd, capture_output=True)
    return p.returncode, (p.stdout.decode("utf-8", "replace") + p.stderr.decode("utf-8", "replace")).strip()


report = {}

original = open(DICT, encoding="utf-8").read()
base_sha = hashlib.sha256(original.encode("utf-8")).hexdigest()
if original.count(SALTED) != 1:
    sys.stdout.write("ABORT control setup: salted line count=%d\n" % original.count(SALTED))
    sys.exit(3)

open(DICT, "w", encoding="utf-8", newline="\n").write(original.replace(SALTED, CORRUPT, 1))
rc_bad, out_bad = run([sys.executable, ARM])
report["negative_control"] = {
    "arm_rc_with_one_char_added_to_agent_stopping": rc_bad,
    "arm_first_fail_line": [l for l in out_bad.split("\n") if l.startswith("FAIL")][:1],
}
open(DICT, "w", encoding="utf-8", newline="\n").write(original)
after_sha = hashlib.sha256(open(DICT, encoding="utf-8").read().encode("utf-8")).hexdigest()
rc_good, out_good = run([sys.executable, ARM])
report["negative_control"]["restored_sha_equal"] = after_sha == base_sha
report["negative_control"]["arm_rc_after_restore"] = rc_good
report["negative_control"]["arm_tail_after_restore"] = out_good.split("\n")[-1]

scratch = os.path.join(TREE, "_qoder_jianpanggong_0555_basegate")
for d in (os.path.join(scratch, "frontend", "scripts"), os.path.join(scratch, "frontend", "src", "i18n")):
    os.makedirs(d, exist_ok=True)
base_text = subprocess.run(["git", "-C", ROOT, "show", "%s:frontend/src/i18n/LocaleContext.tsx" % TIP],
                          capture_output=True).stdout
open(os.path.join(scratch, "frontend", "src", "i18n", "LocaleContext.tsx"), "wb").write(base_text)
subprocess.run(["cp", SHIPPED, os.path.join(scratch, "frontend", "scripts", "i18n_detail_parity_r1.py")],
               capture_output=True)
rc_ship_on_base, out_ship_on_base = run([sys.executable, os.path.join(
    scratch, "frontend", "scripts", "i18n_detail_parity_r1.py")])
rc_ship_on_mine, out_ship_on_mine = run([sys.executable, SHIPPED])
report["provenance_control"] = {
    "shipped_gate_rc_on_base_tip": rc_ship_on_base,
    "shipped_gate_last_line_on_base_tip": out_ship_on_base.split("\n")[-1],
    "shipped_gate_rc_on_my_tree": rc_ship_on_mine,
    "shipped_gate_last_line_on_my_tree": out_ship_on_mine.split("\n")[-1],
    "identical_failure": out_ship_on_base.split("\n")[-1] == out_ship_on_mine.split("\n")[-1],
}

json.dump(report, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
sys.stdout.write(json.dumps(report, ensure_ascii=False, indent=1) + "\n")
sys.exit(0 if (rc_bad != 0 and rc_good == 0 and after_sha == base_sha) else 1)
