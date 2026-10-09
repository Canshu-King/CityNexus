#!/usr/bin/env python3
"""Commander's own authoritative e2e runner.

Why this file exists: lane runs are reported to me inside lane .out files, and a
number I did not produce is not evidence I can sign.  This starts its own backend
and its own vite on ports nobody else holds, in its own worktree, against a
throwaway `_run<id>.db`, and prints the exit code it actually observed.

Authoritative mode is not optional here: playwrightEnv refuses to run without
CITYNEXUS_E2E_PORT / CITYNEXUS_BACKEND_PORT / CITYNEXUS_PYTHON /
CITYNEXUS_DATABASE_URL / CITYNEXUS_E2E_RUN_ID, which is exactly the set this
script supplies, so a borrowed neighbour's server cannot answer for my numbers.

Usage:
  cmdr_e2e_r1.py --wt D:/moodle/_qoder_cmdr_ord0338_land --target e2e/foo.spec.ts
  cmdr_e2e_r1.py --wt ... --target e2e/ --full
Fresh run id per attempt is required by the backend's fresh-or-no-run guard, so
the script derives one from the clock and refuses to reuse an existing db file.
"""
import argparse
import datetime
import glob
import io
import json
import os
import re
import shutil
import subprocess
import sys

VENV_PY = r"D:/moodle/CityNexus/.venv/Scripts/python.exe"
NM_SOURCE = os.path.realpath(r"D:/moodle/_qoder_integration_20260919/frontend/node_modules")
HERE = os.path.dirname(os.path.abspath(__file__))


def free_port(base):
    """A port pair (p, p+1000) nobody is holding.

    First version bound both numbers on one socket and every candidate failed:
    a socket that is already bound cannot be bound again (WSAEINVAL), so the
    helper reported NO_FREE_PORT on an idle machine.  Two sockets, one per
    number, is the check that actually means what its name says.
    """
    import socket

    def bindable(p):
        with socket.socket() as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind(("127.0.0.1", p))
                return True
            except OSError:
                return False

    p = base
    while p < base + 400:
        if bindable(p) and bindable(p + 1000):
            return p
        p += 1
    raise SystemExit("NO_FREE_PORT near %d" % base)


def ensure_node_modules(front_dir):
    """Junction the shared install; never copy it, and never delete through it."""
    dst = os.path.join(front_dir, "node_modules")
    if os.path.isdir(dst):
        return {"mode": "present", "path": dst.replace("\\", "/")}
    if not os.path.isdir(NM_SOURCE):
        raise SystemExit("NODE_MODULES_SOURCE_MISSING " + NM_SOURCE)
    r = subprocess.run('cmd /c mklink /J "%s" "%s"' % (dst, NM_SOURCE),
                       shell=True, capture_output=True, text=True, errors="replace")
    if not os.path.isdir(dst):
        raise SystemExit("JUNCTION_FAILED rc=%s %s" % (r.returncode, r.stdout[-200:]))
    return {"mode": "junction", "path": dst.replace("\\", "/"),
            "target": NM_SOURCE.replace("\\", "/")}


def summarize(text):
    """Pull the counts Playwright actually printed, not the ones I expect."""
    out = {}
    for key in ("passed", "failed", "flaky", "skipped", "interrupted", "did not run"):
        m = re.search(r"^\s+(\d+) %s\b" % key, text, re.M)
        if m:
            out[key] = int(m.group(1))
    names = sorted(set(re.findall(r"^\s+\[chromium\] .+?›\s+\S+$", text, re.M)))
    return out, names


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--wt", required=True, help="worktree root")
    ap.add_argument("--target", required=True, help="e2e/... spec or directory")
    ap.add_argument("--full", action="store_true", help="this is the whole-suite run")
    ap.add_argument("--grep", default=None, help="optional -g pattern")
    ap.add_argument("--tag", default="run")
    ap.add_argument("--timeout-min", type=int, default=55)
    a = ap.parse_args()

    front = os.path.join(a.wt, "frontend")
    if not os.path.isdir(front):
        print("NO_FRONTEND_DIR " + front, file=sys.stderr)
        return 2
    tree = subprocess.run(["git", "-C", a.wt, "rev-parse", "HEAD"],
                          capture_output=True, text=True, errors="replace").stdout.strip()
    if not re.fullmatch(r"[0-9a-f]{40}", tree):
        print("TREE_UNRESOLVED in " + a.wt, file=sys.stderr)
        return 2

    stamp = datetime.datetime.now().strftime("%H%M%S")
    run_id = "cmdr%s%s" % (stamp, a.tag.replace("-", ""))
    ev_dir = os.path.join(a.wt, "review", "evidence")
    os.makedirs(ev_dir, exist_ok=True)
    db = os.path.join(ev_dir, "_%s.db" % run_id)
    if os.path.exists(db):
        print("DB_EXISTS_REFUSE " + db, file=sys.stderr)
        return 2
    fe_port = free_port(4300 if a.full else 4400)
    be_port = fe_port + 1000

    nm = ensure_node_modules(front)
    env = dict(os.environ)
    # The authoritative config refuses to start while an external AI key is in the
    # environment, because a deterministic suite must not be answered by a live
    # model.  This shell carries DEEPSEEK_API_KEY, so the keys are dropped for the
    # child.  Only the *names* removed are recorded; values are never printed.
    dropped = sorted(k for k in list(env)
                     if re.search(r"(API_KEY|AUTH_TOKEN|SECRET)$|^OPENAI_|^DEEPSEEK_", k))
    for k in dropped:
        env.pop(k, None)
    env.update({
        "CITYNEXUS_E2E_AUTHORITATIVE": "1",
        "CITYNEXUS_E2E_PORT": str(fe_port),
        "CITYNEXUS_BACKEND_PORT": str(be_port),
        "CITYNEXUS_PYTHON": VENV_PY,
        "CITYNEXUS_DATABASE_URL": "sqlite:///" + db.replace("\\", "/"),
        "CITYNEXUS_E2E_RUN_ID": run_id,
        # the config requires an explicit declaration rather than an absence
        "CITYNEXUS_AI_ENABLED": "false",
    })
    cmd = "npx playwright test %s --reporter=line --workers=1" % a.target
    if a.grep:
        cmd += " -g \"%s\"" % a.grep.replace('"', "'")

    log_path = os.path.join(HERE, "e2e_logs", "%s_%s_%s.log" % (a.tag, tree[:8], stamp))
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    header = "run_id=%s tree=%s port=%d/%d target=%s full=%s db=%s\n" % (
        run_id, tree, fe_port, be_port, a.target, a.full, os.path.basename(db))
    started = datetime.datetime.now()
    # Stream straight to the log file.  The first version collected the whole run
    # in a pipe and wrote it at the end, which meant a 46-minute full-suite run gave
    # me a 0-byte log for its entire duration: no way to see where it was, and no
    # way to tell a slow run from a dead one.
    with io.open(log_path, "wb") as fh:
        fh.write(header.encode("utf-8", "replace"))
        fh.flush()
        r = subprocess.Popen(cmd, cwd=front, env=env, shell=True,
                             stdout=fh, stderr=subprocess.STDOUT)
        rc = r.wait(timeout=a.timeout_min * 60)
    with io.open(log_path, "rb") as fh:
        raw = fh.read()
    raw = raw[len(header.encode("utf-8", "replace")):]
    text = header + raw.decode("utf-8", "replace")
    counts, names = summarize(text)
    verdict = "GREEN" if rc == 0 else "RED"
    if not counts and not names:
        verdict = "NO_READING"
    result = {
        "run_id": run_id, "tree": tree, "worktree": a.wt.replace("\\", "/"),
        "target": a.target, "full": a.full, "grep": a.grep,
        "ports": {"frontend": fe_port, "backend": be_port},
        "python": VENV_PY.replace("\\", "/"), "db": os.path.basename(db),
        "env_keys_dropped_names_only": dropped,
        "node_modules": nm, "exit_code": rc, "verdict": verdict,
        "counts": counts, "listed_case_count": len(names),
        "started_local": started.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "duration_s": (datetime.datetime.now() - started).total_seconds(),
        "log": log_path.replace("\\", "/"),
        "log_bytes": os.path.getsize(log_path),
    }
    out_json = os.path.join(HERE, "e2e_logs", "%s_%s_%s.json" % (a.tag, tree[:8], stamp))
    io.open(out_json, "w", encoding="utf-8").write(json.dumps(result, ensure_ascii=False, indent=1))
    print(json.dumps(result, ensure_ascii=False, indent=1))
    # failing case names, verbatim from the run, for baseline-set comparison
    fail_block = re.search(r"Failed tests:\n(.*?)(?:\n  \d+ (?:passed|skipped)|\Z)", text, re.S)
    if fail_block:
        fl = [l.strip() for l in fail_block.group(1).splitlines() if l.strip()]
        io.open(out_json + ".failed.txt", "w", encoding="utf-8").write("\n".join(fl) + "\n")
        print("FAILED_LIST %d -> %s.failed.txt" % (len(fl), out_json))
    return 0 if rc == 0 else 3


if __name__ == "__main__":
    sys.exit(main())
