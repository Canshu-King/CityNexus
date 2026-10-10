"""Rewrite the C8/C9 reach logic from the screen truth the dump arm produced (加闸工):

  * /v8/spend is not a route -- the spend face is a 花费 tab on /v8/trips;
  * the two spend empty states need the catalogue-empty journey this spec already builds through
    public endpoints (the staged ACTIVE journey has 9 priced facts, so those cells never render there);
  * /v8/twin and /v8/bookings do render their cells on the staged journey.

Also removes the temporary dump arm."""

import io
import sys

SPEC = r"D:\moodle\_qoder_jiazagong_0407\wt\frontend\e2e\qoder-ord0407-empty-state-actions.spec.ts"

src = io.open(SPEC, encoding="utf-8", newline="").read()

# 1. drop the diagnostic arm (from its comment to the final closing of the describe)
start = src.index('  test("C8D dump every probed screen"')
src = src[:start] + "});\n"

# 2. table: add journey + fix routes/tab, keyed per cell
REPL = [
    (
        '''      key: "spend-empty",
      locator: '[data-testid="spend-empty"]',
      expect_text: "现在还没有可加的花费",
      routes: ["spend", "trips", "hub"],
      tab_text: "花费",''',
        '''      key: "spend-empty",
      locator: '[data-testid="spend-empty"]',
      expect_text: "现在还没有可加的花费",
      routes: ["trips"],
      tab_text: "花费",
      journey: "unlocatable",''',
    ),
    (
        '''      key: "spend-no-lines",
      locator: '[data-testid="spend-no-lines"]',
      expect_text: "这台服务器对这趟行程一条花费项都没有答出来。",
      routes: ["spend", "trips", "hub"],
      tab_text: "花费",''',
        '''      key: "spend-no-lines",
      locator: '[data-testid="spend-no-lines"]',
      expect_text: "这台服务器对这趟行程一条花费项都没有答出来。",
      routes: ["trips"],
      tab_text: "花费",
      journey: "unlocatable",''',
    ),
    (
        '''      routes: ["twin"],
      src: "frontend/src/features/traveler-twin/TwinPanel.tsx:33",''',
        '''      routes: ["twin"],
      journey: "staged",
      src: "frontend/src/features/traveler-twin/TwinPanel.tsx:33",''',
    ),
    (
        '''      routes: ["bookings"],
      src: "frontend/src/features/inbox/JourneyInboxWorkbench.tsx:892",''',
        '''      routes: ["bookings"],
      journey: "staged",
      src: "frontend/src/features/inbox/JourneyInboxWorkbench.tsx:892",''',
    ),
    (
        'const CENSUS_CELLS: Array<{ key: string; locator: string; expect_text: string; routes: string[]; src: string; tab_text?: string }> = [',
        'const CENSUS_CELLS: Array<{ key: string; locator: string; expect_text: string; routes: string[]; src: string; tab_text?: string; journey?: string }> = [',
    ),
    # 3. reach: boot the right journey, then probe; tab click by rendered text
    (
        '''  async function cellActionNumbers(page: Page, cell: (typeof CENSUS_CELLS)[number]) {
    for (const route of cell.routes) {
      await page.goto(`/v8/${route}`, { waitUntil: "load" });
      await settleShell(page);''',
        '''  async function cellActionNumbers(
    page: Page,
    cell: (typeof CENSUS_CELLS)[number],
    ids: { staged: string; unlocatable: string },
  ) {
    const which = cell.journey === "unlocatable" ? ids.unlocatable : ids.staged;
    await boot(page, which, "zh-CN");
    for (const route of cell.routes) {
      await page.goto(`/v8/${route}`, { waitUntil: "load" });
      await settleShell(page);
      if (cell.tab_text) {
        const opened = await page.evaluate((txt: string) => {
          const el = Array.from(document.querySelectorAll("button, [role=tab]")).find(
            (e) => ((e as HTMLElement).innerText ?? "").replace(/\\s+/g, "").indexOf(txt) >= 0,
          );
          if (!el) return 0;
          (el as HTMLElement).click();
          return 1;
        }, cell.tab_text);
        if (opened) await page.waitForTimeout(1500);
      }
      const onTab = await measureCell(page, cell);
      if (onTab) return { ...onTab, reached_by: cell.tab_text ? `tab:${cell.tab_text}` : "route" };''',
    ),
    (
        '''      const attempts: Array<{ via: string; found: any }> = [];
      let found = await measureCell(page, cell);
      attempts.push({ via: "route", found });
      if (found) return { ...found, reached_by: "route" };''',
        '''      let found = await measureCell(page, cell);
      if (found) return { ...found, reached_by: "route" };''',
    ),
    # 4. both tests resolve the two journeys once and pass them down
    (
        '''    const id = await stageJourneyId(page);
    await boot(page, id, "zh-CN");
    const rows: Record<string, any> = {};
    for (const cell of CENSUS_CELLS) {
      const one = await cellActionNumbers(page, cell);''',
        '''    const ids = { staged: await stageJourneyId(page), unlocatable: (await createUnlocatableJourney(page)).journey_id };
    const rows: Record<string, any> = {};
    for (const cell of CENSUS_CELLS) {
      const one = await cellActionNumbers(page, cell, ids);''',
    ),
    (
        '''    const id = await stageJourneyId(page);
    await boot(page, id, "zh-CN");
    const perCell: Record<string, any> = {};
    const empty: string[] = [];
    for (const cell of CENSUS_CELLS) {
      const one = await cellActionNumbers(page, cell);''',
        '''    const ids = { staged: await stageJourneyId(page), unlocatable: (await createUnlocatableJourney(page)).journey_id };
    const perCell: Record<string, any> = {};
    const empty: string[] = [];
    for (const cell of CENSUS_CELLS) {
      const one = await cellActionNumbers(page, cell, ids);''',
    ),
]

for old, new in REPL:
    n = src.count(old)
    if n != 1:
        print("ABORT anchor count %d for %r" % (n, old[:70]))
        sys.exit(1)
    src = src.replace(old, new, 1)

io.open(SPEC, "w", encoding="utf-8", newline="").write(src)
print("PATCHED reach, bytes", len(src), "| braces", src.count("{") - src.count("}"), "| parens", src.count("(") - src.count(")"))
print("dump arm gone:", "C8D" not in src)
