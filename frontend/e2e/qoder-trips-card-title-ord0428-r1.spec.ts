/**
 * ORD-0428 (lane 票夹卡片标题) — a saved trip fact may not be titled with the server's own internal
 * marker, nor with a reference number standing in for a place name.
 *
 * Measured on the base generation (`bdee2fc3…`), phone 390x844, zh-CN and en, against this lane's own
 * sqlite and its own journey:
 *   - `journey_memory_payload` (`backend/app/integrations/inbox/semantic_intake.py`) writes `title` as
 *     one of four words the server uses for ITSELF — "Arrive" / "Depart" / "Journey commitment" /
 *     "Travel fact" — and the row painted that word as its name on a Chinese screen.
 *   - the same payload fills `label` from a place name, else `confirmation_ref`, else the reservation's
 *     type code.  With a berth instead of a name the row read `NOPLACE716` where a station belongs.
 *   - `location or confirmation_ref or reservation_type` cannot be told apart by looking at the string,
 *     so the payload now states which branch it took (`label_kind`) and the row reads that.
 *
 * Two nodes, because the order asks for two different proofs:
 *   N1 the live server's rows: a place name paints a name, a reference number paints the gap it is,
 *      and no internal marker word reaches the painted title of any card on the trips screen;
 *   N2 the two branches the live import door cannot reach (`RESERVATION_TYPE`, and a payload that
 *      states no branch at all) through a stubbed response — the row must still name the gap and must
 *      not shorten or echo a machine value.
 *
 * The "did not disappear" half is read from the row's own technical fold, the same channel ORD-0517
 * established for `semantic_key` on the wallet card: below the name, never as it.
 */
import { expect, test, type Page } from "@playwright/test";
import { writeFileSync } from "node:fs";

import { evidencePath } from "./_qoderEvidence";
import { scanScreenText } from "./_qoderTextScan";

const FILE = "e2e/qoder-trips-card-title-ord0428-r1.spec.ts";
const node = (id: string, detail: string) => `${FILE} :: ${id} — ${detail}`;
const RUN = process.env.CITYNEXUS_E2E_RUN_ID ?? "dev";

const clean = (value: string | null | undefined) =>
  String(value ?? "").replace(/\s+/g, " ").trim();

/* The four words `semantic_intake.py` uses for its own anchor nodes, plus the panel's own title. */
const INTERNAL_MARKER_WORDS = ["Arrive", "Depart", "Journey commitment", "Travel fact"];
const SCREAMING = /\b[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+\b/g;
const UUID = /\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b/g;

/** This lane's own journey, with two confirmed reservations and one open draft behind it. */
async function seedOwnFacts(page: Page, stamp: string) {
  const traveler = await (
    await page.request.post("/api/v1/travelers", {
      data: { display_name: "ORD-0428 lane", locale: "zh-CN", timezone: "Asia/Shanghai" },
    })
  ).json();
  const journey = await (
    await page.request.post("/api/v1/journeys", {
      data: {
        traveler_id: traveler.id,
        title: "天津周末",
        city_code: "CN-TIANJIN",
        timezone: "Asia/Shanghai",
        start_at: "2026-10-09T18:00:00+08:00",
        end_at: "2026-10-11T15:00:00+08:00",
        budget: { amount_minor: 120000, currency: "CNY" },
        stay_budget: { amount_minor: 70000, currency: "CNY" },
        party_size: 2,
        occupancy: { adults: 2, rooms: 1 },
        arrival_anchor: { at: "2026-10-09T18:00:00+08:00", location: "Tianjin West Station" },
        departure_anchor: { at: "2026-10-11T15:00:00+08:00", location: "Tianjin Binhai Airport" },
      },
    })
  ).json();
  const journeyId = String(journey.id);

  const cases = [
    {
      reservation_type: "RAIL",
      confirmation_ref: `NAMED${stamp}`,
      origin: { name: "天津西站" },
      destination: { name: "北京南站" },
      scheduled_departure_at: "2026-10-09T18:40:00+08:00",
      scheduled_arrival_at: "2026-10-09T19:32:00+08:00",
      amount_minor: 5480,
      currency: "CNY",
    },
    {
      /* A berth, not a name: the server has a reference and a type, and no place to show. */
      reservation_type: "COACH",
      confirmation_ref: `NOPLACE${stamp}`,
      origin: { address: "天津长途客运站" },
      destination: { terminal: "唐山客运中心" },
      scheduled_departure_at: "2026-10-10T13:00:00+08:00",
      scheduled_arrival_at: "2026-10-10T15:20:00+08:00",
    },
  ];

  for (const reservation of cases) {
    const created = await (
      await page.request.post(`/api/v1/journeys/${journeyId}/inbox/import`, {
        data: { artifact_type: "STRUCTURED_JSON", payload: { reservation } },
      })
    ).json();
    const draft = created.draft ?? created;
    if ((draft.unresolved_fields ?? []).length === 0) {
      await page.request.post(
        `/api/v1/journeys/${journeyId}/inbox/${draft.id}/confirm`,
        { data: {} },
      );
    } else {
      throw new Error(
        node("seed", `the ${reservation.reservation_type} import stayed unresolved: ${JSON.stringify(draft.unresolved_fields)}`),
      );
    }
  }

  /* A plan behind the journey, so the other three trips tabs have real cards to measure too. */
  await page.request.post(`/api/v1/journeys/${journeyId}/stay-options/generate`);
  const listed = await (
    await page.request.get(`/api/v1/journeys/${journeyId}/stay-options`)
  ).json();
  const options = listed.options ?? [];
  if (options.length === 0) throw new Error(node("seed", "the stay-aware optimiser returned no options"));
  const chosen = options.find((item: any) => item.status === "RECOMMENDED") ?? options[0];
  await page.request.post(`/api/v1/journeys/${journeyId}/stay-options/${chosen.id}/select`);

  const memory = await (
    await page.request.get(`/api/v1/journeys/${journeyId}/memory`)
  ).json();
  return { journeyId, memory: memory.items ?? [], kinds: (memory.items ?? []).map((item: any) => item.label_kind) };
}

async function openTrips(page: Page, journeyId: string, locale: string) {
  await page.addInitScript(
    ({ id, loc }) => {
      localStorage.clear();
      localStorage.setItem("citynexus.v8.journey_id", id);
      localStorage.setItem("citynexus.locale", loc);
    },
    { id: journeyId, loc: locale },
  );
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/v8/trips", { waitUntil: "load" });
  await expect(
    page.getByTestId("trips-tab-bookings"),
    node("boot", "the trips screen never painted its section tabs"),
  ).toBeVisible({ timeout: 30_000 });
}

/** The painted text of each saved-fact row's name slot.
 *  The row handle is the panel's own row element and its `<strong>`, both of which exist on the base
 *  generation too: a gate whose red comes from a locator this lane introduced proves the locator, not
 *  the title, so the title node must be able to read the old screen as well as the new one. */
async function readRowNames(page: Page, expected: number, nodeId: string) {
  await page.getByTestId("trips-tab-bookings").click();
  const rows = page.locator(".v13-2-memory-panel li");
  await expect(
    rows,
    node(nodeId, `the saved-fact list never reached ${expected} row(s), so nothing was measured`),
  ).toHaveCount(expected, { timeout: 30_000 });
  const count = await rows.count();
  const names: string[] = [];
  for (let index = 0; index < count; index += 1) {
    const row = rows.nth(index);
    await row.scrollIntoViewIfNeeded({ timeout: 5_000 }).catch(() => null);
    /* Read as painted text, not as a `data-*` mirror of it. */
    names.push(clean(await row.locator("strong").first().innerText()));
  }
  return { count, names };
}

test.describe("ORD-0428 the saved trip facts are named by a name", () => {
  for (const arm of [
    { code: "zh", locale: "zh-CN", named: "北京南站", gap: "服务器只给了这条行程事实的确认号，没有给地点名字" },
    { code: "en", locale: "en", named: "北京南站", gap: "The server gave a reference number for this trip fact, not a place name" },
  ]) {
    test(`ord0428-1-live-rows-${arm.code} — 屏上行程事实的标题必须是名字`, async ({ page }) => {
      test.setTimeout(300_000);
      const NODE = `ord0428-1-${arm.code}`;
      const stamp = String(Math.floor(Math.random() * 1e6)).padStart(6, "0");
      const seeded = await seedOwnFacts(page, stamp);
      await openTrips(page, seeded.journeyId, arm.locale);

      /* The server states which branch it took; this arm only proceeds if both branches exist, or the
         absence of a machine value below would be vacuous. */
      expect(
        seeded.kinds,
        node(NODE, `the payload carried ${JSON.stringify(seeded.kinds)}, not both branches`),
      ).toEqual(expect.arrayContaining(["PLACE_NAME", "CONFIRMATION_REF"]));

      const rows = await readRowNames(page, 2, NODE);
      const named = rows.names.find((text) => text.includes(arm.named));
      expect(
        named ?? "",
        node(NODE, `no row was titled with the place name the server wrote; rows read ${JSON.stringify(rows.names)}`),
      ).toContain(arm.named);

      const nameless = rows.names.find((text) => text.includes(arm.gap));
      expect(
        nameless ?? "",
        node(NODE, `the row with no place name did not state that gap; rows read ${JSON.stringify(rows.names)}`),
      ).toContain(arm.gap);

      /* The reference number is gone from the name slot on every row. */
      for (const text of rows.names) {
        expect(
          text,
          node(NODE, `the raw confirmation reference NOPLACE${stamp} is still wearing a name: "${text}"`),
        ).not.toContain(`NOPLACE${stamp}`);
        for (const marker of INTERNAL_MARKER_WORDS) {
          expect(
            text,
            node(NODE, `the server's internal marker "${marker}" is painted as the row's title: "${text}"`),
          ).not.toContain(marker);
        }
      }

      /* The painted layer is read BEFORE anything is opened: an unbounded "folds closed" claim made
         after clicking one open is the same kind of instrument defect the order is about. */
      const folds = page.getByTestId("v13-2-memory-technical");
      expect(
        await folds.count(),
        node(NODE, "the raw server word has nowhere on this row left to be read"),
      ).toBe(2);
      await expect(
        folds.first(),
        node(NODE, "a fold was already open, so the sweep below is not the closed-fold layer"),
      ).not.toHaveAttribute("open", "");
      const view = await scanScreenText(page);
      expect(
        view.visualLeaves,
        node(NODE, "the painted scan found no text at all, so every absence below is vacuous"),
      ).toBeGreaterThan(40);
      expect(
        [...new Set(view.visual.match(SCREAMING) ?? [])],
        node(NODE, "a SCREAMING_SNAKE token reached the painted layer while every fold was closed"),
      ).toEqual([]);
      expect(
        [...new Set(view.visual.match(UUID) ?? [])],
        node(NODE, "an identifier reached the painted layer while every fold was closed"),
      ).toEqual([]);

      /* The fold is the other half of the order: the machine value stepped out of the title, it did
         not vanish.  Measured by a traveller's click, not by a DOM flag. */
      await folds.first().locator("summary").click();
      await expect(
        folds.first(),
        node(NODE, "opening the row's technical detail painted nothing"),
      ).toContainText("Travel fact");
      await expect(folds.first()).toContainText("PLACE_NAME");

      writeFileSync(
        evidencePath(`ord0428/rows-${arm.code}.json`),
        JSON.stringify(
          {
            run: RUN,
            node: NODE,
            journey_id: seeded.journeyId,
            label_kinds: seeded.kinds,
            painted_names: rows.names,
            folds: 2,
            painted_leaves: view.visualLeaves,
          },
          null,
          2,
        ) + "\n",
        "utf-8",
      );
    });
  }

  /**
   * The live import door cannot reach every branch: confirming without a `confirmation_ref` is refused
   * with that field named in `unresolved_fields`, and a payload written before `label_kind` existed
   * states no branch at all.  This node stubs those beside `ACTIVITY_TITLE`, so every branch the row
   * can be given is judged against painted text -- the reference-number branch by the live node above.
   */
  test("ord0428-2-unreachable-branches-name-their-gap — 取不到的两支也要说清缺什么", async ({ page }) => {
    test.setTimeout(240_000);
    const NODE = "ord0428-2";
    const stamp = String(Math.floor(Math.random() * 1e6)).padStart(6, "0");
    const seeded = await seedOwnFacts(page, stamp);
    await page.addInitScript((id) => {
      localStorage.clear();
      localStorage.setItem("citynexus.v8.journey_id", id);
      localStorage.setItem("citynexus.locale", "zh-CN");
    }, seeded.journeyId);

    const items = [
      { id: `11111111-1111-4111-8111-${"a".repeat(12)}`, kind: "RESERVATION", role: "ARRIVAL", title: "Arrive", label: "天津西站", label_kind: "PLACE_NAME", at: "2026-10-09T18:40:00+08:00", status: "PROTECTED", protected: true, confidence: null, reasoning_summary: "", semantic_node_key: null },
      { id: `22222222-2222-4222-8222-${"b".repeat(12)}`, kind: "RESERVATION", role: "DEPARTURE", title: "Depart", label: "RAIL", label_kind: "RESERVATION_TYPE", at: "2026-10-10T09:10:00+08:00", status: "PROTECTED", protected: true, confidence: null, reasoning_summary: "", semantic_node_key: null },
      { id: `33333333-3333-4333-8333-${"c".repeat(12)}`, kind: "COMMITMENT", role: "MID_TRIP", title: "海河悦榕庄 湖景房", label: "海河悦榕庄 湖景房", label_kind: "ACTIVITY_TITLE", at: "2026-10-10T20:00:00+08:00", status: "PROTECTED", protected: true, confidence: null, reasoning_summary: "", semantic_node_key: null },
      { id: `44444444-4444-4444-8444-${"d".repeat(12)}`, kind: "RESERVATION", role: "UNKNOWN", title: "Travel fact", label: "XYZREF9", at: "2026-10-11T12:00:00+08:00", status: "PROTECTED", protected: false, confidence: null, reasoning_summary: "", semantic_node_key: null },
    ];
    await page.route("**/api/v1/journeys/*/memory", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ journey_id: seeded.journeyId, title: "Journey Memory", items }),
      }),
    );
    await page.goto("/v8/trips", { waitUntil: "load" });

    const rows = await readRowNames(page, 4, NODE);
    expect(
      rows.names[0],
      node(NODE, `a place name stopped being painted as its own name: "${rows.names[0]}"`),
    ).toContain("天津西站");
    expect(
      rows.names[1],
      node(NODE, `the type-code branch did not name its gap: "${rows.names[1]}"`),
    ).toContain("服务器只给了这条行程事实的预订类型，没有给地点名字");
    expect(
      rows.names[2],
      node(NODE, `an activity title is a name and should be painted as one: "${rows.names[2]}"`),
    ).toContain("海河悦榕庄 湖景房");
    expect(
      rows.names[3],
      node(NODE, `a payload that states no branch was answered with something other than the gap: "${rows.names[3]}"`),
    ).toContain("服务器没有给这条行程事实的地点名字");

    for (const text of rows.names) {
      for (const machine of ["RAIL", "XYZREF9", "Arrive", "Depart", "Travel fact"]) {
        expect(
          text,
          node(NODE, `"${machine}" is standing where a traveller's name belongs: "${text}"`),
        ).not.toContain(machine);
      }
      expect(
        text,
        node(NODE, `an identifier was shortened and used as a name: "${text}"`),
      ).not.toMatch(/[0-9a-f]{8}-[0-9a-f]{4}/);
    }

    /* Still reachable, one level down. */
    const folds = page.getByTestId("v13-2-memory-technical");
    expect(await folds.count(), node(NODE, "the demoted values left the row entirely")).toBe(4);
    await folds.nth(1).locator("summary").click();
    await expect(folds.nth(1), node(NODE, "the fold did not carry the server's own word")).toContainText("Depart");
    await expect(folds.nth(1), node(NODE, "the fold did not carry the raw label")).toContainText("RAIL");
    await folds.nth(3).locator("summary").click();
    await expect(folds.nth(3), node(NODE, "the fold did not carry the reference the row refused to paint")).toContainText("XYZREF9");

    writeFileSync(
      evidencePath("ord0428/branches.json"),
      JSON.stringify({ run: RUN, node: NODE, painted_names: rows.names, folds: 4 }, null, 2) + "\n",
      "utf-8",
    );
  });
});
