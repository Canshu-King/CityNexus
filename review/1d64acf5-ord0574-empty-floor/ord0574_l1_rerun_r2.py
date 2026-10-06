# -*- coding: utf-8 -*-
"""ORD-0574 L1, done properly: ref = a real branch name (r1 passed 'HEAD', which is not fetchable).

Local side: a zero-byte file created in temp. Remote side: backend/app/commerce/__init__.py on
mirror/integration-frontend-apple-pass1, which is zero bytes in the tree (blob e69de29bb2d1d6434b8b29ae775ad8c2e48c5391).
Both channels are the shipped tool's own.
"""
import io, json, os, subprocess, sys, tempfile
WT = r"D:\moodle\_qoder_lane_S4_0926\wt0391"
MAIN = r"D:\moodle\CityNexus"
HERE = os.path.dirname(os.path.abspath(__file__))
TOKEN = r"D:/moodle/_qoder_recovery_20260919/.api_tok_20260920"
REF = "mirror/integration-frontend-apple-pass1"
PATH = "backend/app/commerce/__init__.py"
EMPTY = "e69de29bb2d1d6434b8b29ae775ad8c2e48c5391"

def sh(argv, **kw):
    e = dict(os.environ)
    for k in ("HTTP_PROXY","HTTPS_PROXY","http_proxy","https_proxy","ALL_PROXY","all_proxy"): e.pop(k, None)
    e["PYTHONIOENCODING"] = "utf-8"
    p = subprocess.run(argv, capture_output=True, env=e, timeout=kw.get("timeout", 900))
    return p.returncode, p.stdout.decode("utf-8","replace"), p.stderr.decode("utf-8","replace")

R = {"ref": REF, "path": PATH}
rc, out, err = sh(["git","-C",MAIN,"ls-tree","-r","--format=%(objectname) %(objectsize)",
                   "refs/remotes/origin/" + REF, PATH])
f = out.split()
if len(f) != 2 or f[0] != EMPTY or f[1] != "0":
    raise SystemExit("ABORT: the remote side of my fixture is not a zero-byte blob: %r" % out[:150])
R["remote_side_verified_zero_bytes"] = out.strip()

fd, empty_local = tempfile.mkstemp(prefix="cnx_0b_", suffix=".md"); os.close(fd)
if os.path.getsize(empty_local) != 0: raise SystemExit("ABORT: fixture not zero bytes")
R["fixture"] = empty_local.replace("\\","/")
try:
    code = ("import sys,json;sys.path.insert(0,r'%s');"
            "from tools.cnx_ledger_mirror_sync_check_r1 import check_sync;"
            "st=check_sync(local_path=r'%s',ref='%s',path='%s',repo_dir=r'%s',token_file=r'%s',reads=1);"
            "print(json.dumps(st,ensure_ascii=False))" % (WT, empty_local, REF, PATH, MAIN, TOKEN))
    rc, out, err = sh([sys.executable, "-c", code])
    R["L1_rc"] = rc
    R["L1_stderr_tail"] = err[-240:]
    if not out.strip(): raise SystemExit("ABORT: leg produced no stdout, rc=%d" % rc)
    st = json.loads(out.strip())
    for k in ("verdict","exit_code","local_blob","remote_blob","local_bytes","remote_bytes",
              "points_compared","points_matched","remote_self_proved","first_differing_line",
              "local_changed_under_the_run","arm"):
        R["L1_" + k] = st[k]
    R["L1_compared_points"] = st["compared_points"]
    R["L1_local_snapshots"] = st["local_snapshots"]
    R["L1_remote_reads"] = st["remote_reads"]
    # the claim I am about to make, asserted from the reading rather than typed
    if st["local_blob"] != EMPTY or st["remote_blob"] != EMPTY:
        raise SystemExit("ABORT: the tool did not read zeros on both sides, so this is not the fixture I claimed")
    R["L1_both_sides_are_the_empty_blob"] = True
    R["L1_answered_current"] = (st["verdict"] == "CURRENT")
    R["L1_exit_zero"] = (st["exit_code"] == 0)
    # second run of the same fixture: the verdict must not depend on which snapshot got picked
    rc2, out2, err2 = sh([sys.executable, "-c", code])
    st2 = json.loads(out2.strip())
    R["L1_repeat_verdict"] = st2["verdict"]
    R["L1_repeat_rc"] = rc2
    R["L1_stable"] = (st2["verdict"] == st["verdict"])
    # L4b: the refusal's real exit code through the CLI, measured without a pipe
    e = dict(os.environ)
    for k in ("HTTP_PROXY","HTTPS_PROXY","http_proxy","https_proxy","ALL_PROXY","all_proxy"): e.pop(k, None)
    e.pop("CITYNEXUS_API_TOKEN_FILE", None)
    e["PYTHONIOENCODING"] = "utf-8"
    p = subprocess.run([sys.executable, os.path.join(WT,"tools","cnx_ledger_mirror_sync_check_r1.py"),
                        "--local", r"D:\moodle\CITYNEXUS_AGENT_CONTROL.md", "--token-file","", "--reads","1"],
                       capture_output=True, env=e, timeout=600)
    se = p.stderr.decode("utf-8","replace")
    R["L4_no_token_rc"] = p.returncode
    R["L4_exception_line"] = [l for l in se.split("\n") if l.strip().startswith("tools.cnx_ledger_mirror_reader_r1.IncompleteRemoteRead")][:1]
    R["L4_docstring_promise"] = "0 CURRENT, 7 LAGGING, 8 DIVERGED, 9 the reader refused"
    R["L4_promise_kept"] = (p.returncode == 9)
    # L4c: same refusal reached through the public function (what an importer/the hook sees), run as its own file
    rc3, out3, err3 = sh([sys.executable, os.path.join(HERE, "ord0574_l4c_importer_r2.py")])
    R["L4c_importer_leg"] = out3.strip()
    R["L4c_importer_rc"] = rc3
finally:
    os.unlink(empty_local)
    R["fixture_removed"] = not os.path.exists(empty_local)
    R["ledger_bytes_after"] = os.path.getsize(r"D:\moodle\CITYNEXUS_AGENT_CONTROL.md")

io.open(os.path.join(HERE,"ord0574_l1_rerun_r2.json"),"w",encoding="utf-8",newline="\n").write(
    json.dumps(R, ensure_ascii=False, indent=1))
print(json.dumps(R, ensure_ascii=False, indent=1))
