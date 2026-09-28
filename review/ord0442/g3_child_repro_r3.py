"""ORD-0442 - why does G3's two-uvicorn door die on a connection that is never refused by hand?

The door (`backend/tests/test_qoder_g3_xproc_http.py`) spawns two real uvicorn children and polls
`http://127.0.0.1:<port>/api/v1/health` with `urllib.request.urlopen`.  On this machine it aborts with
`[WinError 10061]` inside the *first* poll, before the child has had any chance to answer - and the
same process can talk to the same child fine when the proxy variables are out of the way.

This script separates the two possibilities and names which leg died:

  arm A  env exactly as a plain terminal has it (this box exports HTTP(S)_PROXY to a port nobody listens on)
  arm B  same child, same port, proxy variables removed from the environment
  arm C  a raw socket to the child (no urllib, no proxy handling at all), in both envs

Usage: python g3_child_repro_r3.py <tree-root> <out-json> [A|B|C]
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

TREE = Path(sys.argv[1]).resolve()
OUT = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else Path("g3_child_repro_r3.json")
BACKEND = TREE / "backend"
WORKER = BACKEND / "tests" / "_qoder_g3_http_worker.py"
PROXY_NAMES = ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy")
DEAD_PROXY = "http://127.0.0.1:7892"


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _env(strip_proxy: bool) -> dict:
    env = dict(os.environ)
    if strip_proxy:
        for name in PROXY_NAMES:
            env.pop(name, None)
    else:
        for name in ("HTTP_PROXY", "HTTPS_PROXY"):
            env[name] = DEAD_PROXY
    env["NO_PROXY"] = "localhost,127.0.0.1,::1"
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONPATH"] = os.pathsep.join(p for p in (str(TREE), str(BACKEND), env.get("PYTHONPATH", "")) if p)
    for name in ("DEEPSEEK_API_KEY", "OPENAI_API_KEY", "CITYNEXUS_AI_API_KEY", "CITYNEXUS_AI_ENABLED"):
        env.pop(name, None)
    return env


def _spawn(port: int, database_url: str, log: Path, env: dict):
    handle = log.open("wb")
    proc = subprocess.Popen(
        [sys.executable, "-X", "utf8", str(WORKER), str(port), database_url],
        cwd=str(BACKEND), stdout=handle, stderr=subprocess.STDOUT, env=env,
    )
    return proc, handle


def _urllib_probe(port: int, env: dict, label: str) -> dict:
    """A child process with that environment asks the URL, so proxy handling is the variable."""
    script = (
        "import json,urllib.request,urllib.error\n"
        f"URL='http://127.0.0.1:{port}/api/v1/health'\n"
        "try:\n"
        "    r=urllib.request.urlopen(URL,timeout=4)\n"
        "    print(json.dumps({'outcome':'answered','status':r.status,'url':URL}))\n"
        "except urllib.error.URLError as e:\n"
        "    print(json.dumps({'outcome':'URLError','reason_type':type(e.reason).__name__,'reason':str(e.reason)[:120],'url':URL}))\n"
        "except Exception as e:\n"
        "    print(json.dumps({'outcome':type(e).__name__,'reason':str(e)[:120]}))\n"
    )
    proc = subprocess.run([sys.executable, "-X", "utf8", "-c", script], env=env,
                          capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30)
    line = (proc.stdout or "").strip().splitlines()
    return {"arm": label, "child_exit": proc.returncode,
            "reported": json.loads(line[-1]) if line else None,
            "stderr_tail": (proc.stderr or "")[-200:]}


def _raw_socket_probe(port: int) -> dict:
    started = time.perf_counter()
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=4.0):
            return {"connect": "ok", "ms": round((time.perf_counter() - started) * 1000, 1)}
    except OSError as exc:
        return {"connect": type(exc).__name__, "errno": getattr(exc, "errno", None),
                "strerror": str(exc)[:120], "ms": round((time.perf_counter() - started) * 1000, 1)}


def main() -> int:
    sys.path.insert(0, str(BACKEND))
    os.environ["CITYNEXUS_DATABASE_URL"] = "sqlite:///" + (Path(tempfile.mkdtemp()) / "repro.db").as_posix()
    os.environ["CITYNEXUS_DEMO_MODE"] = "true"
    from app.db.session import ensure_schema, make_engine  # noqa: PLC0415

    temp_dir = Path(tempfile.mkdtemp(prefix="cnx_g3repro_"))
    database = temp_dir / "workers.db"
    url = f"sqlite:///{database.as_posix()}"
    engine = make_engine(url)
    ensure_schema(engine)
    engine.dispose()

    receipt: dict = {"tree": str(TREE).replace("\\", "/"), "arms": [], "python": sys.executable}

    for label, strip in (("A_default_env_with_dead_proxy", False), ("B_proxy_vars_removed", True)):
        port = _free_port()
        log = temp_dir / f"worker_{port}.log"
        env = _env(strip)
        proc, handle = _spawn(port, url, log, env)
        waited = 0.0
        served = None
        attempts: list[dict] = []
        while waited < 45.0:
            if proc.poll() is not None:
                served = {"child_exit": proc.returncode}
                break
            raw = _raw_socket_probe(port)
            attempts.append({"at_s": round(waited, 1), **raw})
            if raw["connect"] == "ok":
                served = {"child_alive": True, "raw_socket": raw}
                break
            time.sleep(0.5)
            waited += 0.5
        urllib_read = _urllib_probe(port, env, label)
        tail = log.read_text(encoding="utf-8", errors="replace")[-900:]
        proc.terminate()
        handle.close()
        receipt["arms"].append({
            "arm": label,
            "env_proxy_values": {k: env.get(k) for k in ("HTTP_PROXY", "HTTPS_PROXY", "NO_PROXY")},
            "port": port,
            "waited_s": round(waited, 1),
            "readiness_attempts_head": attempts[:4],
            "readiness_attempt_count": len(attempts),
            "ready_reading": served,
            "urllib_leg": urllib_read,
            "child_log_tail": tail,
        })

    OUT.write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8")
    print("wrote", str(OUT).replace("\\", "/"), "arms", len(receipt["arms"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
