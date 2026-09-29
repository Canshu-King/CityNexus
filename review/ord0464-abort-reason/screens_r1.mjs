/* ORD-0464 · the four cells of a screen acceptance, read off the rendered page.
 * Three journeys, three states, one browser. Nothing is stubbed: each journey is created and binned
 * through the product's own doors, then the hub is opened and the panel's rendered text is read.
 */
import { chromium } from "playwright";

const BASE = "http://127.0.0.1:4192";
const API = "http://127.0.0.1:8713";
const WINDOW = { start: "2027-07-01T02:00:00+00:00", end: "2027-07-03T10:00:00+00:00" };

async function json(path, init) {
  const r = await fetch(`${API}/api/v1${path}`, {
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    ...init,
  });
  const text = await r.text();
  if (!r.ok && r.status !== 204) throw new Error(`${path} -> ${r.status} ${text.slice(0, 200)}`);
  return text ? JSON.parse(text) : null;
}

async function makeJourney(tag) {
  const traveler = await json("/travelers", {
    method: "POST",
    body: JSON.stringify({ display_name: `ORD-0464 screen ${tag}`, locale: "zh-CN", timezone: "Asia/Shanghai" }),
  });
  const journey = await json("/journeys", {
    method: "POST",
    body: JSON.stringify({
      traveler_id: traveler.id,
      title: `ORD-0464 screen ${tag}`,
      city_code: "CNX-DEMO",
      timezone: "Asia/Shanghai",
      start_at: WINDOW.start,
      end_at: WINDOW.end,
      budget: { currency: "CNY", amount_minor: 500000 },
      planning_mode: "balanced",
    }),
  });
  return String(journey.id);
}

const out = { base: BASE, runs: [] };
const browser = await chromium.launch();

async function read(jid, tag, bin) {
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, locale: "zh-CN" });
  const page = await ctx.newPage();
  await page.addInitScript((id) => {
    localStorage.clear();
    localStorage.setItem("citynexus.v8.journey_id", id);
    localStorage.setItem("citynexus.locale", "zh-CN");
  }, jid);
  await page.goto(`${BASE}/v8/hub`, { waitUntil: "load" });
  const panel = page.getByTestId("journey-abort");
  await panel.waitFor({ state: "visible", timeout: 30_000 });
  const trim = (v) => String(v ?? "").replace(/\s+/g, " ").trim();
  const opener = panel.getByTestId("abort-open");
  const doneHandle = panel.getByTestId("abort-done");
  /* A trip that is already binned shows no trigger at all, so asking its trigger for text would hang
     until timeout -- which is what the first run of this instrument did on the third arm. Count first,
     then wait for whichever cell the panel is entitled to show. */
  /* The panel mounts in a reading state and answers with either the trigger or the recorded cell, so
     wait for one of the two instead of counting immediately -- the first run counted while the read
     was still in flight and then waited forever for a cell that had not been chosen yet. */
  await panel.locator('[data-testid="abort-open"],[data-testid="abort-done"]').first()
    .waitFor({ state: "visible", timeout: 25_000 });
  const hasOpener = (await opener.count()) > 0;
  const before = { trigger: hasOpener ? trim(await opener.textContent()) : null, boxes: 0, labels: [] };
  if (hasOpener) {
    await panel.getByTestId("abort-open").click();
    before.boxes = await panel.getByTestId("abort-code").count();
    before.labels = await panel.locator(".cn-abort-code label span").evaluateAll((ns) =>
      ns.map((n) => String(n.textContent ?? "").replace(/\s+/g, " ").trim()),
    );
    before.question = (await panel.getByTestId("abort-question").textContent())?.replace(/\s+/g, " ").trim();
    before.help = (await panel.getByTestId("abort-help").textContent())?.replace(/\s+/g, " ").trim();
    before.confirm = (await panel.getByTestId("abort-confirm").textContent())?.replace(/\s+/g, " ").trim();
    before.confirmDisabled = await panel.getByTestId("abort-confirm").isDisabled();
    before.skip = (await panel.getByTestId("abort-skip").textContent())?.replace(/\s+/g, " ").trim();
    before.noteMaxLength = await panel.getByTestId("abort-note").getAttribute("maxlength");
  }
  if (bin) await bin(page, panel);
  const done = doneHandle;
  let after = null;
  if (await done.count()) {
    after = {
      state: await done.getAttribute("data-cnx-state"),
      text: (await done.textContent())?.replace(/\s+/g, " ").trim(),
    };
  }
  const server = await json(`/journeys/${jid}/outcomes`);
  const events = (server.events ?? []).filter((e) => e.event_type === "JOURNEY_DELETED");
  await page.screenshot({ path: `D:/moodle/_qoder_q_ord0369_wk/o0464_${tag}.png` });
  out.runs.push({ tag, journey_id: jid, on_screen_before: before, on_screen_after: after, server_rows: events });
  await ctx.close();
}

await read(await makeJourney("declared"), "declared", async (page, panel) => {
  await panel.locator('[data-cnx-code="BUDGET_DOES_NOT_FIT"]').check();
  await panel.locator('[data-cnx-code="PROTECTED_ITEM_DROPPED"]').check();
  await panel.getByTestId("abort-note").fill("住的那一晚超出了预算");
  await panel.getByTestId("abort-confirm").click();
  await panel.getByTestId("abort-done").waitFor({ timeout: 20_000 });
});

await read(await makeJourney("skipped"), "skipped", async (page, panel) => {
  await panel.getByTestId("abort-skip").click();
  await panel.getByTestId("abort-done").waitFor({ timeout: 20_000 });
});

/* The third state is produced the way the product produces it today: a client that deletes with no
   body at all -- which is every client on this tree before ORD-0464 -- and then a traveller opens the
   trip. Nothing is stubbed and no row is edited. */
const silentJid = await makeJourney("silent");
await json(`/journeys/${silentJid}`, { method: "DELETE" });
await read(silentJid, "silent", null);

await browser.close();
console.log(JSON.stringify(out, null, 1));
