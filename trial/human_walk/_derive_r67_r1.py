import pathlib
import sys

ROOT = pathlib.Path(r"D:/moodle/_cmdr_rescue_v3_1022/trial/human_walk")
text = (ROOT / "_s_arm_r66.mjs").read_text(encoding="utf-8")

anchor = "            note(`ASK_REFUSAL_SENT ${round} t=${elapsed()}`);"
if text.count(anchor) != 1:
    sys.exit(f"ABORT anchor count={text.count(anchor)}")

# The card says which side to move; the walk has to actually move it, otherwise the same
# INSUFFICIENT_TRAVEL_GAP comes back for the rest of the run and nothing is proven about recovery.
repair = anchor + '''
            // The sentence offers two exits; take the one it lists second — pull the earlier stop's end
            // time forward by fifteen minutes on every band — then let the loop re-save, re-freeze and re-select.
            const movedBack = await timeInputs.evaluateAll((nodes) => {
              const touched = [];
              for (const node of nodes) {
                const label = node.getAttribute("aria-label") || "";
                if (!/结束时间/.test(label)) continue;
                const parts = node.value.split(":").map((part) => Number(part));
                const minutes = Math.max(0, parts[0] * 60 + parts[1] - 15);
                const next = `${String(Math.floor(minutes / 60)).padStart(2, "0")}:${String(minutes % 60).padStart(2, "0")}`;
                if (next === node.value) continue;
                touched.push(`${label} ${node.value}->${next}`);
                const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
                setter.call(node, next);
                node.dispatchEvent(new Event("input", { bubbles: true }));
              }
              return touched;
            });
            note(`GAP_REPAIR ${round} ${JSON.stringify(movedBack).slice(0, 320)} t=${elapsed()}`);
            await page.waitForTimeout(1500);'''
text = text.replace(anchor, repair)

old = "drift-check-${TAG}-r66.txt"
if text.count(old) != 1:
    sys.exit(f"ABORT out count={text.count(old)}")
text = text.replace(old, "drift-check-${TAG}-r67.txt")

target = ROOT / "_t_arm_r67.mjs"
target.write_text(text, encoding="utf-8", newline="\n")
print("WROTE", target.name, target.stat().st_size)
