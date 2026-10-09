"""ORD-0395, after the change: real uvicorn again, so the served document in the evidence file is
the one this tree actually produces."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

WT = Path(r"D:/moodle/_qoder_lane_heyuegong_20261009/wt")
BACKEND = WT / "backend"
PYTHON = Path(r"D:/moodle/CityNexus/backend/.venv/Scripts/python.exe")
SCRATCH = Path(r"E:/heyuegong_0395")
OUT = WT / "review" / "ord0395" / "UVICORN_READINGS_R1.txt"
TOKEN = "ord0395-armed-token"
PORT = 47914

opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def http(method: str, url: str, headers: dict | None = None):
    request = urllib.request.Request(url, method=method, headers=headers or {})
    try:
        with opener.open(request, timeout=30) as response:
            return response.status, response.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", "replace")


def main() -> int:
    rows: list[str] = [
        "ORD-0395, read off this tree: real uvicorn, no mock, no proxy.",
        "Started with backend/.venv (Python 3.12.14) against a throwaway sqlite file on E:;",
        "driver review/ord0395/uvicorn_after_r1.py; bodies are verbatim from the responses.",
    ]
    database = SCRATCH / "ord0395_after.db"
    if database.exists():
        database.unlink()
    env = {k: v for k, v in os.environ.items() if "PROXY" not in k.upper()}
    env.update(
        {
            "CITYNEXUS_DATABASE_URL": f"sqlite:///{database.as_posix()}",
            "CITYNEXUS_DEMO_MODE": "true",
            "CITYNEXUS_DEMO_RESET_TOKEN": TOKEN,
        }
    )
    handle = open(SCRATCH / "uvicorn_after.log", "w", encoding="utf-8")
    process = subprocess.Popen(
        [str(PYTHON), "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(PORT)],
        cwd=str(BACKEND),
        env=env,
        stdout=handle,
        stderr=subprocess.STDOUT,
    )
    try:
        deadline = time.time() + 120
        while time.time() < deadline:
            try:
                if http("GET", f"http://127.0.0.1:{PORT}/api/v1/health")[0] == 200:
                    break
            except Exception:  # noqa: BLE001
                time.sleep(1.0)
        else:
            raise RuntimeError("backend never became healthy")

        base = f"http://127.0.0.1:{PORT}/api/v1/demo/reset"
        rows.append(f"### uvicorn on :{PORT}, CITYNEXUS_DEMO_MODE=true, token configured")
        for name, headers in (
            ("no token presented", None),
            ("wrong token presented", {"X-Demo-Reset-Token": "not-the-operator"}),
            ("correct token presented", {"X-Demo-Reset-Token": TOKEN}),
        ):
            status, body = http("POST", base, headers)
            rows.append(f"{name}: http_status={status} body={body}")
        served = json.loads(http("GET", f"http://127.0.0.1:{PORT}/openapi.json")[1])
        declaration = served["paths"]["/api/v1/demo/reset"]["post"]["responses"]
        rows.append(f"served statuses: {sorted(declaration)}")
        rows.append(f"served 403 keys: {sorted(declaration['403'])}")
        rows.append(f"served 403 description: {declaration['403']['description']}")
    finally:
        process.terminate()
        process.wait(timeout=30)
        handle.close()
    text = "\n".join(rows) + "\n"
    OUT.write_text(text, encoding="utf-8")
    print(text)
    print(f"lines_in_output={len(text.splitlines())}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
