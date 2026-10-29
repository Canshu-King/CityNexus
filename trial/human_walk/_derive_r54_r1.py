import pathlib
import sys

SRC = pathlib.Path(r"D:/moodle/_cmdr_rescue_v3_1022/trial/human_walk/_map_walk_r52.mjs")
DST = pathlib.Path(r"D:/moodle/_cmdr_rescue_v3_1022/trial/human_walk/_plan_hand_r54.mjs")
text = SRC.read_text(encoding="utf-8")

replacements = [
    ('const OUT = `${DIR}/map-planned-${TAG}-r52.txt`;',
     'const OUT = `${DIR}/plan-open-hand-${TAG}-r54.txt`;'),
    ('note(`LOOP ${round}/${i} GATE ${JSON.stringify(gate.slice(0, 1))} BLOCK ${JSON.stringify(gaps.slice(0, 2))} ALERT ${JSON.stringify(alerts.slice(0, 1))}`);',
     'note(`LOOP ${round}/${i} GATE ${JSON.stringify(gate.slice(0, 1))} GAPS_ALL ${JSON.stringify(gaps)} ALERT ${JSON.stringify(alerts.slice(0, 1))}`);'),
]
for old, new in replacements:
    if text.count(old) != 1:
        sys.exit(f"ABORT anchor count={text.count(old)} for {old[:60]!r}")
    text = text.replace(old, new)

# Replace the tail (everything from the map-recorder comment onward) with the hand-under-test reads.
marker = "// The knife under test: after the traveller's own accept"
if text.count(marker) != 1:
    sys.exit(f"ABORT marker count={text.count(marker)}")
head, _sep, _tail = text.partition(marker)

tail = '''// The knife under test is no longer the map: it is the hand that has to sit beside the server's
// refusal sentence (backend/app/services.py:742 makes the candidate unselectable while a confirmed
// time band still has no place).  Read every gap paragraph, then press the hand if it is there.
const gapsAll = await page.locator(".rev-plan-gap").allInnerTexts().catch(() => []);
note(`PLAN_GAPS_ALL ${JSON.stringify(gapsAll)} t=${elapsed()}`);
note(`PLAN_SELECT ${await page.locator('[data-testid="rev-plan-select"]').count()}`);
note(`PLAN_START ${await page.locator('[data-testid="rev-plan-start"]').count()}`);
const hand = page.locator('[data-testid="rev-plan-open-place-explore"]');
note(`PLAN_HAND ${await hand.count()} t=${elapsed()}`);
await shot(`${TAG}-r54-plan-blocked`);
if (await hand.count()) {
  const pressed = await press(hand, "open-place-hand", 12000);
  await page.waitForTimeout(4000);
  const after = await bodyText();
  note(`HAND_PRESSED ${pressed} t=${elapsed()}`);
  note(`AFTER_HAND_HEAD ${JSON.stringify(after.replace(/\\s+/g, " ").slice(0, 300))}`);
  note(`AFTER_HAND_HAS_EXPLORE ${/探索|查找地点|候选地点|已找到的地点/.test(after)}`);
  await shot(`${TAG}-r54-after-hand`);
}
note(`ERRORS ${JSON.stringify(errors.slice(0, 3))}`);
await ctx.close();
'''

DST.write_text(head + tail, encoding="utf-8", newline="\n")
print(f"WROTE {DST} bytes={DST.stat().st_size}")
