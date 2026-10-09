import { expect, test } from "@playwright/test";
import { readFileSync, writeFileSync } from "node:fs";
import { evidencePath } from "./_qoderEvidence";
import { openStageEntry } from "./_qoderStageEntry";

/**
 * wenangong-0501 -- the nine words sceneClock.ts now reads from the shared dictionary,
 * measured where they are owed: on the stage's own rows, on a phone, in both languages,
 * one server state at a time.
 *
 * The expected strings are not written down here. They come from
 * `review/wenangong/i18n_scene_clock_expect.json`, the table a generator copied out of the
 * authoritative tip's own inline arms -- so a reworded dictionary line cannot satisfy this
 * spec, and a word wired to the wrong server state shows up as a named red row.
 */

const FILE = "e2e/qoder-wenangong-scene-words-render.spec.ts";
const node = (id: string, detail: string) => `${FILE} :: ${id} — ${detail}`;
const clean = (text: string) => text.replace(/\s+/g, " ").trim();

type Case = { state: string; key: string; field: "basis" | "evidence" };

const CASES: Case[] = [
  { state: "CURSOR", key: "clock.basis.cursor", field: "basis" },
  { state: "JOURNEY_START", key: "clock.basis.journeyStart", field: "basis" },
  { state: "NOT_STATED_BY_SERVER", key: "clock.basis.notStated", field: "basis" },
  { state: "REFERENCED", key: "clock.evidence.referenced", field: "evidence" },
  { state: "FROZEN_WITHOUT_TTL", key: "clock.evidence.frozenWithoutTtl", field: "evidence" },
  {
    state: "EVIDENCE_REFERENCE_INCONSISTENT",
    key: "clock.evidence.referenceInconsistent",
    field: "evidence",
  },
  { state: "NO_FROZEN_EVIDENCE", key: "clock.evidence.none", field: "evidence" },
  { state: "NO_SCENARIO", key: "clock.evidence.noScenario", field: "evidence" },
  { state: "SOMETHING_THE_SERVER_MADE_UP", key: "clock.evidence.unknown", field: "evidence" },
];

// The expiry half of the evidence row belongs to the panel and is not this order's face.
const EXPIRY_ABSENT: Record<string, string> = { "zh-CN": "没有到期时间", en: "no expiry" };

test("wenangong-scene-words-reach-the-stage-in-both-languages — 九枚词逐枚上屏，逐字等于现尖那些字", async ({
  page,
}) => {
  test.setTimeout(300_000);
  const table = JSON.parse(
    readFileSync(new URL("../../review/wenangong/i18n_scene_clock_expect.json", import.meta.url), "utf-8"),
  ) as Record<string, { zh: string; en: string }>;

  const live = await page.request.get("/api/v1/demo/scene");
  expect(live.ok(), node("scene-words-seed", `GET /demo/scene answered ${live.status()}`)).toBe(true);
  const seeded = (await live.json()) as Record<string, unknown>;
  const journeyId = seeded.journey_id;
  expect(
    typeof journeyId === "string" && journeyId.length > 0,
    node("scene-words-seed", `the seeded stage holds no journey (${JSON.stringify(seeded)})`),
  ).toBe(true);

  let scene: Record<string, unknown> = {};
  await page.route("**/api/v1/demo/scene", (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(scene) }),
  );
  /* The locale arrives through the address so one init script serves both languages: it runs
     before the provider reads storage, and a second script would only stack behind the first. */
  await page.addInitScript(
    ([id]) => {
      localStorage.clear();
      localStorage.setItem("citynexus.v8.journey_id", id as string);
      const wanted = new URLSearchParams(window.location.search).get("cnxlocale");
      if (wanted === "en" || wanted === "zh-CN") localStorage.setItem("citynexus.locale", wanted);
    },
    [String(journeyId)],
  );
  await page.setViewportSize({ width: 390, height: 844 });

  const readings: Record<string, unknown>[] = [];
  for (const lang of ["zh-CN", "en"]) {
    for (const item of CASES) {
      scene = {
        demo_mode: true,
        journey_id: journeyId,
        journey_status: "PLANNING",
        current_activity_id: null,
        scene_start_at: "2026-10-09T18:00:00+08:00",
        scene_end_at: "2026-10-11T15:00:00+08:00",
        effective_now: "2026-10-10T12:00:00+08:00",
        basis: item.field === "basis" ? item.state : "CURSOR",
        evidence_expires_at: null,
        evidence_state: item.field === "evidence" ? item.state : "FROZEN_WITHOUT_TTL",
        evidence_snapshot_id: "snapshot-probe",
        evidence_reference_consistent: true,
        mobility_legs_total: 5,
        mobility_legs_with_evidence: 5,
        plan_version_id: "11111111-1111-4111-8111-111111111111",
      };

      await page.goto(`/v8/hub?cnxlocale=${lang}`, { waitUntil: "load" });
      await openStageEntry(page, node(item.key, "the stage window would not open"));

      const cell = page.getByTestId(item.field === "basis" ? "sim-basis" : "sim-evidence");
      await expect(cell, node(item.key, `${lang}: no ${item.field} row on screen`)).toBeVisible({
        timeout: 30_000,
      });
      await expect(
        cell,
        node(item.key, `${lang}: the ${item.field} row sits outside the 390x844 viewport`),
      ).toBeInViewport();

      const shown = clean(await cell.innerText());
      const wanted = item.key in table ? (lang === "zh-CN" ? table[item.key].zh : table[item.key].en) : "";
      const expected =
        item.field === "basis" ? wanted : `${wanted} · ${EXPIRY_ABSENT[lang]}`;
      const composed = expected.replace("{state}", item.state);

      readings.push({
        locale: lang,
        server_state: item.state,
        key: item.key,
        shown,
        expected: composed,
        matched: shown === composed,
      });
      expect(
        shown,
        node(item.key, `${lang}: the row reads ${JSON.stringify(shown)}, not ${JSON.stringify(composed)}`),
      ).toBe(composed);
    }
  }

  const unmatched = readings.filter((row) => row.matched !== true).length;
  writeFileSync(
    evidencePath("ui-overnight/wenangong-scene-words-render.json"),
    JSON.stringify(
      {
        generatedBy: "wenangong-0501",
        head: process.env.CITYNEXUS_E2E_GIT_HEAD ?? "unknown",
        readings: readings.length,
        unmatched,
        rows: readings,
      },
      null,
      2,
    ) + "\n",
    "utf-8",
  );
  await page.screenshot({ path: evidencePath("ui-overnight/wenangong-scene-words.png"), fullPage: true });
});
