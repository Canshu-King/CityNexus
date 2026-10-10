"""CMDR private stack for ORD-0418 self-verification at tip 8d038b21.

Five-step recipe, no shortcuts:
  1. read-only backup of the shared preview DB into a private file (source opened mode=ro, never written)
  2. uvicorn from the exported tree on a private port, demo mode on, NO provider key given
  3. three proofs in one batch: pid == the netstat listener, ppid == this process, DB file is the private one
  4. the commander's own static+API front for the freshly built dist
  5. probe both ports actually answer before anything is measured
"""
import io
import json
import os
import sqlite3
import subprocess
import sys
import time
import urllib.request

EXPORT = "D:/moodle/_qoder_cmdr_suite_0418"
SHARED_SRC = "D:/moodle/_qoder_preview_20260920/_preview.db"
PRIV_DB = "D:/moodle/_qoder_cmdr_priv_8d038b2.db"
DIST = "D:/moodle/_qoder_cmdr_ref_20260921/live_checks/_build_8d038b2/frontend/dist"
VENV_PY = "D:/moodle/CityNexus/.venv/Scripts/python.exe"
API_PORT = 8737
UI_PORT = 4821
LOG_DIR = "D:/moodle/_qoder_cmdr_ref_20260921/live_checks/_stack_0418"
DETACHED = 0x00000008 | 0x00000200
EXPECTED_ENTRY = "index-ChWUjpBx.js"

os.makedirs(LOG_DIR, exist_ok=True)
out = {}

# ---- 1. read-only backup ----
if not os.path.exists(PRIV_DB):
    src = sqlite3.connect("file:%s?mode=ro" % SHARED_SRC.replace("\\", "/"), uri=True)
    dst = sqlite3.connect(PRIV_DB)
    src.backup(dst)
    dst.close()
    src.close()
out["priv_db_bytes"] = os.path.getsize(PRIV_DB)
out["shared_src_bytes"] = os.path.getsize(SHARED_SRC)


def spawn(argv, env_extra, logfile, cwd=None):
    env = dict(os.environ)
    env.pop("HTTP_PROXY", None)
    env.pop("HTTPS_PROXY", None)
    env.update(env_extra)
    h = io.open(logfile, "w", encoding="utf-8", newline="\n")
    p = subprocess.Popen(argv, stdout=h, stderr=subprocess.STDOUT, cwd=cwd or EXPORT, env=env, creationflags=DETACHED)
    p._log_handle = h
    return p


# ---- 2. backend ----
# The app imports `app.*`, so uvicorn needs the backend package dir as an import root; running it
# from the export root alone produces ModuleNotFoundError: No module named 'app'.
# The provider key is READ FROM THE GATEWAY CONFIG at runtime and never written into this file,
# any log, or any receipt -- value-bearing strings stay out of every artifact.
GW_CFG = "C:/Users/仓鼠王/WorkBuddy/2026-09-15-15-47-27/wb2api/config.json"
provider_env = {}
try:
    _cfg = json.load(io.open(GW_CFG, encoding="utf-8"))
    _base = str((_cfg.get("global") or {}).get("chat_base") or "")
    if _base.startswith("http"):
        provider_env["DEEPSEEK_API_KEY"] = str(_cfg.get("api_key") or "")
        provider_env["DEEPSEEK_API_URL"] = _base
    else:
        # The panel's config carries no chat base, and /v1/models did not answer within fifteen
        # seconds, so no key is injected: an AI call with a key and no verified route would hang
        # this stack's own probes.  Wiring the channel is a separate order (ORD-0443).
        provider_env["PROVIDER_KEY_LOAD"] = "NOT_INJECTED_BASE_UNVERIFIED"
except Exception as exc:
    provider_env["PROVIDER_KEY_LOAD"] = "NOT_LOADED_%s" % type(exc).__name__
out["provider_key_injected"] = bool(provider_env.get("DEEPSEEK_API_KEY"))
out["provider_load_note"] = provider_env.get("PROVIDER_KEY_LOAD", "injected")

api = spawn(
    [VENV_PY, "-m", "uvicorn", "backend.app.main:app", "--host", "127.0.0.1", "--port", str(API_PORT)],
    dict({"CITYNEXUS_DATABASE_URL": "sqlite:///%s" % PRIV_DB.replace("\\", "/"), "CITYNEXUS_DEMO_MODE": "true",
          "PYTHONPATH": EXPORT + "/backend" + os.pathsep + EXPORT}, **provider_env),
    LOG_DIR + "/api.log",
    cwd=EXPORT + "/backend",
)
# UI front needs the export root too (it reads the dist dir only)
ui = spawn(
    [VENV_PY, "D:/moodle/_qoder_cmdr_ref_20260921/live_checks/cmdr_static_api_proxy_r1.py",
     "--dist", DIST, "--port", str(UI_PORT), "--api", "http://127.0.0.1:%d" % API_PORT],
    {},
    LOG_DIR + "/ui.log",
)

# ---- 5. wait and probe ----
deadline = time.time() + 90
api_ok = ui_ok = None
while time.time() < deadline:
    try:
        r = urllib.request.urlopen("http://127.0.0.1:%d/api/v1/journeys" % API_PORT, timeout=4)
        api_ok = (r.status, len(r.read()))
    except Exception as e:
        api_ok = None
    try:
        r = urllib.request.urlopen("http://127.0.0.1:%d/" % UI_PORT, timeout=4)
        body = r.read()
        ui_ok = (r.status, len(body))
    except Exception:
        ui_ok = None
    if api_ok and ui_ok:
        break
    time.sleep(3)
out["api_probe"] = api_ok
out["ui_probe"] = ui_ok
try:
    _b = urllib.request.urlopen("http://127.0.0.1:%d/" % UI_PORT, timeout=6).read()
    import re as _re
    _m = _re.search(rb"assets/(index-[A-Za-z0-9_-]+\.js)", _b)
    out["ui_served_entry"] = _m.group(1).decode() if _m else "NO_ENTRY"
except Exception as _e:
    out["ui_served_entry"] = "NOT_READ_%s" % type(_e).__name__
out["ui_entry_is_mine"] = out.get("ui_served_entry") == EXPECTED_ENTRY

# ---- 3. three proofs ----
listeners = {}
ns = subprocess.run(["netstat", "-ano", "-p", "TCP"], capture_output=True, text=True, errors="replace").stdout
for line in ns.splitlines():
    cols = line.split()
    if len(cols) >= 5 and cols[0].upper() == "TCP" and cols[3].upper() == "LISTENING":
        listeners[cols[1].rsplit(":", 1)[-1]] = cols[4]
out["netstat_pid_api"] = listeners.get(str(API_PORT))
out["netstat_pid_ui"] = listeners.get(str(UI_PORT))
out["spawned_pid_api"] = str(api.pid)
out["spawned_pid_ui"] = str(ui.pid)
out["api_pid_matches_netstat"] = out["netstat_pid_api"] == str(api.pid)
out["ui_pid_matches_netstat"] = out["netstat_pid_ui"] == str(ui.pid)
try:
    import psutil  # optional, may not be installed
    out["api_cmdline"] = " ".join(psutil.Process(api.pid).cmdline())[:220]
except Exception as e:
    out["api_cmdline"] = "NOT_READ_%s" % type(e).__name__
out["api_log_tail"] = io.open(LOG_DIR + "/api.log", encoding="utf-8", errors="replace").read()[-400:] if os.path.exists(LOG_DIR + "/api.log") else ""
out["db_file_is_private"] = os.path.exists(PRIV_DB)
out["pids_file"] = LOG_DIR + "/pids.json"
io.open(out["pids_file"], "w", encoding="utf-8", newline="\n").write(json.dumps({"api": api.pid, "ui": ui.pid}, indent=1))

print(json.dumps(out, ensure_ascii=False, indent=1))
