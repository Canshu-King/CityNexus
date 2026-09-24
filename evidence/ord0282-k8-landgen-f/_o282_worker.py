"""One ORD-0282 worker: a real uvicorn process serving the landed export's own `app.main:app`.

Usage:  python _o282_worker.py <port> <database-url>

Nothing is suppressed and nothing is patched: the only thing this file does is set the database
before the app imports, then serve.  It self-reports pid / ppid / the database file it actually
resolved, because "a 200 on my port" does not prove the port is mine (lane F's own lesson from
the shared-port ruling).
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def main() -> int:
    port = int(sys.argv[1])
    database_url = sys.argv[2]
    os.environ["CITYNEXUS_DATABASE_URL"] = database_url
    os.environ["CITYNEXUS_AI_ENABLED"] = "false"
    # No external provider may answer this measurement: settings reads DEEPSEEK_API_KEY as a
    # fallback, and a remote run lands outside the commit boundary the rowcounts are read from.
    stripped = [n for n in ("DEEPSEEK_API_KEY", "OPENAI_API_KEY", "CITYNEXUS_AI_API_KEY",
                            "CITYNEXUS_LIVE_VALHALLA_URL") if os.environ.pop(n, None) is not None]

    import uvicorn  # noqa: PLC0415
    from app.core.config import settings  # noqa: PLC0415
    from app.main import app  # noqa: PLC0415 - importing runs ensure_schema

    resolved = str(Path(settings.database_url.replace("sqlite:///", "", 1)).resolve())
    print(json.dumps({"kind": "serving", "pid": os.getpid(), "ppid": os.getppid(), "port": port,
                      "database_url": settings.database_url, "resolved_db_file": resolved,
                      "ai_enabled": settings.ai_enabled, "ai_api_key_present": bool(settings.ai_api_key),
                      "env_keys_stripped": stripped}), flush=True)
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
