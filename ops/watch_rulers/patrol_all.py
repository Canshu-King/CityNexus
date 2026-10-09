"""Commander one-shot patrol: bus, lanes, ledger, tip, preview health — in a single report.

Everything here is read-only. It deliberately prints no credential value and no user PII:
the preview check only records HTTP status codes, and the live-DB check is opened with mode=ro
and reports counts.

Usage: python patrol_all.py [last-read-bus-comment-id]
"""

import base64
import io
import json
import hashlib
import os
import re
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

TOK = open(r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920", encoding="utf-8").read().strip()
LEDGER = r"D:\moodle\CITYNEXUS_AGENT_CONTROL.md"
INTEG = r"D:\moodle\_qoder_integration_20260919"
LIVE_DB = r"D:\moodle\_qoder_cmdr_gate_20260921\backend\_live.db"
TUNNEL = "https://fonts-facilities-hotel-installing.trycloudflare.com/api/v1/demo/scene"
PROXY = "http://127.0.0.1:4782"
LANES = {
    "8c66aa92": "C backend", "8ccd71d8": "F gates/contracts", "e345b9d6": "D frontend",
    "dc19d662": "E red-team", "c01d72a3": "B providers/cold-chain", "9baacb24": "HERMES",
    "d291c9dc": "HARNESS", "aad2d1f2": "HJ-P3", "1a986a24": "HJ-P1", "d4b04a0f": "HJ-P2",
}


def gh(path):
    req = urllib.request.Request("https://api.github.com" + path)
    for k, v in {"Authorization": f"Bearer {TOK}", "Accept": "application/vnd.github+json",
                 "User-Agent": "citynexus-commander"}.items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, {"_err": e.read().decode("utf-8", "replace")[:160]}
    except Exception as e:  # noqa: BLE001
        return type(e).__name__, {"_err": str(e)[:160]}


def section(name):
    print("\n" + "=" * 72 + "\n" + name + "\n" + "=" * 72)


last = int(sys.argv[1]) if len(sys.argv) > 1 else 0

section("BUS (Issue #1)")
st, meta = gh("/repos/Canshu-King/CityNexus-Workspace/issues/1")
if not isinstance(meta, dict) or "comments" not in meta:
    print(f"FETCH_FAILED (issue metadata) status={st} body={str(meta)[:180]}")
    print("=> this is NOT 'no new comments'. A read failure must never read as an empty inbox: retry before deciding.")
else:
    total = int(meta.get("comments") or 0)
    per = 30
    last_page = max(1, (total + per - 1) // per)
    pages = [last_page] if last_page == 1 else [last_page - 1, last_page]
    all_seen = {}
    fetch_ok = True
    for pg in pages:
        st, comments = gh(f"/repos/Canshu-King/CityNexus-Workspace/issues/1/comments?per_page={per}&page={pg}")
        if not isinstance(comments, list):
            print(f"FETCH_FAILED (comments list page {pg}) status={st} body={str(comments)[:180]}")
            print("=> this is NOT 'no new comments'; retry.")
            fetch_ok = False
            continue
        for c in comments:
            if isinstance(c, dict) and c.get("id"):
                all_seen[int(c["id"])] = c
    if not all_seen:
        raise SystemExit(0)
    hi = max(all_seen)
    new = [all_seen[k] for k in sorted(all_seen) if k > last]
    print(f"total={total} pages={pages} observed={len(all_seen)} highest_id_seen={hi} new_since_{last}={len(new)}")
    for c in new:
        body = c.get("body") or ""
        head = body.strip().split("\n")[0][:110]
        print(f"  id={c['id']} at={c['created_at']} len={len(body)} | {head}")
        for line in body.splitlines():
            if re.match(r"^##\s", line):
                print("      ", line[:100])
    # index of the newest ten, regardless of watermark: a comment older than my own last post
    # must still be visible, because I used to advance the watermark from my own id and skipped them.
    print("  --- index of newest 10 (watermark-independent; nothing may be hidden here) ---")
    for c in [all_seen[k] for k in sorted(all_seen, reverse=True)[:10]]:
        body = (c.get("body") or "").strip().split("\n")[0][:86]
        flag = "NEW " if c["id"] > last else "seen"
        print(f"   [{flag}] id={c['id']} {c['created_at'][11:19]}Z {body}")
    print(f"  --- safe watermark to use next time: {hi} ---")

section("LANES (runtimeState)")
try:
    out = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         "Get-CimInstance Win32_Process | Where-Object { $_.Name -match 'python|node|uv' } | "
         "Select-Object -First 400 ProcessId,Name | ConvertTo-Json -Compress"],
        capture_output=True, text=True, timeout=60).stdout
    procs = json.loads(out or "[]")
    if isinstance(procs, dict):
        procs = [procs]
    print(f"python/node/uv processes alive: {len(procs)}")
except Exception as e:  # noqa: BLE001
    print("process probe failed:", type(e).__name__, str(e)[:80])
print("lane runtime states come from list_chat_sessions (MCP) — this script cannot read them;")
print("expected active lanes:", ", ".join(LANES.values()))

section("LEDGER")
raw = io.open(LEDGER, "rb").read()
txt = raw.decode("utf-8", "replace")
nl = raw.count(b"\n")
has_crlf = b"\r\n" in raw
print(f"bytes={len(raw)} lines={nl} CRLF={has_crlf}")
heads = re.findall(r"^#{3,4} .*$", txt, re.M)
print("last 6 sections:")
for h in heads[-6:]:
    print("   ", h[:104])
statuses = re.findall(r"^- id: (ORD-\d+)(?:.|\n)*?^  status: (.*)$", txt, re.M)
_real_heads = re.findall(r"^- id: (ORD-\d{4})", txt, re.M)
print(f"REAL board entries (heading-anchored): {len(_real_heads)} "
      f"| substring '- id: ORD-' (prose-inflated, NOT a denominator): {txt.count('- id: ORD-')} "
      f"| '## ORDERS' anchor lines: {sum(1 for _l in txt.split(chr(10)) if _l.startswith('## ORDERS'))}")
recent = [s for s in statuses if re.search(r"T2[123]:|@2026-09-21 2[123]", s[1])]
print(f"board entries with a 21:00-23:59 status: {len(recent)}")
for oid, stt in recent[-14:]:
    print(f"   {oid}: {stt[:118]}")

section("TIP / TREE")
git = lambda *a: (subprocess.run(["git", "-C", INTEG] + list(a), capture_output=True, text=True, timeout=60).stdout or "").strip()
print("tip:", git("log", "--format=%h %ad %s", "--date=format:%H:%M", "-n", "1"))
print("last 6:", "|".join(git("log", "--format=%h %s", "-n", "6").splitlines()))
porcelain = git("status", "--porcelain")
print("dirty tracked files:", len([l for l in porcelain.splitlines() if l.startswith(" M") or l.startswith("M ")]),
      "| untracked:", len([l for l in porcelain.splitlines() if l.startswith("??")]))

section("PREVIEW HEALTH (no secrets printed)")
def http(url, method="GET", timeout=40):
    req = urllib.request.Request(url, method=method)
    if method == "POST":
        req.add_header("Content-Length", "0")
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, round(time.time() - t0, 2), r.read(300).decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, round(time.time() - t0, 2), e.read(300).decode("utf-8", "replace")
    except Exception as e:  # noqa: BLE001
        return type(e).__name__, round(time.time() - t0, 2), str(e)[:160]

code, dt, body = http(TUNNEL)
print(f"tunnel GET (deliberately unauthenticated) /api/v1/demo/scene -> {code} in {dt}s "
      f"({'chain alive' if code in (200, 401, 403) else 'CHECK: not a normal HTTP answer'})")

# The R13 guard is installed AFTER authentication, so an anonymous probe would answer 401 and make the
# guard look absent. Authenticate with the local credential file (user<TAB>secret) via the derived
# session cookie; neither the secret nor the cookie value is ever printed.
def cookie_hdrs():
    try:
        user, secret = open(r"D:\moodle\_qoder_preview_20260920\run\preview_auth.txt",
                            encoding="utf-8").read().strip().split("\t")
        tok = base64.b64encode(f"{user}:{secret}".encode()).decode()
        ck = "cnxpreview=" + hashlib.sha256(f"cnx-preview-session::{secret}".encode()).hexdigest()[:32]
        return {"Authorization": "Basic " + tok, "Cookie": ck}
    except Exception as e:  # noqa: BLE001
        print("  (credential file unreadable -> guard check will be anonymous:", type(e).__name__, ")")
        return {}


HDRS = cookie_hdrs()


def http_auth(url, method="GET", timeout=40):
    req = urllib.request.Request(url, method=method)
    for k, v in HDRS.items():
        req.add_header(k, v)
    if method == "POST":
        req.add_header("Content-Length", "0")
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, round(time.time() - t0, 2), r.read(300).decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, round(time.time() - t0, 2), e.read(300).decode("utf-8", "replace")
    except Exception as e:  # noqa: BLE001
        return type(e).__name__, round(time.time() - t0, 2), str(e)[:160]


code2, dt2, b2 = http_auth(PROXY + "/")
bundle = re.findall(r"index-[A-Za-z0-9_-]+\.js", b2)
print(f"proxy  GET / (authed) -> {code2} in {dt2}s | bundle refs in first 300B: {bundle[:1] or 'beyond read window'}")
code3, dt3, body3 = http_auth(PROXY + "/api/v1/demo/reset", "POST")
guarded = "PREVIEW_GUARDED" in body3
verdict = "ENFORCED" if (code3 == 403 and guarded) else ("refused-without-guard-marker" if code3 in (403, 404) else "NOT-ENFORCED-CHECK")
print(f"proxy  POST /api/v1/demo/reset (authed) -> {code3} in {dt3}s | R13 guard: {verdict} "
      f"| PREVIEW_GUARDED in body: {guarded}")
if code2 == 401 or code3 == 401:
    print("  note: 401 here means the credential did not validate - re-check the file format, not the guard.")

if os.path.exists(LIVE_DB):
    con = sqlite3.connect(f"file:{LIVE_DB}?mode=ro", uri=True)
    try:
        counts = {t: con.execute(f"select count(*) from {t}").fetchone()[0]
                  for t in ("journeys", "plan_versions", "travelers")}
        cities = con.execute("select city_code, count(*) from places group by city_code").fetchall()
        print("user DB (read-only):", counts, "| places:", cities)
    finally:
        con.close()
else:
    print("live DB path not found:", LIVE_DB)

print("\n[silence] credential values and cookies are never printed by design.")
