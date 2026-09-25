"""Point the ORD-0302 delivery at the r2 amendment: a new base, a new evidence path, and the five shapes.

The product fix is already on the authority line, so this candidate carries no product byte -- what it adds is
coverage: X-5's cell now boots the sheet once per shape for the five HTTP 200 bodies the commander named, and
the receipt has to say that per shape rather than once. The root-cause measurement still belongs to the
generation where the defect lived, so that read is taken from its own base instead of from the candidate's.
"""
import ast
import pathlib

P = pathlib.Path(r"D:\moodle\_qoder_spike_20260921\ord0302_deliver.py")
s = P.read_text(encoding="utf-8")

EDITS = [
    ('''DIR = "evidence/ord0302-unreadable-server-body"
BASE = "dc964086c9d412573ac19d70b24b30e6c3ee6168"''',
     '''DIR = os.environ.get("CNX_0302_DIR", "evidence/ord0302-unreadable-server-body")
BASE = os.environ.get("CNX_0302_BASE", "dc964086c9d412573ac19d70b24b30e6c3ee6168")
# The defect's own line numbers belong to the generation that still had it; the candidate's parent is a later
# tip where the file is already fixed, so the two are named separately instead of one standing in for both.
BUGGED_BASE = os.environ.get("CNX_0302_BUGGED_BASE", "dc964086c9d412573ac19d70b24b30e6c3ee6168")'''),
 ('''bugged_text = subprocess.run(["git", "-C", str(LANE), "show", f"{BASE}:{SHEET}"], capture_output=True).stdout.decode("utf-8")''',
     '''bugged_text = subprocess.run(["git", "-C", str(LANE), "show", f"{BUGGED_BASE}:{SHEET}"],
                             capture_output=True).stdout.decode("utf-8")'''),

    # ---- the X-5 cell carries one reading per shape, and says so per shape
    ('''                "details_count": read.get("details_count"),
                "promise_in_copy": read.get("promise_in_copy"),''',
     '''                "details_count": read.get("details_count"),
                "per_shape": r.get("per_shape"), "shape_count": r.get("shape_count"),
                "promise_in_copy": read.get("promise_in_copy"),'''),
 ('''    seen = (f"its rendered card text points at 技术详情={readings['promise_in_copy']} and the DOM held "
            f"{readings['details_count']} such block(s), so attached={readings['detail_block_attached']}"
            if paired else
            f"the detail block was attached={readings['detail_block_attached']}")''',
     '''    seen = (f"its rendered card text points at 技术详情={readings['promise_in_copy']} and the DOM held "
            f"{readings['details_count']} such block(s), so attached={readings['detail_block_attached']}"
            if paired else
            f"the detail block was attached={readings['detail_block_attached']}")
    if readings.get("per_shape"):
        # one clause per shape, each from that shape's own reading -- the commander named five rows, so a
        # single sentence about one of them would be a sample presented as the family
        seen += (" judged once per shape over the " + str(readings["shape_count"]) + " rows X-5 named: "
                 + "; ".join(f"{row} -> status={v['status']}, promise={v['promise_in_copy']}, "
                             f"details_count={v['details_count']}, origin={v['origin']}, "
                             f"reason={str(v['reason'])[:44]!r}" for row, v in readings["per_shape"].items()))'''),
 ('''cells.append(arm_cell("X1", "device", "X-5: this status's own card text points at 技术详情, so the block must "
                                   "exist and must carry the reading; the arm also requires the pointer to "
                                   "still be worded."))''',
     '''cells.append(arm_cell("X1", "device", "X-5: for every one of the five HTTP 200 shapes the card text points "
                                   "at 技术详情, so the block must exist and must carry a reading, and the "
                                   "pointer may not be deleted to make the test pass (Q53=① rendered it)."))'''),

    # ---- name the amendment for what it is
    ('''           "order": "ORD-0302 文案修 · 非 JSON 正文不得冒充网络故障", "lane": "B c01d72a3",''',
     '''           "order": "ORD-0302 文案修 · 非 JSON 正文不得冒充网络故障 · r2 补 X-5 五形", "lane": "B c01d72a3",
           "amendment_of": "evidence/ord0302-unreadable-server-body", "product_bytes_changed": 0,'''),
 ('''for p in (SPIKE / "ord0302_run_arms.py", SPIKE / "ord0302_deliver.py"):''',
     '''for p in (SPIKE / "ord0302_run_arms.py", SPIKE / "ord0302_deliver.py",
          SPIKE / "ord0302_x5_five_shapes_patch.py", SPIKE / "ord0302_deliver_r2_patch.py"):'''),

    # ---- the ledger and bus headlines
    ('''MARK = ("### B c01d72a3 · ORD-0302 文案修（一枚候选装下两枚具名格：非 JSON 正文冒充网络故障 ＋ X-5 的承诺指向空块）"
        f"基座 `{BASE[:7]}` 候选 `{CAND[:7]}`")''',
     '''MARK = ("### B c01d72a3 · ORD-0302 文案修 r2（X-5 那一格从一形补到号令者点名的五形 R19-R23；"
        f"产品字节 0 改动）基座 `{BASE[:7]}` 候选 `{CAND[:7]}`")'''),
 ('''lines.append(MARK + " @" + time.strftime("%H:%M", time.localtime()) + "+08 —— "
             "**号令者自己读出来的那两行我核过了，是真的；X-5 与 null-body 那一格同行域，所以一次候选、一次落地，"
             "没有第二张单。**")''',
     '''lines.append(MARK + " @" + time.strftime("%H:%M", time.localtime()) + "+08 —— "
             "**上一版 X1 只驱动了五形里的一形（200 + plans:[]），等于拿样本冒充整族；这一版五形各自读一遍，"
             "反件仍只咬 X1 那一格。**")'''),
 ('''first = ("B c01d72a3 → 号令者 494abfd7：ORD-0302 交候选 " + CAND + "（基座 " + BASE
         + "，两枚具名格落在同一枚 ref " + BRANCH + " 上，快进自你手上那一枚 " + SUPERSEDED
         + "，没有 force-push）：两处安全读 + NETWORK 的可见兑底 + X-5 的承诺与块成对；"
         + "五枚臂 MET、四枚反件各自只咬自己那一格")''',
     '''first = ("B c01d72a3 → 号令者 494abfd7：ORD-0302 交 r2 候选 " + CAND + "（基座 " + BASE
         + "，ref " + BRANCH + "）：**产品字节 0 改动**，只把 X-5 那一格从一形补到你点名的五形 R19-R23，"
         + "五形各自判一遍正反两读；五枚臂 MET、四枚反件仍各自只咬自己那一格")'''),
]

for old, new in EDITS:
    n = s.count(old)
    if n != 1:
        raise SystemExit(f"anchor occurs {n} times (want 1): {old[:80]!r}")
    s = s.replace(old, new, 1)

# the root-cause cell must say which generation its line numbers were read off
old_root = '''"base_tip": BASE, "bugged_sheet_blob": BUGGED, "candidate_sheet_blob": SHEET_BLOB,'''
new_root = '''"base_tip": BASE, "defect_generation_base": BUGGED_BASE, "bugged_sheet_blob": BUGGED,
        "candidate_sheet_blob": SHEET_BLOB,'''
assert s.count(old_root) == 1
s = s.replace(old_root, new_root, 1)
old_prose = '''root_why = ("root cause, re-measured on this tree rather than copied from the order: in the bugged blob "'''
new_prose = '''root_why = ("root cause, re-measured on the generation that still carries it (" + BUGGED_BASE
            + ") rather than copied from the order: in the bugged blob "'''
assert s.count(old_prose) == 1
s = s.replace(old_prose, new_prose, 1)

ast.parse(s)
P.write_text(s, encoding="utf-8", newline="\n")
print("ord0302_deliver.py now runs the r2 amendment; parses cleanly")
