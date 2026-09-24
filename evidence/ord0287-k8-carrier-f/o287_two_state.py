"""ORD-0287 判据 3：同一格两态可跑 —— 权威树 GREEN、拆掉守卫后同一格 RED，且正控 K2 两态都绿。"""
from __future__ import annotations

import difflib
import os
import hashlib
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RUN = Path("D:/moodle/_qoder_f_run")
import os
BACKEND = Path(os.environ.get("O287_BACKEND", str(RUN / "e_0282_45b0a5e" /
           "Canshu-King-CityNexus-45b0a5e281cae9c37715173afd3ac5778f309ca7/backend")))
OUT = Path(os.environ.get("O287_OUT", str(RUN / "o225_receipts/ord0287_two_state_run.json")))
MAIN = BACKEND / "app/main.py"
CARRIER = "tests/test_qoder_ord0287_k8_carrier.py"
PY = r"D:\moodle\CityNexus\.venv\Scripts\python.exe"
LANDING = "416ea4f210e967130710a900cdecd20e7a1b5eca"
GUARD = ("                    .where(IdempotencyKey.key == key,\n"
         "                           IdempotencyKey.response_json.is_(None))\n")
NOGUARD = "                    .where(IdempotencyKey.key == key)\n"



def blob(b: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(b) + b).hexdigest()


def run(label: str, nodeid: str | None = None):
    db = RUN / f"_o287_state_{label}.db"
    for suf in ("", "-wal", "-shm"):
        if Path(str(db) + suf).exists():
            Path(str(db) + suf).unlink()
    import os
    e = dict(os.environ)
    for k in ("DEEPSEEK_API_KEY", "OPENAI_API_KEY", "CITYNEXUS_AI_API_KEY", "CITYNEXUS_LIVE_VALHALLA_URL"):
        e.pop(k, None)
    e["CITYNEXUS_DATABASE_URL"] = f"sqlite:///{db.as_posix()}"
    e["CITYNEXUS_AI_ENABLED"] = "false"
    target = f"{CARRIER}::{nodeid}" if nodeid else CARRIER
    t0 = time.time()
    p = subprocess.run([PY, "-m", "pytest", target, "-q", "--no-header", "-p", "no:cacheprovider",
                        "-rf", "--tb=line"], cwd=str(BACKEND), capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env=e, timeout=1800)
    lines = [l for l in (p.stdout or "").splitlines() if l.strip()]
    for suf in ("", "-wal", "-shm"):
        if Path(str(db) + suf).exists():
            Path(str(db) + suf).unlink()
    return {"target": target, "rc": p.returncode, "seconds": round(time.time() - t0, 1),
            "collected_line": next((l for l in lines if "collected" in l or "no tests ran" in l), ""),
            "summary_line": next((l for l in reversed(lines)
                                  if "passed" in l or "failed" in l or "error" in l), ""),
            "failure_lines": [l for l in lines if l.startswith(("FAILED", "E ", "tests/"))][:4]}


original = MAIN.read_bytes()
assert blob(original) == LANDING, f"SETUP：权威树不是那枚 blob：{blob(original)}"
data = {"what": "ORD-0287 判据 3：载体两态可跑（守卫在位 / 拆掉），K2 正控两边都绿 ⇒ 红可归因",
        "lane": "F 8ccd71d8", "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "tree": {"backend_cwd": str(BACKEND), "main_py_landing_blob": blob(original),
                 "carrier_file": CARRIER,
                 "carrier_blob": blob((BACKEND / CARRIER).read_bytes())},
        "rounds": [],
        "backend_env_override": os.environ.get("O287_BACKEND", "(default export)")}
try:
    for rnd in (1, 2):
        entry = {"round": rnd}
        entry["authoritative"] = {
            "both_cells": run(f"a{rnd}_both"),
            "K1": run(f"a{rnd}_k1", "test_K1_a_receipt_another_writer_already_filled_is_never_rewritten_and_refuses_by_name"),
            "K2": run(f"a{rnd}_k2", "test_K2_my_own_unfilled_claims_do_get_filled_and_hold_my_answer"),
            "main_blob": blob(MAIN.read_bytes())}
        text = MAIN.read_text(encoding="utf-8")
        assert text.count(GUARD) == 1, f"SETUP：守卫锚点命中 {text.count(GUARD)} 次"
        mutated = text.replace(GUARD, NOGUARD)
        hunks = [l for l in difflib.unified_diff(text.splitlines(), mutated.splitlines(), lineterm="")
                 if l.startswith("@@")]
        MAIN.write_bytes(mutated.encode("utf-8"))
        after = blob(MAIN.read_bytes())
        compile_ok = subprocess.run([PY, "-m", "py_compile", str(MAIN)], capture_output=True).returncode == 0
        entry["mutant"] = {
            "before_blob": LANDING, "after_blob_40": after, "hunks": len(hunks),
            "hunk_headers": hunks, "py_compile_ok": compile_ok,
            "removed_expression": "IdempotencyKey.response_json.is_(None)",
            "lines_delta": [len(text.splitlines()), len(mutated.splitlines())],
            "K1": run(f"m{rnd}_k1", "test_K1_a_receipt_another_writer_already_filled_is_never_rewritten_and_refuses_by_name"),
            "K2": run(f"m{rnd}_k2", "test_K2_my_own_unfilled_claims_do_get_filled_and_hold_my_answer")}
        MAIN.write_bytes(original)
        assert blob(MAIN.read_bytes()) == LANDING, f"ROUND {rnd}：还原后 blob 不等 ⇒ 停"
        entry["restored_byte_exact"] = True
        data["rounds"].append(entry)
        print(f"[r{rnd}] 权威 K1={entry['authoritative']['K1']['rc']} K2={entry['authoritative']['K2']['rc']} | "
              f"突变 K1={entry['mutant']['K1']['rc']} K2={entry['mutant']['K2']['rc']} | "
              f"after={after[:9]} hunks={entry['mutant']['hunks']} py_compile={compile_ok} 还原 OK")
finally:
    MAIN.write_bytes(original)
data["final"] = {"main_blob_after_all": blob(MAIN.read_bytes()),
                 "byte_exact_vs_landing": blob(MAIN.read_bytes()) == LANDING}
K1_NAME = "test_K1_a_receipt"


def rc(entry, face, cell):
    return entry[face][cell]["rc"]


data["derived"] = {
    "carrier_green_on_authoritative": all(r["authoritative"]["K1"]["rc"] == 0
                                          and r["authoritative"]["K2"]["rc"] == 0 for r in data["rounds"]),
    "same_cell_red_under_mutation": all(rc(r, "mutant", "K1") != 0 for r in data["rounds"]),
    "positive_control_still_green_under_mutation": all(rc(r, "mutant", "K2") == 0 for r in data["rounds"]),
    "one_hunk_every_round": all(r["mutant"]["hunks"] == 1 for r in data["rounds"]),
    "py_compile_every_round": all(r["mutant"]["py_compile_ok"] for r in data["rounds"]),
    "restored_every_round": all(r["restored_byte_exact"] for r in data["rounds"]),
    "verdict": None}
d = data["derived"]
d["verdict"] = ("TWO_STATE_CARRIER_OK" if all(d[k] for k in list(d)[:5]) and data["final"]["byte_exact_vs_landing"]
                else "NOT_ELIGIBLE")
OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
print(json.dumps({"derived": d, "final": data["final"],
                  "K1_mutant_failure_lines": data["rounds"][0]["mutant"]["K1"]["failure_lines"]},
                 ensure_ascii=False, indent=1))
print("WROTE", OUT, OUT.stat().st_size, "B")
