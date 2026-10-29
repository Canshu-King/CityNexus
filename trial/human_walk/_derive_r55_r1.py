import pathlib
import sys

ROOT = pathlib.Path(r"D:/moodle/_cmdr_rescue_v3_1022/trial/human_walk")
r52 = (ROOT / "_map_walk_r52.mjs").read_text(encoding="utf-8")
r54 = (ROOT / "_plan_hand_r54.mjs").read_text(encoding="utf-8")

# 1) Rename the receipt so no arm writes over another arm's evidence.
old_out = 'const OUT = `${DIR}/plan-open-hand-${TAG}-r54.txt`;'
new_out = 'const OUT = `${DIR}/go-active-${TAG}-r55.txt`;'
if r54.count(old_out) != 1:
    sys.exit(f"ABORT out-anchor count={r54.count(old_out)}")
body = r54.replace(old_out, new_out)

# 2) The walk could only press 确认方案，开始行程 inside the same breath as a successful select, so once
#    the candidate had become SELECTED the start key sat on screen unpressed.  Give it its own look.
anchor = "    if (selVisible && selEnabled) {"
fallback = """    if (selCount === 0 && (await visible(startButton)) && await press(startButton, `start-fallback-${round}-${i}`, 30000)) {
      startedJourney = true;
      await page.waitForTimeout(9000);
      await shot(`${TAG}-g7-started-fallback`);
      break;
    }
"""
if body.count(anchor) != 1:
    sys.exit(f"ABORT loop-anchor count={body.count(anchor)}")
body = body.replace(anchor, fallback + anchor)

# 3) Re-attach the map reads that arm L dropped, cutting them out of arm J verbatim so the two arms
#    cannot drift apart on the judgement lines.
marker = "// The knife under test: after the traveller's own accept"
if r52.count(marker) != 1:
    sys.exit(f"ABORT map-marker count={r52.count(marker)}")
map_section = r52.split(marker, 1)[1].rsplit("await ctx.close();", 1)[0]
map_section = marker + map_section

hand_marker = "// The knife under test is no longer the map"
if body.count(hand_marker) != 1:
    sys.exit(f"ABORT hand-marker count={body.count(hand_marker)}")
head, _sep, hand_tail = body.partition(hand_marker)
hand_only = hand_tail.rsplit("note(`ERRORS ", 1)[0]
tail = hand_marker + hand_only + map_section + "await ctx.close();\n"

target = ROOT / "_go_active_r55.mjs"
target.write_text(head + tail, encoding="utf-8", newline="\n")
print(f"WROTE {target.name} bytes={target.stat().st_size}")
print("HAS_MAP_READS", "MAP_READS_EVERY" in target.read_text(encoding="utf-8"))
print("HAS_HAND", "rev-plan-open-place-explore" in target.read_text(encoding="utf-8"))
print("HAS_FALLBACK", "start-fallback" in target.read_text(encoding="utf-8"))
