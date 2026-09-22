/**
 * ORD-0232's **end-to-end** arm: real `plans/generate`, real audit feed, real places directory, no
 * route stubs anywhere.  It lives outside the acceptance suite (`playwright.ord0232-real.config.ts`
 * points `testDir` here), because the fact it consumes is emitted only by `a96fabf`, which is not an
 * ancestor of this tip.  Run it through `review/ord0232_e2e_replay.py`, which refuses to start it
 * while that is true instead of producing a red nobody owns.
 */
import { expect, test } from "@playwright/test";

const FILE = "e2e-ord0232-real/ord0232-real-chain.spec.ts";
const NODE = "ord0232-5-real-plan-generation-puts-the-dropped-stop-on-the-screen";
const node = (detail: string) => `${FILE} :: ${NODE} — ${detail}`;

test(NODE + " — 真链路走完，屏上必须点名被丢的那一站", async ({ page, request }) => {
  test.setTimeout(420_000);

  const scene = (await (await request.get("/api/v1/demo/scene")).json()) as {
    journey_id?: string;
  };
  const journeyId = String(scene.journey_id ?? "");
  expect(journeyId, node("the demo scene gave no journey to work on")).toBeTruthy();

  const experience = (await (
    await request.get(`/api/v1/journeys/${journeyId}/experience`)
  ).json()) as { journey?: { traveler_id?: string; city_code?: string } };
  const travelerId = String(experience.journey?.traveler_id ?? "");
  const cityCode = String(experience.journey?.city_code ?? "");
  expect(travelerId && cityCode, node("journey identity unreadable, so no capability could be filed")).toBeTruthy();

  /* `severity: HARD` is refused on the plain write path (409, "hard capability needs /confirm"), so
     the confirmation route is the only door and the payload follows CapabilityInput's own fields. */
  const confirm = await request.post(`/api/v1/travelers/${travelerId}/capabilities/confirm`, {
    data: [{ code: "STROLLER", severity: "HARD", scope: "TRAVELER" }],
  });
  expect(
    `${confirm.status()} ${await confirm.text()}`.slice(0, 300),
    node("filing the HARD stroller capability failed, so the gate had nothing to reject on"),
  ).toMatch(/^200 /);

  const generated = await request.post(`/api/v1/journeys/${journeyId}/plans/generate`, { data: {} });
  expect(
    `${generated.status()}`,
    node("plans/generate did not answer, so no candidate could have been dropped"),
  ).toBe("201");

  const feed = (await (
    await request.get(`/api/v1/journeys/${journeyId}/agent-feed?limit=200`)
  ).json()) as { events?: Array<Record<string, any>> };
  const rejections = (feed.events ?? []).filter(
    (event) => String(event?.event_type ?? "") === "plans.candidate_rejected",
  );
  expect(
    rejections.length,
    node(
      `the real feed carried no plans.candidate_rejected event; got ${JSON.stringify(
        (feed.events ?? []).map((event) => event?.event_type),
      ).slice(0, 300)}`,
    ),
  ).toBeGreaterThan(0);

  const first = String(rejections[0]?.facts?.failures?.[0] ?? "");
  const placeId = first.split(":").slice(1).join(":");
  expect(placeId, node(`the rejection fact named no place id: ${first}`)).toBeTruthy();
  const places = (await (
    await request.get(`/api/v1/places?city_code=${encodeURIComponent(cityCode)}`)
  ).json()) as Array<{ id?: string; name?: string }>;
  const name = String((places ?? []).find((place) => place?.id === placeId)?.name ?? "");
  expect(
    name,
    node(`the places directory has no name for ${placeId}; the screen would have to say "could not read"`),
  ).toBeTruthy();

  await page.addInitScript((id) => {
    localStorage.clear();
    localStorage.setItem("citynexus.v8.journey_id", id as string);
    localStorage.setItem("citynexus.locale", "zh-CN");
  }, journeyId);
  await page.goto("/v8/hub", { waitUntil: "load" });
  const row = page.getByTestId("dropped-candidate-row");
  await expect(
    row.first(),
    node("the hub rendered no dropped-candidate row although the feed carried a real rejection"),
  ).toBeVisible({ timeout: 30_000 });
  const texts: string[] = [];
  for (let index = 0; index < (await row.count()); index += 1) {
    texts.push((await row.nth(index).innerText()).replace(/\s+/g, " ").trim());
  }
  expect(
    texts.join(" | "),
    node(`the row does not name the stop the server named (${name} / ${placeId}): ${texts.join(" | ")}`),
  ).toContain(name);
  expect(
    texts.join(" | "),
    node(`the raw place id leaked into the traveller's text: ${texts.join(" | ")}`),
  ).not.toContain(placeId);
});
