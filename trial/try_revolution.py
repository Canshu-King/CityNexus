"""Start the actual Revolution frontend + backend with isolated CONTROLLED test data.

Run on Windows from the repository root:
    py -3.13 trial/try_revolution.py

This tool never publishes an external endpoint and never enables AI or payments.
"""
from __future__ import annotations

import argparse
import os
import secrets
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import venv
import webbrowser
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"
TRIAL = ROOT / "trial"
RUNTIME = TRIAL / ".runtime"
FRONT_PORT = 14173
BACK_PORT = 18201
CITY_PORT = 18202
OVERPASS_PORT = 18203


def require_open_port(port: int) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as check:
        check.settimeout(0.5)
        if check.connect_ex(("127.0.0.1", port)) == 0:
            raise RuntimeError(
                f"Port {port} is already occupied; this trial must never adopt another process. "
                "Stop the old trial or the conflicting application."
            )


def prepare_python() -> Path:
    if sys.version_info < (3, 12):
        raise RuntimeError("Python 3.12+ required; on Windows try: py -3.13 trial/try_revolution.py")
    venv_dir = RUNTIME / "python-venv"
    py = venv_dir / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    first_run = not py.exists()
    if first_run:
        print("[setup] Creating isolated trial Python environment ...", flush=True)
        venv.EnvBuilder(with_pip=True, clear=False).create(str(venv_dir))
    if first_run:
        print("[setup] Installing backend dependencies ...", flush=True)
        subprocess.run([str(py), "-m", "pip", "install", "-e", str(BACKEND)],
                       cwd=ROOT, check=True)
    else:
        # If a partially installed venv exists, repair it rather than borrow host Python.
        probe = subprocess.run([str(py), "-c", "import fastapi, uvicorn, sqlalchemy, httpx"],
                               cwd=BACKEND, capture_output=True, text=True)
        if probe.returncode:
            print("[setup] Repairing incomplete isolated backend environment ...", flush=True)
            subprocess.run([str(py), "-m", "pip", "install", "-e", str(BACKEND)],
                           cwd=ROOT, check=True)
    return py


def prepare_frontend() -> str:
    node = shutil.which("node")
    npm = shutil.which("npm.cmd" if os.name == "nt" else "npm") or shutil.which("npm")
    if not node or not npm:
        raise RuntimeError("Node.js and npm are required. Install Node.js 22 LTS and reopen your terminal.")
    vite = FRONTEND / "node_modules" / "vite" / "bin" / "vite.js"
    if not vite.exists():
        print("[setup] Running npm ci in frontend (trial branch only) ...", flush=True)
        subprocess.run([npm, "ci"], cwd=FRONTEND, check=True)
    if not vite.exists():
        raise RuntimeError("Vite was not installed. Check frontend/npm ci output.")
    return node


def health(url: str, timeout_s: float = 2.0) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=timeout_s) as response:
            return response.status == 200
    except (urllib.error.URLError, OSError, TimeoutError):
        return False


def wait_for(name: str, url: str, process: subprocess.Popen, seconds: int = 70) -> None:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"{name} stopped during startup (exit={process.returncode}); inspect trial/.runtime/{name}.err.log")
        if health(url):
            return
        time.sleep(0.5)
    raise RuntimeError(f"{name} did not become healthy at {url}; inspect trial/.runtime/{name}.err.log")


def isolated_environment(db_name: str) -> dict[str, str]:
    env = os.environ.copy()
    # Remove inherited external credentials/configuration. An existing Qoder
    # session must not turn a local trial into a live AI/provider deployment.
    for key in list(env):
        if key.startswith(("CITYNEXUS_", "REV_TRIAL_")) or key in {
            "DEEPSEEK_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY",
        }:
            env.pop(key, None)
    secret_path = RUNTIME / "traveler_auth_secret.txt"
    if secret_path.exists():
        secret = secret_path.read_text(encoding="utf-8").strip()
    else:
        secret = secrets.token_hex(32)
        secret_path.write_text(secret + "\n", encoding="utf-8")
    env.update({
        "CITYNEXUS_ENV": "development",
        "CITYNEXUS_DATABASE_URL": "sqlite:///./" + db_name,
        "CITYNEXUS_DEMO_MODE": "true",
        "CITYNEXUS_AI_ENABLED": "false",
        "CITYNEXUS_GUARDIAN_AUTORUN": "false",
        "CITYNEXUS_PREDICTIVE_AUTOPILOT_ENABLED": "false",
        "CITYNEXUS_TRAVELER_AUTH_SECRET": secret,
        "CITYNEXUS_TRAVELER_AUTH_TTL_SECONDS": "86400",
        # LIVE is a required internal switch for this code path, but the exact
        # loopback endpoints below are independently graded TEST_PROVIDER.
        "CITYNEXUS_REAL_CITY_ENABLED": "true",
        "CITYNEXUS_REAL_CITY_MODE": "live",
        "CITYNEXUS_CITY_SEARCH_ENABLED": "true",
        "CITYNEXUS_CITY_SEARCH_PROVIDER": "nominatim",
        "CITYNEXUS_CITY_SEARCH_TEST_PROVIDER": "true",
        "CITYNEXUS_CITY_SEARCH_BASE_URL": f"http://127.0.0.1:{CITY_PORT}",
        "CITYNEXUS_OVERPASS_URL": f"http://127.0.0.1:{OVERPASS_PORT}/api",
        "CITYNEXUS_BACKEND_PORT": str(BACK_PORT),
        "REV_TRIAL_CITY_PORT": str(CITY_PORT),
        "REV_TRIAL_OVERPASS_PORT": str(OVERPASS_PORT),
        "NO_PROXY": "127.0.0.1,localhost,::1",
        "no_proxy": "127.0.0.1,localhost,::1",
    })
    return env


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fresh", action="store_true",
                        help="Use a new isolated database without deleting your previous trial data")
    parser.add_argument("--no-browser", action="store_true",
                        help="Print the local URL without auto-opening desktop browser")
    args = parser.parse_args()

    RUNTIME.mkdir(parents=True, exist_ok=True)
    for port in (FRONT_PORT, BACK_PORT, CITY_PORT, OVERPASS_PORT):
        require_open_port(port)

    python = prepare_python()
    node = prepare_frontend()
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    db = f"_revolution_hands_on_{stamp}.db" if args.fresh else "_revolution_hands_on.db"
    env = isolated_environment(db)

    children: list[tuple[str, subprocess.Popen]] = []
    handles = []

    def start(name: str, executable: str, argv: list[str], cwd: Path) -> subprocess.Popen:
        out = (RUNTIME / f"{name}.out.log").open("w", encoding="utf-8")
        err = (RUNTIME / f"{name}.err.log").open("w", encoding="utf-8")
        handles.extend([out, err])
        proc = subprocess.Popen([executable, *argv], cwd=str(cwd), env=env,
                                stdout=out, stderr=err)
        children.append((name, proc))
        return proc

    try:
        fixtures = start("fixtures", sys.executable, [str(TRIAL / "controlled_provider.py")], ROOT)
        wait_for("fixtures", f"http://127.0.0.1:{CITY_PORT}/status", fixtures)
        if not health(f"http://127.0.0.1:{OVERPASS_PORT}/status"):
            raise RuntimeError("Overpass test fixture has not started; inspect fixtures.err.log")

        api = start("backend", str(python),
                    ["-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
                     "--port", str(BACK_PORT)], BACKEND)
        wait_for("backend", f"http://127.0.0.1:{BACK_PORT}/api/v1/health", api)

        vite_script = FRONTEND / "node_modules" / "vite" / "bin" / "vite.js"
        ui = start("frontend", node, [str(vite_script), "--host", "127.0.0.1",
                                      "--port", str(FRONT_PORT), "--strictPort"], FRONTEND)
        wait_for("frontend", f"http://127.0.0.1:{FRONT_PORT}/api/v1/health", ui)
        address = f"http://127.0.0.1:{FRONT_PORT}/v8/hub"
        print("\nRevolution browser trial is ready (isolated from Qoder).")
        print("OPEN:", address)
        print("SOURCE: CONTROLLED TEST_PROVIDER. Places are samples, NOT verified real locations.")
        print("AI: OFF. Payment/booking: mock only. Backend bound to localhost.")
        print("DB:", db)
        print("For Android USB Chrome (ADB installed): adb reverse tcp:14173 tcp:14173")
        print("Then on phone visit: http://localhost:14173/v8/hub")
        print("For iPhone/full HTTPS PWA trial, configure a separate authenticated HTTPS staging origin.")
        print("Logs:", RUNTIME)
        print("\nKeep this terminal open while trying the UI.")
        if not args.no_browser:
            webbrowser.open(address)
        input("Press Enter to stop all trial services (or Ctrl+C): ")
        return 0
    except KeyboardInterrupt:
        print("\nStopping trial services ...")
        return 130
    finally:
        for _, child in reversed(children):
            if child.poll() is None:
                child.terminate()
        for _, child in reversed(children):
            try:
                child.wait(timeout=8)
            except subprocess.TimeoutExpired:
                child.kill()
        for handle in handles:
            handle.close()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"\nRevolution trial did not start: {exc}", file=sys.stderr)
        raise SystemExit(1)
