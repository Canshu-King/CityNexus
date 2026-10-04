"""ORD-0512 place_name 格：把两趟全套的红集合按 nodeid 成对比，判这手到底带进或带走了哪几枚。

同一棵树、同一枚解释器、同一道 `--ignore`（那枚 `citynexus_mcp` 缺包在本机收不起来），只差三枚
产品/契约字节加一枚生成的客户端：一趟是现尖原样 + 本手那支新文件，另一趟是本手改后的字节。

判语只有三种，且不许挑好听的那一种写：

  NEW_RED_EMPTY        本手之后红集合是之前那份的子集（改后没有多红）
  NEW_RED_FOUND        列出具体的新红，整手不许交
  AND_THESE_WENT_GREEN 之前红、现在绿的枚号（本手应当只有这一格非空，且逐枚是本单自己的臂）
"""
import io
import json
import pathlib
import re
import sys

LANE = pathlib.Path(r"D:/moodle/_qoder_b_ord0417_20260928")
OUT = LANE / "evidence/ord0512/place_name"
FAILED = re.compile(r"^FAILED (\S+::\S+)", re.M)
MY_ARMS = {
    "tests/test_qoder_ord0512_place_name_on_the_wire_r1.py::test_the_store_name_reaches_the_plan_door",
    "tests/test_qoder_ord0512_place_name_on_the_wire_r1.py::test_a_stop_that_was_never_placed_answers_null",
    "tests/test_qoder_ord0512_place_name_on_the_wire_r1.py::test_the_field_is_one_vocabulary_in_the_two_schema_halves_and_the_runtime",
    "tests/test_qoder_ord0512_place_name_on_the_wire_r1.py::test_the_name_is_read_off_the_row_the_door_already_loaded",
}


def reds(path: pathlib.Path) -> set[str]:
    text = io.open(path, encoding="utf-8", errors="replace").read()
    return {line.split(" ", 1)[0] for line in FAILED.findall(text)}


def main() -> int:
    base_path = OUT / "backend_suite_base_r1.txt"
    patched_path = OUT / "backend_suite_r1.txt"
    for path in (base_path, patched_path):
        if not path.exists():
            print("REFUSE: missing run %s" % path)
            return 2
    base, patched = reds(base_path), reds(patched_path)
    new_red = sorted(patched - base)
    went_green = sorted(base - patched)
    verdict = "NEW_RED_EMPTY" if not new_red else "NEW_RED_FOUND"
    unexplained = sorted(set(went_green) - MY_ARMS)
    report = {
        "base_red_count": len(base),
        "patched_red_count": len(patched),
        "new_red": new_red,
        "went_green": went_green,
        "went_green_all_belong_to_this_order": not unexplained,
        "unexplained_recovered_arms": unexplained,
        "verdict": verdict,
        "base_tail": [line for line in io.open(base_path, encoding="utf-8", errors="replace").read().splitlines()
                      if " passed" in line or " failed" in line][-1:],
        "patched_tail": [line for line in io.open(patched_path, encoding="utf-8", errors="replace").read().splitlines()
                         if " passed" in line or " failed" in line][-1:],
    }
    (OUT / "suite_red_set_diff_r1.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    print("BASE=%d PATCHED=%d VERDICT=%s NEW_RED=%d RECOVERED=%d ALL_MINE=%s"
          % (len(base), len(patched), verdict, len(new_red), len(went_green), report["went_green_all_belong_to_this_order"]))
    print("NEW_RED=%s" % json.dumps(new_red, ensure_ascii=False))
    print("RECOVERED=%s" % json.dumps(went_green, ensure_ascii=False))
    return 0 if verdict == "NEW_RED_EMPTY" and not unexplained else 6


if __name__ == "__main__":
    sys.exit(main())
