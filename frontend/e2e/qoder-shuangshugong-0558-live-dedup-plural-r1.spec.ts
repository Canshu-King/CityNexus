/**
 * ORD-0558 · lane 双数工 — the Live screen's merged-suggestions line, both count states.
 * LAYER: integration (RENDERED component). Nothing here imports `englishCountNoun` and
 * asserts on its return value; the assertions read the painted text of
 * `[data-testid="live-deduped"]` on the real `/v8/live` route.
 *
 * The table row this lane was given is the Chinese arm of the line, and Chinese classifiers
 * do not inflect, so that row is not an English defect.  The English arm below it already
 * reads through the shared ruler.  What the order still asks for is the proof: the same
 * screen at a count of one and at a count of two, in English.
 *
 * `duplicateCount` is pendingAll minus pending over the semantic diff key, so feeding N
 * pending proposals that share one diff yields duplicateCount = N - 1.  Two English arms
 * therefore cover count 1 and count 2.  Every `/api/v1/` call is served from fixtures, so
 * this run does not depend on a backend answering.
 *
 * Line coordinates in the readouts are located by scanning the source at run time
 * (probeSource), never typed in by hand.
 */

import { expect, test, type Page } from "@playwright/test";
import { readFileSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { evidencePath } from "./_qoderEvidence";

const JOURNEY_ID = "e2e-0558-journey";
const HERE = dirname(fileURLToPath(import.meta.url));
const TARGET_SOURCE = resolve(HERE, "../src/features/execution/LiveRecovery.tsx");
const RULER_MODULE = "frontend/src/lib/plural.ts";

type Disruption = {
  id: string;
  type: string;
  severity: string;
  status?: string | null;
  affected_activity_id: string | null;
  occurred_at: string;
  resolved_at?: string | null;
};

type Proposal = {
  id: string;
  status: string;
  trigger_event_id?: string | null;
  hard_constraints_passed: boolean;
  locked_commitments_preserved: boolean;
  diff: { removed?: string[]; added?: string[]; moved?: string[] };
};

/** One identical semantic diff, repeated across proposal ids: that is what the dedup folds. */
function identicalPending(count: number): Proposal[] {
  return Array.from({ length: count }, (_unused, index) => ({
    id: `dup-${index + 1}`,
    status: "PRESENTED",
    trigger_event_id: null,
    hard_constraints_passed: true,
    locked_commitments_preserved: true,
    diff: { removed: ["Nanputou sunset slot"], added: ["Breeze terrace table"], moved: [] },
  }));
}

type SourceProbe = {
  file: string;
  totalLines: number;
  zhArmLine: number;
  enArmLine: number;
  duplicateCountLine: number;
  rulerImportLine: number;
  enArmCarriesRuler: boolean;
  enArmText: string;
};

function probeSource(): SourceProbe {
  const text = readFileSync(TARGET_SOURCE, "utf-8");
  const lines = text.split(/\r?\n/);
  const find = (needle: string, from = 0): number => {
    for (let index = from; index < lines.length; index += 1) {
      if (lines[index].includes(needle)) return index + 1;
    }
    return -1;
  };
  const zhArmLine = find("已合并 ${duplicateCount}");
  const enArmLine = find("Merged ${duplicateCount}", zhArmLine === -1 ? 0 : zhArmLine);
  return {
    file: "frontend/src/features/execution/LiveRecovery.tsx",
    totalLines: lines.length,
    zhArmLine,
    enArmLine,
    duplicateCountLine: find("const duplicateCount ="),
    rulerImportLine: find('from "../../lib/plural"'),
    enArmCarriesRuler: enArmLine > 0 && lines[enArmLine - 1].includes("englishCountNoun"),
    enArmText: enArmLine > 0 ? lines[enArmLine - 1].trim() : "",
  };
}

function experienceFixture(): Record<string, unknown> {
  return {
    journey: {
      id: JOURNEY_ID,
      traveler_id: "e2e-0558-traveler",
      title: "Xiamen weekend",
      city_code: "CN-XIAMEN",
      timezone: "Asia/Shanghai",
      start_at: "2026-10-09T18:00:00+08:00",
      end_at: "2026-10-11T15:00:00+08:00",
      budget: { amount_minor: 120000, currency: "CNY" },
    },
    trip: {
      arrival_anchor: { at: "2026-10-09T18:00:00+08:00", location: "Xiamen Station" },
      departure_anchor: { at: "2026-10-11T15:00:00+08:00", location: "Xiamen Airport" },
      party_size: 2,
      occupancy: { adults: 2, rooms: 1 },
      stay_budget: { amount_minor: 70000, currency: "CNY" },
    },
    offers: [],
    options: [],
    selected_option_id: null,
    mobility_facts: [],
    active_plan: {
      id: "plan-0558",
      version_no: 1,
      status: "ACTIVE",
      source: "E2E_RENDER",
      current_activity_id: null,
      // Deliberately no activities and no disruptions: the dedup line must render on its
      // own so nothing else competes with the reading, and maplibre never loads tiles.
      activities: [],
      legs: [],
      user_location: null,
      disruptions: [] as Disruption[],
    },
    recovery: null,
    experience_flags: {
      needs_review: false,
      recovery_required: false,
      staleness: false,
      feasibility_failures: [],
    },
  };
}

function offlineFixture() {
  return {
    journey_id: JOURNEY_ID,
    sequence: 1,
    valid_until: "2026-12-31T00:00:00Z",
    snapshot: {
      active_plan_version_id: null,
      current_activity_id: null,
      next_24h: [],
      legs: [],
      hotel: null,
      reservations: [],
      read_only: true,
      financial_actions_allowed: false,
    },
    provider_freshness: { latest_provider_capture_at: null, transit_realtime: "UNKNOWN" },
    updated_at: "2026-10-09T10:00:00Z",
  };
}

async function seed(page: Page, locale: "en" | "zh-CN") {
  // addInitScript is serialized into the page, so nothing from this module's scope survives
  // there: every value it needs arrives through the arg, or the keys are never written and
  // the shell opens the create-a-trip wizard instead of the Live screen.
  await page.addInitScript(({ journeyId, code }) => {
    localStorage.setItem("citynexus.v8.journey_id", journeyId);
    localStorage.setItem("citynexus.demo.journey_id", journeyId);
    localStorage.setItem("citynexus.locale", code);
    try {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (navigator as any).serviceWorker.register = () => Promise.resolve({});
    } catch {
      /* no-op */
    }
  }, { journeyId: JOURNEY_ID, code: locale });
}

/** One dispatcher on /api/v1/ so route-registration order can never bite. */
async function mockApi(page: Page, replans: Proposal[]) {
  await page.route(/\/api\/v1\//, (route) => {
    const pathname = new URL(route.request().url()).pathname;
    const send = (json: unknown) =>
      route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(json) });
    if (pathname.endsWith("/experience")) return send(experienceFixture());
    if (pathname.endsWith("/replans")) return send(replans);
    if (pathname.endsWith("/plans")) return send([]);
    if (pathname.endsWith("/twin")) return send({ id: "twin-1", context: {} });
    if (pathname.endsWith("/agent-policy"))
      return send({
        mode: "ADVISORY",
        auto_accept_replan: false,
        version: 1,
        max_auto_replan_cost_delta_minor: 5000,
        max_auto_loss_minor: 0,
        max_auto_schedule_drift_min: 20,
      });
    if (pathname.endsWith("/wallet"))
      return send({ reservations: [], commitments: [], offline_ready: true });
    if (pathname.endsWith("/offline-snapshot")) return send(offlineFixture());
    if (pathname.endsWith("/runtime-status")) return send({});
    // The /v8/live route also mounts the V10 execution panel, which reads
    // web.data.observations.length and new Date(clock.data.now) unguarded.
    if (pathname.endsWith("/execution-clock"))
      return send({
        now: "2026-10-09T10:00:00+08:00",
        timezone: "Asia/Shanghai",
        current_activity_id: null,
      });
    if (pathname.endsWith("/web-observations")) return send({ observations: [] });
    return send({});
  });
}

type Arm = {
  name: string;
  locale: "en" | "zh-CN";
  proposals: number;
  duplicateCount: number;
  expected: string;
  /** The form a hand-joined `${n} suggestions` would paint at this count. */
  forbidden: string;
};

const ARMS: Arm[] = [
  {
    name: "E1en_one",
    locale: "en",
    proposals: 2,
    duplicateCount: 1,
    expected: "Merged 1 identical suggestion.",
    forbidden: "Merged 1 identical suggestions.",
  },
  {
    name: "E2en_two",
    locale: "en",
    proposals: 3,
    duplicateCount: 2,
    expected: "Merged 2 identical suggestions.",
    forbidden: "Merged 2 identical suggestion.",
  },
  {
    name: "Z1zh_one",
    locale: "zh-CN",
    proposals: 2,
    duplicateCount: 1,
    expected: "已合并 1 个内容相同的建议。",
    forbidden: "",
  },
  {
    name: "Z2zh_two",
    locale: "zh-CN",
    proposals: 3,
    duplicateCount: 2,
    expected: "已合并 2 个内容相同的建议。",
    forbidden: "",
  },
];

async function readArm(page: Page, arm: Arm, probe: SourceProbe): Promise<string> {
  // Anything that escapes the fixture dispatcher is recorded rather than silently borrowed
  // from a neighbour: this run points vite's /api proxy at a port nothing listens on.
  const escaped: string[] = [];
  page.on("requestfailed", (request) => escaped.push(request.url()));
  await seed(page, arm.locale);
  await mockApi(page, identicalPending(arm.proposals));
  await page.goto("/v8/live", { waitUntil: "domcontentloaded" });

  await expect(page.getByTestId("live-recovery")).toBeVisible();

  const deduped = page.getByTestId("live-deduped");
  await expect(deduped).toBeVisible();
  // Exact whole-element text: a missing or an extra "s" fails here, which is the point.
  await expect(deduped).toHaveText(arm.expected);
  if (arm.forbidden) {
    await expect(deduped).not.toHaveText(arm.forbidden);
  }

  const screenshot = evidencePath("ord0558", `${arm.name}.png`);
  await deduped.screenshot({ path: screenshot });

  const actual = (await deduped.innerText()).trim();
  writeFileSync(
    evidencePath("ord0558", `${arm.name}.json`),
    JSON.stringify(
      {
        order: "ORD-0558",
        lane: "shuangshugong",
        arm: arm.name,
        locale: arm.locale,
        proposals_fed: arm.proposals,
        duplicate_count_expected: arm.duplicateCount,
        expected_text: arm.expected,
        forbidden_text_ruled_out: arm.forbidden,
        rendered_text: actual,
        match: actual === arm.expected,
        requests_escaped_the_fixtures: escaped,
        screenshot,
        source_probe: probe,
        ruler_module: RULER_MODULE,
      },
      null,
      2,
    ),
  );
  return actual;
}

test.describe("ORD-0558 LiveRecovery merged-suggestions line, both count states", () => {
  test("S0probe: the counted noun on the English arm reaches the ruler, and the arms are adjacent", () => {
    const probe = probeSource();
    expect(probe.zhArmLine).toBeGreaterThan(0);
    expect(probe.enArmLine).toBe(probe.zhArmLine + 1);
    expect(probe.enArmCarriesRuler).toBe(true);
    expect(probe.rulerImportLine).toBeGreaterThan(0);
    expect(probe.duplicateCountLine).toBeGreaterThan(0);
    writeFileSync(
      evidencePath("ord0558", `${"S0probe"}.json`),
      JSON.stringify({ order: "ORD-0558", lane: "shuangshugong", arm: "S0probe", ...probe }, null, 2),
    );
  });

  for (const arm of ARMS) {
    test(arm.name, async ({ page }) => {
      const probe = probeSource();
      const actual = await readArm(page, arm, probe);
      expect(actual).toBe(arm.expected);
    });
  }
});
