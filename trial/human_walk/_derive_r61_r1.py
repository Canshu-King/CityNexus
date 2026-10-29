import pathlib
import sys

ROOT = pathlib.Path(r"D:/moodle/_cmdr_rescue_v3_1022/trial/human_walk")
text = (ROOT / "_go_active_r57.mjs").read_text(encoding="utf-8")

anchor = "let startedJourney = false;"
if text.count(anchor) != 1:
    sys.exit(f"ABORT anchor count={text.count(anchor)}")

drift = '''// The last open box on the first knife: a traveller who moves exactly one half-day band must see the
// other bands stay where they were.  Only the last time input is touched, then the real 保存 is pressed.
const openFold = page.locator("text=编辑行程时间（可选）").first();
if (await visible(openFold)) { await openFold.click().catch(() => {}); await page.waitForTimeout(1500); }
const timeInputs = page.locator('input[type="time"]');
const readTimes = () => timeInputs.evaluateAll((nodes) => nodes.map((node) => ({
  label: node.getAttribute("aria-label") || "", value: node.value,
})));
const before = await readTimes();
note(`DRIFT_FOLD ${await visible(openFold)} TIME_COUNT ${before.length} BEFORE ${JSON.stringify(before).slice(0, 900)} t=${elapsed()}`);
if (before.length > 1) {
  const lastIndex = before.length - 1;
  const lastLabel = before[lastIndex].label;
  const current = before[lastIndex].value;
  const [hh, mm] = current.split(":").map((part) => Number(part));
  const total = hh * 60 + mm + 30;
  const next = `${String(Math.floor(total / 60) % 24).padStart(2, "0")}:${String(total % 60).padStart(2, "0")}`;
  await timeInputs.nth(lastIndex).fill(next);
  note(`TIME_EDITED ${JSON.stringify(lastLabel)} ${current} -> ${next} t=${elapsed()}`);
  if (await press(saveButton, "save-drift", 30000)) {
    await page.waitForTimeout(7000);
    const alerted = await page.locator(".rev-plan-message, [role='alert'], [role='status']").allInnerTexts().catch(() => []);
    note(`DRIFT_SAVE_ALERT ${JSON.stringify(alerted.slice(0, 3))}`);
    const after = await readTimes();
    const changed = after.filter((row) => {
      const prior = before.find((item) => item.label === row.label);
      return prior ? row.value !== prior.value : true;
    }).map((row) => row.label);
    const lost = before.filter((row) => !after.some((item) => item.label === row.label)).map((row) => row.label);
    note(`TIME_AFTER ${JSON.stringify(after).slice(0, 900)} t=${elapsed()}`);
    note(`DRIFT_CHANGED_ONLY ${JSON.stringify(changed)} COUNT ${before.length}->${after.length} LOST ${JSON.stringify(lost)}`);
    const movedOthers = changed.filter((label) => label !== lastLabel);
    note(`DRIFT_COUNT ${movedOthers.length} TARGET_ONLY ${changed.length === 1 ? "yes" : "no"} t=${elapsed()}`);
    await shot(`${TAG}-drift-after`);
  } else {
    note("DRIFT_SAVE_NOT_PRESSED");
  }
} else {
  note("DRIFT_NO_TIME_INPUTS -- the fold never opened or the draft has no timed bands");
}

'''
text = text.replace(anchor, drift + anchor)

out_old = "const OUT = `${DIR}/go-active-${TAG}-r57.txt`;"
out_new = "const OUT = `${DIR}/drift-check-${TAG}-r61.txt`;"
if text.count(out_old) != 1:
    sys.exit(f"ABORT out-anchor count={text.count(out_old)}")
text = text.replace(out_old, out_new)

target = ROOT / "_drift_check_r61.mjs"
target.write_text(text, encoding="utf-8", newline="\n")
print("WROTE", target.name, target.stat().st_size)
