/**
 * 快钉工 (session 332ffba9) -- the commander's named ask from 号令者放行点名:
 * walk the inbox workbench screen for real, with the fact row whose value is an object that
 * carries no name, no location and no title, and hand back (a) one reading per language and
 * (b) the measured reachability verdict for the action on that screen.
 *
 * The string under test is the one this lane routed through the dictionary in
 * `review/快钉工-0557-r3` (row `frontend/src/features/recovery/../../features/inbox/JourneyInboxWorkbench.tsx:283`
 * -> `t("inbox.recorded")`).  Everything here reads rendered text, never a data attribute.
 *
 * Supply, stated up front so nobody mistakes this for a release number: own backend process,
 * own throwaway sqlite file whose name carries this run's id, own frontend port, structured-JSON
 * import through the product's own aside -- no mocked routes, no SQL, no shared demo database.
 */
import { expect, test, type Page } from "@playwright/test";
import { writeFileSync } from "node:fs";
import { evidencePath } from "./_qoderEvidence";
import { createFreshJourney } from "./_qoderFreshJourney";

const FILE = "e2e/qoder-332ffba9-inbox-unnamed-fact-screen-walk-r1.spec.ts";
const node = (id: string, detail: string) => `${FILE} :: ${id} — ${detail}`;
const RUN_ID = process.env.CITYNEXUS_E2E_RUN_ID ?? "unset";
const REF = `KD332FFBA9-${Math.floor(Math.random() * 1e6).toString().padStart(6, "0")}`;

test.use({ viewport: { width: 390, height: 844 }, hasTouch: true });

type RowReading = { label: string; value: string };

async function openBookings(page: Page, journeyId: string, locale: "zh-CN" | "en") {
  /* page.evaluate before the first navigation runs on about:blank, where localStorage throws. */
  await page.addInitScript((id) => {
    localStorage.setItem("citynexus.v8.journey_id", id);
    localStorage.setItem("citynexus.demo.journey_id", id);
  }, journeyId);
  await page.addInitScript((value) => {
    localStorage.setItem("citynexus.locale", value);
  }, locale);
  await page.goto("/v8/bookings", { waitUntil: "load" });
  await expect(page.getByTestId("bookings-advanced")).toBeVisible({ timeout: 30_000 });
}

async function importUnnamedOrigin(page: Page) {
  await page.getByTestId("bookings-advanced").locator("summary").click();
  await page
    .getByTestId("bookings-json-input")
    .fill(
      JSON.stringify({
        reservation_type: "RAIL",
        title: "天津西 → 北京南 高铁",
        confirmation_ref: REF,
        /* An object with none of name / location / title: the exact shape that has to fall
           through renderFact's object arm to the dictionary word. */
        origin: { gate: "A3", coach: "05" },
      }),
    );
  await page.locator('button.v8-primary:not([disabled])').last().click();
  /* The aside only creates the server's draft; the fact rows live on the review panel that this
     same mount has to open from the queue -- that indirection is what ORD-0146 was about. */
  await expect(page.getByTestId("inbox-pending-row").first()).toBeVisible({ timeout: 20_000 });
  await page.getByTestId("inbox-open-review").first().click();
  await expect(page.getByTestId("v10-inbox-draft")).toBeVisible({ timeout: 20_000 });
}

async function everyMessage(page: Page) {
  return page.$$eval(".v8-message", (nodes) =>
    nodes.map((n) => ({
      text: (n.textContent ?? "").trim().replace(/\s+/g, " ").slice(0, 120),
      host: n.closest("[data-testid]")?.getAttribute("data-testid") ?? n.parentElement?.className ?? "",
    })),
  );
}

async function draftRows(page: Page): Promise<RowReading[]> {
  return page.$$eval('[data-testid="v10-inbox-draft"] dl > div', (nodes) =>
    nodes.map((n) => {
      const dt = n.querySelector("dt");
      const dd = n.querySelector("dd");
      return {
        label: (dt?.textContent ?? "").trim(),
        value: (dd?.textContent ?? "").trim(),
      };
    }),
  );
}

/** A button the traveller can actually press: rendered box, in view, centre hit lands on it. */
async function pressProbe(page: Page, testid: string) {
  return page.evaluate((id) => {
    const el = document.querySelector<HTMLElement>(`[data-testid="${id}"]`);
    if (!el) return { present: false };
    el.scrollIntoView({ block: "center", inline: "nearest" });
    const r = el.getBoundingClientRect();
    const box = { x: Math.round(r.x), y: Math.round(r.y), width: Math.round(r.width), height: Math.round(r.height) };
    const inViewport = r.width > 0 && r.height > 0 && r.top >= 0 && r.bottom <= window.innerHeight;
    const cx = Math.round(r.x + r.width / 2);
    const cy = Math.round(r.y + r.height / 2);
    const hit = document.elementFromPoint(cx, cy);
    const hitOwns = !!hit && (hit === el || el.contains(hit) || hit.contains(el));
    const style = getComputedStyle(el);
    return {
      present: true,
      label: (el.textContent ?? "").trim().replace(/\s+/g, " ").slice(0, 40),
      box,
      inViewport,
      centreHit: hit ? `${hit.tagName.toLowerCase()}${(hit.getAttribute("data-testid") || "").replace(/^/, "#")}` : "none",
      hitOwns,
      disabled: (el as HTMLButtonElement).disabled === true || el.getAttribute("aria-disabled") === "true",
      visibility: style.visibility,
      display: style.display,
    };
  }, testid);
}

async function pressableControls(page: Page): Promise<string[]> {
  return page.evaluate(() =>
    Array.from(document.querySelectorAll<HTMLElement>("button, [role=button], summary, a.v8-primary"))
      .filter((el) => {
        const r = el.getBoundingClientRect();
        const s = getComputedStyle(el);
        return r.width > 0 && r.height > 0 && s.visibility !== "hidden" && s.display !== "none";
      })
      .map((el) => (el.textContent ?? "").trim().replace(/\s+/g, " ").slice(0, 30))
      .filter((t) => t.length > 0),
  );
}

test("kuaidinggong-inbox-unnamed-fact-screen-walk — 无名事实那行两语都念字典里的词，确认动作的可达性实测出来", async ({ page, request }) => {
  test.setTimeout(300_000);
  const NODE = "kuaidinggong-inbox-unnamed-fact-screen-walk";
  const seeded = await createFreshJourney(request, { select: false });
  const out: Record<string, unknown> = {
    node: NODE,
    run_id: RUN_ID,
    journey_id: seeded.journeyId,
    reference: REF,
    supply: "own backend + own throwaway sqlite (name carries run id) + own frontend port; structured JSON through the product aside; no mocked route",
  };

  await openBookings(page, seeded.journeyId, "zh-CN");
  await importUnnamedOrigin(page);

  const zhRows = await draftRows(page);
  out.zh_rows = zhRows;
  const zhUnnamed = zhRows.filter((r) => r.value === "已记录");
  expect(
    zhUnnamed.length,
    node(NODE, `the Chinese screen printed ${JSON.stringify(zhRows)} — no row reads 已记录, so the dictionary word is not what the object-without-name arm renders`),
  ).toBeGreaterThan(0);

  out.zh_messages = await everyMessage(page);
  const zhConfirm = await pressProbe(page, "v13-2-confirm");
  out.zh_confirm = zhConfirm;
  out.zh_pressable = await pressableControls(page);
  await page.screenshot({ path: evidencePath("kuaidinggong-inbox-unnamed-origin-zh.png"), fullPage: true });

  /* Same mount, same draft, only the language flips -- the panel renders the draft this mount
     created, so reloading would measure an empty page instead. */
  await page.getByTestId("topbar-language").click();
  await page.waitForTimeout(600);

  const enRows = await draftRows(page);
  out.en_rows = enRows;
  const enUnnamed = enRows.filter((r) => r.value === "Recorded");
  expect(
    enUnnamed.length,
    node(NODE, `after switching language the screen printed ${JSON.stringify(enRows)} — no row reads Recorded`),
  ).toBeGreaterThan(0);

  out.en_messages = await everyMessage(page);
  const enConfirm = await pressProbe(page, "v13-2-confirm");
  out.en_confirm = enConfirm;
  out.en_pressable = await pressableControls(page);
  await page.screenshot({ path: evidencePath("kuaidinggong-inbox-unnamed-origin-en.png"), fullPage: true });

  /* Why the action is or is not pressable, in the server's own words rather than the front end's. */
  const inbox = await (await request.get(`/api/v1/journeys/${seeded.journeyId}/inbox`)).json();
  const mine = (inbox.drafts ?? []).find((d: any) => String(d.extracted?.confirmation_ref ?? "") === REF) ?? null;
  out.server_draft = { status: mine?.status ?? null, unresolved_fields: mine?.unresolved_fields ?? null, origin: mine?.extracted?.origin ?? null };
  out.confirm_enabled_verdict = {
    zh_disabled: (zhConfirm as any).disabled === true,
    en_disabled: (enConfirm as any).disabled === true,
    reason_from_server_unresolved: (mine?.unresolved_fields ?? []).length,
  };

  /* Arm B: fill what THIS screen actually offers, then ask again whether the action is pressable.
     Reporting "disabled" without trying the correction path would leave the wrong conclusion down. */
  const stamps = page.locator('[data-testid="v10-inbox-draft"] input[type="datetime-local"]');
  out.correction_inputs_found = await stamps.count();
  if ((await stamps.count()) >= 2) {
    await stamps.nth(0).fill("2026-10-09T18:00");
    await stamps.nth(1).fill("2026-10-09T20:40");
    await page.getByTestId("v13-2-save-corrections").click();
    await page.waitForTimeout(2_500);
    const afterInbox = await (await request.get(`/api/v1/journeys/${seeded.journeyId}/inbox`)).json();
    const afterMine = (afterInbox.drafts ?? []).find((d: any) => String(d.extracted?.confirmation_ref ?? "") === REF) ?? null;
    out.after_correction_server = {
      status: afterMine?.status ?? null,
      unresolved_fields: afterMine?.unresolved_fields ?? null,
    };
    out.after_correction_confirm = await pressProbe(page, "v13-2-confirm");
    out.after_correction_messages = await everyMessage(page);
  }

  /* Arm C: the screen's own control inventory, plus a real attempt at the one remaining field this
     panel does offer (the anchor role), so "this screen cannot finish the review" is measured. */
  out.panel_controls = await page.evaluate(() => {
    const panel = document.querySelector('[data-testid="v10-inbox-draft"]');
    if (!panel) return [];
    return Array.from(panel.querySelectorAll("input, select, button, [role=combobox], summary")).map((el) => {
      const label = (el.closest("label")?.textContent ?? el.getAttribute("aria-label") ?? "").trim().replace(/\s+/g, " ").slice(0, 24);
      return {
        tag: el.tagName.toLowerCase(),
        type: (el as HTMLInputElement).type ?? null,
        testid: el.getAttribute("data-testid") ?? null,
        label,
        value: ((el as HTMLInputElement).value ?? "").slice(0, 20),
      };
    });
  });
  out.destination_inputs_on_this_panel = await page
    .locator('[data-testid="v10-inbox-draft"] input')
    .evaluateAll((nodes) => nodes.filter((n) => /到达|destination|to/i.test(n.name + " " + (n.getAttribute("aria-label") ?? "") + " " + (n.placeholder ?? ""))).length);
  out.anchor_role_control = await page.getByTestId("v13-2-anchor-role").count();

  /* Arm D: the row has to be *rendered*, not merely present in the DOM -- measure its own box, and
     take an element screenshot so a human can read the same line I am quoting. */
  out.row_boxes = await page.$$eval('[data-testid="v10-inbox-draft"] dl > div', (nodes) =>
    nodes.map((n) => {
      const dd = n.querySelector("dd");
      if (!dd) return null;
      const r = dd.getBoundingClientRect();
      return {
        text: (dd.textContent ?? "").trim().slice(0, 16),
        width: Math.round(r.width),
        height: Math.round(r.height),
        inViewport: r.top >= 0 && r.bottom <= window.innerHeight,
      };
    }).filter(Boolean),
  );
  await page.getByTestId("v10-inbox-draft").screenshot({ path: evidencePath("panel-after-language-flip.png") });

  writeFileSync(
    evidencePath("kuaidinggong-inbox-unnamed-origin-readout.json"),
    JSON.stringify(out, null, 2) + "\n",
    "utf-8",
  );
  const lines = Object.entries(out).map(([k, v]) => `${k} ${JSON.stringify(v)}`);
  writeFileSync(evidencePath("kuaidinggong-inbox-unnamed-origin-readout.txt"), lines.join("\n") + "\n", "utf-8");

  expect(
    (enConfirm as any).present && (zhConfirm as any).present,
    node(NODE, `the confirm control was not found on the draft panel in one of the two languages: zh ${JSON.stringify(zhConfirm)} en ${JSON.stringify(enConfirm)}`),
  ).toBe(true);
});
