"""两枚尺的"改前/改后"读数：同一把形状判据分别跑在尖那一代与我这一代上，行号一律现推。

不改产品字节：只读树、只算清单。旧的锚是 `(SITE, 45)` 与五枚文件名白名单，这里把"树现在答什么"
逐枚抄下来，红/绿由 pytest 那两趟给（日志名在同一目录）。
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOTS = {"tip_00b5f25e": Path("D:/moodle/_qoder_anchor_rulers_20261002/tip_00b5f25e9b6b408fba8906ef3ffd49caa5eb84b9"),
         "branch_5cb0bd0a": Path("D:/moodle/_qoder_anchor_rulers_20261002/branchfull_5cb0bd0a")}
PY = "D:/moodle/CityNexus/.venv/Scripts/python.exe"
HOME_SHAPE = re.compile(r'os\.getenv\(\s*"CITYNEXUS_WRITE_BUSY_TIMEOUT_MS"\s*,\s*"(\d+)"\s*\)')
BIND_SHAPE = re.compile(r"\bbusy_timeout\w*\s*[=:]\s*(\d+)")
ACCESSOR = re.compile(r"^\s*def\s+busy_timeout_ms\s*\(")
IMPORT_SHAPE = re.compile(r"^\s*from app\.db\.write_deadline import [^\n]*busy_timeout")
NAMED = ("busy_timeout_ms()", "busy_timeout_seconds()", "write_busy_timeout_ms()",
         "write_busy_timeout_seconds()", "effective_busy_timeout_ms(", "settings.write_busy_timeout_ms")
APPLIER = re.compile(r'(PRAGMA busy_timeout|"timeout"\s*:|\.connect\(|create_engine\()')
OLD_ROSTER = ["catalog_hydration_operations.py", "config.py", "session.py",
              "stay_generation_operations.py", "write_deadline.py"]
SITE = "frontend/src/features/shared/SharedJourneyPanel.tsx"


def mentions(backend_app: Path, root: Path) -> list[dict]:
    rows = []
    for p in sorted(backend_app.rglob("*.py")):
        for i, l in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            if "busy_timeout" in l:
                rows.append({"path": str(p.relative_to(root)).replace("\\", "/"), "line": i,
                             "text": l.strip()})
    return rows


def g4_view(root: Path) -> dict:
    rows = mentions(root / "backend" / "app", root)
    homes = [r for r in rows if HOME_SHAPE.search(r["text"])]
    declared = int(HOME_SHAPE.search(homes[0]["text"]).group(1)) if len(homes) == 1 else None
    same = re.compile(r"(?<!\d)%s(?!\d)" % declared) if declared else None
    bindings = [(r, BIND_SHAPE.search(r["text"])) for r in rows]
    appliers = [r for r in rows if APPLIER.search(r["text"]) and not BIND_SHAPE.search(r["text"])]
    return {"mentions_files": sorted({Path(r["path"]).name for r in rows}),
            "old_roster_would_red": sorted({Path(r["path"]).name for r in rows}) != OLD_ROSTER,
            "old_roster_missing": sorted(set(Path(r["path"]).name for r in rows) - set(OLD_ROSTER)),
            "declaration_home": [{k: homes[0][k] for k in ("path", "line")} if homes else None,
                                 ][0],
            "declared_ms": declared,
            "copies_of_that_number": ([] if not same
                                      else [r for r in rows if r is not homes[0] and same.search(r["text"])]),
            "accessor_defs": [{k: r[k] for k in ("path", "line")}
                              for r in rows if ACCESSOR.match(r["text"])],
            "importers": [{k: r[k] for k in ("path", "line")} for r in rows if IMPORT_SHAPE.match(r["text"])],
            "worker_waits": [{"path": r["path"], "line": r["line"], "ms": int(m.group(1))}
                             for r, m in bindings if m],
            "appliers_asking_the_source": sum(1 for r in appliers if any(s in r["text"] for s in NAMED)),
            "appliers_total": len(appliers)}


def h_view(root: Path) -> dict:
    import sys as _s
    _s.path.insert(0, str(root / "backend"))
    from app.security import credential_literals as CL
    rep = CL.scan(root)
    lines = (root / SITE).read_text(encoding="utf-8", errors="replace").splitlines()
    decl = [i for i, l in enumerate(lines) if re.match(r"^(?:export\s+)?const REFUSAL_KEY\b", l.strip())]
    entry = [i for i, l in enumerate(lines) if re.match(r"^\s*token_unknown\s*:", l)]
    return {"hits_in_product_path": rep["hits_in_product_path"], "verdict": rep["verdict"],
            "hits_vocabulary_exempted": rep["hits_vocabulary_exempted"],
            "exempted": sorted((e["path"], e["line"]) for e in rep["vocabulary_exemptions"]),
            "REFUSAL_KEY_declared_at": (decl or [None])[0],
            "token_unknown_line_derived_by_symbol": (entry[0] + 1) if entry else None,
            "old_pinned_line_45_still_there": bool(entry and entry[0] + 1 == 45)}


out = {"interpreter": PY, "python": subprocess.run([PY, "-V"], capture_output=True,
                                                   text=True, errors="replace").stdout.strip(),
       "trees": {}}
for name, root in ROOTS.items():
    out["trees"][name] = {"exists": root.is_dir(), "g4": g4_view(root), "h01b": h_view(root)}
dst = Path("D:/moodle/_qoder_anchor_rulers_20261002/anchor_ruler_readings_r1.json")
dst.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print("WROTE", dst)
for name, t in out["trees"].items():
    print(name, "old_roster_red:", t["g4"]["old_roster_would_red"],
          "| derived token_unknown line:", t["h01b"]["token_unknown_line_derived_by_symbol"],
          "| exempted:", t["h01b"]["exempted"])
