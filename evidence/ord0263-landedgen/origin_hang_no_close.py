"""ORD-0263 §⑤ instrument: an origin that hangs reads and NEVER closes them, with a side log that proves it.

Why this replaces `mixed_origin_port.py` for this round: the commander's new constraint is
*"这次不允许由仪器替产品收口"*. The old instrument hung a read for 40 s and then closed the socket, which is
exactly what let the shipped-but-unfixed bundle appear to classify at 40.311 s - my instrument ended the read,
the product did not. So here a hung read is held open until either the run is torn down or **the browser gives
up on it**, and the handler records which of the two happened.

That gives the two-sided evidence §⑤ asks for, and it comes out of the instrument rather than out of me:

* `closed_by_instrument == 0` throughout - nothing on my side ever ended a read;
* a client abort observed by the server (`recv` returning b"" while still open on my side) is the browser's own
  deadline firing, and `abandoned_after_s` times it independently of the page sampler;
* if the page settles and NO abandon is ever recorded, the cell is `NOT_PRODUCT_BOUND` and must be written as such.

Two modes, one code path, so the only difference between the states is whether `/api/v1/health` answers:
  answered-health  -> /api/v1/health = 500 json (an origin that spoke and spoke badly), everything else hangs
  fully-silent     -> nothing is ever answered, including /health

Loopback only, my own port, hard ceiling, and the side log is appended every 5 s so a later read of
"who ended the read" is a file reading, not a memory.
"""
from __future__ import annotations

import http.server
import json
import socket
import socketserver
import sys
import threading
import time

PORT = 8411
CEILING_SECONDS = 1500
MODE = (sys.argv[1] if len(sys.argv) > 1 else "answered-health")
LOG = rf"D:\moodle\_qoder_harness_ord0254\ord0263_origin_state_{MODE.replace('-', '_')}.log"

STATE = {"opened": 0, "answered_health": 0, "hung_now": 0, "closed_by_instrument": 0,
         "abandoned_by_client": 0, "still_open": 0, "events": []}
LOCK = threading.Lock()


def log(kind: str, **kw) -> None:
    row = {"at": time.strftime("%H:%M:%S", time.localtime()), "t_s": round(time.time() - T0, 2),
           "kind": kind}
    row.update(kw)
    with LOCK:
        STATE["events"].append(row)
        with open(LOG, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


class Handler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_GET(self):  # noqa: N802
        if self.path.startswith("/api/v1/health") and MODE == "answered-health":
            body = b'{"detail":"instrument: origin answered badly on purpose"}'
            with LOCK:
                STATE["answered_health"] += 1
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            log("health_answered_500", path=self.path)
            return
        self.hang()

    def do_POST(self):  # noqa: N802
        self.hang()

    def hang(self):
        path = self.path
        started = time.time()
        with LOCK:
            STATE["opened"] += 1
            STATE["hung_now"] += 1
            n = STATE["opened"]
        log("read_opened_hanging", path=path, hung_no=n)
        self.connection.settimeout(1.0)
        outcome = "ceiling"
        while time.time() - started < CEILING_SECONDS:
            try:
                data = self.connection.recv(1)
            except socket.timeout:
                continue
            except OSError:
                outcome = "socket_error"
                break
            if data == b"":
                # the peer sent FIN: the browser gave up on this read on its own
                outcome = "abandoned_by_client"
                break
        age = round(time.time() - started, 2)
        with LOCK:
            STATE["hung_now"] -= 1
            if outcome == "abandoned_by_client":
                STATE["abandoned_by_client"] += 1
            else:
                STATE["still_open"] += 1
        log("read_ended", path=path, age_s=age, outcome=outcome,
            closed_by_instrument=False)
        self.close_connection = True

    def log_message(self, *a):  # keep the side log the only channel
        pass


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


T0 = time.time()


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"at": time.strftime("%H:%M:%S", time.localtime()), "t_s": 0.0,
                             "kind": "instrument_start", "mode": MODE, "port": PORT,
                             "never_closes_hangs": True}, ensure_ascii=False) + "\n")
    with Server(("127.0.0.1", PORT), Handler) as srv:
        t = threading.Thread(target=srv.serve_forever, daemon=True)
        t.start()
        print(f"origin mode={MODE} on :{PORT}; side log {LOG}", flush=True)
        try:
            while time.time() - T0 < CEILING_SECONDS:
                time.sleep(5)
                with LOCK:
                    snap = {k: v for k, v in STATE.items() if k != "events"}
                    snap["kind"] = "state"
                    snap["mode"] = MODE
                    snap["t_s"] = round(time.time() - T0, 2)
                    snap["at"] = time.strftime("%H:%M:%S", time.localtime())
                with open(LOG, "a", encoding="utf-8") as fh:
                    fh.write(json.dumps(snap, ensure_ascii=False) + "\n")
        except KeyboardInterrupt:
            pass
    srv.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
