import pathlib
import sys

ROOT = pathlib.Path(r"D:/moodle/_cmdr_rescue_v3_1022/trial/human_walk")
text = (ROOT / "_go_active_r55.mjs").read_text(encoding="utf-8")

recorder_old = """  note(`HTTP ${method} ${resp.status()} ${url.replace(/^http:\\/\\/[^/]+/, "")}`);"""
recorder_new = """  const line = `HTTP ${method} ${resp.status()} ${url.replace(/^http:\\/\\/[^/]+/, "")}`;
  if (resp.status() >= 400) {
    let detail = "";
    try { detail = JSON.stringify(await resp.json()).slice(0, 500); } catch { detail = "(unreadable body)"; }
    note(line + " BODY " + detail);
  } else {
    note(line);
  }"""
if text.count(recorder_old) != 1:
    sys.exit(f"ABORT recorder-anchor count={text.count(recorder_old)}")
text = text.replace(recorder_old, recorder_new)

save_old = """      if (await press(saveButton, `save-${round}-${i}`, 30000)) { await page.waitForTimeout(6000); continue; }"""
save_new = """      if (await press(saveButton, `save-${round}-${i}`, 30000)) {
        await page.waitForTimeout(6000);
        // Arm M pressed 保存为正式候选方案 seven times and never once wrote down what the card said
        // back, so the refusal names lived only on the screen.  Read them every press.
        const saved = await page.locator(".rev-plan-message, [role='alert']").allInnerTexts().catch(() => []);
        note(`SAVE_ALERT ${round}/${i} ${JSON.stringify(saved.slice(0, 3))}`);
        continue;
      }"""
if text.count(save_old) != 1:
    sys.exit(f"ABORT save-anchor count={text.count(save_old)}")
text = text.replace(save_old, save_new)

out_old = "const OUT = `${DIR}/go-active-${TAG}-r55.txt`;"
out_new = "const OUT = `${DIR}/go-active-${TAG}-r57.txt`;"
if text.count(out_old) != 1:
    sys.exit(f"ABORT out-anchor count={text.count(out_old)}")
text = text.replace(out_old, out_new)

target = ROOT / "_go_active_r57.mjs"
target.write_text(text, encoding="utf-8", newline="\n")
print("WROTE", target.name, target.stat().st_size)
