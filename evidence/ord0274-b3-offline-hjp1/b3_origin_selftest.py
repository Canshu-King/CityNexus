"""Prove the two-pointer origin can even produce the failure the control arm claims to detect.

Cheap on purpose: no browser, no backend, two seconds of wall clock.  If the split root does not
answer a .js URL with the previous generation's index.html -- status 200, HTML body, and the event
line saying so -- then the control arm would be theatre and B3 must not be signed either way.
"""
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
LANE = r"D:\moodle\_qoder_hjp1_o207_20260922"
PY = r"C:\Users\仓鼠王\AppData\Local\Programs\Python\Python313\python.exe"
PORT = 8965
RUNDIR = os.path.join(LANE, "o2b3_selftest")
ROOT_NEW = os.path.join(LANE, "o290", "next_gen", "frontend", "dist")
ROOT_OLD = os.path.join(LANE, "o290", "s3_b2b", "frontend", "dist")


def entry(d):
    import re
    html = open(os.path.join(d, "index.html"), encoding="utf-8").read()
    return re.search(r"assets/(index-[\w-]+\.js)", html).group(1)


def get(p):
    try:
        with urllib.request.urlopen("http://127.0.0.1:%d%s" % (PORT, p), timeout=8) as r:
            return r.status, r.read(), r.headers.get("content-type", "")
    except urllib.error.HTTPError as e:
        return e.code, e.read(), e.headers.get("content-type", "")


def main():
    shutil.rmtree(RUNDIR, ignore_errors=True)
    os.makedirs(RUNDIR)
    open(os.path.join(RUNDIR, "current_root.txt"), "w").write(ROOT_NEW)
    open(os.path.join(RUNDIR, "mode.txt"), "w").write("answer")
    open(os.path.join(RUNDIR, "asset_root.txt"), "w").write(ROOT_NEW)
    p = subprocess.Popen([PY, os.path.join(LANE, "o2b3_origin.py"), RUNDIR, str(PORT), "9"],
                         stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    out = {"pid": p.pid, "new_bundle": entry(ROOT_NEW), "old_bundle": entry(ROOT_OLD)}
    try:
        time.sleep(2.5)
        st, body, ct = get("/")
        out["shell"] = {"status": st, "is_html": b"<!doctype html" in body.lower(),
                        "names_new_bundle": entry(ROOT_NEW).encode() in body, "ctype": ct}
        st, body, ct = get("/assets/" + entry(ROOT_NEW))
        out["primary_assets_new"] = {"status": st, "bytes": len(body), "ctype": ct,
                                     "is_html": body.lstrip()[:15].lower().startswith(b"<!doctype")}
        open(os.path.join(RUNDIR, "asset_root.txt"), "w").write(ROOT_OLD)
        st, body, ct = get("/assets/" + entry(ROOT_NEW))
        old_shell = open(os.path.join(ROOT_OLD, "index.html"), "rb").read()
        out["split_assets_missing"] = {"status": st, "bytes": len(body), "ctype": ct,
                                       "is_html": body.lstrip()[:15].lower().startswith(b"<!doctype"),
                                       "equals_old_shell_bytes": body == old_shell,
                                       "names_old_bundle": entry(ROOT_OLD).encode() in body}
        st, body, ct = get("/assets/" + entry(ROOT_OLD))
        out["split_old_asset_still_served"] = {"status": st, "bytes": len(body),
                                               "is_html": body.lstrip()[:15].lower().startswith(b"<!doctype")}
        lines = [json.loads(l) for l in open(os.path.join(RUNDIR, "requests.jsonl"), encoding="utf-8") if l.strip()]
        ev = [l for l in lines if l.get("kind") == "static"]
        out["events"] = {"static_total": len(ev),
                         "flagged_html_at_js": [e["path"] for e in ev if e.get("html_at_js_url")],
                         "asset_root_named": sorted({e.get("asset_root") for e in ev}),
                         "shell_root_named": sorted({e.get("shell_root") for e in ev}),
                         "first_three": ev[:3]}
        flagged = [e["path"] for e in ev if e.get("html_at_js_url")]
        out["events"]["flagged_html_at_js"] = flagged
        out["verdict"] = "SELFTEST_OK" if (
            out["primary_assets_new"]["status"] == 200 and not out["primary_assets_new"]["is_html"]
            and out["split_assets_missing"]["status"] == 200 and out["split_assets_missing"]["is_html"]
            and out["split_assets_missing"]["equals_old_shell_bytes"]
            and "/assets/" + entry(ROOT_NEW) in flagged
            and out["split_old_asset_still_served"]["status"] == 200
            and not out["split_old_asset_still_served"]["is_html"]
        ) else "SELFTEST_FAIL"
    finally:
        subprocess.run(["taskkill", "/F", "/PID", str(p.pid)], capture_output=True)
        time.sleep(1.0)
        shutil.rmtree(RUNDIR, ignore_errors=True)
        out["rundir_gone"] = not os.path.exists(RUNDIR)
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0 if out.get("verdict") == "SELFTEST_OK" else 1


if __name__ == "__main__":
    sys.exit(main())
