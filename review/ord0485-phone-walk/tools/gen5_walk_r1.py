"""ORD-0485 -r4 on the live tip 822db3d9 -- re-take every reading this generation, in one run.

What the recut order asks for is not a re-derivation of the old numbers: the entry asset name, the
served-bundle hash, the screen text and the dictionary key gap all have to be measured on
`1e95d106f81b29048ba17695fd0e49172516b9b1` and on the candidate built from it.  Two faces, two
outputs, no shared path -- the defect that made this lane issue its own erratum was one instrument
writing two generations into one file.

Identity proof per face, the two that are obtainable from a static `vite preview`: the entry asset
name read out of the index.html this server answers, and served bytes == disk bytes for that asset.
The third proof (a request line in an access log) is named NOT_AVAILABLE_BY_CMDR rather than
inferred: `vite preview` writes nothing to my log files except its own boot banner, which was
mistaken for a request line once already.
"""
import hashlib
import json
import os
import re
import subprocess
import sqlite3
import sys
import time
import urllib.request
from datetime import datetime

LANE = r"D:/moodle/_qoder_phone_ord0485_20260930"
PY = r"D:/moodle/CityNexus/.venv/Scripts/python.exe"
NODE = r"C:/Program Files/nodejs/node.exe"
SHARED = r"D:\moodle\_qoder_preview_20260920\_preview.db"
DB = os.path.join(LANE, "run", "phone_gen5_walk.db")
BACKEND_PORT = 8142
FACES = [("TIP_822db3d9", "faces/tip5", "wt13", 4874, "wt13", "walk_gen5_tip"),
         ("O0485_R4", "faces/o0485_r4", "wt11", 4875, "wt11", "walk_gen5_r4")]
op = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def env_clean(extra=None):
    e = {k: v for k, v in os.environ.items()
         if k.upper() not in ("HTTP_PROXY", "HTTPS_PROXY", "DEEPSEEK_API_KEY")}
    if extra:
        e.update(extra)
    return e


def listener(port):
    out = subprocess.run(["netstat", "-ano", "-p", "tcp"], stdout=subprocess.PIPE,
                         timeout=30).stdout
    for line in out.decode("gbk", errors="replace").splitlines():
        q = line.split()
        if len(q) >= 5 and q[0].upper() == "TCP" and q[1].endswith(":%d" % port) \
                and q[3].upper() == "LISTENING":
            return q[4]
    return None


def stop(pid):
    if not pid or not str(pid).isdigit():
        return "NOTHING_TO_STOP"
    subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], stdout=subprocess.DEVNULL,
                   stderr=subprocess.DEVNULL, timeout=60)
    return "STOPPED"


def fresh_store():
    for suffix in ("", "-wal", "-shm"):
        if os.path.exists(DB + suffix):
            os.remove(DB + suffix)
    src = sqlite3.connect("file:" + SHARED.replace("\\", "/") + "?mode=ro", uri=True)
    dst = sqlite3.connect(DB)
    src.backup(dst)
    dst.close()
    src.close()
    st = os.stat(SHARED)
    return {"journeys": sqlite3.connect(DB).execute("SELECT COUNT(*) FROM journeys").fetchone()[0],
            "shared_bytes": st.st_size,
            "shared_mtime_local": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(st.st_mtime))}


def boot_backend(tree):
    log = os.path.join(LANE, "run", "gen5_walk_backend_%d.log" % BACKEND_PORT)
    ps = ("$env:HTTP_PROXY=''; $env:HTTPS_PROXY=''; $env:DEEPSEEK_API_KEY=''; "
          "$env:PYTHONPATH='%s'; $env:CITYNEXUS_DATABASE_URL='sqlite:///%s'; "
          "$env:CITYNEXUS_DEMO_MODE='true'; $env:CITYNEXUS_AI_ENABLED='false'; "
          "Start-Process -FilePath '%s' -ArgumentList '-m','uvicorn','app.main:app',"
          "'--host','127.0.0.1','--port','%d' -WorkingDirectory '%s' -WindowStyle Hidden "
          "-RedirectStandardOutput '%s' -RedirectStandardError '%s'"
          % (LANE + "/" + tree, DB.replace("\\", "/"), PY, BACKEND_PORT,
             LANE + "/" + tree + "/backend", log, log + ".err"))
    with open(log + ".launcher", "ab") as sink:
        try:
            subprocess.run(["powershell", "-NoProfile", "-Command", ps], stdout=sink,
                           stderr=sink, timeout=90)
        except subprocess.TimeoutExpired:
            return {"ready": False, "ABORT": "LAUNCHER_TIMEOUT_90S"}
    for _ in range(45):
        time.sleep(2)
        pid = listener(BACKEND_PORT)
        if pid:
            try:
                with op.open("http://127.0.0.1:%d/api/v1/demo/scene" % BACKEND_PORT,
                             timeout=10) as r:
                    if r.status == 200:
                        scene = json.loads(r.read().decode("utf-8"))
                        return {"ready": True, "pid": pid,
                                "journey_id": scene.get("journey_id"),
                                "evidence_state": scene.get("evidence_state")}
            except Exception:
                continue
    return {"ready": False, "ABORT": "BACKEND_NEVER_ANSWERED"}


def serve(face_dir, port, tree):
    log = os.path.join(LANE, "run", "gen5_walk_face_%d.log" % port)
    bytes_before = os.path.getsize(log) if os.path.exists(log) else 0
    with open(log, "ab") as sink:
        subprocess.Popen([NODE, "node_modules/vite/bin/vite.js", "preview",
                          "--outDir", os.path.join(LANE, face_dir), "--host", "127.0.0.1",
                          "--port", str(port), "--strictPort"],
                         cwd=os.path.join(LANE, tree, "frontend"),
                         env=env_clean({"CITYNEXUS_BACKEND_PORT": str(BACKEND_PORT)}),
                         creationflags=0x208, stdout=sink, stderr=sink)
    abs_face = os.path.join(LANE, face_dir)
    for _ in range(30):
        time.sleep(2)
        try:
            with op.open("http://127.0.0.1:%d/" % port, timeout=10) as r:
                html = r.read().decode("utf-8", "replace")
        except Exception:
            continue
        m = re.search(r'src="/assets/(index-[\w\-]+\.js)', html)
        asset = m.group(1)
        js_path = os.path.join(abs_face, "assets", asset)
        with op.open("http://127.0.0.1:%d/assets/%s" % (port, asset), timeout=60) as r:
            served = r.read()
        disk = open(js_path, "rb").read()
        added = open(log, "rb").read()[bytes_before:]
        request_lines = re.findall(rb"\S+ GET /", added)
        return {"port": port, "face_dir": face_dir, "entry_asset": asset,
                "index_html_bytes_served": len(html.encode("utf-8")),
                "bundle_bytes_served": len(served), "bundle_bytes_on_disk": len(disk),
                "bundle_local_sha1_served": hashlib.sha1(served).hexdigest(),
                "bundle_local_sha1_disk": hashlib.sha1(disk).hexdigest(),
                "bundle_bytes_equal_served_vs_disk": served == disk,
                "log_bytes_added_since_boot": len(added),
                "access_log_request_lines_found": len(request_lines),
                "access_log_proof": ("AVAILABLE" if request_lines else
                                     "NOT_AVAILABLE_BY_CMDR: vite preview writes no request line "
                                     "to the file this lane controls"),
                "listener_pid": listener(port)}
    return {"port": port, "face_dir": face_dir, "ABORT": "FACE_NEVER_ANSWERED"}


def walk(base, out_dir):
    env = env_clean({"CNX_WALK_BASE": base, "CNX_WALK_OUT": os.path.join(LANE, "evidence", out_dir),
                     "CITYNEXUS_BACKEND_PORT": str(BACKEND_PORT)})
    p = subprocess.run([NODE, os.path.join(LANE, "tools", "walk_phone_gen2_r1.cjs")],
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env, timeout=1200)
    text = p.stdout.decode("utf-8", "replace")
    open(os.path.join(LANE, "run", "gen5_walk_%s.txt" % out_dir), "w", encoding="utf-8").write(text)
    json_path = os.path.join(LANE, "evidence", out_dir, "walk_r2.json")
    d = json.load(open(json_path, encoding="utf-8")) if os.path.exists(json_path) else {}
    screens = d.get("screens", [])
    hits = {}
    for s in screens:
        for h in (s.get("machine_word_hits") or []):
            hits.setdefault(h, []).append(s.get("route"))
    import_screen = [s for s in screens if "import" in str(s.get("route", ""))]
    return {"exit": p.returncode, "walk": os.path.relpath(json_path, LANE),
            "screen_count": len(screens), "page_errors_total": d.get("page_errors_total"),
            "non_write_requests": len(d.get("requests_non_get", []) or []),
            "machine_word_keys": sorted(hits),
            "import_screen_evidence_labels": [s.get("evidence_labels") for s in import_screen],
            "import_screen_head": [str(s.get("rendered_text_head", ""))[:200]
                                   for s in import_screen],
            "routes": [s.get("route") for s in screens]}


def carrier(port):
    """The accepted ORD-0485 word gate, replayed unchanged against this generation's served face.

    The spec and its config live in `export/frontend` (the host this lane has been running them on);
    the config refuses to start unless `CITYNEXUS_ORD0485_BASE` points at 127.0.0.1:4xxx, and it has
    no webServer block, so the only bundle it can read is the one this driver is serving.
    """
    log = os.path.join(LANE, "run", "gen5_carrier_%d.txt" % port)
    p = subprocess.run(
        [NODE, "node_modules/@playwright/test/cli.js", "test",
         "--config", "playwright.ord0485-phone.config.ts",
         "e2e/qoder-ord0485-phone-words.spec.ts", "--reporter=line"],
        cwd=os.path.join(LANE, "export", "frontend"),
        env=env_clean({"CITYNEXUS_ORD0485_BASE": "http://127.0.0.1:%d" % port,
                       "CNX_PHONE_NODE": NODE}),
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=600)
    text = p.stdout.decode("utf-8", "replace")
    open(log, "w", encoding="utf-8").write(text)
    verdict = [l for l in text.splitlines() if re.search(r"\d+ (passed|failed)", l)]
    return {"port": port, "exit": p.returncode, "log": os.path.relpath(log, LANE),
            "verdict_line": verdict[-1].strip() if verdict else text.strip().splitlines()[-3:],
            "red_test_names": re.findall(r"^\s+\d+\) .*spec\.ts:\d+:\d+ › (\S+)", text, re.M),
            "notes": [l for l in text.splitlines() if "—" in l][:4]}


def gap(src_tree, walk_json, out_name, label):
    env = env_clean({"CNX_GAP_SRC": os.path.join(LANE, src_tree, "frontend", "src"),
                     "CNX_GAP_WALK": walk_json, "CNX_GAP_OUT": os.path.join(LANE, "evidence", out_name),
                     "CNX_GAP_LABEL": label})
    p = subprocess.run([PY, "-X", "utf8", os.path.join(LANE, "tools", "i18n_key_gap_r2.py")],
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env, timeout=180)
    text = p.stdout.decode("utf-8", "replace")
    try:
        d = json.loads(text)
    except ValueError:
        return {"exit": p.returncode, "unparsed": text[:400]}
    return {"exit": p.returncode, "out": out_name,
            "label": d.get("label"),
            "dictionary_sha256_over_bytes": d.get("dictionary_sha256_over_bytes"),
            "referenced_key_count": d.get("referenced_key_count"),
            "keys_in_en": d.get("keys_in_en"), "keys_in_zhCN": d.get("keys_in_zhCN"),
            "referenced_keys_missing_from_both": d.get("referenced_keys_missing_from_both"),
            "missing_from_both": d.get("missing_from_both")}


def main():
    out = {"tool": "gen5_walk_r1", "took_local": datetime.now().astimezone().isoformat()}
    stop(listener(BACKEND_PORT))
    out["store"] = fresh_store()
    out["backend"] = boot_backend("wt13")
    if not out["backend"].get("ready"):
        print(json.dumps(out, indent=2, ensure_ascii=False))
        return 1
    receipts = []
    for label, face_dir, tree, port, gap_tree, walk_dir in FACES:
        entry = {"label": label, "face_dir": face_dir, "gap_tree": gap_tree}
        entry["serve"] = serve(face_dir, port, tree)
        base = "http://127.0.0.1:%d" % port
        entry["walk"] = walk(base, walk_dir)
        walk_json = os.path.join(LANE, "evidence", walk_dir, "walk_r2.json")
        entry["gap"] = gap(gap_tree, walk_json,
                           "i18n_gap_%s_r1.json" % label, label)
        receipts.append(entry)
        print("%s screens=%s pageerrors=%s missing=%s labels=%s" % (
            label, entry["walk"]["screen_count"], entry["walk"]["page_errors_total"],
            entry["gap"].get("referenced_keys_missing_from_both"),
            entry["walk"]["import_screen_evidence_labels"]), flush=True)
        entry["carrier"] = carrier(port)
        stop(listener(port))
    out["faces"] = receipts
    dicts = {r["label"]: hashlib.sha256(open(os.path.join(
        LANE, r["gap_tree"], "frontend", "src", "i18n", "LocaleContext.tsx"), "rb").read()).hexdigest()
        for r in receipts}
    out["dictionary_files"] = dicts
    out["the_two_dictionaries_are_different_bytes"] = len(set(dicts.values())) == 2
    path = os.path.join(LANE, "evidence", "gen5_walk_r1.json")
    json.dump(out, open(path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(json.dumps(out, indent=2, ensure_ascii=False)[:3500])
    print("WROTE " + path)
    stop(listener(BACKEND_PORT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
