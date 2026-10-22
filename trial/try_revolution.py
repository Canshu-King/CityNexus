"""Start the actual Revolution frontend + backend with isolated CONTROLLED test data.

Run on Windows from the repository root:
    py -3.13 trial/try_revolution.py

Default: REAL public OpenStreetMap/Photon data after explicit UI consent.
Use --sample only if you intentionally want controlled offline locations.
The backend remains isolated on localhost; AI is opt-in via --agent.
Mock booking/payment and user approval boundaries remain unchanged.
"""
from __future__ import annotations

import argparse
import os
import re
import secrets
import shutil
import socket
import subprocess
import sys
import time
import tomllib
import urllib.error
import urllib.request
import venv
import webbrowser
from datetime import datetime
from pathlib import Path

from wb2api_agent import agent_settings, router_health
from amap_credentials import load_amap_key


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"
TRIAL = ROOT / "trial"
RUNTIME = TRIAL / ".runtime"
FRONT_PORT = 14173
BACK_PORT = 18201
CITY_PORT = 18202
OVERPASS_PORT = 18203


def parse_port(value: str) -> int:
    try:
        port = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("port must be an integer") from exc
    if not 1024 <= port <= 65535:
        raise argparse.ArgumentTypeError("port must be between 1024 and 65535")
    return port


def resume_database(runtime: Path, filename: str) -> str:
    """Explicitly resume one existing trial DB and its adjacent auth secret."""
    target = (runtime / filename).resolve()
    if target.parent != runtime.resolve() or target.suffix != ".db" or not target.is_file():
        raise RuntimeError("Choose an existing .db file directly inside --runtime-dir")
    if not (runtime / "traveler_auth_secret.txt").is_file():
        raise RuntimeError("The original trial authentication secret is required to resume")
    return target.as_posix()


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
    # Reuse this checkout's installed runtime; separate runs only need new data,
    # not another copy of all Python dependencies.
    project_python = BACKEND / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if project_python.exists():
        probe = subprocess.run([str(project_python), "-c", "import fastapi, uvicorn, sqlalchemy, httpx"],
                               cwd=BACKEND, capture_output=True, text=True)
        if probe.returncode == 0:
            return project_python
    venv_dir = TRIAL / ".runtime" / "python-venv"
    py = venv_dir / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    first_run = not py.exists()
    if first_run:
        print("[setup] Creating isolated trial Python environment ...", flush=True)
        venv.EnvBuilder(with_pip=True, clear=False).create(str(venv_dir))
    # The backend pyproject intentionally has no build-system. Install its declared
    # dependencies rather than trying 'pip install -e backend' (which may try to
    # package source/data/output directories as a distribution).
    requirements = tomllib.loads((BACKEND / "pyproject.toml").read_text(encoding="utf-8"))["project"]["dependencies"]
    if first_run:
        print("[setup] Installing backend runtime dependencies ...", flush=True)
        subprocess.run([str(py), "-m", "pip", "install", *requirements],
                       cwd=ROOT, check=True)
    else:
        # If a partially installed venv exists, repair it rather than borrow host Python.
        probe = subprocess.run([str(py), "-c", "import fastapi, uvicorn, sqlalchemy, httpx"],
                               cwd=BACKEND, capture_output=True, text=True)
        if probe.returncode:
            print("[setup] Repairing incomplete isolated backend environment ...", flush=True)
            subprocess.run([str(py), "-m", "pip", "install", *requirements],
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
        installed = subprocess.run([npm, "ci", "--no-audit", "--no-fund"],
                                   cwd=FRONTEND, text=True, capture_output=True)
        if installed.returncode:
            output = installed.stdout + "\n" + installed.stderr
            # Revolution's pre-existing package-lock.json is missing three type
            # packages. Work around only this known npm EUSAGE mismatch without
            # writing package.json or package-lock.json. Do not hide network/permission errors.
            mismatched_lock = (
                ("EUSAGE" in output or "npm ci can only install" in output or
                 "can only install packages when" in output)
                and ("lock file" in output or "in sync" in output)
            )
            if not mismatched_lock:
                print(output[-6000:], file=sys.stderr)
                raise RuntimeError(
                    "npm ci failed for a reason other than a mismatched lockfile; "
                    "inspect the printed npm error."
                )
            print("[setup] Existing Revolution npm lockfile is out of sync; "
                  "installing dependencies without changing package files ...", flush=True)
            subprocess.run([npm, "install", "--no-audit", "--no-fund",
                            "--no-save", "--no-package-lock"],
                           cwd=FRONTEND, check=True)
    if not vite.exists():
        raise RuntimeError("Vite was not installed. Check frontend npm output.")
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
            raise RuntimeError(f"{name} stopped during startup (exit={process.returncode}); inspect {RUNTIME / (name + '.err.log')}")
        if health(url):
            return
        time.sleep(0.5)
    raise RuntimeError(f"{name} did not become healthy at {url}; inspect {RUNTIME / (name + '.err.log')}")


def isolated_environment(
    db_name: str,
    *,
    sample: bool,
    contact_email: str | None,
    backend_port: int = BACK_PORT,
    city_port: int = CITY_PORT,
    overpass_port: int = OVERPASS_PORT,
) -> dict[str, str]:
    # Read the operator's encrypted per-user credential before clearing inherited
    # CityNexus settings. Only the backend receives this explicitly selected key.
    amap_key = None if sample else load_amap_key()
    env = os.environ.copy()
    # On Windows, urllib/httpx stop consulting the system proxy as soon as any
    # proxy environment entry exists. Preserve that proxy before adding the
    # loopback NO_PROXY below, or public OSM requests unexpectedly go direct.
    for scheme, proxy in urllib.request.getproxies().items():
        if scheme in {"http", "https", "all"} and proxy:
            env.setdefault(scheme.upper() + "_PROXY", proxy)
    # Remove inherited external credentials/configuration. An existing Qoder
    # session must not turn a local trial into a live AI/provider deployment.
    for key in list(env):
        if key.startswith(("CITYNEXUS_", "REV_TRIAL_")) or key in {
            "DEEPSEEK_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "WB2API_KEY",
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
        "CITYNEXUS_DATABASE_URL": "sqlite:///" + (Path(db_name).as_posix() if Path(db_name).is_absolute() else "./" + db_name),
        "CITYNEXUS_DEMO_MODE": "false",
        "CITYNEXUS_AI_ENABLED": "false",
        "CITYNEXUS_GUARDIAN_AUTORUN": "false",
        "CITYNEXUS_PREDICTIVE_AUTOPILOT_ENABLED": "false",
        "CITYNEXUS_TRAVELER_AUTH_SECRET": secret,
        "CITYNEXUS_TRAVELER_AUTH_TTL_SECONDS": "86400",
        "CITYNEXUS_REAL_CITY_ENABLED": "true",
        "CITYNEXUS_REAL_CITY_MODE": "live",
        "CITYNEXUS_PHOTON_ENABLED": "false",
        "CITYNEXUS_POI_DISCOVERY_PROVIDER": "overpass",
        "CITYNEXUS_CITY_PROVIDER": "mock-city",
        "CITYNEXUS_MOBILITY_PROVIDER": "mock-mobility",
        "CITYNEXUS_BOOKING_PROVIDER": "mock-booking",
        "CITYNEXUS_PAYMENT_PROVIDER": "mock-payment",
        "CITYNEXUS_CONTEXT_PROVIDER": "mock-context",
        "CITYNEXUS_BACKEND_PORT": str(backend_port),
        "VITE_REV_TRIAL_MODE": "sample" if sample else "live",
        "NO_PROXY": "127.0.0.1,localhost,::1",
        "no_proxy": "127.0.0.1,localhost,::1",
    })
    if amap_key:
        env["CITYNEXUS_AMAP_WEB_KEY"] = amap_key
    if sample:
        # No network provider is used for sample searches. Every test result
        # is explicitly graded TEST_PROVIDER by the existing backend.
        env.update({
            "CITYNEXUS_CITY_SEARCH_ENABLED": "true",
            "CITYNEXUS_CITY_SEARCH_PROVIDER": "nominatim",
            "CITYNEXUS_CITY_SEARCH_TEST_PROVIDER": "true",
            "CITYNEXUS_CITY_SEARCH_BASE_URL": f"http://127.0.0.1:{city_port}",
            "CITYNEXUS_NOMINATIM_URL": f"http://127.0.0.1:{city_port}",
            "CITYNEXUS_OVERPASS_URL": f"http://127.0.0.1:{overpass_port}/api",
            # The sample path remains isolated on the local Overpass fixture.
            "CITYNEXUS_PHOTON_ENABLED": "false",
            "CITYNEXUS_POI_DISCOVERY_PROVIDER": "overpass",
            "REV_TRIAL_CITY_PORT": str(city_port),
            "REV_TRIAL_OVERPASS_PORT": str(overpass_port),
        })
    else:
        if not contact_email:
            raise RuntimeError("Real public geocoding requires a provider contact email.")
        env.update({
            "CITYNEXUS_CITY_SEARCH_ENABLED": "true",
            "CITYNEXUS_CITY_SEARCH_PROVIDER": "nominatim",
            "CITYNEXUS_CITY_SEARCH_TEST_PROVIDER": "false",
            "CITYNEXUS_CITY_SEARCH_BASE_URL": "https://nominatim.openstreetmap.org",
            "CITYNEXUS_NOMINATIM_URL": "https://nominatim.openstreetmap.org",
            "CITYNEXUS_PHOTON_ENABLED": "true",
            "CITYNEXUS_POI_DISCOVERY_PROVIDER": "photon",
            # Nominatim requires an operator-identifying User-Agent.
            # The email is typed locally and is sent ONLY as a provider header;
            # it is never stored in a checkout, database or printed in logs.
            "CITYNEXUS_CITY_SEARCH_USER_AGENT":
                "CityNexus-RevolutionFirstLook/1.0 (mailto:" + contact_email + ")",
            "CITYNEXUS_PHOTON_USER_AGENT":
                "CityNexus-RevolutionFirstLook/1.0 (mailto:" + contact_email + ")",
            "CITYNEXUS_OVERPASS_URL": "https://overpass-api.de/api",
        })
    return env


def main() -> int:
    global RUNTIME
    parser = argparse.ArgumentParser()
    parser.add_argument("--fresh", action="store_true",
                        help="Use a new isolated database without deleting your previous trial data")
    parser.add_argument("--sample", action="store_true",
                        help="Explicitly choose controlled local fake places instead of live public map search")
    parser.add_argument("--agent", action="store_true",
                        help="Explicitly connect the existing Hermes tool-loop to local wb2api 7865/auto:cheapest")
    parser.add_argument("--agent-direct-model", default=None,
                        help="Use exact wb2api 7863 model, e.g. global:deepseek-v4.1-flash (may incur charges)")
    parser.add_argument("--no-browser", action="store_true",
                        help="Print the local URL without auto-opening desktop browser")
    parser.add_argument("--runtime-dir", type=Path, default=None,
                        help="Store this instance's database and logs in a separate local directory")
    parser.add_argument("--resume-database", default=None,
                        help="Existing .db filename in --runtime-dir; preserves original signed trial state")
    parser.add_argument("--wb2api-key-file", type=Path, default=None,
                        help="Explicit local key file or gateway guide; read in memory only, requires --agent")
    parser.add_argument("--frontend-port", type=parse_port, default=FRONT_PORT,
                        help=f"Use a separate frontend port (default: {FRONT_PORT})")
    parser.add_argument("--backend-port", type=parse_port, default=BACK_PORT,
                        help=f"Use a separate backend port (default: {BACK_PORT})")
    parser.add_argument("--city-port", type=parse_port, default=CITY_PORT,
                        help=f"Use a separate local city fixture port with --sample (default: {CITY_PORT})")
    parser.add_argument("--overpass-port", type=parse_port, default=OVERPASS_PORT,
                        help=f"Use a separate local Overpass fixture port with --sample (default: {OVERPASS_PORT})")
    args = parser.parse_args()
    if args.runtime_dir is not None:
        RUNTIME = args.runtime_dir.expanduser().resolve()
    existing_db = None
    if args.resume_database:
        if args.fresh or args.runtime_dir is None:
            raise RuntimeError("--resume-database requires --runtime-dir and cannot use --fresh")
        existing_db = resume_database(RUNTIME, args.resume_database)
    front_port = args.frontend_port
    back_port = args.backend_port
    city_port = args.city_port
    overpass_port = args.overpass_port

    contact_email = None
    if not args.sample:
        print("\nREVOLUTION REAL CITY EXPERIENCE")
        print("External geocoding: OpenStreetMap Nominatim; places: Photon.")
        print("Nothing is sent while typing; the UI separately asks for each provider consent.")
        print("Nominatim requires an identifying contact email in its User-Agent.")
        print("Enter your own contact email locally. It will be sent to Nominatim,")
        print("but never put in the Git repository or printed in the logs.")
        contact_email = (os.environ.get("CITYNEXUS_NOMINATIM_CONTACT_EMAIL") or "").strip()
        if not contact_email:
            contact_email = input("Nominatim contact email: ").strip()
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", contact_email):
            raise RuntimeError("A valid contact email is required for LIVE search. Use --sample to run offline.")
    agent_enabled = bool(args.agent or args.agent_direct_model)
    if args.wb2api_key_file is not None and not agent_enabled:
        raise RuntimeError("--wb2api-key-file requires explicit --agent")
    agent_config: dict[str, str] = {}
    agent_label = "DISABLED"
    if agent_enabled:
        print("\nAI 旅行规划 · 本机 wb2api")
        print("你在页面提交需求时会发送给模型，可能产生费用。")
        # --agent is an explicit local operator choice; this step configures
        # the model but DOES NOT invoke it. Each actual AI text submission in
        # the browser is an independent explicit request with cost disclosure.
        if not args.agent_direct_model:
            healthy, state = router_health()
            if not healthy:
                raise RuntimeError("请先启动本机 WorkBuddy2API 路由（7865）：" + state)
        try:
            agent_config, agent_label = agent_settings(direct_model=args.agent_direct_model, key_file=args.wb2api_key_file)
        except ValueError as exc:
            raise RuntimeError(str(exc)) from exc
        print("模型选择：", agent_config["CITYNEXUS_HERMES_MODEL"])
        print("打开页面后，在底部输入框和 Agent 讨论；点「按讨论的方向开始研究」后查询地点。")
    RUNTIME.mkdir(parents=True, exist_ok=True)
    ports = ((front_port, back_port, city_port, overpass_port)
             if args.sample else (front_port, back_port))
    if len(set(ports)) != len(ports):
        raise RuntimeError("Each selected service must use a distinct port.")
    for port in ports:
        require_open_port(port)

    python = prepare_python()
    node = prepare_frontend()
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    db = f"_revolution_hands_on_{stamp}.db" if args.fresh else "_revolution_hands_on.db"
    if args.runtime_dir is not None:
        db = (RUNTIME / db).as_posix()
    if existing_db:
        db = existing_db
    env = isolated_environment(
        db,
        sample=args.sample,
        contact_email=contact_email,
        backend_port=back_port,
        city_port=city_port,
        overpass_port=overpass_port,
    )

    children: list[tuple[str, subprocess.Popen]] = []
    handles = []

    def start(name: str, executable: str, argv: list[str], cwd: Path,
              child_env: dict[str, str] | None = None) -> subprocess.Popen:
        out = (RUNTIME / f"{name}.out.log").open("w", encoding="utf-8")
        err = (RUNTIME / f"{name}.err.log").open("w", encoding="utf-8")
        handles.extend([out, err])
        proc = subprocess.Popen([executable, *argv], cwd=str(cwd), env=child_env or env,
                                stdout=out, stderr=err)
        children.append((name, proc))
        return proc

    try:
        if args.sample:
            fixtures = start("fixtures", sys.executable, [str(TRIAL / "controlled_provider.py")], ROOT)
            wait_for("fixtures", f"http://127.0.0.1:{city_port}/status", fixtures)
            if not health(f"http://127.0.0.1:{overpass_port}/status"):
                raise RuntimeError("Overpass test fixture has not started; inspect fixtures.err.log")

        # Trial-only FastAPI wrapper adds the authenticated read-only Hermes
        # discovery guide. The existing app.main routers/lifespan remain intact.
        # The non-agent run also imports this wrapper, but its AI route fails
        # closed unless settings.ai_enabled AND Hermes credentials are present.
        api = start("backend", str(python),
                    ["-m", "uvicorn", "--app-dir", str(TRIAL),
                     "agent_preview_app:app", "--host", "127.0.0.1",
                     "--port", str(back_port)], BACKEND, {**env, **agent_config})
        wait_for("backend", f"http://127.0.0.1:{back_port}/api/v1/health", api)

        vite_script = FRONTEND / "node_modules" / "vite" / "bin" / "vite.js"
        ui_env = {key: value for key, value in env.items() if key != "CITYNEXUS_AMAP_WEB_KEY"}
        ui = start("frontend", node, [str(vite_script), "--host", "127.0.0.1",
                                      "--port", str(front_port), "--strictPort"], FRONTEND, ui_env)
        wait_for("frontend", f"http://127.0.0.1:{front_port}/api/v1/health", ui)
        address = f"http://127.0.0.1:{front_port}/revolution"
        print("\nRevolution browser trial is ready (isolated from Qoder and fusion).")
        print("OPEN:", address)
        print("SOURCE:", "CONTROLLED TEST_PROVIDER (sample places)" if args.sample
              else "REAL PUBLIC OSM PROVIDERS (network access after specific user consent)")
        print("高德地图：", "已加载本机 Web 服务 Key" if env.get("CITYNEXUS_AMAP_WEB_KEY") else "未配置")
        print("Agent:", "CONFIGURED (" + agent_label + ")" if agent_enabled else "OFF")
        print("Discuss in the bottom chat; explicitly start research after confirming AI and map-source consent.")
        print("Payment/booking: mock only. Backend bound to localhost.")
        print("DB:", db)
        print(f"For Android USB Chrome (ADB installed): adb reverse tcp:{front_port} tcp:{front_port}")
        print(f"Then on phone visit: http://localhost:{front_port}/revolution")
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
