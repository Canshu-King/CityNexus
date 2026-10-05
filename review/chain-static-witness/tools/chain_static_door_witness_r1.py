"""Independent witness on the phone-chain static door :4783 -- read-only, and it does not re-run the other
lane's script.

Why a separate instrument is worth a turn: another lane reported that the static door accepts and returns
nothing (`http=000` in ~3 ms on five paths, `net::ERR_EMPTY_RESPONSE` in a browser) while the api door on
:4787 still answers 200.  That blocks my real-device cell, and the cause they named -- the served day33 build
-- is a hypothesis I cannot check by re-running their curl loop.  So this probe changes three things:

  * a different client (urllib, plus a raw socket that prints how many bytes come back before EOF), so a curl
    quirk cannot be the whole story;
  * it asks WHO owns the listening socket and what command line that PID carries -- a door held by a process
    that is not the expected static server explains 3ms-empty far better than a missing asset does;
  * it asks whether the directory that server claims to serve still exists and is non-empty, with the check
    done on the path read out of the command line, not typed from memory.

Nothing here restarts, kills, or rebinds anything: other people's processes are not mine to touch.
"""
import json
import os
import socket
import subprocess
import urllib.error
import urllib.request
from datetime import datetime

LANE = r"D:/moodle/_qoder_82f55d8a_ord0567_sweep".replace("_qoder_82f55d8a_ord0567_sweep",
                                                          "_qoder_phone_ord0485_20260930")
PATHS = ["/", "/v8/hub", "/index.html", "/favicon.svg", "/assets/", "/v8/trips", "/__probe_missing_zz"]
API_PATH = "http://127.0.0.1:4787/api/v1/health"
API_CONTROL = "http://127.0.0.1:4787/api/v1/journeys"


def run(cmd):
    p = subprocess.run(cmd, capture_output=True, timeout=60)
    return p.returncode, p.stdout.decode("utf-8", "replace"), p.stderr.decode("utf-8", "replace")


def http_get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "cnx-0afdb49b-witness/1"})
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            body = r.read(4096)
            return {"url": url, "status": r.status, "bytes": len(body), "ctype": r.headers.get("Content-Type")}
    except urllib.error.HTTPError as e:
        return {"url": url, "status": e.code, "bytes": len(e.read(4096)), "class": "HTTPError"}
    except Exception as e:
        return {"url": url, "status": "NO_RESPONSE", "error": type(e).__name__ + ": " + str(e)[:90]}


def raw_socket(url):
    """What the wire actually says: connect, send one request, count bytes until the peer closes."""
    host, port, path = "127.0.0.1", 4783, url.split("4783", 1)[1] or "/"
    s = socket.socket()
    s.settimeout(8)
    total = b""
    try:
        s.connect((host, port))
        s.sendall(("GET " + path + " HTTP/1.0\r\nHost: 127.0.0.1:4783\r\n\r\n").encode())
        while True:
            chunk = s.recv(4096)
            if not chunk:
                break
            total += chunk
            if len(total) > 65536:
                break
        return {"path": path, "bytes_received": len(total), "first_bytes": total[:60].decode("latin1")}
    except Exception as e:
        return {"path": path, "error": type(e).__name__ + ": " + str(e)[:90]}
    finally:
        s.close()


def owners(port):
    rc, out, _e = run(["netstat", "-ano", "-p", "TCP"])
    rows = [l.split() for l in out.splitlines() if (" LISTENING ") in (" " + l.replace("\r", "") + " ") or
            l.strip().endswith("LISTENING") or "LISTENING" in l]
    pids = sorted({r[-1] for r in rows if len(r) >= 5 and r[1].endswith(":" + str(port))})
    procs = []
    for pid in pids:
        rc2, out2, _e2 = run(["powershell", "-NoProfile", "-Command",
                              "Get-CimInstance Win32_Process -Filter \"ProcessId=%s\" | "
                              "Select-Object -ExpandProperty CommandLine" % pid])
        procs.append({"pid": pid, "command_line": out2.strip()[:400]})
    return {"port": port, "listening_pids": pids, "processes": procs}


def main():
    got = [http_get("http://127.0.0.1:4783" + p) for p in PATHS]
    raws = [raw_socket("http://127.0.0.1:4783" + p) for p in ["/", "/index.html"]]
    api = http_get(API_PATH)
    api_control = http_get(API_CONTROL)
    stat_owner, api_owner = owners(4783), owners(4787)
    served = []
    for pr in stat_owner["processes"]:
        cl = pr["command_line"]
        for token in cl.replace("\\", "/").split():
            if token and os.path.exists(token) and os.path.isdir(token):
                entries = os.listdir(token)
                served.append({"path": token, "entries": len(entries),
                               "has_index_html": any(e == "index.html" for e in entries),
                               "asset_dirs": sorted({e for e in entries if e.startswith("assets") or
                                                     e.endswith(".html")})[:6]})
                break
    no_response = sum(1 for g in got if g.get("status") == "NO_RESPONSE")
    out = {"schema": "CNX_CHAIN_STATIC_DOOR_WITNESS_V1", "tool": "chain_static_door_witness_r1",
           "took_local": datetime.now().astimezone().isoformat(), "probed_paths": len(got),
           "no_response": no_response, "statuses": [str(g.get("status")) for g in got],
           "reads": got, "raw_sockets": raws, "api_health": api, "api_control": api_control,
           "static_owner": stat_owner, "api_owner": api_owner, "served_dirs": served,
           "actions_taken": {"restarts": 0, "kills": 0, "rebinds": 0, "writes_to_other_lanes": 0}}
    dest = os.path.join(LANE, "evidence", "chain_static_door_witness_r1.json")
    json.dump(out, open(dest, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print(json.dumps({"probed_paths": len(got), "no_response": no_response,
                      "statuses": [str(g.get("status")) for g in got],
                      "api_health": str(api.get("status")), "api_control": str(api_control.get("status")),
                      "static_pids": stat_owner["listening_pids"], "api_pids": api_owner["listening_pids"],
                      "raw": [(r.get("path"), r.get("bytes_received", r.get("error"))) for r in raws],
                      "served": served}, ensure_ascii=False, indent=1))
    for pr in stat_owner["processes"]:
        print("static pid", pr["pid"], "|", pr["command_line"][:220])
    print("WROTE " + dest)


if __name__ == "__main__":
    main()
