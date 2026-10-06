# -*- coding: utf-8 -*-
"""Self-declared next item: the "empty input must be non-zero" floor, measured on the entries this generation
still runs - one row per entry, real run each, no replica and no editing of the entry under test.

Declared denominator and why each is in it (everything else in the work dir is a one-shot generator that ran
once and is not re-run, so an empty-input floor on it would protect nothing):
  E1 tools/cnx_ledger_mirror_sync_check_r1.py  shipping; the cadence runs it. Empty input = a 0-byte local file.
  E2 tools/cnx_ledger_mirror_reader_r1.py      shipping; both the check and the hook read through it.
                                               Empty input = a path that does not exist on the ref.
  E3 anchor_drift_survey_r3.py                 the named survey; it takes a tip as argv[1].
                                               Empty input = the empty tree sha (a real tree with no entries).
  E4 empty_denominator_scan_r2.py              my scanner; it reports its own empty-root case in-band.
  E5 tools/cnx_ledger_mirror_sync_hook_r1.py   shipping; the inserter calls it once per applied block.
                                               Empty input = the 0-byte local file, through its own function.
  E6 empty_leg_reachability_r3.py              the write-leg audit ruler.
                                               NOT FEEDABLE without editing: it always scans its own directory,
                                               so an empty directory cannot be handed to it. Its floor is quoted
                                               from source and marked as unmeasured rather than counted as green.

Nothing here writes the ledger, a published artifact, or a ref; every entry that produces an output file is
copied into a temp directory first, and the survey is given a tip so it does not touch the network.
"""
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
WT = r"D:\moodle\_qoder_lane_S4_0926\wt0391"
TOOLS = os.path.join(WT, "tools")
TOKEN = r"D:/moodle/_qoder_recovery_20260919/.api_tok_20260920"
LEDGER = r"D:\moodle\CITYNEXUS_AGENT_CONTROL.md"
EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
REF = "mirror/integration-frontend-apple-pass1"


def env(extra=None):
    e = dict(os.environ)
    for k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "ALL_PROXY", "all_proxy"):
        e.pop(k, None)
    e["PYTHONIOENCODING"] = "utf-8"
    if extra:
        e.update(extra)
    return e


def run(argv, cwd=None, extra_env=None, timeout=900):
    p = subprocess.run(argv, capture_output=True, env=env(extra_env), cwd=cwd, timeout=timeout)
    return p.returncode, p.stdout.decode("utf-8", "replace"), p.stderr.decode("utf-8", "replace")


def main():
    R = {"declared_denominator": 6}
    tmp = tempfile.mkdtemp(prefix="cnx_floor_probe_")
    fd, empty_local = tempfile.mkstemp(prefix="cnx_0b_", suffix=".md", dir=tmp)
    os.close(fd)
    if os.path.getsize(empty_local) != 0:
        raise SystemExit("ABORT: fixture not zero bytes")
    rows = []
    try:
        # E1 shipping check, 0-byte local against the real remote
        rc, out, err = run([sys.executable, os.path.join(TOOLS, "cnx_ledger_mirror_sync_check_r1.py"),
                            "--local", empty_local, "--token-file", TOKEN, "--reads", "1"])
        v = re.search(r'"verdict":\s*"([A-Z_]+)"', out)
        rows.append({"id": "E1", "entry": "tools/cnx_ledger_mirror_sync_check_r1.py",
                     "empty_input": "0-byte local file, real remote", "rc": rc,
                     "verdict": v.group(1) if v else None,
                     "refused_empty": rc != 0, "how": "CLI"})
        # E2 shipping reader, a path that does not exist on the ref
        code = ("import sys,json;sys.path.insert(0,r'%s');"
                "from tools.cnx_ledger_mirror_reader_r1 import read_remote_ledger, IncompleteRemoteRead;"
                "import os;os.environ['CITYNEXUS_API_TOKEN_FILE']=r'%s';"
                "r=read_remote_ledger(ref='%s',path='no/such/path/here.md',token_file=r'%s');"
                "print('READ', r.get('blob_id'), r.get('bytes'))"
                % (WT, TOKEN, REF, TOKEN))
        rc, out, err = run([sys.executable, "-c", code])
        leg = re.search(r"IncompleteRemoteRead: (\w+):", err)
        rows.append({"id": "E2", "entry": "tools/cnx_ledger_mirror_reader_r1.py",
                     "empty_input": "path that does not exist on the ref", "rc": rc,
                     "refusal_leg": leg.group(1) if leg else None,
                     "refused_empty": rc != 0, "how": "function call"})
        # E3 the named survey, empty tree as the tip (no network, real run)
        survey = os.path.join(HERE, "anchor_drift_survey_r3.py")
        shutil.copy(survey, tmp)
        rc, out, err = run([sys.executable, os.path.join(tmp, "anchor_drift_survey_r3.py"), EMPTY_TREE], cwd=tmp)
        files = re.search(r"files[^0-9]{0,6}(\d+)", out)
        rows.append({"id": "E3", "entry": "anchor_drift_survey_r3.py",
                     "empty_input": "empty tree sha as the tip", "rc": rc,
                     "reported_files": files.group(1) if files else None,
                     "stdout_tail": out.strip()[-160:], "stderr_tail": err.strip()[-120:],
                     "refused_empty": rc != 0, "how": "CLI with an empty tree"})
        # E4 my scanner reports its own empty-root case in-band; parse the JSON objects out of its stdout
        # (its scan root is a constant inside the file, so the empty directory is its own leg, not an argument
        # I hand it - recorded that way rather than pretending I fed it an empty input)
        scan = os.path.join(HERE, "empty_denominator_scan_r2.py")
        shutil.copy(scan, tmp)
        rc, out, err = run([sys.executable, os.path.join(tmp, "empty_denominator_scan_r2.py")], cwd=tmp)
        dec = json.JSONDecoder()
        objs, i = [], 0
        while i < len(out):
            j = out.find("{", i)
            if j < 0:
                break
            try:
                o, end = dec.raw_decode(out, j)
                objs.append(o)
                i = end
            except ValueError:
                i = j + 1
        empty_case = next((o["empty_root_counterexample"] for o in objs
                           if isinstance(o, dict) and "empty_root_counterexample" in o), None)
        if empty_case is None:
            raise SystemExit("ABORT: the scanner printed no empty-root case - I will not invent one")
        rows.append({"id": "E4", "entry": "empty_denominator_scan_r2.py",
                     "empty_input": "empty directory (its own in-band leg, root is a constant in the file)",
                     "rc": rc, "empty_root_refused": empty_case.get("refused"),
                     "empty_root_detail": (empty_case.get("detail") or "")[:120],
                     "refused_empty": bool(empty_case.get("refused")),
                     "how": "CLI in a temp copy"})
        # E5 shipping hook, 0-byte local through its own function
        code5 = ("import sys,json;sys.path.insert(0,r'%s');"
                 "from tools.cnx_ledger_mirror_sync_hook_r1 import run_after_insert;"
                 "line=run_after_insert(trail=r'%s',arm='',local_path=r'%s',repo_dir=r'%s',"
                 "token_file=r'%s',reads=1);"
                 "print(json.dumps({k:line[k] for k in ('verdict','exit_code','appended')}))"
                 % (WT, os.path.join(tmp, "trail_e5.jsonl"), empty_local, r"D:\moodle\CityNexus", TOKEN))
        rc, out, err = run([sys.executable, "-c", code5])
        j5 = json.loads(out.strip().split("\n")[-1]) if out.strip() else {}
        rows.append({"id": "E5", "entry": "tools/cnx_ledger_mirror_sync_hook_r1.py",
                     "empty_input": "0-byte local file, real remote", "rc": rc,
                     "returned_exit_code": j5.get("exit_code"), "verdict": j5.get("verdict"),
                     "refused_empty": j5.get("exit_code", 0) != 0, "how": "function call"})
        # E6 the audit ruler: floor quoted from source, empty input not reachable without editing it
        src = io.open(os.path.join(HERE, "empty_leg_reachability_r3.py"), encoding="utf-8").read()
        floor_lines = [l.strip() for l in src.split("\n") if "ABORT: no .py files under" in l]
        rows.append({"id": "E6", "entry": "empty_leg_reachability_r3.py",
                     "empty_input": "NOT FEEDABLE without editing the entry (it scans its own directory)",
                     "rc": None, "floor_in_source": floor_lines[0] if floor_lines else None,
                     "refused_empty": None, "how": "not run - marked unmeasured, not counted as green"})

        R["rows"] = rows
        R["entries_refusing_empty"] = sum(1 for r in rows if r["refused_empty"] is True)
        R["entries_answering_ok_on_empty"] = sum(1 for r in rows if r["refused_empty"] is False)
        R["entries_unmeasured"] = sum(1 for r in rows if r["refused_empty"] is None)
        R["survey_is_the_open_one"] = next((r["id"] for r in rows if r["id"] == "E3"
                                            and r["refused_empty"] is False), None)
        R["fixture_removed"] = True
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        R["temp_removed"] = not os.path.exists(tmp)
        R["ledger_bytes_after"] = os.path.getsize(LEDGER)

    io.open(os.path.join(HERE, "empty_input_floor_probe_r1.json"), "w", encoding="utf-8",
            newline="\n").write(json.dumps(R, ensure_ascii=False, indent=1))
    print(json.dumps(R, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
