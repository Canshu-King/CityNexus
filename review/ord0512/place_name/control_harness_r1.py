"""ORD-0512 place_name 格的对照件：把三处产品/契约字节退回现尖，只留测试文件，看哪几枚臂变红。

形制与这单的反件纪律一致：

  1. 先读下将要被替换的四枚字节的 sha256（三枚产品/契约 + 测试文件本身，测试文件不该被动过，
     它的哈希在还原后必须逐字相同——否则"臂变红了"量的就不是同一把尺）；
  2. 三枚产品/契约取现尖 refs/tmp/line_2032 的字节原样写入（不是我手改的"退化版"）；
  3. 跑这格那六枚臂，逐枚记 passed/failed；
  4. 写回并再哈希，"还原"是文件的事实而不是意图的说法。

usage: python ord0512_place_name_control_r1.py
"""
import hashlib
import io
import json
import pathlib
import subprocess
import sys

LANE = pathlib.Path(r"D:/moodle/_qoder_b_ord0417_20260928")
TREE = LANE / "placecut_r1"
REPO = r"D:/moodle/CityNexus"
TIP = "refs/tmp/line_2032"
OUT = LANE / "evidence/ord0512/mutant"

PRODUCT = [
    "backend/app/schemas.py",
    "backend/app/services.py",
    "contracts/openapi.yaml",
]
SPEC = "backend/tests/test_qoder_ord0512_place_name_on_the_wire_r1.py"
# The runner's cwd is `backend/`, so the path handed to pytest drops that first segment; the
# snapshot above is always tree-relative.
SPEC_ARG = "tests/test_qoder_ord0512_place_name_on_the_wire_r1.py"
PY = r"D:/moodle/CityNexus/.venv/Scripts/python.exe"


def digest(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tip_bytes(rel: str) -> bytes:
    done = subprocess.run(["git", "-C", REPO, "show", f"{TIP}:{rel}"], capture_output=True, check=True)
    return done.stdout


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    kept = {rel: (TREE / rel).read_bytes() for rel in [*PRODUCT, SPEC]}
    report = {"tip": subprocess.run(["git", "-C", REPO, "rev-parse", TIP], capture_output=True,
                                    text=True).stdout.strip()}
    report["sha_before"] = {rel: hashlib.sha256(kept[rel]).hexdigest() for rel in kept}
    report["tip_sha_of_the_same_paths"] = {rel: hashlib.sha256(tip_bytes(rel)).hexdigest() for rel in PRODUCT}
    try:
        for rel in PRODUCT:
            (TREE / rel).write_bytes(tip_bytes(rel))
        report["applied"] = "reverted_to_tip_bytes"
        proc = subprocess.run(
            [PY, "-m", "pytest", SPEC_ARG, "-q", "-p", "no:cacheprovider", "--no-header", "-rf"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(TREE / "backend"),
        )
        text = proc.stdout + proc.stderr
        report["runner_rc"] = proc.returncode
        report["summary"] = [line for line in text.splitlines() if " passed" in line or " failed" in line][-2:]
        report["red_arms"] = sorted({line.split("::")[-1].strip() for line in text.splitlines()
                                     if line.startswith("FAILED ")})
        report["tail"] = text.splitlines()[-14:]
    finally:
        for rel, data in kept.items():
            (TREE / rel).write_bytes(data)
    report["restored_matches_original"] = {rel: digest(TREE / rel) == report["sha_before"][rel] for rel in kept}
    report["spec_untouched"] = report["restored_matches_original"][SPEC]
    (OUT / "place_name_control_r1.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    print("RC=%s SUMMARY=%s" % (report["runner_rc"], report["summary"]))
    print("RED=%s" % json.dumps(report["red_arms"], ensure_ascii=False))
    print("RESTORED=%s SPEC_UNTOUCHED=%s" % (all(report["restored_matches_original"].values()), report["spec_untouched"]))
    print("REPORT=%s" % (OUT / "place_name_control_r1.json"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
