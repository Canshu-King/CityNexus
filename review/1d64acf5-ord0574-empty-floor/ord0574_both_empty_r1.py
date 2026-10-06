# -*- coding: utf-8 -*-
"""ORD-0574: feed the *shipped* mirror self-check a both-sides-empty fixture and paste its own verdict.

No replica, no line-range excerpt: this calls the tool that is on the authoritative line, with
  - the LOCAL side  = a zero-byte file in the system temp directory (created here, deleted at the end)
  - the REMOTE side = a zero-byte file that already exists in the authoritative tree
                      (backend/app/commerce/__init__.py, blob e69de29bb2d1d6434b8b29ae775ad8c2e48c5391)
read through the tool's own two channels.

Four legs, all real, in one run so the numbers come from the same minute:
  L1 both sides empty            -> the verdict under examination
  L2 local empty, remote real     -> single-sided control (must not answer CURRENT)
  L3 both sides the real ledger   -> positive control (must answer CURRENT)
  L4 refusal exit codes measured WITHOUT a pipe (a pipe masks rc; the docstring claims 9 for "reader refused")

Nothing here writes the ledger, a ref, or a product file.
"""
import io
import json
import os
import subprocess
import sys
import tempfile

WT = r"D:\moodle\_qoder_lane_S4_0926\wt0391"
MAIN = r"D:\moodle\CityNexus"
HERE = os.path.dirname(os.path.abspath(__file__))
TOKEN = r"D:/moodle/_qoder_recovery_20260919/.api_tok_20260920"
LEDGER = r"D:\moodle\CITYNEXUS_AGENT_CONTROL.md"
EMPTY_REPO_PATH = "backend/app/commerce/__init__.py"
EMPTY_BLOB = "e69de29bb2d1d6434b8b29ae775ad8c2e48c5391"


def clean_env():
    e = dict(os.environ)
    for k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "ALL_PROXY", "all_proxy"):
        e.pop(k, None)
    e["PYTHONIOENCODING"] = "utf-8"
    return e


def sh(argv, **kw):
    p = subprocess.run(argv, capture_output=True, env=clean_env(), timeout=kw.get("timeout", 600))
    return p.returncode, p.stdout.decode("utf-8", "replace"), p.stderr.decode("utf-8", "replace")


def main():
    if not os.path.isdir(WT):
        raise SystemExit("ABORT: %s missing" % WT)
    if not os.path.isfile(TOKEN):
        raise SystemExit("ABORT: token path missing - the second channel would silently be single-source")

    # the empty-file path must be zero bytes *in the tree I am reading from*, measured not assumed
    rc, out, err = sh(["git", "-C", MAIN, "ls-tree", "-r", "--format=%(objectname) %(objectsize) %(path)",
                       "HEAD", EMPTY_REPO_PATH])
    fields = out.split()
    if len(fields) < 3 or fields[0] != EMPTY_BLOB or fields[1] != "0":
        raise SystemExit("ABORT: %s is not a zero-byte blob on the local tip (%r)" % (EMPTY_REPO_PATH, out[:120]))
    tip = sh(["git", "-C", MAIN, "rev-parse", "HEAD"])[1].strip()

    # local zero-byte fixture, in temp, removed no matter how the run exits
    fd, empty_local = tempfile.mkstemp(prefix="cnx_0byte_fixture_", suffix=".md")
    os.close(fd)
    if os.path.getsize(empty_local) != 0:
        raise SystemExit("ABORT: the fixture I just made is not zero bytes")

    R = {"tip_local": tip, "empty_repo_path": EMPTY_REPO_PATH, "empty_blob": EMPTY_BLOB,
         "fixture": empty_local.replace("\\", "/"), "fixture_bytes": 0}
    try:
        # L1 both sides empty - call the shipped function through its own module
        code = (
            "import sys,json;sys.path.insert(0,r'%s');"
            "from tools.cnx_ledger_mirror_sync_check_r1 import check_sync;"
            "st=check_sync(local_path=r'%s',ref='HEAD',path='%s',repo_dir=r'%s',token_file=r'%s',reads=1);"
            "print(json.dumps(st,ensure_ascii=False))" % (WT, empty_local, EMPTY_REPO_PATH, MAIN, TOKEN)
        )
        rc, out, err = sh([sys.executable, "-c", code], timeout=600)
        R["L1_both_empty"] = {"rc": rc, "stdout": out.strip()[:400], "stderr_tail": err[-240:]}
        if rc == 0 and out.strip():
            st = json.loads(out.strip())
            R["L1_verdict"] = st["verdict"]
            R["L1_exit_code"] = st["exit_code"]
            R["L1_local_blob"] = st["local_blob"]
            R["L1_remote_blob"] = st["remote_blob"]
            R["L1_local_bytes"] = st["local_bytes"]
            R["L1_remote_bytes"] = st["remote_bytes"]
            R["L1_points"] = [st["points_compared"], st["points_matched"]]
            R["L1_self_proved"] = st["remote_self_proved"]
            R["L1_first_differing_line"] = st["first_differing_line"]

        # L2 local empty, remote = the real ledger
        code2 = (
            "import sys,json;sys.path.insert(0,r'%s');"
            "from tools.cnx_ledger_mirror_sync_check_r1 import check_sync;"
            "st=check_sync(local_path=r'%s',ref='commander/control',path='CITYNEXUS_AGENT_CONTROL.md',"
            "repo_dir=r'%s',token_file=r'%s',reads=1);"
            "print(json.dumps({'verdict':st['verdict'],'exit_code':st['exit_code'],"
            "'local_blob':st['local_blob'],'remote_blob':st['remote_blob'],"
            "'local_bytes':st['local_bytes'],'remote_bytes':st['remote_bytes'],"
            "'first_differing_line':st['first_differing_line']}))" % (WT, empty_local, MAIN, TOKEN)
        )
        rc, out, err = sh([sys.executable, "-c", code2], timeout=600)
        R["L2_local_empty"] = {"rc": rc, "stdout": out.strip()[:400], "stderr_tail": err[-200:]}
        if out.strip():
            j = json.loads(out.strip())
            R["L2_verdict"] = j["verdict"]

        # L3 both sides the real ledger (positive control) + the CLI's own exit code, no pipe
        cli = [sys.executable, os.path.join(WT, "tools", "cnx_ledger_mirror_sync_check_r1.py"),
               "--local", LEDGER, "--token-file", TOKEN, "--reads", "1"]
        rc, out, err = sh(cli, timeout=600)
        R["L3_real_ledger"] = {"rc": rc, "stdout": out.strip()[:400], "stderr_tail": err[-200:]}

        # L4 the no-token refusal's REAL exit code (docstring claims 9; a pipe would have hidden it)
        cli4 = [sys.executable, os.path.join(WT, "tools", "cnx_ledger_mirror_sync_check_r1.py"),
                "--local", LEDGER, "--token-file", "", "--reads", "1"]
        env = clean_env()
        env.pop("CITYNEXUS_API_TOKEN_FILE", None)
        p = subprocess.run(cli4, capture_output=True, env=env, timeout=600)
        so = p.stdout.decode("utf-8", "replace")
        se = p.stderr.decode("utf-8", "replace")
        R["L4_no_token"] = {"rc": p.returncode, "stdout": so.strip()[:200],
                            "exc_line": [l for l in se.split("\n") if l.strip().startswith(("IncompleteRemoteRead",
                                                                                             "tools.cnx_ledger_mirror_reader_r1.IncompleteRemoteRead"))][:1],
                            "docstring_claim": "9 the reader refused"}

        # L5 the same tool's own self-test still passes today (arms bite) - real CLI, real rc
        cli5 = [sys.executable, os.path.join(WT, "tools", "cnx_ledger_mirror_sync_check_r1.py"),
                "--self-test", "--token-file", TOKEN]
        rc, out, err = sh(cli5, timeout=600)
        R["L5_selftest"] = {"rc": rc, "stdout_tail": out.strip()[-420:], "stderr_tail": err[-160:]}
    finally:
        os.unlink(empty_local)
        R["fixture_removed"] = not os.path.exists(empty_local)
        R["ledger_bytes_after_run"] = os.path.getsize(LEDGER)

    io.open(os.path.join(HERE, "ord0574_both_empty_r1.json"), "w", encoding="utf-8", newline="\n").write(
        json.dumps(R, ensure_ascii=False, indent=1))
    print(json.dumps(R, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
