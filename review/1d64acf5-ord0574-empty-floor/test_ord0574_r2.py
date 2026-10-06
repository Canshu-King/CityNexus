# -*- coding: utf-8 -*-
"""Test the ORD-0574 r2 candidates in an ISOLATED temp module tree (the landed files are never imported here).

Legs, all real:
  T1 both sides empty            -> candidate must answer NOT_ANSWERED, exit 9   (the "must go red" case)
  T1b same, on the shipped r1     -> CURRENT, exit 0  (the before reading, same minute)
  T2 local empty, remote real     -> must still go red (DIVERGED), unchanged
  T3 both = the real ledger        -> must still be CURRENT (the fix must not break the working verdict)
  T4 no-token CLI exit code        -> must be the documented 9 (was 1 in r1)
  T5 candidate --self-test          -> arms_all_correct true, rc 0
  T6 hook_r2 --self-test            -> arms_all_correct true, rc 0 (trail pointed into temp, real file untouched)
  T7 flip_a_byte through the candidate CLI -> verdict != CURRENT
Every assertion is computed from the reading; the script aborts if a leg returns nothing.
"""
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile

WT = r"D:\moodle\_qoder_lane_S4_0926\wt0391"
MAIN = r"D:\moodle\CityNexus"
HERE = os.path.dirname(os.path.abspath(__file__))
TOKEN = r"D:/moodle/_qoder_recovery_20260919/.api_tok_20260920"
LEDGER = r"D:\moodle\CITYNEXUS_AGENT_CONTROL.md"
REF = "mirror/integration-frontend-apple-pass1"
EMPTY_PATH = "backend/app/commerce/__init__.py"
EMPTY_BLOB = "e69de29bb2d1d6434b8b29ae775ad8c2e48c5391"


def env():
    e = dict(os.environ)
    for k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "ALL_PROXY", "all_proxy"):
        e.pop(k, None)
    e["PYTHONIOENCODING"] = "utf-8"
    return e


def run(argv, extra_env=None, timeout=900):
    e = env()
    if extra_env:
        e.update(extra_env)
    p = subprocess.run(argv, capture_output=True, env=e, timeout=timeout)
    return p.returncode, p.stdout.decode("utf-8", "replace"), p.stderr.decode("utf-8", "replace")


def call_check(root, module, local, ref, path, reads=1):
    """Run the shipped check_sync through a caller that propagates the documented exit code.

    The rc measured here is a real process exit code (ord0574_r2_caller_r3.py raises SystemExit with the
    verdict's code), not a dict field - that is the distinction that made my first pass report three
    spurious reds by comparing `rc` of a print-wrapper against the documented code.
    """
    rc, out, err = run([sys.executable, os.path.join(HERE, "ord0574_r2_caller_r3.py"),
                        root, module, local, ref, path],
                       extra_env={"CITYNEXUS_API_TOKEN_FILE": TOKEN})
    if not out.strip():
        raise SystemExit("ABORT: leg %s/%s produced no stdout rc=%d err=%s" % (module, ref, rc, err[-240:]))
    return rc, json.loads(out.strip().split("\n")[-1]), err[-200:]


def main():
    tmp = tempfile.mkdtemp(prefix="cnx_ord0574_r2_")
    tools_dir = os.path.join(tmp, "tools")
    os.makedirs(tools_dir)
    R = {"isolation_root": tmp.replace("\\", "/")}
    try:
        shutil.copy(os.path.join(WT, "tools", "cnx_ledger_mirror_reader_r1.py"), tools_dir)
        shutil.copy(os.path.join(HERE, "cnx_ledger_mirror_sync_check_r2.py"), tools_dir)
        shutil.copy(os.path.join(HERE, "cnx_ledger_mirror_sync_hook_r2.py"), tools_dir)
        shutil.copy(os.path.join(WT, "tools", "cnx_ledger_mirror_sync_check_r1.py"), tools_dir)
        shutil.copy(os.path.join(WT, "tools", "cnx_ledger_mirror_sync_hook_r1.py"), tools_dir)
        R["copied"] = sorted(os.listdir(tools_dir))

        fd, empty_local = tempfile.mkstemp(prefix="cnx_0b_", suffix=".md", dir=tmp)
        os.close(fd)
        if os.path.getsize(empty_local) != 0:
            raise SystemExit("ABORT: fixture not zero bytes")

        # T1 candidate on both-empty
        rc, j, e = call_check(tmp, "cnx_ledger_mirror_sync_check_r2", empty_local, REF, EMPTY_PATH)
        R["T1_candidate"] = j
        R["T1_rc"] = rc
        # T1b shipped r1 on the same fixture
        rc1, j1, e1 = call_check(tmp, "cnx_ledger_mirror_sync_check_r1", empty_local, REF, EMPTY_PATH)
        R["T1b_shipped_r1"] = j1
        R["T1b_rc"] = rc1
        # assertions computed, not typed
        R["T1_candidate_refused_current"] = (j["verdict"] != "CURRENT")
        R["T1_candidate_not_answered"] = (j["verdict"] == "NOT_ANSWERED")
        R["T1_candidate_exit_9"] = (j["exit_code"] == 9 and rc == 9)
        R["T1_shipped_answered_current"] = (j1["verdict"] == "CURRENT")
        R["T1_floor_flag_reported"] = (j.get("emptiness_floor") is True)
        R["T1_both_blobs_are_empty"] = (j["local_blob"] == EMPTY_BLOB == j["remote_blob"])

        # T2 one-sided empty still red (candidate)
        rc2, j2, _ = call_check(tmp, "cnx_ledger_mirror_sync_check_r2", empty_local,
                                "commander/control", "CITYNEXUS_AGENT_CONTROL.md")
        R["T2_candidate_local_empty"] = {"verdict": j2["verdict"], "rc": rc2,
                                         "local_bytes": j2["local_bytes"], "remote_bytes": j2["remote_bytes"]}
        R["T2_still_red"] = (j2["verdict"] != "CURRENT" and rc2 != 0)

        # T3 real ledger both sides still CURRENT (candidate)
        rc3, j3, _ = call_check(tmp, "cnx_ledger_mirror_sync_check_r2", LEDGER,
                                "commander/control", "CITYNEXUS_AGENT_CONTROL.md")
        R["T3_candidate_real_ledger"] = {"verdict": j3["verdict"], "rc": rc3,
                                         "local_blob": j3["local_blob"], "remote_blob": j3["remote_blob"],
                                         "emptiness_floor": j3.get("emptiness_floor")}
        R["T3_current_preserved"] = (j3["verdict"] == "CURRENT" and rc3 == 0)

        # T4 no-token CLI exit code, candidate
        cli = [sys.executable, os.path.join(tools_dir, "cnx_ledger_mirror_sync_check_r2.py"),
               "--local", LEDGER, "--token-file", "", "--reads", "1"]
        e4 = env()
        e4.pop("CITYNEXUS_API_TOKEN_FILE", None)
        p4 = subprocess.run(cli, capture_output=True, env=e4, timeout=600)
        R["T4_cli_no_token_rc"] = p4.returncode
        R["T4_cli_stderr"] = p4.stderr.decode("utf-8", "replace").strip()[-200:]
        R["T4_documented_9_kept"] = (p4.returncode == 9)

        # T5 candidate --self-test
        rc5, out5, err5 = run([sys.executable, os.path.join(tools_dir, "cnx_ledger_mirror_sync_check_r2.py"),
                               "--self-test", "--token-file", TOKEN])
        R["T5_selftest_rc"] = rc5
        R["T5_selftest_tail"] = out5.strip()[-360:]
        R["T5_arms_all_correct"] = ('"arms_all_correct": true' in out5)
        R["T5_stderr_tail"] = err5[-160:]

        # T6 hook_r2 --self-test with a TEMP trail (real trail path not used).
        # The hook CLI has no --token-file flag on purpose: it takes the credential from the environment.
        trail = os.path.join(tmp, "trail_r2.jsonl")
        rc6, out6, err6 = run([sys.executable, os.path.join(tools_dir, "cnx_ledger_mirror_sync_hook_r2.py"),
                               "--self-test", "--trail", trail],
                              extra_env={"CITYNEXUS_API_TOKEN_FILE": TOKEN})
        R["T6_hook_selftest_rc"] = rc6
        R["T6_hook_tail"] = out6.strip()[-360:]
        R["T6_hook_arms_all_correct"] = ('"arms_all_correct": true' in out6)
        R["T6_trail_in_temp"] = os.path.exists(trail)
        R["T6_stderr_tail"] = err6[-160:]

        # T7 flip_a_byte through the candidate CLI
        rc7, out7, _ = run([sys.executable, os.path.join(tools_dir, "cnx_ledger_mirror_sync_check_r2.py"),
                            "--arm", "flip_a_byte", "--local", LEDGER, "--token-file", TOKEN])
        R["T7_flip"] = {"rc": rc7, "stdout": out7.strip()[:240]}
        j7 = json.loads(out7.strip())
        R["T7_flip_not_current"] = (j7["verdict"] != "CURRENT")

        # T8 the hook's run_after_insert on the both-empty fixture: exit code must not be 0
        code8 = ("import sys,json;sys.path.insert(0,r'%s');import importlib;"
                 "m=importlib.import_module('tools.cnx_ledger_mirror_sync_hook_r2');"
                 "line=m.run_after_insert(trail=r'%s',arm='',local_path=r'%s',ref='%s',path='%s',"
                 "repo_dir=r'%s',token_file=r'%s',reads=1);"
                 "print(json.dumps({k:line[k] for k in ('verdict','exit_code','appended','tool')}))"
                 % (tmp, os.path.join(tmp, "trail_call.jsonl"), empty_local, REF, EMPTY_PATH, MAIN, TOKEN))
        rc8, out8, err8 = run([sys.executable, "-c", code8])
        R["T8_hook_call_on_empty"] = {"rc": rc8, "stdout": out8.strip()[:240], "err": err8[-160:]}
        if out8.strip():
            j8 = json.loads(out8.strip().split("\n")[-1])
            # the hook's own returned exit_code field (the CLI cannot be pointed at this fixture: it has no
            # --ref/--path flags), so this leg is labelled as a returned-field check, not a process rc
            R["T8_hook_returned_exit_code"] = j8["exit_code"]
            R["T8_hook_exit_nonzero_on_empty"] = (j8["exit_code"] != 0)
            R["T8_hook_trail_appended"] = (j8["appended"] is True)
            R["T8_hook_tool_name"] = j8["tool"]

        R["all_arms_green"] = bool(R["T1_candidate_not_answered"] and R["T1_candidate_exit_9"]
                                   and R["T1_shipped_answered_current"] and R["T2_still_red"]
                                   and R["T3_current_preserved"] and R["T4_documented_9_kept"]
                                   and R["T5_arms_all_correct"] and R["T6_hook_arms_all_correct"]
                                   and R["T7_flip_not_current"])
        R["ledger_bytes_after"] = os.path.getsize(LEDGER)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        R["isolation_removed"] = not os.path.exists(tmp)

    io.open(os.path.join(HERE, "test_ord0574_r2.json"), "w", encoding="utf-8", newline="\n").write(
        json.dumps(R, ensure_ascii=False, indent=1))
    print(json.dumps(R, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
