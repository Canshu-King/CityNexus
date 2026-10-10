"""Build the two-way self-test receipt for the NEW whole-suite collection arm I just bolted onto my own
landing door (`preflight_and_land_r1.py`).

Every verdict below is DERIVED from the two captured readings - no literal "PASS" anywhere, because a
machine-read receipt whose verdicts are typed by hand is not evidence (standing rule: evidence computed,
not literal).  Both readings were produced by the same interpreter, the same export recipe and the same
command line; the only difference is the tree.
"""
import hashlib
import io
import json
import os
import subprocess
import time

HERE = os.path.dirname(os.path.abspath(__file__))
EV = os.path.join(os.path.dirname(HERE), "evidence", "cmdr-patrol-0404")
TOOL = os.path.join(HERE, "preflight_and_land_r1.py")


def blob(raw):
    return hashlib.sha1(b"blob %d\0" % len(raw) + raw).hexdigest()


def read(name):
    return json.load(io.open(os.path.join(EV, name), encoding="utf-8"))


good, bad = read("pf_goodtip.json"), read("pf_badcand.json")
gs, bs = good["gate_run"]["whole_suite"], bad["gate_run"]["whole_suite"]
tool_raw = io.open(TOOL, "rb").read()

arm = {
    "clean_tree": gs,
    "poisoned_tree": bs,
    "same_command": gs["cmd"] == bs["cmd"],
    "same_interpreter": gs["cmd"].startswith("D:/moodle/CityNexus/.venv/Scripts/python.exe"),
    "collected_equal": gs["collected"] == bs["collected"],
}
checks = {
    # the arm must SPEAK on the tree that carries an unimportable test file...
    "arm_refuses_the_poisoned_tree": (bs["collect_exit"] != 0 and bs["interrupted"] is True
                                      and any("ZERO tests" in p for p in bad["problems"])
                                      and any("whole-suite collection exit" in p for p in bad["problems"])),
    # ...and must STAY SILENT on the tree that is already on the line.  `pf_goodtip` is refused, but only for
    # ahead=0 (candidate == tip), which is the pre-existing arm's job; the new arm adds nothing to it.
    "arm_stays_silent_on_the_clean_tree": (gs["collect_exit"] == 0 and gs["interrupted"] is False
                                           and not any("whole-suite" in p for p in good["problems"])),
    "collection_measured_on_both": bool(gs["collected"]) and bool(bs["collected"]),
    "both_arms_ran_the_same_command": arm["same_command"] and arm["same_interpreter"],
    "the_two_trees_differ_only_in_execution": arm["collected_equal"],
}
out = {
    "schema": "CNX_CMDR_LANDING_GATE_SUITE_ARM_SELFTEST_V1",
    "lane": "commander 494abfd7",
    "at_local": time.strftime("%Y-%m-%dT%H:%M:%S+0800"),
    "what_changed": "preflight_and_land_r1.py gained a whole-suite `--collect-only` arm (default on, "
                    "--suite-collect off to silence).  It runs on the FULL-tree export of the candidate, with "
                    "PYTHONPATH set to the export root, and refuses the landing unless collect_exit==0, no "
                    "`Interrupted`, and a non-zero collected count.",
    "why": "A candidate carrying one unimportable test file makes pytest abort during collection of the whole "
           "tree: the named files still report a tidy summary while ZERO of the rest ever ran.  Per-file "
           "collection cannot see that.  Observed on refs/heads/agent/S2-hermes-port-candidates.",
    "tool": {"path": "live_checks/preflight_and_land_r1.py", "blob": blob(tool_raw), "bytes": len(tool_raw),
             "lines": tool_raw.decode("utf-8", "replace").count("\n") + 1},
    "trees": {"clean": good["generations"] if "generations" in good else good.get("tip"),
              "poisoned_ref": "refs/heads/agent/S2-hermes-port-candidates",
              "poisoned": bad["candidate"] if "candidate" in bad else None},
    "arm_readings": arm,
    "derived": checks,
    "claim_kind": "recomputation",
    "raw_receipts": {"pf_goodtip.json": blob(io.open(os.path.join(EV, "pf_goodtip.json"), "rb").read()),
                     "pf_badcand.json": blob(io.open(os.path.join(EV, "pf_badcand.json"), "rb").read())},
}
txt = json.dumps(out, ensure_ascii=False, indent=1)
io.open(os.path.join(HERE, "_suite_arm_selftest_r1.json"), "w", encoding="utf-8", newline="\n").write(txt)
print(json.dumps(out["derived"], ensure_ascii=False, indent=1))
print("tool blob", out["tool"]["blob"], "| collected clean/poisoned",
      gs["collected"], bs["collected"], "| bytes", len(txt.encode("utf-8")))
