"""Derive the X arm from the W arm: keep everything up to the place-hand press, then append the
explore-screen tail that has to finish the chain the hand promises.

The cut is asserted, not assumed -- the derived head must still contain the hand press it replaces
the tail of, and the tail must be the file I just wrote.  Nothing here edits the W arm.
"""
import pathlib
import re

ROOT = pathlib.Path(r"D:/moodle/_cmdr_rescue_v3_1022/trial/human_walk")
head_src = (ROOT / "_w_arm_r70.mjs").read_text(encoding="utf-8").splitlines(keepends=True)
tail = (ROOT / "_x_tail_r73.frag.mjs").read_text(encoding="utf-8")

anchor = None
for index, line in enumerate(head_src):
    if "AFTER_HAND_HAS_EXPLORE" in line:
        anchor = index
        break
if anchor is None:
    raise SystemExit("ABORT: the hand-press anchor is not in the W arm")

cut = None
for index in range(anchor, min(anchor + 6, len(head_src))):
    if head_src[index].strip() == "}":
        cut = index
        break
if cut is None:
    raise SystemExit("ABORT: could not find the block that closes the hand press")

head = "".join(head_src[: cut + 1])
for must in ("rev-plan-open-place-explore", "HAND_PRESSED", "PLAN_GAPS_ALL"):
    if must not in head:
        raise SystemExit("ABORT: head lost " + must)

head = head.replace("drift-check-${TAG}-r70.txt", "x-full-chain-${TAG}-r73.txt")
head = head.replace("_chrome_gozero_map46", "_chrome_gozero_x73")
if "x-full-chain" not in head or "_chrome_gozero_x73" not in head:
    raise SystemExit("ABORT: the output or profile swap did not land")

# The W arm's own trailing map block is gone, so the derived file must not still close the context
# before my tail does.
if head.count("await ctx.close();") != 0:
    raise SystemExit("ABORT: head still closes the context")

out = ROOT / "_x_arm_r73.mjs"
out.write_text(head + "\n" + tail, encoding="utf-8", newline="\n")
print("DERIVED", out.name, "head_lines", len(head.splitlines()), "total_bytes", out.stat().st_size)
print("CLOSES", len(re.findall(r"await ctx\.close\(\);", out.read_text(encoding='utf-8'))))
