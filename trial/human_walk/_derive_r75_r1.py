"""Derive the Y arm: the same traveller walk, but against the clean worktree stack on :14462.

Only three things change -- the base URL, the browser profile and the receipt name -- and each swap
is asserted, so a silent no-op cannot be reported as a second generation walked.
"""
import pathlib

ROOT = pathlib.Path(r"D:/moodle/_cmdr_rescue_v3_1022/trial/human_walk")
src = (ROOT / "_x_arm_r73.mjs").read_text(encoding="utf-8")
out = ROOT / "_y_arm_clean_r75.mjs"

swaps = [
    ('const BASE = "http://127.0.0.1:14461"', 'const BASE = "http://127.0.0.1:14462"'),
    ('_chrome_gozero_x73', '_chrome_gozero_y75'),
    ('x-full-chain-${TAG}-r73.txt', 'clean-chain-${TAG}-r75.txt'),
]
text = src
for old, new in swaps:
    if old not in text:
        raise SystemExit("ABORT: anchor missing -> " + old)
    text = text.replace(old, new)
if text.count("14462") != 1 or "14461" in text:
    raise SystemExit("ABORT: the base swap is not the single one I meant")
out.write_text(text, encoding="utf-8", newline="\n")
print("DERIVED", out.name, "bytes", out.stat().st_size, "base_14462", text.count("14462"))
