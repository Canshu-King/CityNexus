"""读一份 ORD-0296 的"现场事实"：一次性临时库上量真实 PRAGMA 与配置判级，不碰任何共享面。

为什么要单独一件：门里的 G1 判的是"引擎真的把配置应用到了连接上"。这一件是**另一条路**的读数
（新进程、新库、只 import 到 app.db.session 为止），两边一致才算不是自己跟自己对表。
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SNAP = Path(os.environ.get("O296_SNAP", "D:/moodle/_qoder_f_run/snap_0296_g2/backend"))
OUT = Path("D:/moodle/_qoder_f_run/o225_receipts/ord0296_facts.json")
PY = r"D:\moodle\CityNexus\.venv\Scripts\python.exe"
TMPDB = Path("D:/moodle/_qoder_f_run/_o296_facts.db")

CHILD = r"""
import json, os, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, ".")
from app.core.config import settings
from app.db import write_deadline as WD
from app.db.session import make_engine
from sqlalchemy import text
eng = make_engine(os.environ["CITYNEXUS_DATABASE_URL"])
with eng.connect() as c:
    live = int(c.execute(text("PRAGMA busy_timeout")).scalar_one())
    journal = c.execute(text("PRAGMA journal_mode")).scalar_one()
    driver = c.exec_driver_sql("select sqlite_version()").scalar_one()
try:
    WD.assert_configuration_reachable()
    door = {"raised": False, "named": None}
except Exception as exc:
    door = {"raised": True, "named": type(exc).__name__, "text": str(exc)[:220]}
print(json.dumps({
  "sqlite_driver_version": driver,
  "journal_mode": journal,
  "live_pragma_busy_timeout_ms": live,
  "settings_write_busy_timeout_ms": int(settings.write_busy_timeout_ms),
  "settings_write_deadline_ms": int(settings.write_deadline_ms),
  "settings_env_names_seen": [n for n in os.environ if n.startswith("CITYNEXUS_WRITE_")],
  "deadline_ms_plans": WD.deadline_ms(WD.SCENARIO_PLANS_GENERATE),
  "deadline_ms_commands": WD.deadline_ms(WD.SCENARIO_AGENT_COMMANDS),
  "deadline_sources": {WD.SCENARIO_PLANS_GENERATE: WD.deadline_source(WD.SCENARIO_PLANS_GENERATE),
                       WD.SCENARIO_AGENT_COMMANDS: WD.deadline_source(WD.SCENARIO_AGENT_COMMANDS)},
  "effective_busy_timeout_ms": {s: WD.effective_busy_timeout_ms(s) for s in WD.SCENARIOS},
  "configuration_verdict": WD.configuration_verdict(),
  "door": door,
}, ensure_ascii=False))
"""

for suffix in ("", "-wal", "-shm"):
    Path(str(TMPDB) + suffix).unlink(missing_ok=True)

env = dict(os.environ)
env.update({"CITYNEXUS_DATABASE_URL": "sqlite:///" + TMPDB.as_posix(),
            "CITYNEXUS_AI_ENABLED": "false", "CITYNEXUS_DEMO_MODE": "false"})
for key in ("DEEPSEEK_API_KEY", "OPENAI_API_KEY", "CITYNEXUS_AI_API_KEY",
            "CITYNEXUS_LIVE_VALHALLA_URL", "CITYNEXUS_HERMES_API_URL"):
    env.pop(key, None)

proc = subprocess.run([PY, "-c", CHILD], cwd=str(SNAP), capture_output=True, text=True,
                      encoding="utf-8", errors="replace", env=env, timeout=300)
inline = json.loads(proc.stdout.strip().splitlines()[-1]) if proc.returncode == 0 else {"error": proc.stderr[-400:]}

# 另一枚只读事实：默认值与"松一档"的判级差异（在子进程里用环境变量喂，证明它真的可配）
variant = {}
for name, value in (("CITYNEXUS_WRITE_DEADLINE_MS", "45000"),
                    ("CITYNEXUS_WRITE_DEADLINE_MS_TOO_SMALL", "1"),
                    ("CITYNEXUS_WRITE_DEADLINE_SCENARIOS", "plans.generate:60000")):
    e2 = dict(env)
    key = "CITYNEXUS_WRITE_DEADLINE_MS" if name.endswith("TOO_SMALL") else name
    e2.pop("CITYNEXUS_WRITE_DEADLINE_MS", None)
    e2.pop("CITYNEXUS_WRITE_DEADLINE_SCENARIOS", None)
    if value != "1":
        e2[key] = value
    elif name.endswith("TOO_SMALL"):
        e2["CITYNEXUS_WRITE_DEADLINE_MS"] = "1"
    p2 = subprocess.run([PY, "-c", CHILD], cwd=str(SNAP), capture_output=True, text=True,
                        encoding="utf-8", errors="replace", env=e2, timeout=300)
    doc = json.loads(p2.stdout.strip().splitlines()[-1]) if p2.returncode == 0 else {"error": p2.stderr[-200:]}
    variant[name] = {"verdict": (doc.get("configuration_verdict") or {}).get("verdict"),
                     "deadline_ms_plans": doc.get("deadline_ms_plans"),
                     "effective_busy_timeout_ms": doc.get("effective_busy_timeout_ms"),
                     "door": doc.get("door"), "child_rc": p2.returncode,
                     "stderr_tail": (p2.stderr.strip().splitlines()[-1][:160] if p2.stderr else "")}

collect = subprocess.run([PY, "-m", "pytest", "tests/test_qoder_ord0296_write_deadline.py",
                          "--collect-only", "-q", "-p", "no:cacheprovider"],
                         cwd=str(SNAP), capture_output=True, text=True,
                         encoding="utf-8", errors="replace", env=env, timeout=300)
tail = [l for l in collect.stdout.splitlines() if "collected" in l or "error" in l]

out = {"what": "ORD-0296 现场事实（新进程、一次性临时库；与门内 G1 走不同路径的第二读数）",
       "lane": "F 8ccd71d8",
       "read_at": datetime.now().astimezone().isoformat(timespec="seconds"),
       "cwd": str(SNAP),
       "interpreter": PY,
       "env_stripped": ["DEEPSEEK_API_KEY", "OPENAI_API_KEY", "CITYNEXUS_AI_API_KEY",
                        "CITYNEXUS_LIVE_VALHALLA_URL", "CITYNEXUS_HERMES_API_URL"],
       "throwaway_db": TMPDB.name,
       "demo_reset_calls": 0,
       "live_read": inline,
       "env_variants": variant,
       "collect_only": {"rc": collect.returncode, "line": tail},
       "discipline": {"live_or_preview_db_touched": False, "authoritative_branch_written": False,
                      "credentials_printed": 0}}
for suffix in ("", "-wal", "-shm"):
    Path(str(TMPDB) + suffix).unlink(missing_ok=True)
OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
print(json.dumps({"live": {k: inline.get(k) for k in ("live_pragma_busy_timeout_ms",
                                                      "settings_write_busy_timeout_ms",
                                                      "settings_write_deadline_ms",
                                                      "sqlite_driver_version")},
                  "verdict": (inline.get("configuration_verdict") or {}).get("verdict"),
                  "door_inline": inline.get("door"),
                  "variants": {k: v.get("verdict") for k, v in variant.items()},
                  "collect": tail}, ensure_ascii=False, indent=1))
print("wrote", OUT.name)
