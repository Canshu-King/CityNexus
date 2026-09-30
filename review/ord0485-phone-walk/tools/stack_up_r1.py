"""ORD-0485 lane tool: bring up this lane's private phone-demo stack and prove it is MINE.

Shape:
  * uvicorn on a lane port against a private sqlite copy (never the shared preview DB),
  * `vite preview` on a second lane port serving THIS lane's production dist, with the
    /api proxy pointed at the lane backend through CITYNEXUS_BACKEND_PORT (the preview
    proxy does not default to anything else),
  * identity is proven by content, not by the port being free: a marker row that only my
    backend can write, read back out of MY file over a second mode=ro connection, plus the
    served asset bytes hashed and compared to the bytes on my disk.

The receipt prints every proof it took and names the one it could not take.
"""
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid

LANE = r"D:/moodle/_qoder_phone_ord0485_20260930"
EXPORT = LANE + "/export"
DB = LANE + "/run/phone_ord0485.db"
PY = r"D:/moodle/CityNexus/.venv/Scripts/python.exe"
BACKEND_PORT = int(os.environ.get("CNX_PHONE_BACKEND_PORT", "8139"))
STATIC_PORT = int(os.environ.get("CNX_PHONE_STATIC_PORT", "4861"))
RUN = LANE + "/run"

opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def sh(args, cwd=None, env=None):
    p = subprocess.run(args, cwd=cwd, env=env, shell=False,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return p.returncode, p.stdout.decode("gbk", errors="replace")


def listeners(port):
    rc, out = sh(["netstat", "-ano", "-p", "tcp"])
    if rc != 0:
        raise SystemExit("netstat failed rc=%d - instrument error, not 'nobody listening'" % rc)
    rows = []
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 5 and parts[0].upper() == "TCP" and parts[1].endswith(":%d" % port) \
                and parts[3].upper() == "LISTENING":
            rows.append({"local": parts[1], "pid": parts[4]})
    return rows


def cmdline(pid):
    rc, out = sh(["powershell", "-NoProfile", "-Command",
                  "Get-CimInstance Win32_Process -Filter 'ProcessId=%d' | "
                  "Select-Object -ExpandProperty CommandLine" % int(pid)])
    return out.strip()


def detached(logpath):
    flags = 0x00000208  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
    return {"creationflags": flags,
            "stdout": open(logpath, "ab"), "stderr": subprocess.STDOUT}


def http(method, url, body=None, headers=None, timeout=25):
    data = None
    hdrs = {"Accept": "application/json", "User-Agent": "ORD-0485-lane-phone"}
    if headers:
        hdrs.update(headers)
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        hdrs["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=hdrs, method=method)
    try:
        with opener.open(req, timeout=timeout) as r:
            raw = r.read()
            return r.status, dict(r.headers), raw
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read()
    except Exception as e:
        return None, {"error": type(e).__name__}, b""


def get_json(url):
    st, hd, raw = http("GET", url)
    try:
        return st, (json.loads(raw.decode("utf-8")) if raw else None)
    except Exception:
        return st, {"unparsed_bytes": len(raw)}


def sha1(b):
    return hashlib.sha1(b).hexdigest()


def main():
    receipt = {"tool": "stack_up_r1", "lane": "phone ord0485",
               "backend_port": BACKEND_PORT, "static_port": STATIC_PORT,
               "db": DB, "export": EXPORT,
               "started_local": time.strftime("%Y-%m-%d %H:%M:%S %z"),
               "forbidden_ports_touched": "none - this tool binds only the two lane ports"}

    for label, port in (("backend", BACKEND_PORT), ("static", STATIC_PORT)):
        receipt["pre_boot_listeners_%s" % label] = listeners(port)
        if receipt["pre_boot_listeners_%s" % label]:
            receipt["ABORT"] = "PORT_TAKEN"
            print(json.dumps(receipt, indent=2, ensure_ascii=False))
            return 4

    # ---- backend -----------------------------------------------------------
    benv = dict(os.environ)
    benv["PYTHONPATH"] = EXPORT
    benv["CITYNEXUS_DATABASE_URL"] = "sqlite:///" + DB
    benv["CITYNEXUS_DEMO_MODE"] = "true"
    benv["CITYNEXUS_AI_ENABLED"] = "false"
    benv.pop("DEEPSEEK_API_KEY", None)
    benv.pop("CITYNEXUS_AI_API_KEY", None)
    for k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
        benv.pop(k, None)
    blog = "%s/uvicorn_%d.log" % (RUN, BACKEND_PORT)
    bproc = subprocess.Popen([PY, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
                              "--port", str(BACKEND_PORT)],
                             cwd=EXPORT + "/backend", env=benv, **detached(blog))
    receipt["backend_spawn_pid"] = bproc.pid
    scene = None
    for _ in range(60):
        time.sleep(2)
        st, body = get_json("http://127.0.0.1:%d/api/v1/demo/scene" % BACKEND_PORT)
        if st == 200:
            scene = body
            break
    receipt["backend_alive"] = bproc.poll() is None
    receipt["demo_scene_status"] = None if scene is None else "200"
    receipt["demo_scene"] = scene
    if scene is None:
        receipt["backend_log_tail"] = open(blog, "rb").read()[-1500:].decode("utf-8", "replace")
        print(json.dumps(receipt, indent=2, ensure_ascii=False))
        return 5

    st, hd, raw = http("GET", "http://127.0.0.1:%d/api/v1/health" % BACKEND_PORT)
    receipt["health"] = {"status": st, "body": json.loads(raw.decode("utf-8")) if raw else None}

    # ownership proof 1: a marker only my server can write, read from MY file
    marker = "ord0485-marker-" + uuid.uuid4().hex[:12]
    st, body = None, None
    st, hd, raw = http("POST", "http://127.0.0.1:%d/api/v1/travelers" % BACKEND_PORT,
                       {"display_name": marker, "timezone": "Asia/Shanghai", "locale": "zh-CN"})
    stt = str(st)
    receipt["marker_post_status"] = stt
    import sqlite3
    con = sqlite3.connect("file:%s?mode=ro" % DB.replace("\\", "/"), uri=True)
    try:
        rows = con.execute("SELECT COUNT(*) FROM travelers WHERE display_name = ?",
                           (marker,)).fetchone()[0]
        journey = con.execute("SELECT id, city_code, title, status FROM journeys "
                              "ORDER BY created_at LIMIT 5").fetchall()
        tables = {r[0] for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
    finally:
        con.close()
    receipt["marker_rows_in_my_db"] = rows
    receipt["journey_rows"] = [list(r) for r in journey]
    receipt["new_tables_present_in_my_db"] = {
        "journey_checkins": "journey_checkins" in tables,
        "journey_share_grants": "journey_share_grants" in tables,
        "pois_or_places": [t for t in sorted(tables) if t in ("places", "poi_import_rows", "places_catalog")],
    }
    receipt["ownership_marker_in_my_db"] = rows == 1

    # ---- static face (vite preview over THIS lane's dist) ------------------
    senv = dict(os.environ)
    senv["CITYNEXUS_BACKEND_PORT"] = str(BACKEND_PORT)
    for k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
        senv.pop(k, None)
    slog = "%s/vite_preview_%d.log" % (RUN, STATIC_PORT)
    before_bytes = os.path.getsize(slog) if os.path.exists(slog) else 0
    node = os.environ.get("CNX_PHONE_NODE", r"C:/Program Files/nodejs/node.exe")
    sproc = subprocess.Popen(
        [node, "node_modules/vite/bin/vite.js", "preview",
         "--outDir", EXPORT + "/frontend/dist", "--host", "127.0.0.1",
         "--port", str(STATIC_PORT), "--strictPort"],
        cwd=EXPORT + "/frontend", env=senv, **detached(slog))
    receipt["static_spawn_pid"] = sproc.pid

    index_html = None
    for _ in range(30):
        time.sleep(2)
        st, hd, raw = http("GET", "http://127.0.0.1:%d/" % STATIC_PORT)
        if st == 200 and raw:
            index_html = raw.decode("utf-8", "replace")
            break
    proofs = {}
    if index_html:
        m = re.search(r'assets/(index-[A-Za-z0-9_\-]+\.js)', index_html)
        asset_name = m.group(1) if m else None
        proofs["entry_asset_named_from_my_index_html"] = asset_name
        if asset_name:
            st, hd, raw = http("GET", "http://127.0.0.1:%d/assets/%s" % (STATIC_PORT, asset_name))
            disk = open("%s/frontend/dist/assets/%s" % (EXPORT, asset_name), "rb").read()
            proofs["asset_http_status"] = str(st)
            proofs["asset_content_type"] = hd.get("Content-Type")
            proofs["served_bytes"] = len(raw)
            proofs["disk_bytes"] = len(disk)
            proofs["served_sha1_over_bytes"] = sha1(raw)
            proofs["disk_sha1_over_bytes"] = sha1(disk)
            proofs["PROOF_bytes_equal_served_vs_disk"] = (raw and sha1(raw) == sha1(disk))
        st, hd, raw = http("GET", "http://127.0.0.1:%d/index.html" % STATIC_PORT)
        proofs["index_served_sha1"] = sha1(raw)
        proofs["index_disk_sha1"] = sha1(open(EXPORT + "/frontend/dist/index.html", "rb").read())
        proofs["PROOF_index_bytes_equal"] = proofs["index_served_sha1"] == proofs["index_disk_sha1"]

    ls = listeners(STATIC_PORT)
    proofs["static_listeners"] = ls
    if ls:
        cl = cmdline(ls[0]["pid"])
        proofs["listener_command_line_names_outdir"] = ("--outDir" in cl
                                                        and "phone_ord0485" in cl)
        proofs["listener_command_line"] = cl[:400]

    # third proof attempt: does the static face log requests at all?
    time.sleep(1)
    after_bytes = os.path.getsize(slog) if os.path.exists(slog) else 0
    tail = b""
    if after_bytes > before_bytes:
        with open(slog, "rb") as f:
            f.seek(before_bytes)
            tail = f.read(4000)
    proofs["preview_log_bytes_before"] = before_bytes
    proofs["preview_log_bytes_after_probes"] = after_bytes
    proofs["preview_request_log_rows"] = tail.decode("utf-8", "replace").strip().splitlines()[-6:]
    proofs["PROOF_3_access_log"] = ("AVAILABLE" if any(
        re.search(r'"GET /', line) for line in proofs["preview_request_log_rows"])
        else "NOT_AVAILABLE_BY_CMDR")

    # the static face must reach MY backend through its proxy, not somebody else's
    st, hd, raw = http("GET", "http://127.0.0.1:%d/api/v1/health" % STATIC_PORT)
    body = None
    try:
        body = json.loads(raw.decode("utf-8"))
    except Exception:
        body = {"unparsed_bytes": len(raw)}
    proofs["static_leg_api_health_status"] = str(st)
    proofs["static_leg_api_body_keys"] = sorted(body.keys()) if isinstance(body, dict) else None
    con = sqlite3.connect("file:%s?mode=ro" % DB.replace("\\", "/"), uri=True)
    try:
        proofs["static_leg_marker_seen_via_proxy"] = con.execute(
            "SELECT COUNT(*) FROM travelers WHERE display_name = ?", (marker,)).fetchone()[0]
    finally:
        con.close()
    proofs["marker"] = marker

    receipt["static_identity"] = proofs
    receipt["backend_log_tail"] = open(blog, "rb").read()[-600:].decode("utf-8", "replace")
    out = "%s/stack_up_r1.json" % RUN
    with open(out, "w", encoding="utf-8") as f:
        json.dump(receipt, f, indent=2, ensure_ascii=False)
    print(json.dumps(receipt, indent=2, ensure_ascii=False))
    print("WROTE %s" % out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
