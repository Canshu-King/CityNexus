"""CMDR 07:57 修单的反件：两枚尺改成具名锚/现推导之后，逐格证明两件事。

  · **漂移中性**（旧尺红的那一手现在不许红）：上游在产品源里多出一枚合法用法、或把具名表往上顶
    两行，尺必须仍然绿——旧尺正是被这两件事漂红的；
  · **仍然咬得住**：真正的"抄了两份 / 单源没有消费者 / 具名符号不见了 / 值不再是词典键"每一手
    都必须红，而且红在自己那一格自己的判语上（cause 串逐枚点名）。

每次变异都跑**一枚** nodeid，跑完立刻还原；变异是否落盘由 `git status` 当场回读，不靠话说。
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

WT = Path("D:/moodle/_qoder_newlane_ord0444_20260929/wt_rulers")
BACKEND = WT / "backend"
PY = Path("D:/moodle/CityNexus/.venv/Scripts/python.exe")
DB = BACKEND / "anchor_ce.db"
G4 = "tests/test_qoder_ord0296_write_deadline.py::test_G4_the_lock_wait_is_written_in_exactly_one_place"
H1B = ("tests/test_qoder_ord0479_dictionary_key_shape.py"
       "::test_H01b_the_shipped_tree_clears_and_every_exemption_is_re_derivable")
CREATED: list[Path] = []


def _restore() -> None:
    for p in CREATED:
        try:
            p.unlink()
        except OSError:
            pass
    subprocess.run(["git", "checkout", "--", "."], cwd=str(WT), capture_output=True)


def _read(rel: str) -> str:
    return (WT / rel).read_text(encoding="utf-8")


def _write(rel: str, text: str) -> None:
    (WT / rel).write_text(text, encoding="utf-8", newline="\n")


def _create(rel: str, text: str) -> Path:
    p = WT / rel
    p.write_text(text, encoding="utf-8", newline="\n")
    CREATED.append(p)
    return p


def _run(nodeid: str) -> dict:
    env = {**os.environ, "CITYNEXUS_DATABASE_URL": "sqlite:///./" + DB.name,
           "CITYNEXUS_AI_ENABLED": "false", "PYTHONDONTWRITEBYTECODE": "1"}
    env.pop("CITYNEXUS_LIVE_VALHALLA_URL", None)
    for suffix in ("", "-wal", "-shm"):
        Path(str(DB) + suffix).unlink(missing_ok=True)
    done = subprocess.run([str(PY), "-m", "pytest", nodeid, "-q", "--tb=line", "-p", "no:cacheprovider",
                           "-W", "ignore"], cwd=str(BACKEND), capture_output=True, text=True,
                          encoding="utf-8", errors="replace", env=env, timeout=900)
    out = (done.stdout or "") + (done.stderr or "")
    tail = [l.strip() for l in out.splitlines() if l.strip()][-6:]
    tb = [l.strip() for l in out.splitlines() if ".py:" in l and re.search(r"\.py:\d+:", l)]
    return {"rc": done.returncode, "tail": tail, "tb": tb[-1][:400] if tb else "",
            "assert_lines": [re.search(r"\.py:(\d+):", x).group(1) for x in
                             [y for y in out.splitlines() if re.search(r"\.py:\d+:", y)]]}


def _landed(rel: str) -> bool:
    """变异真落盘了吗：工作树必须报这一枚文件被动过（新建的看它在不在磁盘上）。"""

    if rel in [str(p.relative_to(WT)).replace("\\", "/") for p in CREATED]:
        return (WT / rel).exists()
    done = subprocess.run(["git", "status", "--porcelain", "--", rel], cwd=str(WT),
                          capture_output=True, text=True)
    return done.stdout.strip() != ""


def _case(name: str, nodeid: str, expect: str, cause: str, mutate, expect_line: str = "") -> dict:
    _restore()
    mutated = mutate()
    landed = _landed(mutated)
    t0 = time.time()
    run = _run(nodeid)
    verdict = "RED" if run["rc"] != 0 else "GREEN"
    ok = ((expect == "RED" and verdict == "RED") or (expect == "GREEN" and verdict == "GREEN"))
    #: 红必须红在**那一格自己的那枚断言**上。pytest 的 --tb=line 会把消息截到 200 字符，
    #: 所以判"哪一行断言翻脸"用行号，不用被截掉的关键词。
    named = (run["assert_lines"][:1] == [expect_line]) if expect == "RED" else "n/a"
    row = {"case": name, "expect": expect, "verdict": verdict, "gate_ok": bool(ok and named),
           "mutation_landed": landed, "mutated_path": mutated, "cause_needle": cause,
           "expect_assert_line": expect_line, "actual_assert_line": run["assert_lines"][:1],
           "cause_named_on_screen": named, "rc": run["rc"], "tail": run["tail"],
           "tb": run["tb"], "assert_line": (run["assert_lines"] or [""])[0],
           "seconds": round(time.time() - t0, 1)}
    print(json.dumps({k: row[k] for k in ("case", "expect", "verdict", "gate_ok",
                                          "mutation_landed", "cause_named_on_screen",
                                          "assert_line")}, ensure_ascii=False))
    print("   ", row["tb"][:260])
    return row


# ------------------------------------------------------------------ G4 的六手
def _ce_file(body: str, rel: str = "backend/app/_anchor_ce.py") -> str:
    _create(rel, "from sqlalchemy import text\n\n\n" + body)
    return rel


def g4_same_value_braces():
    """同一枚数换了个写法（`{30000}` 插值）——旧内联白名单看不见，新尺必须看见。"""

    return _ce_file('def leak(session):\n'
                    '    session.execute(text(f"PRAGMA busy_timeout={30000}"))\n')


def g4_above_default():
    """worker 自等被抬到请求路径之上：不是拷贝，但也不再是"射程不同"。"""

    rel = "backend/app/stay_generation_operations.py"
    src = _read(rel)
    assert 'PRAGMA busy_timeout = 1500' in src
    _write(rel, src.replace('PRAGMA busy_timeout = 1500', 'PRAGMA busy_timeout = 45000'))
    return rel


def g4_second_accessor():
    return _ce_file('def busy_timeout_ms() -> int:\n    return 1\n')


def g4_applier_own_number():
    return _ce_file('def ask(engine):\n'
                    '    with engine.connect() as conn:\n'
                    '        conn.execute(text("PRAGMA busy_timeout = " + str(7)))\n')


def g4_consumer_via_settings():
    """漂移中性那一手：又一枚产品文件从 settings 读它（现尖 main.py 的 claim-lease 就是这一形）。
    旧白名单在这里红；新尺不许红。"""

    return _ce_file('from app.core.config import settings\n\n'
                    'PLAN_CLAIM_LEASE_CE_MS = int(settings.write_deadline_ms) '
                    '+ int(settings.write_busy_timeout_ms)\n')


def g4_new_prose_only():
    """漂移中性第二手：新文件只在注释里提到这个名字。"""

    return _ce_file('# busy_timeout stays where it is: the single source module.\n\nCE_X = 1\n')


def g4_import_channel_moved():
    """单源还在，但消费者改从别名模块拿 —— 具名通道断了，尺必须红。"""

    _create("backend/app/db/_anchor_ce_alias.py", "from app.db.write_deadline import *  # noqa: F401,F403\n")
    rel = "backend/app/db/session.py"
    src = _read(rel)
    out = src.replace("from app.db.write_deadline import busy_timeout_ms as write_busy_timeout_ms",
                      "from app.db._anchor_ce_alias import busy_timeout_ms as write_busy_timeout_ms")
    out = out.replace("from app.db.write_deadline import busy_timeout_seconds as write_busy_timeout_seconds",
                      "from app.db._anchor_ce_alias import busy_timeout_seconds as write_busy_timeout_seconds")
    assert out != src
    _write(rel, out)
    return rel


def g4_home_renamed():
    rel = "backend/app/core/config.py"
    src = _read(rel)
    out = src.replace('CITYNEXUS_WRITE_BUSY_TIMEOUT_MS', 'CITYNEXUS_WRITE_LOCK_WAIT_MS')
    assert out != src
    _write(rel, out)
    return rel


# ------------------------------------------------------------------ H01b 的手
def _shift_table(by: int) -> str:
    rel = "frontend/src/features/shared/SharedJourneyPanel.tsx"
    src = _read(rel)
    needle = "export const REFUSAL_KEY"
    pad = "\n".join(["/** drift probe: an unrelated comment line pushed above the table (%d) */" % i
                    for i in range(by)])
    out = src.replace(needle, pad + "\n" + needle, 1)
    assert out != src
    _write(rel, out)
    return rel


def h_shift_one():
    return _shift_table(1)


def h_shift_three():
    return _shift_table(3)


def h_symbol_renamed():
    rel = "frontend/src/features/shared/SharedJourneyPanel.tsx"
    src = _read(rel)
    out = src.replace("export const REFUSAL_KEY", "export const REFUSAL_KEYS")
    assert out != src
    _write(rel, out)
    return rel


def h_label_moved_out():
    rel = "frontend/src/features/shared/SharedJourneyPanel.tsx"
    src = _read(rel)
    out = src.replace('  token_unknown: "shared.refusedTokenUnknown",\n', '', 1)
    assert out != src
    _write(rel, out)
    return rel


def h_label_renamed():
    """值仍是两本词典都认得的键（赦免照旧成立），只有**我锚的那个标签**不见了。

    这一手专咬具名锚本身：门的 `hits_in_product_path` 那一格仍然绿，红只能来自现推导入不到条目。
    """

    rel = "frontend/src/features/shared/SharedJourneyPanel.tsx"
    src = _read(rel)
    out = src.replace('  token_unknown: "shared.refusedTokenUnknown",',
                      '  token_renamed: "shared.refusedTokenUnknown",', 1)
    assert out != src
    _write(rel, out)
    return rel


def h_value_not_a_key():
    rel = "frontend/src/features/shared/SharedJourneyPanel.tsx"
    src = _read(rel)
    out = src.replace('token_unknown: "shared.refusedTokenUnknown"',
                      'token_unknown: "shared.refusedMadeUpKey"')
    assert out != src
    _write(rel, out)
    return rel


def h_table_stops_being_pure():
    """表里混进一枚非词典值 ⇒ 整表不再被赦免 ⇒ 命中的那一行回到 live。"""

    rel = "frontend/src/features/shared/SharedJourneyPanel.tsx"
    src = _read(rel)
    out = src.replace('  unnamed: "shared.refusedUnnamed",\n',
                      '  unnamed: "shared.refusedUnnamed",\n  token_count: 7,\n', 1)
    assert out != src
    _write(rel, out)
    return rel


CASES = [
    # G4 的六手红各红在自己那枚断言上（行号取自本枝提交的那份尺：282 homes / 285 copies /
    # 288 accessor / 291 importers / 295 rival / 299 unattributed）
    ("G4-1 同值换写法（旧白名单看不见）", G4, "RED", "copies", g4_same_value_braces, "285"),
    ("G4-2 worker 自等抬到请求路径之上", G4, "RED", "not_below_the_request_path_wait",
     g4_above_default, "295"),
    ("G4-3 访问器出现第二处定义", G4, "RED", "_anchor_ce.py", g4_second_accessor, "288"),
    ("G4-4 上连接的行自带数字、不问单源", G4, "RED", "appliers_that_bring_their_own_number",
     g4_applier_own_number, "299"),
    ("G4-5 单源通道改指别名模块", G4, "RED", "nobody imports the accessor",
     g4_import_channel_moved, "291"),
    ("G4-6 家的具名环境变量被改名", G4, "RED", "exactly one declaration home", g4_home_renamed, "282"),
    ("G4-7 漂移中性：第六枚合法消费者", G4, "GREEN", "", g4_consumer_via_settings, ""),
    ("G4-8 漂移中性：新文件只在注释里提名字", G4, "GREEN", "", g4_new_prose_only, ""),
    # H01b：漂移中性两手 + 四手各红在具名锚或门自己的断言上（67 声明 / 82 条目 / 210 命中）
    ("H-1 漂移中性：具名表被往上顶 1 行", H1B, "GREEN", "", h_shift_one, ""),
    ("H-2 漂移中性：具名表被往上顶 3 行", H1B, "GREEN", "", h_shift_three, ""),
    ("H-3 符号被改名（锚必须说得出找不到谁）", H1B, "RED", "declarations_found_at",
     h_symbol_renamed, "67"),
    ("H-4 那一行被搬出表外", H1B, "RED", "entries_found_at", h_label_moved_out, "82"),
    ("H-5 标签被改名：具名锚自己红", H1B, "RED", "entries_found_at(renamed label)",
     h_label_renamed, "82"),
    ("H-6 值不再是两本词典都认得的键", H1B, "RED", "hits_in_product_path", h_value_not_a_key, "210"),
    ("H-7 表里混进非词典值 ⇒ 赦免整表失效", H1B, "RED", "hits_in_product_path",
     h_table_stops_being_pure, "210"),
]


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    only = [a.split("=", 1)[1] for a in sys.argv if a.startswith("--only=")]
    _restore()
    base = {"worktree_head": subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(WT),
                                            capture_output=True, text=True).stdout.strip(),
            "interpreter": str(PY), "python": subprocess.run(
                [str(PY), "-V"], capture_output=True, text=True, errors="replace").stdout.strip(),
            "started": time.strftime("%m-%d %H:%M:%S"), "db": str(DB)}
    rows = []
    try:
        for name, node, expect, cause, fn, el in CASES:
            if only and not any(o in name for o in only):
                continue
            rows.append(_case(name, node, expect, cause, fn, el))
    finally:
        _restore()
        clean = subprocess.run(["git", "status", "--porcelain"], cwd=str(WT),
                               capture_output=True, text=True).stdout.strip()
    rows.sort(key=lambda r: r["case"])
    out = {"form": base, "cases": rows,
           "counts": {"total": len(rows),
                      "gate_ok": sum(1 for r in rows if r["gate_ok"]),
                      "mutation_landed": sum(1 for r in rows if r["mutation_landed"]),
                      "cause_named": sum(1 for r in rows if r["cause_named_on_screen"] is True),
                      "red": sum(1 for r in rows if r["verdict"] == "RED"),
                      "green": sum(1 for r in rows if r["verdict"] == "GREEN")},
           "worktree_after_restore": clean,
           "verdict": ("ALL_COUNTEREXAMPLES_BITE_AND_DRIFT_IS_NEUTRAL"
                       if all(r["gate_ok"] and r["mutation_landed"] for r in rows) and clean == ""
                       else "SEE_CASES")}
    dst = Path("D:/moodle/_qoder_newlane_ord0444_20260929/scratch/anchor_ruler_counterexamples_r1.json")
    dst.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(out["verdict"], out["counts"], "worktree clean:", repr(out["worktree_after_restore"]))
    print("WROTE", dst)
    return 0 if out["verdict"].startswith("ALL_") else 1


if __name__ == "__main__":
    import atexit
    atexit.register(_restore)
    sys.exit(main())
