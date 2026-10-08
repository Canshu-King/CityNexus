import { expect, test, type Page } from "@playwright/test";
import { execFileSync } from "node:child_process";
import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { MAP_LABEL_FORBIDDEN, MAP_LABEL_SCOPE, mapLabelSpanViolations, mapLabelViolations, takeOffGlass } from "./_mapLabelRules";
import { stopLabel } from "../src/lib/mapStopLabels";
import { mapCopy } from "../src/i18n/mapPanelCopy";
import { evidencePath } from "./_qoderEvidence";

/**
 * ORD-0415 — the map's forbidden classes are now decided before the word is painted, and that is measurable.
 *
 * r1 of this order measured the absence of a wire: `e2e/_mapLabelRules.ts` held four classes (a clock,
 * a duration, a price, a provider/source string) and no product module consulted them. The reason that
 * went unnoticed is that the acceptance data is clean — every seeded activity title already passes the
 * list, so a hit-count on the seed reads zero whether the rule is applied or not. This file therefore
 * carries its own fixture (see `review/map-label-wiring-r1/stop_rename_fixture_r1.py` for why the write
 * is a store write and not an API call) and reports which case landed, so a zero is never the seed's
 * doing.
 *
 * What each arm answers, one question per arm:
 *   cut-is-subtractive        — `takeOffGlass()` removes the matched span and keeps the rest of the
 *                               server's word verbatim; it never rewords, never substitutes, and a clean
 *                               word comes back byte-equal with nothing removed.
 *   word-with-nothing-left    — a name that is ONLY a forbidden class yields no paintable word, which is
 *                               what `stopLabel()` then has to honour (no chip, not an invented name).
 *   fixture-lands-in-payload  — the six case strings really do arrive from the server on this screen:
 *                               read out of the responses this page received, not from the DOM I judge.
 *   glass-carries-no-class    — every label string the glass renders (chips with a box, plus each pin's
 *                               accessible name, which is the corpus the accepted ORD-0403/0412 gates
 *                               already read) passes the shared list; and the cut words are ON the glass,
 *                               so "no hits" is not "no labels".
 *   whole-word-stops-keep-pin — the stop whose entire word is forbidden keeps a pickable pin and an
 *                               accessible name that is not the forbidden word.
 *   attribution-still-reads   — ORD-0412's obligation survives the wiring: the basemap sentence is
 *                               rendered, byte-equal to the authored copy, and outside the judged corpus.
 *                               The negative control is recorded: fed to the same list it DOES raise
 *                               `source`, which is why the scope has to stay as narrow as it is.
 *
 * Both readings this order asks for come from running THIS file on two sets of product bytes: at the
 * tip before the wiring the `glass-carries-no-class` arm is red and its evidence names how many rendered
 * strings carry a class; at the candidate it is green with none, and `attribution-still-reads` is green
 * in both. The numbers, the sha of each side and the interpreter are in `review/map-label-wiring-r1/`.
 */

const FILE = "e2e/qoder-map-ord0415-forbidden-off-the-glass.spec.ts";
const LABEL_SELECTOR = ".v8-map-panel [data-testid='v8-map-stop-label']";
const PIN_SELECTOR = ".v8-map-panel .v9-map-marker";
const ATTRIBUTION_SELECTOR = "[data-testid='v8-map-attribution']";
const FIXTURE = "../review/map-label-wiring-r1/stop_rename_fixture_r1.py";

/** The six words the fixture puts on the plan, with what the rule says is left of each. */
const CASES = [
  { case: "whole_word_is_a_clock", painted: "19:30", keeps: null, must_lose: "clock-time" },
  { case: "clock_inside_word", painted: "天津之眼 19:30 摩天轮", keeps: "天津之眼 摩天轮", must_lose: "clock-time" },
  { case: "money_inside_word", painted: "瓷房子 门票 ¥60", keeps: "瓷房子 门票", must_lose: "money" },
  { case: "duration_inside_word", painted: "五大道 45 分钟 骑行", keeps: "五大道 骑行", must_lose: "duration" },
  { case: "source_inside_word", painted: "海河 © 游船码头", keeps: "海河 游船码头", must_lose: "source" },
  { case: "clean_control", painted: "古文化街牌坊", keeps: "古文化街牌坊", must_lose: null },
] as const;

const push = (arm: string, body: Record<string, unknown>) => {
  const target = evidencePath("ord0415-wiring", `reading_${arm}.json`);
  writeFileSync(target, JSON.stringify({ file: FILE, arm, ...body }, null, 1), "utf-8");
  console.log(`${FILE} :: ${arm} — ${JSON.stringify(body)}`);
};

const node = (arm: string, detail: string) => `${FILE} :: ${arm} — ${detail}`;

/** The sqlite file this run owns, and the interpreter that may write it. Authoritative mode requires
 *  both (`playwrightEnv.ts`), so nothing here borrows another lane's database.
 *  Three slashes, the same way `playwrightEnv.ts` reads it back: `sqlite:///D:/…` is a Windows absolute
 *  path with its own leading slash, and stripping two gives `/D:/…`, which `existsSync` answers false
 *  for -- a parse bug that reads as "this run has no database". */
const databasePath = (): string => {
  const url = process.env.CITYNEXUS_DATABASE_URL ?? "";
  return url.startsWith("sqlite:///") ? url.replace(/^sqlite:\/\/\//, "") : "";
};

const runFixture = (mode: "--apply" | "--revert" | "--read", journeyId?: string): Record<string, unknown> => {
  const python = process.env.CITYNEXUS_PYTHON ?? "";
  const db = databasePath();
  expect(python.length, node("fixture", "CITYNEXUS_PYTHON must name the interpreter that writes this run's own database")).toBeGreaterThan(0);
  expect(existsSync(db), node("fixture", `this run's database is not on disk: ${db}`)).toBe(true);
  const args = [FIXTURE, "--db", db, mode];
  if (journeyId) args.push("--journey", journeyId);
  const out = execFileSync(python, args, { encoding: "utf-8", maxBuffer: 8 * 1024 * 1024 });
  const first = out.split("\n").filter((line) => line.trim().startsWith("{"))[0] ?? "{}";
  return JSON.parse(first) as Record<string, unknown>;
};

async function enterMap(page: Page): Promise<void> {
  await page.goto("/v8/map", { waitUntil: "load", timeout: 90_000 });
  await expect(page.getByTestId("v8-maplibre-panel").first()).toBeVisible({ timeout: 25_000 });
  await page.waitForTimeout(1_800);
}

/** The glass, as the accepted map gates read it: chips that actually render, and each pin's name. */
const readGlass = (page: Page) =>
  page.evaluate(
    ({ labelSelector, pinSelector, attributionSelector }: { labelSelector: string; pinSelector: string; attributionSelector: string }) => {
      const chips = Array.from(document.querySelectorAll<HTMLElement>(labelSelector)).map((el) => {
        const box = el.getBoundingClientRect();
        const style = getComputedStyle(el);
        return {
          ordinal: el.getAttribute("data-stop-ordinal") ?? "",
          text: (el.textContent ?? "").trim(),
          source: el.getAttribute("data-name-source"),
          removed: el.getAttribute("data-forbidden-removed"),
          placement: el.getAttribute("data-placement"),
          /* Rendered, not merely present: `map-stop-labels.css` hides a name by clipping it, so a node
             in the document is not evidence an eye can read it. */
          rendered: style.visibility === "visible" && style.display !== "none" && box.width > 0 && box.height > 0,
          box: { w: Math.round(box.width), h: Math.round(box.height) },
        };
      });
      const pins = Array.from(document.querySelectorAll<HTMLElement>(pinSelector)).map((el) => {
        const box = el.getBoundingClientRect();
        return {
          painted: (el.textContent ?? "").trim(),
          aria: el.getAttribute("aria-label") ?? "",
          role: el.getAttribute("role") ?? "",
          rendered: box.width > 0 && box.height > 0,
        };
      });
      const attribution = document.querySelector<HTMLElement>(attributionSelector);
      const attributionBox = attribution?.getBoundingClientRect();
      return {
        chips,
        renderedChips: chips.filter((chip) => chip.rendered),
        pins,
        renderedPins: pins.filter((pin) => pin.rendered),
        attributionText: (attribution?.innerText ?? "").trim(),
        attributionRendered: !!attributionBox && attributionBox.width > 0 && attributionBox.height > 0,
        attributionBox: attributionBox ? { w: Math.round(attributionBox.width), h: Math.round(attributionBox.height) } : null,
      };
    },
    { labelSelector: LABEL_SELECTOR, pinSelector: PIN_SELECTOR, attributionSelector: ATTRIBUTION_SELECTOR },
  );

/** Every string the glass carries for a stop: a rendered word beside a pin, plus what the pin announces. */
const judgedStrings = (glass: Awaited<ReturnType<typeof readGlass>>) => [
  ...glass.renderedChips.map((chip) => chip.text),
  ...glass.renderedPins.map((pin) => pin.aria),
];

/** Two judges, both reported, never one folded into the other: `mapLabelViolations` is the list the
 *  four accepted gates judge with, and `mapLabelSpanViolations` is as wide as the cut the product
 *  makes. They disagree on `duration` (the accepted pattern cannot reach a Chinese label, measured in
 *  `review/map-label-wiring-r1/`) and a single number would hide which one is being claimed. */
const countHits = (strings: string[]) => {
  const rows = strings.map((text) => ({
    text,
    accepted_classes: mapLabelViolations(text),
    span_classes: mapLabelSpanViolations(text),
  }));
  return {
    accepted: rows.filter((row) => row.accepted_classes.length > 0),
    span: rows.filter((row) => row.span_classes.length > 0),
  };
};

test.describe("ORD-0415 forbidden classes off the map glass", () => {
  test("cut-is-subtractive — the cut removes what the list names and keeps the rest of the word", async () => {
    const rows = CASES.map((item) => {
      const cut = takeOffGlass(item.painted);
      return {
        case: item.case,
        painted: item.painted,
        text: cut.text,
        removed: cut.removed,
        violations_after_cut: mapLabelViolations(cut.text),
        span_violations_after_cut: mapLabelSpanViolations(cut.text),
        /* Would the ORIGINAL word have been flagged by each judge? Recorded per case so the gap between
           the two is this run's measurement, not my reading of a regex. */
        accepted_before_cut: mapLabelViolations(item.painted),
        span_before_cut: mapLabelSpanViolations(item.painted),
      };
    });
    push("cut-is-subtractive", {
      rows,
      forbidden_classes: MAP_LABEL_FORBIDDEN.map((rule) => rule.name),
      /* The classes the accepted judge cannot see on a Chinese word while the cut removes them:
         the reason this gate reports a span-judged hit count next to the accepted one. */
      judges_disagree_on: rows.filter((row) => row.span_before_cut.length !== row.accepted_before_cut.length)
        .map((row) => ({ case: row.case, accepted: row.accepted_before_cut, span: row.span_before_cut })),
    });
    for (const row of rows) {
      const wanted = CASES.find((item) => item.case === row.case)!;
      expect(row.violations_after_cut, node("A1", `${row.case}: the cut left ${JSON.stringify(row.violations_after_cut)} behind in「${row.text}」`)).toEqual([]);
      expect(row.span_violations_after_cut, node("A1", `${row.case}: the cut left ${JSON.stringify(row.span_violations_after_cut)} behind as a traveller reads it:「${row.text}」`)).toEqual([]);
      if (wanted.must_lose) {
        expect(row.removed, node("A1", `${row.case}: the class ${wanted.must_lose} was not taken off ${row.painted}`)).toContain(wanted.must_lose);
      } else {
        expect(row.removed, node("A1", `a clean word was cut anyway: ${JSON.stringify(row)}`)).toEqual([]);
        expect(row.text, node("A1", `a clean word was rewritten: ${row.painted} -> ${row.text}`)).toBe(row.painted);
      }
      if (wanted.keeps) {
        expect(row.text, node("A1", `${row.case}: expected the remaining parts of the word, got「${row.text}」`)).toBe(wanted.keeps);
        /* Subtractive, never substituting: what is painted has to be built out of the server's own words. */
        for (const kept of wanted.keeps.split(" ")) {
          expect(row.painted.includes(kept), node("A1", `${row.case}:「${kept}」is painted but was never in the server's word`)).toBe(true);
        }
      }
    }
  });

  test("word-with-nothing-left — stopLabel paints no word rather than a rejected one, and never invents", async () => {
    const whole = stopLabel({ place_name: null, title: "19:30" });
    const remainder = stopLabel({ place_name: null, title: "天津之眼 19:30 摩天轮" });
    const clean = stopLabel({ place_name: "古文化街牌坊", title: "19:30 集合点" });
    const nameless = stopLabel({ place_name: "  ", title: "" });
    push("word-with-nothing-left", {
      whole_word_forbidden: whole,
      remainder,
      place_name_wins_and_is_clean: clean,
      no_name_at_all: nameless,
    });
    expect(whole, node("A2", "a name made only of a forbidden class still produced a word")).toBeNull();
    expect(remainder?.text, node("A2", `the cut lost the name: ${JSON.stringify(remainder)}`)).toBe("天津之眼 摩天轮");
    expect(remainder?.removed, node("A2", "the cut did not record what it removed")).toContain("clock-time");
    expect(clean?.text, node("A2", "a readable place name was killed by a dirty title beside it")).toBe("古文化街牌坊");
    expect(clean?.from, node("A2", `the fold lost its owner: ${clean?.from}`)).toBe("place_name");
    expect(nameless, node("A2", "an absent name produced an invented word")).toBeNull();
  });
});

/** Put the six words on this run's plan and land on the map that reads them.
 *  Every browser arm calls this itself: the before-run is expected to fail one of these arms, and an
 *  arm that only worked because a sibling arm seeded it would be skipped with it -- which is how a
 *  reading goes missing instead of going red. */
const seedAndEnter = async (page: Page) => {
  await enterMap(page);
  const journeyId = await page.evaluate(() => localStorage.getItem("citynexus.v8.journey_id") ?? "");
  expect(journeyId.length, node("fixture", "the shell has no journey to put stops on")).toBeGreaterThan(8);
  const applied = runFixture("--apply", journeyId);
  expect(applied.ok, node("fixture", `the fixture did not land every case: ${JSON.stringify(applied)}`)).toBe(true);
  return { journeyId, applied };
};

test.describe("ORD-0415 on the running screen", () => {
  test("fixture-lands-in-payload — the six words arrive from the server, not from my DOM", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    const { journeyId, applied } = await seedAndEnter(page);
    push("fixture-applied", { journey_id: journeyId, applied });

    const bodies: unknown[] = [];
    page.on("response", async (response) => {
      if (!response.url().includes("/api/v1/")) return;
      try {
        bodies.push(await response.json());
      } catch {
        /* a tile or a non-JSON answer carries no activity list */
      }
    });
    await enterMap(page);
    const titles: string[] = [];
    const placeNames: (string | null)[] = [];
    const walk = (value: unknown) => {
      if (Array.isArray(value)) return value.forEach(walk);
      if (value && typeof value === "object") {
        const record = value as Record<string, unknown>;
        const plan = record.active_plan as { activities?: unknown } | undefined;
        if (Array.isArray(plan?.activities)) {
          for (const item of plan!.activities as Record<string, unknown>[]) {
            if (typeof item?.title === "string") titles.push(item.title);
            placeNames.push(typeof item?.place_name === "string" ? item.place_name : null);
          }
        }
        Object.values(record).forEach(walk);
      }
    };
    bodies.forEach(walk);
    const present = CASES.map((item) => ({ case: item.case, in_payload: titles.includes(item.painted) }));
    push("fixture-lands-in-payload", {
      journey_id: journeyId,
      payload_responses: bodies.length,
      titles_seen: titles.length,
      distinct_titles: Array.from(new Set(titles)).slice(0, 14),
      /* Which field this screen's stop words actually come from: the owner's v8 read is the branch that
         paints, and saying so keeps `place_name` from being assumed. */
      place_name_keys: placeNames.filter((name) => name !== null).length,
      cases_in_payload: present,
    });
    for (const row of present) {
      expect(row.in_payload, node("B1", `the server never sent the ${row.case} word, so a zero hit would be luck`)).toBe(true);
    }
  });

  test("glass-carries-no-class — nothing the list forbids is rendered, and the cut words still are", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await seedAndEnter(page);
    const glass = await readGlass(page);
    const judged = judgedStrings(glass);
    const hits = countHits(judged);
    const offenders = hits.span;
    const shownChipTexts = glass.renderedChips.map((chip) => chip.text);
    const cutLanded = CASES.filter((item) => item.keeps && item.keeps !== item.painted)
      .map((item) => ({ case: item.case, on_glass: shownChipTexts.includes(item.keeps) }));
    const controlLanded = shownChipTexts.includes("古文化街牌坊");
    const fired = glass.renderedChips.filter((chip) => chip.removed && chip.removed !== "nothing")
      .map((chip) => ({ text: chip.text, removed: chip.removed }));
    push("glass-carries-no-class", {
      chip_nodes: glass.chips.length,
      rendered_chips: glass.renderedChips.length,
      rendered_pins: glass.renderedPins.length,
      judged_string_count: judged.length,
      /* The before-picture, in the instrument's own words: on product bytes that never consulted the
         list these are the rendered strings that carry a class, and this is the count the order asks
         for before the wiring. */
      rendered_strings_with_forbidden_class: offenders.length,
      /* 处 under the accepted list, in case the two judges disagree on what is on this screen. */
      rendered_strings_with_accepted_class: hits.accepted.length,
      offenders,
      cut_words_on_glass: cutLanded,
      clean_control_on_glass: controlLanded,
      rule_fired_on: fired,
    });
    expect(glass.renderedChips.length, node("B2", "no label rendered at all, so a zero-hit reading would be vacuous")).toBeGreaterThan(0);
    expect(offenders, node("B2", `forbidden class rendered on the glass: ${JSON.stringify(offenders)}`)).toEqual([]);
    expect(hits.accepted, node("B2", `class flagged by the accepted list: ${JSON.stringify(hits.accepted)}`)).toEqual([]);
    for (const row of cutLanded) {
      expect(row.on_glass, node("B2", `${row.case}: the word was hidden instead of cut — the traveller lost the name, not the clock`)).toBe(true);
    }
    expect(controlLanded, node("B2", "the clean control name was killed by the wiring (over-kill)")).toBe(true);
    expect(fired.length, node("B2", "no rendered chip says a class was taken off it: the rule did not fire on this screen")).toBeGreaterThan(0);
  });

  test("whole-word-stops-keep-pin — a stop with no paintable word is still a stop a finger can hit", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await seedAndEnter(page);
    const glass = await readGlass(page);
    const clockOrdinal = glass.renderedChips.find((chip) => chip.text.includes("19:30"));
    const noChipForTheClock = !clockOrdinal;
    const pinsWithoutAWord = glass.renderedPins.filter(
      (pin) => !glass.renderedChips.some((chip) => chip.ordinal === pin.painted),
    );
    const announcedForbidden = glass.renderedPins.filter((pin) => mapLabelSpanViolations(pin.aria).length > 0);
    push("whole-word-stops-keep-pin", {
      chip_carrying_the_clock: clockOrdinal ?? null,
      no_chip_for_the_clock: noChipForTheClock,
      pin_count: glass.renderedPins.length,
      chip_count: glass.renderedChips.length,
      pins_without_a_rendered_word: pinsWithoutAWord,
      pins_announcing_a_forbidden_class: announcedForbidden,
    });
    expect(noChipForTheClock, node("B3", `a word the rule forbids reached the glass as a chip: ${JSON.stringify(clockOrdinal)}`)).toBe(true);
    expect(announcedForbidden, node("B3", `a pin announced a forbidden class: ${JSON.stringify(announcedForbidden)}`)).toEqual([]);
    expect(glass.renderedPins.length, node("B3", "the map painted no pins, so 'still pickable' could not be tested")).toBeGreaterThan(0);
    for (const pin of pinsWithoutAWord) {
      expect(pin.role, node("B3", `a stop with no word lost its button role: ${JSON.stringify(pin)}`)).toBe("button");
      expect(pin.rendered, node("B3", `a stop with no word lost its hit target: ${JSON.stringify(pin)}`)).toBe(true);
      expect(pin.aria.length, node("B3", `a stop with no word has no accessible name either: ${JSON.stringify(pin)}`)).toBeGreaterThan(0);
    }
  });

  test("attribution-still-reads — ORD-0412's sentence survives the wiring untouched", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await seedAndEnter(page);
    const glass = await readGlass(page);
    const authoredEn = mapCopy("en", "attributionRaster");
    const authoredZh = mapCopy("zh", "attributionRaster");
    const judged = judgedStrings(glass);
    const insideJudgedCorpus = judged.some((text) => text.length > 0 && glass.attributionText.includes(text));
    const raisedIfFed = mapLabelViolations(glass.attributionText);
    const shot = evidencePath("ord0415-wiring", "attribution_after_wiring.png");
    await page.locator(ATTRIBUTION_SELECTOR).screenshot({ path: shot });
    push("attribution-still-reads", {
      scope: MAP_LABEL_SCOPE,
      authored_en: authoredEn,
      authored_zh: authoredZh,
      on_screen: glass.attributionText,
      matches_authored_arm: glass.attributionText === authoredEn || glass.attributionText === authoredZh,
      rendered: glass.attributionRendered,
      box: glass.attributionBox,
      inside_judged_corpus: insideJudgedCorpus,
      /* Recorded, not asserted away: the same list does flag this sentence, which is exactly why the cut
         must be pointed at label words and never at the panel. */
      violations_if_it_were_judged: raisedIfFed,
      shot,
    });
    expect(glass.attributionRendered, node("B4", "the basemap attribution stopped rendering")).toBe(true);
    /* Whichever arm the shell is showing, it is the authored sentence byte-for-byte: the wiring cut
       label words, not the licence. */
    expect(glass.attributionText.length, node("B4", "the attribution renders no text")).toBeGreaterThan(0);
    expect(glass.attributionText, node("B4", "the tile host is gone from the compliance sentence")).toContain("tile.openstreetmap.org");
    expect(
      glass.attributionText === authoredEn || glass.attributionText === authoredZh,
      node("B4", `the sentence is neither authored arm: ${glass.attributionText}`),
    ).toBe(true);
    expect(insideJudgedCorpus, node("B4", "a judged label string is now part of the compliance sentence")).toBe(false);
    expect(raisedIfFed, node("B4", "the exemption protects nothing: the list no longer matches the attribution")).toContain("source");
  });

  test.afterAll(() => {
    /* Put the plan back: this run's database is shared with the rest of the suite in one invocation,
       and a dirty title left behind would make another lane's name-on-the-glass assertion read my data. */
    if (!databasePath()) return;
    try {
      const out = runFixture("--revert");
      writeFileSync(evidencePath("ord0415-wiring", "reading_fixture-reverted.json"), JSON.stringify({ file: FILE, ...out }, null, 1), "utf-8");
    } catch (error) {
      writeFileSync(
        evidencePath("ord0415-wiring", "reading_fixture-revert-FAILED.json"),
        JSON.stringify({ file: FILE, error: String(error) }, null, 1),
        "utf-8",
      );
    }
  });
});
