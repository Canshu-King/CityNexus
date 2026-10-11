"""Fix the C8/C9 probe (加闸工): the first run died because it measured a still-loading shell.

Adds (1) a settle wait for the boot skeleton to leave, (2) a tab arm for cells that live behind a
section tab on their screen, (3) a wider route probe list for the two spend cells, and records which
arm found each cell so the receipt says how it was reached."""

import io
import sys

SPEC = r"D:\moodle\_qoder_jiazagong_0407\wt\frontend\e2e\qoder-ord0407-empty-state-actions.spec.ts"
OLD_TABLE = '''      routes: ["spend", "trips", "hub"],
      src: "frontend/src/features/trip/SpendPanel.tsx:105",'''
NEW_TABLE = '''      routes: ["spend", "trips", "hub"],
      tab_text: "花费",
      src: "frontend/src/features/trip/SpendPanel.tsx:105",'''
OLD_TABLE2 = '''      routes: ["spend", "trips", "hub"],
      src: "frontend/src/features/trip/SpendPanel.tsx:173",'''
NEW_TABLE2 = '''      routes: ["spend", "trips", "hub"],
      tab_text: "花费",
      src: "frontend/src/features/trip/SpendPanel.tsx:173",'''
OLD_TYPE = "const CENSUS_CELLS: Array<{ key: string; locator: string; expect_text: string; routes: string[]; src: string }> = ["
NEW_TYPE = "const CENSUS_CELLS: Array<{ key: string; locator: string; expect_text: string; routes: string[]; src: string; tab_text?: string }> = ["
OLD_HEAD = """  /** One cell's two numbers, on the first probed route where the cell's own sentence is rendered. */
  async function cellActionNumbers(page: Page, cell: (typeof CENSUS_CELLS)[number]) {
    for (const route of cell.routes) {
      await page.goto(`/v8/${route}`, { waitUntil: "load" });
      const found = await page.evaluate("""
NEW_HEAD2 = """  /** Wait until the boot skeleton has left the page: measuring a shell that is still filling in is
      how the first run of this arm reported "cell not rendered" for a cell that does exist. */
  async function settleShell(page: Page) {
    await page
      .waitForFunction(
        () => {
          const t = (document.body && document.body.innerText) || "";
          return t.indexOf("正在准备城市周末行程") < 0 && document.querySelectorAll("[data-testid]").length > 3;
        },
        undefined,
        { timeout: 20_000 },
      )
      .catch(() => undefined);
  }

  async function measureCell(page: Page, cell: (typeof CENSUS_CELLS)[number]) {
    return page.evaluate("""
OLD_TAIL = """        [cell.locator, cell.expect_text],
      );
      if (found) return found;
    }
    return null;
  }"""
NEW_TAIL = """    [cell.locator, cell.expect_text],
  );
}

  /** One cell's two numbers: probe each route, and for a cell behind a section tab click that tab too. */
  async function cellActionNumbers(page: Page, cell: (typeof CENSUS_CELLS)[number]) {
    for (const route of cell.routes) {
      await page.goto(`/v8/${route}`, { waitUntil: "load" });
      await settleShell(page);
      const attempts: Array<{ via: string; found: any }> = [];
      let found = await measureCell(page, cell);
      attempts.push({ via: "route", found });
      if (found) return { ...found, reached_by: "route" };
      if (cell.tab_text) {
        const clicked = await page.evaluate((txt: string) => {
          const els = Array.from(document.querySelectorAll("button, [role=tab], a")).filter(
            (e) => ((e as HTMLElement).innerText ?? "").replace(/\\s+/g, "").indexOf(txt) >= 0,
          );
          if (!els.length) return 0;
          (els[0] as HTMLElement).click();
          return 1;
        }, cell.tab_text);
        if (clicked) {
          await page.waitForTimeout(1500);
          found = await measureCell(page, cell);
          attempts.push({ via: "tab", found });
          if (found) return { ...found, reached_by: `tab:${cell.tab_text}` };
        }
      }
      // the screen may own several tabs; sweep them once before giving up on this route
      for (let i = 0; i < 8; i++) {
        const opened = await page.evaluate((idx: number) => {
          const els = Array.from(document.querySelectorAll("button, [role=tab]")).filter((e) => {
            const r = e.getBoundingClientRect();
            return r.width > 0 && r.height > 0;
          });
          if (idx >= els.length) return 0;
          (els[idx] as HTMLElement).click();
          return 1;
        }, i);
        if (!opened) break;
        await page.waitForTimeout(600);
        found = await measureCell(page, cell);
        if (found) return { ...found, reached_by: `tab-sweep#${i}` };
      }
    }
    return null;
  }"""

src = io.open(SPEC, encoding="utf-8", newline="").read()
for old, new in ((OLD_TYPE, NEW_TYPE), (OLD_TABLE, NEW_TABLE), (OLD_TABLE2, NEW_TABLE2)):
    if src.count(old) != 1:
        print("ABORT anchor not unique:", repr(old[:60]), src.count(old)); sys.exit(1)
    src = src.replace(old, new, 1)
if src.count(OLD_HEAD) != 1:
    print("ABORT head anchor count", src.count(OLD_HEAD)); sys.exit(1)
src = src.replace(OLD_HEAD, NEW_HEAD2, 1)
if src.count(OLD_TAIL) != 1:
    print("ABORT tail anchor count", src.count(OLD_TAIL)); sys.exit(1)
src = src.replace(OLD_TAIL, NEW_TAIL, 1)
io.open(SPEC, "w", encoding="utf-8", newline="").write(src)
print("PATCHED, bytes", len(src))
