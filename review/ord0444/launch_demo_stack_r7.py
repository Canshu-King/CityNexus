"""ORD-0444 -- launcher for the private demo-mode stack used by the `demo/reset` counter-case.

The reset token is read from a file and put into this process's environment only.  It is never
printed, never written into a receipt, and never appears on a command line: the order's rule is
that a key value may not reach a file, log, receipt or message, and a throwaway local token is
still a key value.  The path and the field name are what get reported.

Field name: `CITYNEXUS_DEMO_RESET_TOKEN` (`backend/app/main.py:2085` -- `DEMO_RESET_ENV`).
Header name: `X-Demo-Reset-Token` (`backend/app/main.py:2086` -- `DEMO_RESET_HEADER`).
"""

from __future__ import annotations

import os
import secrets
import sys
from pathlib import Path

TOKEN_FILE = Path("D:/moodle/_qoder_newlane_ord0444_20260929/scratch/demo_reset_token.txt")
DB = Path(sys.argv[1])
PORT = sys.argv[2]

if not TOKEN_FILE.exists():
    TOKEN_FILE.write_text(secrets.token_hex(16), encoding="utf-8")

os.environ["CITYNEXUS_DATABASE_URL"] = f"sqlite:///{DB.as_posix()}"
os.environ["CITYNEXUS_DEMO_MODE"] = "true"
os.environ["CITYNEXUS_DEMO_RESET_TOKEN"] = TOKEN_FILE.read_text(encoding="utf-8").strip()

sys.path.insert(0, str(Path("D:/moodle/_qoder_newlane_ord0444_20260929/wt/backend")))

import uvicorn  # noqa: E402  -- the import must come after the environment is declared

uvicorn.run("app.main:app", host="127.0.0.1", port=int(PORT), log_level="info")
