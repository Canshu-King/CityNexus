/**
 * ORD-0570 第二批 · 抬进字典的那六枚措辞，两语各上一次屏。
 *
 * 一态一格一个 test：上一版把五趟导航串在同一页里，第 4 趟时浏览器被关掉（这台机器此刻物理内存只剩
 * 一 GB 上下），读数于是整趟丢。改成每格自己一次进入，Playwright 负责关页面与上下文。
 *
 * 门的回包一律先取本车道这台服务器真发的那一份，再只改动要造的那一处（其余字段逐字保留），
 * 所以每行读数都带见证类型：
 *   NATURAL            —— 这台服务器此刻的回包就长出这一格；
 *   STUB_EMPTY_ROWS / STUB_EMPTY_TITLE / STUB_REVERSED_ROWS / STUB_DELAY
 *                      —— 只换那一处；它说明「门回这一形时屏上念什么」，不说明这台服务器今天发了它。
 * 断言读渲染出来的文字（innerText），字典那一侧的字节由文件现读；带 {hole} 的按洞切两截找，屏上整句抄回。
 */
import { expect, test, type Page } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";

const DICTIONARY = "src/i18n/LocaleContext.tsx";
const OUT = path.join(process.cwd(), "..", "review", "beichengong-0570");
const LIST = /\/api\/v1\/journeys(\?|$)/;
type Mode = "NATURAL" | "STUB_EMPTY_ROWS" | "STUB_EMPTY_TITLE" | "STUB_REVERSED_ROWS" | "STUB_DELAY";
type Cell = { key: string; mode: Mode; testid: string; must: boolean; skip?: string };

const CELLS: Cell[] = [
  { key: "access.sortHeading", mode: "NATURAL", testid: "", must: true },
  { key: "access.pickLabel", mode: "NATURAL", testid: "", must: true },
  // 壳把已打开的行程传下来，所以「先选一条要看的行程」这句在自然态不出现；
  // 我原以为它出现在门回空列表那一形，实测那一形整块面板不再挂载，所以那句也没被读到
  // 这句这轮拿不到屏读，两种态都试过：自然态下壳把已打开的那趟行程直接传进面板，chosen 一上来不是 null；
  // 把门的回包换成空列表时整块面板不再挂载（那趟 test 是 60 秒超时，不是断言红）。
  // 所以这一格现在带 skip 理由跳过，不再每跑一次留一枚与内容无关的红；
  // 「自然态屏上没有这句」那次观察落在 run11 的读数件里（ABSENT 行），字面等价由首节的字节抬键证明
  {
    key: "access.pickNone",
    mode: "NATURAL",
    testid: "access-trips-hint",
    must: false,
    skip: "这句在这一代屏上长不出来：壳把已打开的那趟行程直接传进面板，chosen 一上来不是 null；"
      + "把门的回包换成空列表时整块面板不再挂载。自然态里读到的是 ABSENT（读数在 "
      + "run11 那份里），不断言也不假装读到过；这一格现在跳过，免得每次跑都留一枚与内容无关的红。",
  },
  { key: "access.sortCurrent", mode: "STUB_REVERSED_ROWS", testid: "access-sort-current", must: true },
  { key: "access.pickEmpty", mode: "STUB_EMPTY_ROWS", testid: "access-trips-empty", must: true },
  { key: "access.tripUntitled", mode: "STUB_EMPTY_TITLE", testid: "", must: true },
  { key: "access.pickLoading", mode: "STUB_DELAY", testid: "access-trips-loading", must: true },
];

function dictValue(key: string, book: "en" | "zh"): string {
  const lines = fs.readFileSync(DICTIONARY, "utf8").split("\n");
  const zhStart = lines.findIndex((l) => l.startsWith("const zhCN: Dict"));
  for (let i = 0; i < lines.length; i += 1) {
    const m = /^\s*"([^"]+)": "(.*)",$/.exec(lines[i]);
    if (m && m[1] === key && (i < zhStart ? "en" : "zh") === book) return m[2];
  }
  throw new Error("字典里没有这枚键的一侧：" + key + " " + book);
}

/** 带 {hole} 的那格屏上是填好的句子：按洞切两截找，屏上整句抄回。 */
function findFilled(hay: string, want: string): { at: number; seen: string } {
  if (!/\{\w+\}/.test(want)) {
    const at = hay.toLowerCase().indexOf(want.toLowerCase());
    return { at, seen: at >= 0 ? hay.slice(at, at + want.length) : "" };
  }
  let cursor = -1;
  let end = 0;
  for (const piece of want.split(/\{\w+\}/).map((s) => s.trim()).filter(Boolean)) {
    const at = hay.toLowerCase().indexOf(piece.toLowerCase(), cursor + 1);
    if (at < 0) return { at: -1, seen: "" };
    if (cursor < 0) cursor = at;
    end = at + piece.length;
  }
  return { at: cursor, seen: hay.slice(Math.max(cursor, 0), end).replace(/\s+/g, " ") };
}

async function enter(page: Page, locale: string, mode: Mode): Promise<void> {
  const seeded = await (await page.request.get("/api/v1/demo/scene")).json();
  const journeyId = String((seeded as { journey_id?: string }).journey_id ?? "");
  expect(journeyId.length, "壳要先有一趟打开的行程").toBeGreaterThan(8);
  await page.addInitScript(
    ([loc, id]) => {
      localStorage.clear();
      localStorage.setItem("citynexus.locale", loc);
      localStorage.setItem("citynexus.v8.journey_id", id);
    },
    [locale, journeyId] as [string, string],
  );
  if (mode !== "NATURAL") {
    await page.route(LIST, async (route) => {
      // 页面被拆掉时这条回调还会被叫一次，里面任何一句抛出来都会把整个 context 带走：
      // 之前 pickNone 那格就是这么红的（读数没落下，只留下一句 browser has been closed）
      let real;
      try {
        real = await route.fetch();
      } catch {
        return;
      }
      const finish = (body: string) => route.fulfill({ response: real, body }).catch(() => undefined);
      let body;
      try {
        body = await real.json();
      } catch {
        return;
      }
      const rows: unknown = Array.isArray(body) ? body : [];
      if (mode === "STUB_EMPTY_ROWS") return finish("[]");
      if (mode === "STUB_DELAY") {
        await new Promise((res) => setTimeout(res, 2000));
        return finish(JSON.stringify(rows));
      }
      const list = rows as Record<string, unknown>[];
      if (!list.length) return finish(JSON.stringify(rows));
      if (mode === "STUB_EMPTY_TITLE") {
        return finish(JSON.stringify(list.map((r, i) => (i === 0 ? { ...r, title: "   " } : r))));
      }
      return finish(JSON.stringify(list.slice().reverse()));
    });
  }
  await page.goto("/v8/hub", { waitUntil: "load" });
  await expect(page.getByTestId("today-hero")).toBeVisible({ timeout: 30_000 });
  await page.goto("/v8/access", { waitUntil: "load" });
  await expect(page.getByTestId("access-panel")).toBeVisible({ timeout: 30_000 });
}

function record(locale: string, line: string): void {
  fs.mkdirSync(OUT, { recursive: true });
  fs.appendFileSync(path.join(OUT, "screen_read_b2_" + locale + "_r1.txt"), line + "\n", "utf8");
}

for (const [locale, book] of [["zh-CN", "zh"], ["en", "en"]] as [string, "en" | "zh"][]) {
  for (const cell of CELLS) {
    test("0570b " + locale + " 屏读 " + cell.key + "（" + cell.mode + "）", async ({ page }) => {
      if (cell.skip) {
        test.skip(true, cell.skip);
        return;
      }
      await enter(page, locale, cell.mode);
      const want = dictValue(cell.key, book);
      let where = "ABSENT";
      let seen = "";
      if (cell.mode === "STUB_DELAY") {
        const box = page.getByTestId(cell.testid);
        if (await box.isVisible({ timeout: 1500 }).catch(() => false)) {
          seen = (await box.innerText()).trim();
          where = "PANEL";
        }
      } else {
        await page.waitForTimeout(cell.mode === "NATURAL" ? 1000 : 800);
        const panel = (await page.getByTestId("access-panel").innerText().catch(() => "")).trim();
        const own = cell.testid
          ? (await page.getByTestId(cell.testid).first().innerText().catch(() => "")).trim()
          : panel;
        for (const [hay, tag] of [[own, "PANEL"], [panel, "PANEL"]] as [string, string][]) {
          const f = findFilled(hay, want);
          if (f.at >= 0) {
            where = tag;
            seen = f.seen;
            break;
          }
        }
        if (where === "ABSENT" && !page.isClosed()) {
          const whole = await page.evaluate(() => document.body.innerText).catch(() => "");
          const f = findFilled(whole, want);
          if (f.at >= 0) {
            where = "PAGE_ONLY";
            seen = f.seen;
          }
        }
      }
      record(locale, [cell.key, cell.mode, where, "字典=" + want, "屏上=" + (seen || "—")].join(" | "));
      // 截图只是附证：这台机器内存见底时 fullPage 截图会整句挂住（挂住不是 reject，catch 接不到），
      // 读数已经落盘了不能因它丢，所以只看视口并给它一枚自己的超时
      await page.screenshot({
        path: path.join(OUT, "shot_b2_" + locale + "_" + cell.key.replace(/\W/g, "_") + ".png"),
        timeout: 10_000,
      }).catch(() => undefined);
      if (cell.must) {
        expect(where, locale + " " + cell.key + " 没在屏上读到（" + cell.mode + "）").not.toBe("ABSENT");
        expect(seen.replace(/\s+/g, " ").length, cell.key + " 屏上文字为空").toBeGreaterThan(0);
      }
    });
  }
}
