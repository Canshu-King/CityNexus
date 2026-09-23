"""ORD-0263 A3 run: a write leg that never settles, on a surface whose ownership I prove first.

Same swapped-origin surface as the S5 reproduction, but this time the origin is the ONLY thing on the
port (no real backend), so:
  - I re-measure S5 a second time, from a second browser generation, to show the fifth state is not a
    one-off of my first run;
  - I then walk the real onboarding wizard and press 确认创建, where the origin accepts the POST and
    never answers it, and sample what the screen says for 35 s.

Ownership proved before any reading is trusted: the port answers with MY origin's own marker, and the
document served is byte-compared against the index.html of MY dist directory.
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import time
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
BASE = pathlib.Path(r"D:\moodle\_qoder_b_ord0263_20260923")
SPIKE = pathlib.Path(r"D:\moodle\_qoder_spike_20260921")
GENB = pathlib.Path(r"D:\moodle\_qoder_b_ord0268_20260923\genB\frontend")
PY = r"D:\moodle\CityNexus\.venv\Scripts\python.exe"
BACKEND_PORT, PREVIEW_PORT = 8441, 4441
DIST = GENB / "dist_ord0268"
DETACHED = 0x00000008 | 0x00000200


def listeners(port):
    out = subprocess.run(["netstat", "-ano"], capture_output=True, text=True,
                         encoding="utf-8", errors="replace").stdout
    return sorted({int(m.group(2)) for m in
                   re.finditer(r"TCP\s+\S+:(\d+)\s+\S+\s+LISTENING\s+(\d+)", out) if int(m.group(1)) == port})


def get(url, timeout=8):
    try:
        with urllib.request.urlopen(urllib.request.Request(url), timeout=timeout) as r:
            return r.status, r.headers.get_content_type(), r.read()
    except Exception as e:  # noqa: BLE001
        return None, type(e).__name__, b""


def spawn(cmd, cwd, log, env):
    with open(log, "a", encoding="utf-8") as fh:
        return subprocess.Popen(cmd, cwd=str(cwd), env=env, stdout=fh, stderr=subprocess.STDOUT,
                                creationflags=DETACHED)


def kill(pids):
    for pid in dict.fromkeys(pids):
        subprocess.run(["taskkill", "/PID", str(pid), "/F"], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")


def sha(b):
    return hashlib.sha256(b).hexdigest()[:16] if isinstance(b, bytes) else sha(b.encode("utf-8"))


def main() -> int:
    for p in (BACKEND_PORT, PREVIEW_PORT):
        if listeners(p):
            print(f"ABORT: :{p} already answers {listeners(p)}")
            return 2
    shutil.rmtree(BASE / "profile_a3w", ignore_errors=True)
    (BASE / "profile_a3w").mkdir(parents=True, exist_ok=True)
    (BASE / "s5_counts.json").unlink(missing_ok=True)
    env = dict(os.environ) | {"PYTHONIOENCODING": "utf-8"}

    html = spawn([PY, str(SPIKE / "q263_html_origin.py"), "--port", str(BACKEND_PORT)],
                 SPIKE, BASE / "a3_html_origin.log", env)
    pv = spawn(["node", "node_modules/vite/bin/vite.js", "preview", "--outDir", "dist_ord0268",
                "--port", str(PREVIEW_PORT), "--strictPort", "--host", "127.0.0.1"],
               GENB, BASE / "a3_preview.log", env | {"CITYNEXUS_BACKEND_PORT": str(BACKEND_PORT)})

    ok = None
    for _ in range(60):
        if listeners(BACKEND_PORT) and listeners(PREVIEW_PORT) and get(f"http://127.0.0.1:{PREVIEW_PORT}/")[0] == 200:
            ok = True
            break
        time.sleep(1)
    if not ok:
        print("ABORT: surface never came up")
        return 3

    # ---- ownership, both directions
    direct_health = get(f"http://127.0.0.1:{BACKEND_PORT}/api/v1/health")
    proxy_health = get(f"http://127.0.0.1:{PREVIEW_PORT}/api/v1/health")
    proxy_doc = get(f"http://127.0.0.1:{PREVIEW_PORT}/v8/hub")
    disk_doc = (DIST / "index.html").read_bytes()
    assets = sorted(p.name for p in (DIST / "assets").iterdir())[:6]
    doc_from_my_dist = proxy_doc[2] == disk_doc
    mine = b"ord0263-s5" in proxy_health[2]
    print(f"ownership: origin marker via proxy={mine}  served doc == my dist/index.html={doc_from_my_dist} "
          f"(proxy {sha(proxy_doc[2])} vs disk {sha(disk_doc)})")
    ownership_detail = {"served_len": len(proxy_doc[2]), "disk_len": len(disk_doc)}
    if not doc_from_my_dist:
        ownership_detail["served_head"] = proxy_doc[2][:160].decode("utf-8", "replace")
        ownership_detail["disk_head"] = disk_doc[:160].decode("utf-8", "replace")

    # ---- S5, second generation, on the profile that already holds a journey and a snapshot
    r1 = subprocess.run(["node", str(SPIKE / "q263_read_page.js"),
                         "--url", f"http://127.0.0.1:{PREVIEW_PORT}/v8/hub",
                         "--profile", str(BASE / "profile_s5"),
                         "--out", str(BASE / "s5_second.json"), "--window", "25",
                         "--label", "S5_second_generation"],
                        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=400)
    print("  " + (r1.stdout or "").strip().splitlines()[-1] if (r1.stdout or "").strip() else f"  S5-2 rc={r1.returncode}")
    s5b = json.loads((BASE / "s5_second.json").read_text(encoding="utf-8")) if (BASE / "s5_second.json").exists() else {"missing": True}

    # ---- A3: real wizard, real 确认创建, POST that never answers
    r2 = subprocess.run(["node", str(SPIKE / "q263_a3_leg.js"),
                         "--url", f"http://127.0.0.1:{PREVIEW_PORT}/v8/hub",
                         "--profile", str(BASE / "profile_a3w"),
                         "--out", str(BASE / "a3_leg.json"), "--seconds", "35"],
                        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600)
    print("  " + (r2.stdout or "").strip().splitlines()[-1] if (r2.stdout or "").strip() else f"  A3 rc={r2.returncode}")
    a3 = json.loads((BASE / "a3_leg.json").read_text(encoding="utf-8")) if (BASE / "a3_leg.json").exists() else {"missing": True, "stderr": (r2.stderr or "")[-400:]}

    counters = (BASE / "s5_counts.json")
    kill(listeners(BACKEND_PORT) + [html.pid] + listeners(PREVIEW_PORT) + [pv.pid])

    out = {"at": time.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
           "order": "ORD-0263 A3 判定 + S5 第二代复现",
           "lane": "B c01d72a3",
           "surface": {"preview_port": PREVIEW_PORT, "origin_port": BACKEND_PORT,
                       "served_build": "dist_ord0268 (landed tip 2b49e3ca, contains ORD-0263)",
                       "origin": "q263_html_origin.py: GET /api/* -> 200 text/html, /api/*/health -> 200 json, POST -> never answers",
                       "browser_mocks": "none",
                       "forbidden_ports_never_requested": [4781, 4782, 8693, 4185, 8713]},
           "ownership_proofs": {"origin_marker_seen_through_proxy": mine,
                                "proxy_health_body_head": proxy_health[2][:80].decode("utf-8", "replace"),
                                "direct_health": [direct_health[0], direct_health[1]],
                                "served_document_equals_my_dist_index": doc_from_my_dist,
                                "served_doc_sha16": sha(proxy_doc[2]), "my_dist_index_sha16": sha(disk_doc),
                                **ownership_detail,
                                "my_dist_assets_sample": assets},
           "S5_second_generation": s5b, "A3": a3,
           "origin_counters": json.loads(counters.read_text(encoding="utf-8")) if counters.exists() else None}
    p = BASE / "q263_a3_reproduction.json"
    p.write_text(json.dumps(out, ensure_ascii=False, indent=1), "utf-8", newline="\n")

    print("\nS5 second:", json.dumps((s5b.get("app_attribution") or {}).get("last"), ensure_ascii=False)[:200])
    print("S5 screen  :", repr((s5b.get("rendered_text") or "").replace("\n", " ")[:140]))
    print("A3 writes  :", json.dumps(a3.get("writes_seen"), ensure_ascii=False)[:200])
    print("A3 settled :", json.dumps(a3.get("write_responses_settled"), ensure_ascii=False)[:120])
    print("A3 blames  :", a3.get("ever_blamed_network_or_origin"), " stop door:", "used" if a3.get("stop_waiting_used") else "not used")
    print("A3 phases  :", json.dumps(a3.get("phase_lines_seen"), ensure_ascii=False)[:200])
    print("A3 lines   :", json.dumps(a3.get("sentences_ever_on_screen"), ensure_ascii=False)[:520])
    print("counters   :", out["origin_counters"])
    print("->", p.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
