"""ORD-0512 place_name 格：把这一手的四组读数一次落盘，交件时逐枚可回读。

跑的都是这格自己的东西：六枚臂在改过的字节上、契约闸、全树 collect-only 的分母、以及 openapi
对账工具在这一代为什么量不出（它要 `frontend/src/generated/api.ts`，本树是稀树，那一路不在）。

usage: python ord0512_place_name_readings_r1.py
"""
import json
import pathlib
import subprocess
import sys

LANE = pathlib.Path(r"D:/moodle/_qoder_b_ord0417_20260928")
TREE = LANE / "placecut_r1"
OUT = LANE / "evidence/ord0512/place_name"
PY = r"D:/moodle/CityNexus/.venv/Scripts/python.exe"
SPEC = "tests/test_qoder_ord0512_place_name_on_the_wire_r1.py"


def run(args, cwd, name):
    done = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(cwd))
    text = (done.stdout or "") + (done.stderr or "")
    (OUT / name).write_text(text, encoding="utf-8", newline="\n")
    tail = [line for line in text.splitlines() if line.strip()][-2:]
    print("%s rc=%s %s" % (name, done.returncode, " | ".join(tail)[:180]))
    return {"rc": done.returncode, "file": str(OUT / name), "tail": tail}


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    readings = {}
    readings["arms_on_patched_bytes"] = run(
        [PY, "-m", "pytest", SPEC, "-q", "-p", "no:cacheprovider", "--no-header", "-v"],
        TREE / "backend", "arms_green_r1.txt")
    readings["contract_gate"] = run(
        [PY, "-m", "pytest", "tests/test_contract.py", "-q", "-p", "no:cacheprovider"],
        TREE / "backend", "contract_gate_r1.txt")
    readings["collection_denominator"] = run(
        [PY, "-m", "pytest", "tests", "--collect-only", "-q", "-p", "no:cacheprovider"],
        TREE / "backend", "collection_r1.txt")
    readings["openapi_parity_tool"] = run([PY, "tools/verify_openapi_parity.py"], TREE, "openapi_parity_r1.txt")
    readings["interpreter"] = run([PY, "-c", "import sys,pytest;print(sys.version);print(pytest.__version__)"],
                                  TREE / "backend", "interpreter_r1.txt")
    (OUT / "place_name_readings_r1.json").write_text(json.dumps(readings, indent=1, ensure_ascii=False), encoding="utf-8")
    print("REPORT=%s" % (OUT / "place_name_readings_r1.json"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
