"""Point the r4 delivery tree and its coordinate list at the receipts this round actually produced.

Three names moved when the round moved from tip 7862c6de to tip 514b397f: the exposure receipts are
named for the tip and the ref they describe, the landing-check receipt is `gen8_landing_check_r1.json`,
and the readings page is `GEN8_READINGS.md`.  The coordinate list has to name them exactly or the
ledger gate gets a claim it cannot resolve.
"""
import ast
import os

LANE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COORD = os.path.join(LANE, "tools", "gen8_coordinates_r1.py")
BLOCKS = os.path.join(LANE, "tools", "gen8_blocks_r1.py")

pairs = [
    ('"review/ord0500-checkin/receipts/exposure_tip_7862c6de_r1.json"',
     '"review/ord0500-checkin/receipts/exposure_tip_514b397f_r1.json"'),
    ('"review/ord0500-checkin/receipts/exposure_r3_candidate_r1.json"',
     '"review/ord0500-checkin/receipts/exposure_r4_candidate_r1.json"'),
    ('"review/ord0500-checkin/receipts/gen8_landing_check_r2.json"',
     '"review/ord0500-checkin/receipts/gen8_landing_check_r1.json"'),
    ('blobs["review/ord0500-checkin/receipts/exposure_tip_7862c6de_r1.json"]',
     'blobs["review/ord0500-checkin/receipts/exposure_tip_514b397f_r1.json"]'),
    ('blobs["review/ord0500-checkin/receipts/exposure_r3_candidate_r1.json"]',
     'blobs["review/ord0500-checkin/receipts/exposure_r4_candidate_r1.json"]'),
    ('blobs["review/ord0500-checkin/receipts/gen8_landing_check_r2.json"]',
     'blobs["review/ord0500-checkin/receipts/gen8_landing_check_r1.json"]'),
    ('"review/ord0500-checkin/GEN5_READINGS.md"', '"review/ord0500-checkin/GEN8_READINGS.md"'),
]
for path in (COORD, BLOCKS):
    text = open(path, encoding="utf-8").read()
    hits = 0
    for old, new in pairs:
        if old in text:
            text = text.replace(old, new)
            hits += 1
    open(path, "w", encoding="utf-8", newline="\n").write(text)
    ast.parse(text)
    print("%-34s %d names retargeted" % (os.path.basename(path), hits))

# the sheet's own header must name this round
SHEET = os.path.join(LANE, "tools", "gen8_sheets_r1.py")
text = open(SHEET, encoding="utf-8").read()
old = "# ORD-0500 r2 -> r3 -- 现尖 7862c6de 读数单（本代全部重量，无跨代折算；Q64 那三趟曝光尺读数在 receipts 里）"
new = ("# ORD-0500 r4 -- 现尖 514b397f96f3b5165b24865f4a544ab6f8020084 读数单"
       "（与 ORD-0530 同族并块后重量；曝光尺两侧对照在 receipts 里）")
if text.count(old) == 1:
    text = text.replace(old, new)
    open(SHEET, "w", encoding="utf-8", newline="\n").write(text)
    ast.parse(text)
    print("gen8_sheets_r1.py header retargeted")
else:
    print("gen8_sheets header anchor count:", text.count(old))
