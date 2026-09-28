"""ORD-0410 lane backend launcher: uvicorn on the lane's own port over the lane's own DB copy.

DEEPSEEK_API_KEY / CITYNEXUS_AI_API_KEY are stripped so no external AI leg is reachable from this
process, and the database URL is absolute because a relative one resolves against cwd and would
land a write in the shared tree.
"""
import json
import os
import runpy
import sys

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8711
CODE_ROOT = "D:/moodle/_qoder_r_ord0410/wt/backend"
DB = "D:/moodle/_qoder_r_ord0410/run/_r_ord0410.db"

_dropped: list[str] = []
# The switch is read by `app.core.config` at import time through os.getenv, so it has to be in the
# *process* environment.  Building a dict and passing it nowhere is how the first run of this
# launcher came up with demo_mode=false while the log line claimed otherwise.
for _k in ("DEEPSEEK_API_KEY", "CITYNEXUS_AI_API_KEY"):
    if os.environ.pop(_k, None) is not None:
        _dropped.append(_k)
os.environ["CITYNEXUS_DATABASE_URL"] = "sqlite:///" + DB.replace("\\", "/")
os.environ["CITYNEXUS_DEMO_MODE"] = "true"
os.environ["PYTHONPATH"] = "D:/moodle/_qoder_r_ord0410/wt"
print(json.dumps({"pid": os.getpid(), "port": PORT, "cwd": CODE_ROOT,
                  "db": DB, "dropped_keys": _dropped, "db_exists": os.path.isfile(DB),
                  "demo_mode_as_read": os.getenv("CITYNEXUS_DEMO_MODE")}), flush=True)
os.chdir(CODE_ROOT)
sys.argv = ["uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(PORT),
            "--log-level", "info"]
runpy.run_module("uvicorn", run_name="__main__")
