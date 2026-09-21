import { expect, test, type Page } from "@playwright/test";
import { writeFileSync } from "node:fs";
import { evidencePath } from "./_qoderEvidence";
import {
  openStageEntry,
  stageDeclaration,
  stageWindowDeclaration,
} from "./_qoderStageEntry";

/**
 * ORD-0082 -- Today's Now/Next must be chosen by the stage's cursor, not by the device clock.
 *
 * The defect was visible on one screen: the Simulation panel quoted the server's `effective_now`
 * (12:00) while the hero under it still read "接下来 · 09:00 Old Town Gate", because the hero
 * selected stops with `Date.now()` and the wall clock sits months before the staged day, so the
 * earliest stop always won.
 *
 * The criterion is therefore agreement with the server's own cursor and next stop -- read out of
 * `/experience`, not off the screen -- which is what makes this "选站" rather than "挪字".  The
 * device-time fallback is allowed only when no scenario can be read, proven by forcing that read
 * to fail, stated inside the hero, with no new panel and no invented vocabulary.
 */

const FILE = "e2e/qoder-today-follows-the-stage.spec.ts";
const node = (id: string, detail: string) => `${FILE} :: ${id} — ${detail}`;

type Activity = { id: string; title: string; sequence_no: number; start_at: string; status: string };
type Scene = Record<string, string | number | boolean | null>;

const clean = (value: string | null | undefined) => String(value ?? "").replace(/\s+/g, " ").trim();

async function readScene(page: Page): Promise<Scene> {
  const response = await page.request.get("/api/v1/demo/scene");
  return (await response.json()) as Scene;
}

/**
 * The server's own statement of where the journey is and what comes next.
 *
 * "Next" is taken from the twin's execution projection -- the field Today is supposed to follow --
 * rather than re-derived here.  Re-deriving it produced a second rule to disagree with, which is
 * the opposite of what this order is for.  `cursor_status` comes along because a cursor the server
 * itself does not trust is a degraded screen, not a station choice.
 */
async function readStage(page: Page, journeyId: string) {
  const experience = await page.request.get(`/api/v1/journeys/${journeyId}/experience`);
  const twinResponse = await page.request.get(`/api/v1/journeys/${journeyId}/twin`);
  if (!experience.ok() || !twinResponse.ok()) return null;
  const plan = ((await experience.json()) as {
    active_plan?: { activities?: Activity[]; current_activity_id?: string | null; cursor_status?: string | null };
  }).active_plan;
  const twin = (await twinResponse.json()) as {
    current_activity_id?: string | null;
    context?: { execution?: { next_activity_id?: string | null; cursor_status?: string | null; next?: { id?: string } | null } };
  };
  if (!plan?.activities?.length) return null;
  const ordered = [...plan.activities].sort((a, b) => a.sequence_no - b.sequence_no);
  const cursorId = twin.current_activity_id ?? plan.current_activity_id ?? null;
  const current = ordered.find((item) => item.id === cursorId) ?? null;
  const declaredNextId =
    twin.context?.execution?.next_activity_id ?? twin.context?.execution?.next?.id ?? null;
  const next = declaredNextId
    ? (ordered.find((item) => item.id === declaredNextId) ?? null)
    : null;
  return {
    ordered,
    current,
    next,
    cursorStatus: twin.context?.execution?.cursor_status ?? plan.cursor_status ?? null,
    declaredNextId,
  };
}

async function pressStageAction(page: Page, id: string) {
  /* The entry is collapsed on a phone by design, and the walk to ACTIVE reloads the page, so open it
     here rather than assuming the panel is on screen. */
  await openStageEntry(page, `pressing ${id}`);
  const row = page.getByTestId(`sim-action-${id}`);
  await row.scrollIntoViewIfNeeded();
  const reasonId = await row.getAttribute("aria-describedby");
  if (await row.getAttribute("aria-disabled")) {
    return {
      pressed: false,
      reason: reasonId ? clean(await page.locator(`#${reasonId}`).innerText()) : "(blocked, no reason element)",
    };
  }
  await row.click();
  await expect(page.getByTestId("sim-outcome")).toBeVisible({ timeout: 30_000 });
  return { pressed: true, outcome: clean(await page.getByTestId("sim-outcome").innerText()) };
}

async function openToday(page: Page, journeyId: string, locale: string, scheme: "light" | "dark", width: number) {
  await page.addInitScript(
    ([id, lang]) => {
      localStorage.clear();
      localStorage.setItem("citynexus.v8.journey_id", id as string);
      localStorage.setItem("citynexus.locale", lang as string);
    },
    [journeyId, locale],
  );
  await page.setViewportSize({ width, height: 844 });
  await page.goto("/v8/hub", { waitUntil: "load" });
  await expect(page.getByTestId("today-hero")).toBeVisible({ timeout: 30_000 });
  await page.emulateMedia({ colorScheme: scheme, media: "screen" });
  await page.waitForTimeout(800);
}

/** Put the scenario into execution through the product's own stage actions. */
async function walkToActive(page: Page) {
  for (let step = 0; step < 5; step += 1) {
    const scene = await readScene(page);
    if (scene.journey_status === "ACTIVE" && scene.basis) return scene;
    if (!scene.plan_version_id) {
      await pressStageAction(page, "prepare");
    } else {
      await pressStageAction(page, "start");
    }
    await page.waitForTimeout(1_500);
    await page.reload({ waitUntil: "load" }).catch(() => undefined);
    await expect(page.getByTestId("today-hero")).toBeVisible({ timeout: 30_000 }).catch(() => undefined);
  }
  return readScene(page);
}

const readNow = async (page: Page) =>
  (await page.getByTestId("today-now").count()) ? clean(await page.getByTestId("today-now").innerText()) : "";
const readNext = async (page: Page) => clean(await page.getByTestId("today-next").innerText());

/* `expect.poll(fn).toContain(x, {message})` silently drops the message, which is why this node once
   failed with a bare "Expected: not ..." and no owner.  Poll here, and on failure re-read the screen
   so the red names both the server's value and the hero's. */
const NODE = "sim-today-hero-follows-the-stage";
async function heroSays(page: Page, read: (page: Page) => Promise<string>, expected: string, label: string) {
  try {
    await expect
      .poll(() => read(page), { timeout: 25_000, intervals: [500] })
      .toContain(expected);
  } catch (failure) {
    throw new Error(
      node(NODE, `${label} never came round: the server says ${JSON.stringify(expected)}, the screen reads ${JSON.stringify(clean(await read(page)))}`),
      { cause: failure },
    );
  }
}
async function heroStopsSaying(page: Page, read: (page: Page) => Promise<string>, was: string, label: string, timeout = 25_000) {
  try {
    await expect
      .poll(() => read(page), { timeout, intervals: [400] })
      .not.toBe(was);
  } catch (failure) {
    throw new Error(
      node(NODE, `${label} did not move within ${Math.round(timeout / 1000)}s: it still reads ${JSON.stringify(clean(await read(page)))} (was ${JSON.stringify(was)})`),
      { cause: failure },
    );
  }
}

for (const viewport of [390, 412]) {
  for (const [locale, words] of [
    ["zh-CN", { scene: "服务器场景", device: "这台设备自己的时间", coordinates: "这个行程还没有可信的坐标" }],
    ["en", { scene: "server", device: "this device", coordinates: "no trustworthy coordinates" }],
  ] as const) {
    test(`sim-today-hero-follows-the-stage [${locale}@${viewport}] — hero 按服务器游标选站`, async ({ page }) => {
      test.setTimeout(300_000);
      const seeded = await readScene(page);
      const journeyId = String(seeded.journey_id ?? "");
      expect(
        journeyId.length > 0,
        node("sim-today-hero-follows-the-stage", "there is no scenario on stage to follow"),
      ).toBe(true);
      await openToday(page, journeyId, locale, "light", viewport);

      const scene = await walkToActive(page);
      /* The stage routes pick *their* scenario (the journey with an active plan, else the most
         recent one), which is not necessarily the one the pre-walk scene named.  Read the id
         again from the post-walk scene and reopen Today on it, or the hero and the server would
         be describing two different journeys and any disagreement would be my fixture's. */
      const stageJourneyId = String(scene.journey_id ?? journeyId);
      if (scene.journey_status !== "ACTIVE") {
        test.skip(
          true,
          `the server will not put this scenario into execution (journey_status=${String(scene.journey_status)}); ` +
            "the hero has no cursor to follow, and this node refuses to assert against a wall clock instead",
        );
      }
      await openToday(page, stageJourneyId, locale, "light", viewport);

      /* Assert the clock source first: a hero that matches the server by luck -- or one that
         quietly fell back to the device -- must not be scored as agreement. */
      const source = page.getByTestId("today-clock-source");
      await expect
        .poll(() => source.getAttribute("data-clock-source"), { timeout: 25_000, intervals: [200] })
        .toBe("SCENE");
      expect(
        clean(await source.innerText()),
        node("sim-today-hero-follows-the-stage", "the settled clock source is not stated as the scenario"),
      ).toContain(words.scene);

      const first = await readStage(page, stageJourneyId);
      /* The server does not always trust its own cursor: on a scenario the wall clock sits outside
         of, the projection says ABSENT_FALLBACK and Today legitimately falls back.  That case is
         the degraded path, not the station choice under test, so the disclosure is asserted here
         and the equality claim is reported as unmeasurable instead of being scored green. */
      if (first?.cursorStatus && first.cursorStatus !== "VALID") {
        expect(
          clean(await page.getByTestId("today-clock-source").innerText()),
          node("sim-today-hero-follows-the-stage",
            `the server's cursor is ${first.cursorStatus} and the hero does not say so on screen`),
        ).toContain(first.cursorStatus);
        test.skip(true, `the server reports the cursor as ${first.cursorStatus}; no station to agree with`);
      }
      expect(
        first?.current,
        node("sim-today-hero-follows-the-stage", "the server reports no cursor, so there is nothing to agree with"),
      ).not.toBeNull();
      const currentTitle = String(first?.current?.title ?? "");
      if (!currentTitle) {
        throw new Error(node(NODE, "the server's cursor names no activity, so the comparison would assert nothing"));
      }
      await heroSays(page, readNow, currentTitle, "Today's 现在");
      if (first?.next || first?.declaredNextId) {
        await heroSays(page, readNext, String(first.next.title), "接下来");
      }

      /* Then move the stage and require the hero to follow the move. */
      const beforeCursorId = String(first?.current?.id ?? "");
      const beforeNext = clean(await readNext(page));
      const advanced = await pressStageAction(page, "advance");
      expect(
        advanced.pressed,
        node("sim-today-hero-follows-the-stage", `advance was blocked before it could be measured: ${advanced.reason}`),
      ).toBe(true);

      let settled = await readStage(page, stageJourneyId);
      for (let step = 0; step < 4 && settled?.current?.id === beforeCursorId; step += 1) {
        await pressStageAction(page, "advance");
        settled = await readStage(page, stageJourneyId);
      }
      const cursorMoved = Boolean(settled?.current && settled.current.id !== beforeCursorId);
      if (cursorMoved) {
        /* 8s, not 25s: the twin also re-reads on a 15s interval, and a wider budget would let a
           screen that was never told the stage moved still pass.  The refresh an action triggers is
           what has to carry the change. */
        await heroStopsSaying(page, readNext, beforeNext, "接下来", 8_000);
      }
      if (settled?.next) {
        await heroSays(page, readNext, String(settled.next.title), "接下来");
      }
      if (settled?.current) {
        expect(
          clean(await readNow(page)),
          node("sim-today-hero-follows-the-stage",
            `after the walk the server's cursor is "${settled.current.title}" and the hero is not on it`),
        ).toContain(String(settled.current.title));
      }

      writeFileSync(
        evidencePath(`ui-overnight/hero-follows-${locale}-${viewport}.json`),
        JSON.stringify(
          {
            generatedBy: "e345b9d6",
            order: "ORD-0082",
            node: "sim-today-hero-follows-the-stage",
            locale,
            viewport,
            scene: { status: scene.journey_status, basis: scene.basis, effective_now: scene.effective_now },
            serverNow: settled?.current?.title ?? null,
            serverNext: settled?.next?.title ?? null,
            heroNow: clean(await readNow(page)),
            heroNext: clean(await readNext(page)),
            cursorMoved,
          },
          null,
          2,
        ) + "\n",
        "utf-8",
      );
    });

    test(`today-clock-source-is-spoken-when-device-time-is-used [${locale}@${viewport}] — 回落不许静默`, async ({ page }) => {
      test.setTimeout(240_000);
      const seeded = await readScene(page);
      const journeyId = String(seeded.journey_id ?? "");
      expect(
        journeyId.length > 0,
        node("today-clock-source-is-spoken-when-device-time-is-used", "no journey to open Today with"),
      ).toBe(true);
      /* Prove the fallback by force: a seeded stage always has a scenario, so waiting for one to
         be absent would never exercise this path. */
      await page.route("**/api/v1/demo/scene", (route) =>
        route.fulfill({
          status: 500,
          contentType: "application/json",
          body: JSON.stringify({ error: { code: "PROBE_FORCED_FAILURE" } }),
        }),
      );
      await page.setViewportSize({ width: viewport, height: 844 });
      await page.addInitScript(
        ([id, lang]) => {
          localStorage.clear();
          localStorage.setItem("citynexus.v8.journey_id", id as string);
          localStorage.setItem("citynexus.locale", lang as string);
        },
        [journeyId, locale],
      );
      await page.goto("/v8/hub", { waitUntil: "load" });
      await expect(page.getByTestId("today-hero")).toBeVisible({ timeout: 30_000 });
      await page.emulateMedia({ colorScheme: "dark", media: "screen" });

      const source = page.getByTestId("today-clock-source");
      /* Both transient and settled fallbacks report DEVICE, so the attribute alone cannot tell
         them apart: wait for the sentence that actually names a cause. */
      await expect(
        source,
        node("today-clock-source-is-spoken-when-device-time-is-used",
          "the hero never settled on a stated reason for using device time"),
      ).toContainText(/读不到服务器场景|台上没有场景|could not be read|no scenario on stage/i, { timeout: 25_000 });
      await expect
        .poll(() => source.getAttribute("data-clock-source"), { timeout: 25_000, intervals: [200] })
        .toBe("DEVICE");
      const said = clean(await source.innerText());
      expect(
        said,
        node("today-clock-source-is-spoken-when-device-time-is-used",
          `the hero does not say device time is in use: ${JSON.stringify(said)}`),
      ).toContain(words.device);
      /* A named cause, not a bare apology: the sentence has to say the scenario could not be read. */
      expect(
        /PROBE_FORCED_FAILURE|could not be read|读不到/i.test(said),
        node("today-clock-source-is-spoken-when-device-time-is-used",
          `the fallback names no reason for using device time: ${JSON.stringify(said)}`),
      ).toBe(true);
      await expect(
        page.getByTestId("today-hero"),
        node("today-clock-source-is-spoken-when-device-time-is-used",
          "a spoken fallback is not allowed to be a broken screen"),
      ).toBeVisible();
      await page.unrouteAll({ behavior: "ignoreErrors" }).catch(() => undefined);
    });
  }
}

test("today-attention-does-not-contradict-the-map — 同屏不能又\"没坐标\"又\"一切正常\"", async ({ page }) => {
  test.setTimeout(240_000);
  const seeded = await readScene(page);
  await openToday(page, String(seeded.journey_id ?? ""), "zh-CN", "light", 390);
  const attention = page.getByTestId("today-attention");
  const mapEmpty = page.getByTestId("v8-map-empty");

  /* The map decides asynchronously: it only knows whether anything can be centred on once the
     raster library loads.  Read the pair once it has committed to one of its two shapes. */
  await expect
    .poll(async () => (await mapEmpty.count()) > 0 || (await page.locator(".maplibregl-canvas").count()) > 0, {
      timeout: 30_000,
      intervals: [500],
    })
    .toBe(true);
  const said = clean(await attention.innerText());
  const empty = (await mapEmpty.count()) > 0;
  if (empty) {
    expect(
      clean(await mapEmpty.innerText()),
      node("today-attention-does-not-contradict-the-map", "the map panel no longer names the missing coordinates"),
    ).toContain("这个行程还没有可信的坐标");
    expect(
      said,
      node("today-attention-does-not-contradict-the-map",
        `the map says there are no trustworthy coordinates while attention says ${JSON.stringify(said)}`),
    ).toContain("这个行程还没有可信的坐标");
    expect(
      /一切正常|All clear/.test(said),
      node("today-attention-does-not-contradict-the-map",
        `attention declares all clear beside an unlocatable trip: ${JSON.stringify(said)}`),
    ).toBe(false);
  } else {
    // The other direction, which the first version of my predicate got wrong: a trip the map can
    // draw -- route geometry, no located activity -- must not be called coordinate-less upstairs.
    expect(
      said.includes("这个行程还没有可信的坐标"),
      node("today-attention-does-not-contradict-the-map",
        `the map drew this trip, yet attention claims it has no coordinates: ${JSON.stringify(said)}`),
    ).toBe(false);
  }
  writeFileSync(
    evidencePath("ui-overnight/today-attention-map.json"),
    JSON.stringify(
      { generatedBy: "e345b9d6", order: "ORD-0082", node: "today-attention-does-not-contradict-the-map", mapEmpty: empty, attention: said },
      null,
      2,
    ) + "\n",
    "utf-8",
  );
});

test("today-scene-window-is-not-called-device-time — 有场景分钟、没投影时不许说\"设备自己的时间\"", async ({ page }) => {
  test.setTimeout(240_000);
  const seeded = await readScene(page);
  const journeyId = String(seeded.journey_id ?? "");
  expect(
    journeyId.length > 0,
    node("today-scene-window-is-not-called-device-time", "no journey to open Today with"),
  ).toBe(true);
  /* This arm is reachable: the two clocks come from two endpoints.  `/demo/scene` can answer ACTIVE
     while `/journeys/{id}/twin` answers a payload with no `context.execution` -- an older build
     behind the same proxy, or a twin request that degrades.  Today then picks its stations from the
     time window measured against the **server's** scene minute, so a reading that calls that
     window "this device's own time" describes a clock that is not in use. */
  const stripped: string[] = [];
  await page.route("**/api/v1/journeys/*/twin**", async (route) => {
    const response = await route.fetch();
    let body: Record<string, unknown>;
    try {
      body = (await response.json()) as Record<string, unknown>;
    } catch {
      return void route.fulfill({ response });
    }
    const context = { ...((body.context ?? {}) as Record<string, unknown>) };
    if (context.execution !== undefined) {
      delete context.execution;
      stripped.push("execution removed");
      body.context = context;
    }
    await route.fulfill({
      status: response.status(),
      contentType: "application/json",
      body: JSON.stringify(body),
    });
  });

  await openToday(page, journeyId, "zh-CN", "light", 390);
  const source = page.getByTestId("today-clock-source");
  /* The stub has to be proved to have fired: a node that passes because the twin never answered is
     measuring a different arm than the one it names. */
  await expect
    .poll(() => stripped.length, {
      timeout: 25_000,
      intervals: [250],
      message: node("today-scene-window-is-not-called-device-time",
        "the twin never answered with a context.execution to strip, so this arm was never exercised"),
    })
    .toBeGreaterThan(0);
  await expect(
    source,
    node("today-scene-window-is-not-called-device-time", "the hero line about which clock is in play vanished"),
  ).toBeVisible();
  await expect(
    source,
    node("today-scene-window-is-not-called-device-time", "the hero never settled on a clock statement"),
  ).toContainText(/服务器场景/, { timeout: 25_000 });

  const said = clean(await source.innerText());
  expect(
    /设备自己的时间|device's own time/i.test(said),
    node("today-scene-window-is-not-called-device-time",
      `the screen claims device time while the window is measured on the server's scene minute: ${JSON.stringify(said)}`),
  ).toBe(false);
  /* And it still has to say what is missing, rather than quietly drawing a station. */
  expect(
    /执行投影|projection/i.test(said),
    node("today-scene-window-is-not-called-device-time",
      `the sentence names no missing projection: ${JSON.stringify(said)}`),
  ).toBe(true);
  await expect
    .poll(() => source.getAttribute("data-clock-source"), { timeout: 25_000, intervals: [250] })
    .toBe("SCENE");
  await expect
    .poll(() => source.getAttribute("data-next-source"), { timeout: 25_000, intervals: [250] })
    .toBe("SCENE_WINDOW");
  writeFileSync(
    evidencePath("ui-overnight/today-scene-window.json"),
    JSON.stringify(
      {
        generatedBy: "e345b9d6",
        order: "ORD-0082",
        node: "today-scene-window-is-not-called-device-time",
        clockSource: "SCENE",
        nextSource: "SCENE_WINDOW",
        said,
      },
      null,
      2,
    ) + "\n",
    "utf-8",
  );
  await page.unrouteAll({ behavior: "ignoreErrors" }).catch(() => undefined);
});

/* ------------------------------------------------------- The stage's floating widget (user's own words:
 * "延时舞台系统我也用不明白，你改成悬浮窗形式，点一下会展开，里面有各种功能，但是别把屏幕挡住").
 *
 * Two overlays already live at the bottom of a phone: the fixed nav and the Copilot pill resting on
 * top of its band (`styles.css:405` puts the dock at `bottom: 72px`, `.v8-content` reserves
 * `124px + safe-area`).  So "floating" is only a fix if the widget clears both, at every scroll
 * position, and still leaves each row centre-hittable -- the same failure ORD-0085 was about, now
 * with a third way to get it wrong (a panel that covers the nav and eats its taps).
 *
 * What this node measures, on the deployed surface: the ball's geometry and hit-ability at rest, the
 * declaration it owes without being opened, that the ball does not move when the page does, the open
 * window's size budget, every row's centre hit and band clearance, that all five nav items are still
 * pressable with the window open, and all four ways back out.
 */
type Rect = { x: number; y: number; width: number; height: number; top: number; bottom: number; right: number };
type Hit = {
  id: string | null;
  visible: boolean;
  centre: boolean;
  hitTag: string;
  inNavBand: boolean;
  centreY: number;
};
type FloatReading = {
  ball: Rect | null;
  ballHitsItself: boolean;
  ballTag: string;
  ballText: string;
  window: Rect | null;
  nav: Rect | null;
  dock: Rect | null;
  navClickable: Array<{ id: string; ok: boolean; hit: string }>;
  rows: Hit[];
};

const overlaps = (a: Rect, b: Rect) =>
  a.right > b.x + 1 && b.right > a.x + 1 && a.bottom > b.top + 1 && b.bottom > a.top + 1;

async function measureFloat(page: Page): Promise<FloatReading> {
  return page.evaluate(() => {
    const rectOf = (element: Element | null | undefined) => {
      if (!element) return null;
      const box = element.getBoundingClientRect();
      return {
        x: box.x,
        y: box.y,
        width: box.width,
        height: box.height,
        top: box.top,
        bottom: box.bottom,
        right: box.right,
      };
    };
    const nav = document.querySelector(".v8-mobile-nav");
    const dock = document.querySelector(".cn-copilot-dock");
    const ball = document.querySelector('[data-testid="sim-ball"]');
    const ballBox = ball ? ball.getBoundingClientRect() : null;
    const ballCentre = ballBox
      ? document.elementFromPoint(ballBox.x + ballBox.width / 2, ballBox.y + ballBox.height / 2)
      : null;
    const window = document.querySelector('[data-testid="sim-pop"]');
    const rows = [...document.querySelectorAll('[data-testid^="sim-action-"]')].map((element) => {
      const button = element as HTMLButtonElement;
      const box = button.getBoundingClientRect();
      /* The window is not in the document while closed, so a measured box here means a drawn row.
         No `details` predicate: that disclosure is gone, and a clause that can never be false is how
         a gate starts passing for free. */
      const shown = box.width > 1 && box.height > 1;
      const centreX = box.x + box.width / 2;
      const centreY = box.y + box.height / 2;
      const inViewport =
        centreX >= 0 && centreY >= 0 && centreX <= innerWidth && centreY <= innerHeight;
      const centre = document.elementFromPoint(centreX, centreY);
      return {
        id: button.getAttribute("data-testid"),
        visible: shown && inViewport,
        centre: centre === button || Boolean(centre && button.contains(centre)),
        hitTag: centre
          ? `${centre.tagName}.${centre.getAttribute("data-testid") ?? centre.className}`
          : "none",
        inNavBand: Boolean(nav && shown && box.bottom > nav.getBoundingClientRect().top + 1 && nav.getBoundingClientRect().bottom > box.top + 1),
        centreY: Math.round(centreY),
      };
    });
    const navItems = [...document.querySelectorAll(".v8-mobile-nav [data-testid^='nav-']")].map((item) => {
      const box = item.getBoundingClientRect();
      const hit = document.elementFromPoint(box.x + box.width / 2, box.y + box.height / 2);
      return {
        id: item.getAttribute("data-testid") ?? "?",
        ok: hit === item || Boolean(hit && item.contains(hit)),
        hit: hit ? `${hit.tagName}.${hit.getAttribute("data-testid") ?? hit.className}` : "none",
      };
    });
    return {
      ball: rectOf(ball),
      ballHitsItself: Boolean(ballCentre && ball && (ballCentre === ball || ball.contains(ballCentre))),
      ballTag: ballCentre ? `${ballCentre.tagName}.${ballCentre.getAttribute("data-testid") ?? ballCentre.className}` : "none",
      ballText: ball ? (ball as HTMLElement).innerText.replace(/\s+/g, " ").trim() : "",
      window: rectOf(window),
      nav: rectOf(nav),
      dock: rectOf(dock),
      navClickable: navItems,
      rows,
    };
  });
}

/* `window.scrollTo` alone is a no-op when a container is the scroller, which would let a "resting"
   reading inherit wherever the last pass left the page.  Walk every box that can scroll. */
const scrollEverywhere = (page: Page, where: "top" | "middle" | "bottom") =>
  page.evaluate((target) => {
    const boxes = [document.documentElement, document.body, ...document.querySelectorAll<HTMLElement>("*")];
    for (const box of boxes) {
      if (box.scrollHeight - box.clientHeight <= 1) continue;
      const max = box.scrollHeight - box.clientHeight;
      box.scrollTop = target === "top" ? 0 : target === "middle" ? max / 2 : max;
    }
    window.scrollTo(0, target === "top" ? 0 : target === "middle" ? innerHeight / 2 : document.body.scrollHeight);
  }, where);

test("sim-stage-actions-are-reachable-and-never-in-the-nav-band — 悬浮球不遮内容，展开后每行都可按、导航仍可点", async ({ page }) => {
  test.setTimeout(300_000);
  const NODE = "sim-stage-actions-are-reachable-and-never-in-the-nav-band";
  const seeded = await readScene(page);
  const journeyId = String(seeded.journey_id ?? "");
  const sceneMinute = String(seeded.effective_now ?? "").slice(11, 16);
  const readings: Record<string, unknown> = {
    seeded: { status: seeded.journey_status, effective_now: seeded.effective_now },
  };

  /* ①②④⑤⑦ -- the ball at rest, and the opened window, at 390 and 412 in both themes. */
  for (const width of [390, 412]) {
    for (const scheme of ["light", "dark"] as const) {
      const arm = `${width}-${scheme}`;
      await openToday(page, journeyId, "zh-CN", scheme, width);
      await expect(
        page.getByTestId("sim-ball"),
        node(NODE, `${arm}: the stage ball is not on screen at all`),
      ).toBeVisible();
      await expect
        .poll(() => page.getByTestId("sim-pop").count(), {
          timeout: 10_000,
          intervals: [250],
          message: node(NODE, `${arm}: the widget opens on its own, which is the "挡住屏幕" being complained about`),
        })
        .toBe(0);

      let atRest = await measureFloat(page);
      expect(
        atRest.ball && atRest.ball.width >= 44 && atRest.ball.height >= 44,
        node(NODE, `${arm}: the ball measures ${JSON.stringify(atRest.ball)}, under the 44px floor`),
      ).toBe(true);
      expect(
        atRest.ballHitsItself,
        node(NODE, `${arm}: the ball is on screen but its own tap lands on ${JSON.stringify(atRest.ballTag)}`),
      ).toBe(true);
      expect(
        atRest.ballText.length,
        node(NODE, `${arm}: a ball must carry a dot, not a sentence -- it reads ${JSON.stringify(atRest.ballText)}`),
      ).toBeLessThanOrEqual(2);
      if (atRest.nav && atRest.ball) {
        expect(
          overlaps(atRest.ball, atRest.nav),
          node(NODE, `${arm}: the ball sits in the nav's band: ball ${JSON.stringify(atRest.ball)} nav ${JSON.stringify(atRest.nav)}`),
        ).toBe(false);
      }
      if (atRest.dock && atRest.ball) {
        expect(
          overlaps(atRest.ball, atRest.dock),
          node(NODE, `${arm}: the ball covers the Copilot pill: ball ${JSON.stringify(atRest.ball)} dock ${JSON.stringify(atRest.dock)}`),
        ).toBe(false);
      }

      /* ⑥ without opening anything: the dot says only "stage / no stage", so the words have to be in
            the accessible name, and they are the same words the window shows. */
      const declared = await stageDeclaration(page);
      expect(
        declared,
        node(NODE, `${arm}: the ball does not say this is a teaching simulation: ${JSON.stringify(declared)}`),
      ).toContain("模拟");
      expect(
        declared,
        node(NODE, `${arm}: the ball does not say the server supplies the time: ${JSON.stringify(declared)}`),
      ).toContain("服务器");
      expect(
        declared,
        node(NODE, `${arm}: the ball omits the server's own scene minute (${JSON.stringify(seeded.effective_now)}): ${JSON.stringify(declared)}`),
      ).toContain(sceneMinute);
      expect(
        declared,
        node(NODE, `${arm}: a flag name reached the traveller-facing line: ${JSON.stringify(declared)}`),
      ).not.toContain("demo_mode");

      /* ① "列表滚动时保持悬浮": the ball belongs to the viewport, so scrolling must not move it. */
      for (const where of ["middle", "bottom", "top"] as const) {
        await scrollEverywhere(page, where);
        const scrolled = await measureFloat(page);
        expect(
          scrolled.ball,
          node(NODE, `${arm} at ${where}: the ball vanished from the screen once the page scrolled`),
        ).not.toBeNull();
        expect(
          Math.abs((scrolled.ball as Rect).y - (atRest.ball as Rect).y) < 1 &&
            Math.abs((scrolled.ball as Rect).x - (atRest.ball as Rect).x) < 1,
          node(NODE, `${arm} at ${where}: the ball moved with the page (${JSON.stringify((atRest.ball as Rect).y)} -> ${JSON.stringify((scrolled.ball as Rect).y)}), so it is not floating`),
        ).toBe(true);
        expect(
          scrolled.rows.filter((item) => item.visible).length,
          node(NODE, `${arm} at ${where}: ${scrolled.rows.filter((item) => item.visible).length} action rows are drawn while the window is closed`),
        ).toBe(0);
        readings[`${arm}-closed-${where}`] = scrolled.ball;
      }

      /* ② the opened window: its own size budget, its own scroll, and nobody else's control covered. */
      await openStageEntry(page, `${arm}: the geometry pass`);
      await scrollEverywhere(page, "top");
      const open = await measureFloat(page);
      expect(
        open.window,
        node(NODE, `${arm}: the window was opened and is not measurable`),
      ).not.toBeNull();
      const box = open.window as Rect;
      expect(
        box.width <= width - 24 + 1,
        node(NODE, `${arm}: the window is ${box.width}px wide at ${width}px (budget: width - 24)`),
      ).toBe(true);
      expect(
        box.height <= 844 * 0.6 + 1,
        node(NODE, `${arm}: the window is ${box.height}px tall (budget: 60% of 844)`),
      ).toBe(true);
      if (open.nav) {
        expect(
          overlaps(box, open.nav),
          node(NODE, `${arm}: the open window covers the bottom navigation: window ${JSON.stringify(box)} nav ${JSON.stringify(open.nav)}`),
        ).toBe(false);
      }
      if (open.dock) {
        expect(
          overlaps(box, open.dock),
          node(NODE, `${arm}: the open window covers the Copilot pill: window ${JSON.stringify(box)} dock ${JSON.stringify(open.dock)}`),
        ).toBe(false);
      }
      expect(
        open.navClickable.filter((item) => !item.ok),
        node(NODE, `${arm}: with the window open these nav items cannot be tapped: ${JSON.stringify(open.navClickable)}`),
      ).toEqual([]);

      /* ②⑦ inside the window: every row must come up to a position where its own centre takes the
            tap and where it is out of the band -- "the window is small" is not an excuse. */
      const ids = open.rows.map((item) => item.id).filter(Boolean) as string[];
      expect(
        ids.length,
        node(NODE, `${arm}: the opened window drew ${ids.length} action rows; the stage has 11`),
      ).toBeGreaterThanOrEqual(9);
      const perRow: Record<string, unknown> = {};
      for (const id of ids) {
        const row = page.getByTestId(id);
        await row.scrollIntoViewIfNeeded();
        const mine = (await measureFloat(page)).rows.find((item) => item.id === id);
        expect(
          mine?.visible,
          node(NODE, `${arm}: ${id} can never be brought on screen inside the window: ${JSON.stringify(mine)}`),
        ).toBe(true);
        expect(
          mine?.centre,
          node(NODE, `${arm}: ${id} is visible but its tap goes to ${JSON.stringify(mine?.hitTag)}: ${JSON.stringify(mine)}`),
        ).toBe(true);
        expect(
          mine?.inNavBand,
          node(NODE, `${arm}: ${id} is still inside the nav band: ${JSON.stringify(mine)}`),
        ).toBe(false);
        perRow[id] = mine;
      }
      readings[`${arm}-open`] = { ball: open.ball, window: box, nav: open.nav, dock: open.dock, perRow };
      /* The claim being made here is visual ("别把屏幕挡住"), so it is filed as pictures at the same size
         the numbers were measured on, viewport rather than full page: the widget belongs to the
         viewport, not to the document. */
      /* ② "内部自己滚动" is a finger fact, not a Playwright one.  The row loop above scrolls with
         `scrollIntoViewIfNeeded`, and a browser will scroll an `overflow: hidden` box for that call too
         -- which is exactly how `killD6-window-body-cannot-be-scoped` survived its first run.  So the
         window's own body has to move under a real wheel event. */
      const body = page.getByTestId("sim-pop-body");
      await body.evaluate((element) => {
        element.scrollTop = 0;
      });
      const bodyBox = await body.boundingBox();
      expect(
        bodyBox,
        node(NODE, `${arm}: the window's scroll body has no box to aim a wheel at`),
      ).not.toBeNull();
      await page.mouse.move(
        (bodyBox as Rect).x + (bodyBox as Rect).width / 2,
        (bodyBox as Rect).y + Math.min(120, (bodyBox as Rect).height / 2),
      );
      await page.mouse.wheel(0, 320);
      await expect
        .poll(() => body.evaluate((element) => element.scrollTop), {
          timeout: 5_000,
          intervals: [150],
          message: node(NODE, `${arm}: a wheel over the window does not scroll its own body, so the rows below the fold belong to the test, not to the traveller`),
        })
        .toBeGreaterThan(0);
      /* The row loop above leaves the window scrolled to its last row; a picture of that is not
         evidence of what the widget looks like when a traveller opens it. */
      await page
        .getByTestId("sim-pop-body")
        .evaluate((element) => {
          element.scrollTop = 0;
        });
      await page.screenshot({
        path: evidencePath(`ui-overnight/stage-float-${arm}-open.png`),
      });
      await page.getByTestId("sim-close").click();
      await expect
        .poll(() => page.getByTestId("sim-pop").count(), {
          timeout: 10_000,
          intervals: [250],
          message: node(NODE, `${arm}: the window's own close control did not close it`),
        })
        .toBe(0);
      await page.screenshot({
        path: evidencePath(`ui-overnight/stage-float-${arm}-closed.png`),
      });
    }
  }

  /* ③ the three other ways back out, in the language the traveller is reading. */
  await openToday(page, journeyId, "zh-CN", "light", 390);
  await openStageEntry(page, "the closing pass");
  await page.getByTestId("sim-ball").click();
  await expect
    .poll(() => page.getByTestId("sim-pop").count(), { timeout: 10_000, intervals: [250] })
    .toBe(0);
  await openStageEntry(page, "the escape pass");
  await page.keyboard.press("Escape");
  await expect
    .poll(() => page.getByTestId("sim-pop").count(), {
      timeout: 10_000,
      intervals: [250],
      message: node(NODE, "Escape left the window open, so the keyboard traveller is trapped in it"),
    })
    .toBe(0);
  await openStageEntry(page, "the outside-tap pass");
  await page.mouse.click(10, 200);
  await expect
    .poll(() => page.getByTestId("sim-pop").count(), {
      timeout: 10_000,
      intervals: [250],
      message: node(NODE, "tapping outside left the window open"),
    })
    .toBe(0);

  /* ⑦ the English arm gets the same contract, at least once: the ball's name and the ESC exit. */
  await openToday(page, journeyId, "en", "dark", 412);
  await openStageEntry(page, "the English arm");
  const english = await stageWindowDeclaration(page);
  expect(
    english,
    node(NODE, `the English window does not state the server's clock: ${JSON.stringify(english)}`),
  ).toMatch(/server/i);
  expect(
    english,
    node(NODE, `the English window leaks a flag name: ${JSON.stringify(english)}`),
  ).not.toContain("demo_mode");
  await page.keyboard.press("Escape");
  await expect
    .poll(() => page.getByTestId("sim-pop").count(), { timeout: 10_000, intervals: [250] })
    .toBe(0);

  writeFileSync(
    evidencePath("ui-overnight/sim-action-hittest.json"),
    JSON.stringify({ generatedBy: "e345b9d6", order: "ORD-0085", node: NODE, readings }, null, 2) + "\n",
    "utf-8",
  );
});



/* ----------------------------------------------------------------- ORD-0082 (b): no proposal, no button.
 * A remembered local id left 接受/拒绝 pressable while `GET /replans` answers [], so the tap did
 * nothing at all.  The row's availability now comes from that list, and its reason names the server.
 */
test("sim-replan-actions-follow-the-server-list — 没有方案就不许点", async ({ page }) => {
  test.setTimeout(240_000);
  const seeded = await readScene(page);
  const journeyId = String(seeded.journey_id ?? "");
  await openToday(page, journeyId, "zh-CN", "light", 390);
  const listed = await page.request.get(`/api/v1/journeys/${journeyId}/replans`);
  expect(listed.ok(), node("sim-replan-actions-follow-the-server-list", `GET /replans answered ${listed.status()}`)).toBe(true);
  const proposals = (await listed.json()) as Array<{ status?: string }>;
  const open = proposals.filter((item) => !["ACCEPTED", "REJECTED", "DECLINED", "SUPERSEDED"].includes(String(item.status ?? "").toUpperCase()));
  await openStageEntry(page, "the replan rows");
  for (const action of ["accept", "reject"]) {
    const row = page.getByTestId(`sim-action-${action}`);
    await row.scrollIntoViewIfNeeded();
    const disabled = await row.getAttribute("aria-disabled");
    if (open.length === 0) {
      expect(
        disabled,
        node("sim-replan-actions-follow-the-server-list",
          `the server lists ${proposals.length} proposals (none open) yet ${action} is pressable -- that tap cannot do anything`),
      ).toBe("true");
      const reasonId = await row.getAttribute("aria-describedby");
      expect(reasonId, node("sim-replan-actions-follow-the-server-list", `${action} is blocked without pointing at a reason`)).not.toBeNull();
      expect(
        clean(await page.locator(`#${reasonId}`).innerText()),
        node("sim-replan-actions-follow-the-server-list",
          `${action}'s reason does not say the server gave no proposal`),
      ).toContain("服务器还没有给出方案");
    } else {
      expect(disabled, node("sim-replan-actions-follow-the-server-list", `${action} blocked although the server lists an open proposal`)).toBeNull();
    }
  }
});

/* ------------------------------------------------------------- ORD-0082 (a): the hero's own small line. */
test("today-hero-meta-does-not-contradict-the-sequence — “暂无安排”要真的是没有", async ({ page }) => {
  test.setTimeout(240_000);
  const seeded = await readScene(page);
  const journeyId = String(seeded.journey_id ?? "");
  await openToday(page, journeyId, "zh-CN", "light", 390);
  const stage = await readStage(page, journeyId);
  if (!stage?.next) {
    test.skip(true, "the server reports no next stop, so there is no claim to check");
  }
  const later = stage
    ? stage.ordered.filter(
        (item) =>
          (stage.next as { sequence_no: number }).sequence_no < item.sequence_no &&
          !["COMPLETED", "SKIPPED", "CANCELLED"].includes(item.status),
      ).length
    : 0;
  const meta = clean(await page.locator('[data-testid="today-next"] small').first().innerText().catch(() => ""));
  if (later > 0) {
    expect(
      /暂无安排|Nothing scheduled/.test(meta),
      node("today-hero-meta-does-not-contradict-the-sequence",
        `the server has ${later} further stop(s) after the advertised one, yet the hero says ${JSON.stringify(meta)}`),
    ).toBe(false);
    /* Two different true sentences can appear here: a calendar-day count ("今天还有 3 项安排") and a
       remaining-stops count ("后面还有 7 站").  Only the second one is checkable against the
       sequence, and the thing that must never appear is a claim that nothing is left. */
    const remaining = meta.match(/后面还有 (\d+) 站/);
    if (remaining) {
      expect(
        Number(remaining[1]),
        node("today-hero-meta-does-not-contradict-the-sequence",
          `the hero says ${remaining[1]} stops remain, the server's sequence says ${later}: ${JSON.stringify(meta)}`),
      ).toBe(later);
    }
  }
  writeFileSync(
    evidencePath("ui-overnight/hero-meta.json"),
    JSON.stringify({ generatedBy: "e345b9d6", order: "ORD-0082", node: "today-hero-meta-does-not-contradict-the-sequence", later, meta, next: stage?.next?.title ?? null }, null, 2) + "\n",
    "utf-8",
  );
});

/* --------------------------------------------------------------------- ORD-0086: a wait you can see,
 * and a refusal that does not outlive the reading it was about.
 * E measured this with CDP-injected 1.5s round trips: press 触发一次中断 while the stage read is
 * still coming in and the panel says "还在读服务器的场景状态", then lift the throttle, watch the
 * read answer 200 -- and the sentence stays until a reload.  A teacher with weak signal presses
 * once and concludes the console is broken.
 * A held route is the same user-visible condition with a fixed clock, so these nodes assert the
 * lifecycle rather than racing a machine's speed.
 */
test("sim-action-in-flight-is-perceivable — 按下去要看得出在跑", async ({ page }) => {
  test.setTimeout(240_000);
  const seeded = await readScene(page);
  const journeyId = String(seeded.journey_id ?? "");
  await openToday(page, journeyId, "zh-CN", "light", 390);

  let release: () => void = () => {};
  const held = new Promise<void>((resolve) => {
    release = resolve;
  });
  await page.route(`**/api/v1/journeys/${journeyId}/events`, async (route) => {
    await held;
    await route.continue();
  });

  await openStageEntry(page, "the in-flight signal");
  const row = page.getByTestId("sim-action-event");
  const blocked = await row.getAttribute("aria-describedby");
  if (blocked) {
    // Not this fixture's job to force: the row answers for a reason, and that reason is asserted
    // by the node below.  Say which reason it was rather than silently passing.
    test.skip(true, `the disruption row is blocked before the wait can be measured: ${JSON.stringify(clean(await page.locator(`#${blocked}`).innerText()))}`);
  }
  await row.click();
  await expect(
    row,
    node("sim-action-in-flight-is-perceivable", "the pressed action gives no busy signal while its request is held"),
  ).toHaveAttribute("aria-busy", "true", { timeout: 5_000 });
  expect(
    clean(await row.innerText()),
    node("sim-action-in-flight-is-perceivable", "the pressed action's own label does not say it is running"),
  ).toContain("正在执行");
  release();
  await expect(
    page.getByTestId("sim-outcome"),
    node("sim-action-in-flight-is-perceivable", "the held request never produced an answer to read"),
  ).toBeVisible({ timeout: 60_000 });
  await expect(row).not.toHaveAttribute("aria-busy", "true");
});

test("sim-refusal-does-not-outlive-the-reading — “还在读”不能读完还挂着", async ({ page }) => {
  test.setTimeout(240_000);
  const t0 = Date.now();
  const mark = (label: string) => console.log(`[refusal-node +${Date.now() - t0}ms] ${label}`);
  const seeded = await readScene(page);
  const journeyId = String(seeded.journey_id ?? "");
  mark("scene id read");

  let release: () => void = () => {};
  const held = new Promise<void>((resolve) => {
    release = resolve;
  });
  await page.route("**/api/v1/demo/scene", async (route) => {
    await held;
    await route.continue();
  });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.addInitScript(
    ([id]) => {
      localStorage.clear();
      localStorage.setItem("citynexus.v8.journey_id", id as string);
      localStorage.setItem("citynexus.locale", "zh-CN");
    },
    [journeyId],
  );
  mark("route held, navigating");
  await page.goto("/v8/hub", { waitUntil: "load" });
  mark("goto resolved");
  await expect(page.getByTestId("today-hero")).toBeVisible({ timeout: 30_000 });
  mark("hero visible");
  await openStageEntry(page, "the refusal lifecycle");

  const row = page.getByTestId("sim-action-event");
  await row.scrollIntoViewIfNeeded();
  mark("row scrolled into view");
  expect(
    await row.getAttribute("aria-disabled"),
    node("sim-refusal-does-not-outlive-the-reading", "the stage read is held, yet the row claims it is ready"),
  ).toBe("true");
  mark("row reported blocked");
  /* A real finger does not wait for a control to become enabled -- that is the whole point of the
     甲 design this node measures (a blocked row must speak its reason when it is activated).
     `click()` without `force` waits for "enabled" and aria-disabled counts, so it would hang here
     and never reach the sentence under test. */
  await row.click({ force: true });
  const outcome = page.getByTestId("sim-outcome");
  mark("row pressed");
  await expect(
    outcome,
    node("sim-refusal-does-not-outlive-the-reading", "pressing a blocked row answered with no sentence at all"),
  ).toBeVisible({ timeout: 10_000 });
  const refusal = clean(await outcome.innerText());
  mark(`refusal on screen: ${JSON.stringify(refusal.slice(0, 60))}`);
  expect(
    refusal,
    node("sim-refusal-does-not-outlive-the-reading", `the refusal does not say it is about a reading: ${JSON.stringify(refusal)}`),
  ).toContain("还在读服务器的场景状态");
  expect(
    await outcome.getAttribute("data-transient"),
    node("sim-refusal-does-not-outlive-the-reading", "a refusal about a missing reading is not marked transient, so nothing can retire it"),
  ).toBe("true");

  release();
  mark("read released");
  await expect(
    page.getByTestId("sim-banner"),
    node("sim-refusal-does-not-outlive-the-reading", "the held scene read never landed, so this node measured nothing"),
  ).toHaveAttribute("data-scene-phase", "ready", { timeout: 30_000 });
  mark("banner ready");
  /* The point of the order: the recovery is the reading arriving, not the traveller leaving and
     coming back.  Counted through `evaluate` rather than the locator, because the first version of
     this node hung for the whole test budget on a screen that had already retired the sentence: if
     the page cannot answer this either, the renderer is wedged and that is a bigger finding. */
  const outcomeCount = () =>
    page.evaluate(() => document.querySelectorAll('[data-testid="sim-outcome"]').length);
  await expect
    .poll(outcomeCount, { timeout: 20_000, intervals: [500] })
    .toBe(0);
  mark("refusal retired");
});

/* A single readable pose can only show one side of a contradiction. The node above checks the pair
   the fixture happens to produce; a mutant that pinned the shared predicate to `false` survived it,
   because that trip *is* placeable. So force the other condition: strip every coordinate and every
   route geometry out of the journey read, and require both halves of the screen to agree. */
test("today-attention-agrees-with-the-map-when-nothing-can-be-placed — 无坐标时两屏同一句话", async ({ page }) => {
  test.setTimeout(240_000);
  const NODE = "today-attention-agrees-with-the-map-when-nothing-can-be-placed";
  const seeded = await readScene(page);
  const journeyId = String(seeded.journey_id ?? "");
  expect(
    journeyId.length > 0,
    node(NODE, "no journey to strip coordinates from"),
  ).toBe(true);
  await page.route(`**/api/v1/journeys/${journeyId}/experience`, async (route) => {
    const response = await route.fetch();
    const body = (await response.json()) as Record<string, unknown>;
    const plan = body?.active_plan as
      | {
          activities?: Array<Record<string, unknown>>;
          legs?: Array<Record<string, unknown>>;
          disruptions?: unknown[];
        }
      | undefined;
    for (const activity of plan?.activities ?? []) {
      activity.metadata = {};
    }
    /* The map can place a trip from route geometry alone, so the geometry has to go too -- otherwise
       this arm draws a map and measures nothing. */
    for (const leg of plan?.legs ?? []) {
      leg.geometry = { type: "Feature", geometry: { type: "LineString", coordinates: [] } };
    }
    /* Strip the problems that would otherwise fill the band: with a disruption on the journey the
       attention line has something *else* to say and never faces the choice under test, which is how
       the first pass of this node let the mutant through. */
    if (plan) plan.disruptions = [];
    body.offers = [];
    await route.fulfill({ status: response.status(), contentType: "application/json", body: JSON.stringify(body) });
  });
  await page.addInitScript(
    ([id]) => {
      localStorage.clear();
      localStorage.setItem("citynexus.v8.journey_id", id as string);
      localStorage.setItem("citynexus.locale", "zh-CN");
    },
    [journeyId],
  );
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/v8/hub", { waitUntil: "load" });
  await expect(page.getByTestId("today-hero")).toBeVisible({ timeout: 30_000 });

  await expect(
    page.getByTestId("v8-map-empty"),
    node(NODE, "a journey with no coordinates and no route geometry should draw the map's honest empty state"),
  ).toBeVisible({ timeout: 30_000 });
  const mapSaid = clean(await page.getByTestId("v8-map-empty").innerText());
  const attention = clean(await page.getByTestId("today-attention").innerText());
  expect(
    mapSaid,
    node(NODE, `the map changed its wording for this case: ${JSON.stringify(mapSaid)}`),
  ).toContain("这个行程还没有可信的坐标");
  expect(
    attention,
    node(NODE, `the map says the trip cannot be placed while attention says ${JSON.stringify(attention)} -- one screen, two answers`),
  ).toContain("这个行程还没有可信的坐标");
  expect(
    /一切正常|All clear/i.test(attention),
    node(NODE, `attention declares all clear beside an unplaceable trip: ${JSON.stringify(attention)}`),
  ).toBe(false);
  writeFileSync(
    evidencePath("ui-overnight/today-attention-map-unplaceable.json"),
    JSON.stringify({ generatedBy: "e345b9d6", order: "ORD-0082", node: NODE, mapSaid, attention }, null, 2) + "\n",
    "utf-8",
  );
});

/* ------------------------------------------------- ORD-0079's four evidence states, on the panel.
 * `924461e` added `FROZEN_WITHOUT_TTL`: 56 sealed pairs and no expiry. Drawn as "no data", the
 * traveller is told the trip has no travel data by a screen whose own server says it has plenty, so
 * the state gets its own words and this node holds it to them -- with the envelope stubbed, because
 * a seeded stage does not sit in that state on demand.
 */
test("sim-evidence-state-says-what-is-sealed — 冻着但没到期不许读成没数据", async ({ page }) => {
  test.setTimeout(180_000);
  const NODE = "sim-evidence-state-says-what-is-sealed";
  const seeded = await readScene(page);
  await page.route("**/api/v1/demo/scene", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        demo_mode: true,
        journey_id: seeded.journey_id,
        journey_status: "PLANNED",
        current_activity_id: null,
        scene_start_at: "2026-10-09T18:00:00+08:00",
        scene_end_at: "2026-10-11T15:00:00+08:00",
        effective_now: "2026-10-10T12:00:00+08:00",
        basis: "JOURNEY_START",
        evidence_expires_at: null,
        evidence_state: "FROZEN_WITHOUT_TTL",
        evidence_snapshot_id: "snapshot-stub",
        evidence_reference_consistent: true,
        mobility_legs_total: 5,
        mobility_legs_with_evidence: 5,
        plan_version_id: "11111111-1111-4111-8111-111111111111",
      }),
    }),
  );
  await page.setViewportSize({ width: 390, height: 844 });
  await page.addInitScript(
    ([id]) => {
      localStorage.clear();
      localStorage.setItem("citynexus.v8.journey_id", id as string);
      localStorage.setItem("citynexus.locale", "zh-CN");
    },
    [String(seeded.journey_id ?? "")],
  );
  await page.goto("/v8/hub", { waitUntil: "load" });
  await openStageEntry(page, NODE);
  const facts = page.getByTestId("sim-scene-facts");
  await expect(facts).toBeVisible({ timeout: 30_000 });
  const said = clean(await page.getByTestId("sim-evidence").innerText());
  expect(
    said,
    node(NODE, `FROZEN_WITHOUT_TTL is drawn as ${JSON.stringify(said)}`),
  ).toContain("封存的");
  expect(
    /没有冻结证据|没有数据|no frozen evidence|no data/i.test(said),
    node(NODE, `a sealed state is reported as missing data: ${JSON.stringify(said)}`),
  ).toBe(false);
  expect(
    said,
    node(NODE, `the missing expiry is not stated: ${JSON.stringify(said)}`),
  ).toContain("没有到期时间");
});

/* ------------------------------------------------------- ORD-0085 fallout, routed as its own gate.
 * While measuring the sheet's clearance for ORD-0085 this was found: at 390x844 the shell reserves
 * 63px for the fixed nav (`--cn-nav-clearance` -> `--cn-nav-h` = item 48 + 8 + 7) while the bar
 * actually renders 76px (its single auto row is 60).  Every page's bottom padding is built from that
 * token, so the last ~13px of any phone screen can sit under the nav at the end of the document --
 * which is the same family of defect as the panel's overlap band, in the app's shared geometry
 * rather than in this panel.  It is stated here as its own red so the shared number gets fixed by
 * whoever owns it, and so ORD-0085 is not scored on a criterion it does not control.
 */
test("nav-reservation-covers-the-rendered-bar — 预留高度不许比导航条本身矮", async ({ page }) => {
  test.setTimeout(180_000);
  const seeded = await readScene(page);
  await openToday(page, String(seeded.journey_id ?? ""), "zh-CN", "light", 390);
  const reading = await page.evaluate(() => {
    const nav = document.querySelector<HTMLElement>(".v8-mobile-nav");
    const shell = document.querySelector<HTMLElement>(".v8-product-shell");
    if (!nav || !shell) return null;
    return {
      reserved: parseFloat(getComputedStyle(shell).paddingBottom),
      navHeight: Math.round(nav.getBoundingClientRect().height),
      rows: getComputedStyle(nav).gridTemplateRows,
      token: getComputedStyle(document.documentElement).getPropertyValue("--cn-nav-h").trim(),
    };
  });
  writeFileSync(
    evidencePath("ui-overnight/nav-reservation.json"),
    JSON.stringify({ generatedBy: "e345b9d6", order: "ORD-0085", node: "nav-reservation-covers-the-rendered-bar", reading }, null, 2) + "\n",
    "utf-8",
  );
  expect(
    reading && reading.reserved >= reading.navHeight,
    node("nav-reservation-covers-the-rendered-bar",
      `the shell reserves ${JSON.stringify(reading?.reserved)}px for a nav that renders ${JSON.stringify(reading?.navHeight)}px (grid row ${JSON.stringify(reading?.rows)}, --cn-nav-h ${JSON.stringify(reading?.token)}): the last ~${JSON.stringify((reading?.navHeight ?? 0) - (reading?.reserved ?? 0))}px of every phone page can sit under the bar`),
  ).toBe(true);
});
