/* Issue #31 C 返工：图文教程的截图必须由同一条用例、同一个代码 SHA、真浏览器真后端一次跑出来。
 *
 * 上一版为什么不合格（用户现场否决的原话是"满篇文字谁看得懂，为什么不在图上标"）：
 *  1. 说"第 1 步"的那张图其实拍的是向导第 3 页——前两步根本没有图；
 *  2. `fullPage: true` 截出几屏长的图，大片留白，重点入口只是一个小号蓝字；
 *  3. 屏上直接铺 `NATIVE_DEEPSEEK_TOOL_LOOP`／`Journey.created` 这类内部码，
 *     而这台部署 AI 是关着的，图上也没说"当前没有真实 AgentRun"。
 * 这一条把八步逐屏拍全，并且**不猜坐标**：每一张都同时记下目标元素的
 * `boundingBox()`、视口宽，标注由 `scripts/annotate_first_trip_guide_r1.py` 按这份清单画上去
 * （粗圆角框 + 箭头 + ①… 编号 + 不超过 14 字的动作话）。
 * 原图与标注图分开存：`docs/assets/raw/` 是原图，`docs/assets/` 是教程引用的标注版。
 */
import { expect, test, type Page } from "@playwright/test";
import { mkdirSync, writeFileSync } from "node:fs";

const RAW = "docs/assets/raw";
const MANIFEST = "docs/assets/manifest.json";
mkdirSync(RAW, { recursive: true });

type Box = { x: number; y: number; width: number; height: number };
/** 渲染状态：包围盒有 ≠ 屏上看得见，所以这两件事分开记。 */
type Paint = {
  opacity: string;
  visibility: string;
  color: string;
  paintedText: string;
  fadedBy: string[];
};
type Target = { testId: string; action: string; box?: Box; paint?: Paint };
type Shot = {
  id: string;
  file: string;
  headline: string;
  note?: string;
  viewportWidth: number;
  targets: Target[];
  /** 这一屏真的印出来的点号机器键（`catalog.count.zero` 那一类）；教程要求它恒为空。 */
  paintedKeys: string[];
};

const shots: Shot[] = [];

async function seedPhone(page: Page) {
  await page.context().addInitScript(() => {
    if (window.name === "cnx31-guide") return;
    try {
      localStorage.clear();
      sessionStorage.clear();
    } catch {
      /* 空设备上没什么可清的 */
    }
    localStorage.setItem("citynexus.theme", "light");
    localStorage.setItem("citynexus.locale", "zh-CN");
    window.name = "cnx31-guide";
  });
  await page.emulateMedia({ colorScheme: "light", media: "screen" });
}

/**
 * 拍一张，并把"该圈谁"一起记下来。
 *
 * 坐标只从 `boundingBox()` 现取，不手写；视口宽一起记，标注脚本按 `PNG 宽 / 视口宽` 缩放——
 * 设备像素比一变，手写的坐标就会偏，那正是这次否决里点名的"人工猜坐标导致偏移"。
 * 文件名一律 ASCII：CJK 文件名在这台机器上撞过车（两张图互相覆盖，教程就会指到错的屏）。
 */
async function shoot(
  page: Page,
  id: string,
  asciiName: string,
  headline: string,
  targets: Target[],
  note?: string,
) {
  const file = `${id}-${asciiName}.png`;
  /* 等这一屏自己把入场动画放完再拍。上一版的图看着"白"，不是产品没渲染，而是截图落在
   * `.v8-page-intro` 的淡入中途（实测 opacity 0.66），字都在、墨都不够——教程要给读者看的
   * 是他手指落下去那一瞬间屏上的样子，那一屏早就淡完了。这里等的就是那半秒。 */
  await page
    .waitForFunction(
      () =>
        (document.getAnimations ? document.getAnimations() : []).every(
          (animation) => animation.playState === "finished" || animation.playState === "idle",
        ),
      null,
      { timeout: 15_000 },
    )
    .catch(() => {
      /* 还在动的动画交给下面那道渲染闸：它会指名是谁没画出来 */
    });
  await page.waitForTimeout(250);
  const viewportWidth = await page.evaluate(() => window.innerWidth);
  /* 这一屏上真的印出来的点号机器键（`catalog.count.zero` 那一类）必须为空。上一版第 ⑥ 张就是
   * 把字典缺键直接拍进了教程，靠人眼看图才发现——所以把它变成一条尺，而不是靠谁去盯。 */
  const paintedKeys = await page.evaluate(() => {
    const visible = document.body ? document.body.innerText.replace(/\s+/g, " ") : "";
    return Array.from(new Set(visible.match(/[a-z][a-z0-9]*\.[a-z][a-z0-9]*\.[a-z0-9]+/g) || []));
  });
  if (paintedKeys.length) {
    console.log(`guide ${id} 屏上印着机器键 ${paintedKeys.join(" | ")}`);
  }
  const recorded: Shot = {
    id,
    file,
    headline,
    viewportWidth,
    paintedKeys,
    ...(note ? { note } : {}),
    targets: [],
  };
  for (const target of targets) {
    const locator = page.getByTestId(target.testId).first();
    const box = await locator.boundingBox().catch(() => null);
    /* 量到盒子不等于屏上看得见。Playwright 的 visible 只看 display/visibility，
     * 一个 opacity:0 的元素照样有包围盒、照样能命中——上一版就是这么"通过"了一张白屏。
     * 教程要圈的是人真能看见的按钮，所以这里把渲染状态一并记进 manifest。 */
    const paint = await locator
      .evaluate((el) => {
        const node = el as HTMLElement;
        const cs = getComputedStyle(node);
        const chain: string[] = [];
        /* 只往上看祖先：祖先没淡入完 = 这一屏还没画出来（上一版白屏就是这个）；
         * 自己发暗是产品自己的禁用态（`trial-next` 在三项填齐前是 0.45），那是给人看的真状态。 */
        let walk: HTMLElement | null = node.parentElement;
        while (walk) {
          const o = Number(getComputedStyle(walk).opacity);
          if (Number.isFinite(o) && o < 1) chain.push(`${walk.className || walk.tagName}:${o}`);
          walk = walk.parentElement;
        }
        /* 输入格里的字在 `.value` 里，不在 textContent 里——按 textContent 判会把填好的格子
         * 读成"没画出来"。 */
        const typed = node instanceof HTMLInputElement || node instanceof HTMLTextAreaElement;
        return {
          opacity: cs.opacity,
          visibility: cs.visibility,
          color: cs.color,
          paintedText: (
            typed ? (node as HTMLInputElement).value : node.textContent || ""
          ).trim().slice(0, 40),
          fadedBy: chain.slice(0, 3),
        };
      })
      .catch(() => null);
    recorded.targets.push({ ...target, ...(box ? { box } : {}), ...(paint ? { paint } : {}) });
    if (paint && (paint.visibility !== "visible" || Number(paint.opacity) < 0.4 ||
        paint.fadedBy.length > 0 || !paint.paintedText)) {
      console.log(`guide ${id} 没画出来 ${target.testId} ${JSON.stringify(paint)}`);
    }
  }
  await page.screenshot({ path: `${RAW}/${file}` });
  shots.push(recorded);
  const missed = recorded.targets.filter((item) => !item.box).map((item) => item.testId);
  console.log(
    `guide ${id} ${headline} | 量到 ${recorded.targets.length - missed.length}/${recorded.targets.length}` +
      (missed.length ? ` | 没量到：${missed.join(", ")}` : ""),
  );
}

test.describe("Issue #31 C 返工：第一次出行的九屏实拍", () => {
  test.setTimeout(240_000);

  test("从第一次打开到 AI 工作动态，逐屏拍全并记下要圈的按钮", async ({ page }) => {
    await seedPhone(page);

    // ① 第一次打开：城市格。这一屏只圈"填哪儿"与"下一步"，不假装已经能点。
    // 城市选北京：这台服务器对它有完整的事实（教程要教的是走通的那条路，不是缺数据的城市——
    // 上一版用天津，第一屏就挂着"这座城市还没准备好"，读者会以为自己做错了什么）。
    await page.goto("/v8", { waitUntil: "load" });
    await expect(page.getByTestId("trial-setup")).toBeVisible({ timeout: 25_000 });
    await page.getByTestId("trial-city").fill("北京");
    await shoot(page, "01", "city", "① 先说要去的城市", [
      /* 这一屏只圈城市格，不圈「下一步」：那一颗此刻还是灰的（三项填齐前 opacity 实测 0.45），
       * GPT 逐张看图判它是"照着点会没反应"的假出口。被圈的东西必须真的能点，所以「下一步」留到
       * 第 ② 张——那时三格都填完、按钮是亮的。 */
      { testId: "trial-city", action: "填城市" },
      /* 试过把下面那段"这座城市还没准备过"也圈上（`trial-city-warning`）：它在向导自己的
       * 滚动容器里，`boundingBox()` 为它滚视口会一直不 settle，整条用例被拖到超时。
       * 那句话本来就在屏上看得见，教程正文里解释它说什么，不靠圈。 */
    ]);

    /* ② 抵达与离开。上一版在这里踩了个真钉子：向导第 1 页要求三样都填齐，
     * `trial-next` 在缺抵达/离开时是 `aria-disabled="true"`——不填就点，只会让用例
     * 卡在"element is not enabled"直到超时（457 次重试）。这正好是教程要教的事。 */
    await page.getByTestId("trial-arrival").fill("北京南站");
    await page.getByTestId("trial-departure").fill("大兴国际机场");
    await page.waitForTimeout(400);
    await shoot(page, "02", "anchors", "② 再填抵达和离开", [
      { testId: "trial-arrival", action: "从哪儿到" },
      { testId: "trial-departure", action: "从哪儿走" },
      { testId: "trial-next", action: "点这里" },
    ]);
    await page.getByTestId("trial-next").click();
    await page.waitForTimeout(500);

    // ③ 核对页：圈出「确认创建」
    await page.getByTestId("trial-next").click();
    await page.waitForTimeout(500);
    await expect(page.getByTestId("trial-create")).toBeVisible({ timeout: 15_000 });
    await shoot(page, "03", "confirm", "③ 核对无误，点这里创建", [
      { testId: "trial-create", action: "点这里创建" },
    ]);

    // ④ Today：圈出「AI 工作动态」
    const created = page.waitForResponse(
      (res) => res.request().method() === "POST" && /\/api\/v1\/journeys$/.test(res.url()),
      { timeout: 60_000 },
    );
    await page.getByTestId("trial-create").click();
    expect((await created).status(), "创建没有回 201").toBe(201);
    await expect(page.getByTestId("hub-secondary-actions"), "Today 没打开").toBeVisible({
      timeout: 20_000,
    });
    /* 提示带里那颗「知道了」以前被压成两行（"知道" / "了"）：这一格是 flex + space-between，
     * 按钮没写 flex:none，正文一长就把它的标签挤断。判据只认渲染出来的行盒。
     * 等的是这一趟建完之后必然出现的那条带：住宿查到结果写一句，查不到也写一句，两种都带这颗按钮。 */
    const dismiss = page.locator("div.v8-message button").last();
    await expect(dismiss, "Today 上没出现带「知道了」的那条提示带").toBeVisible({ timeout: 40_000 });
    const dismissGeometry = await dismiss.evaluate((node) => {
      const range = document.createRange();
      range.selectNodeContents(node);
      const rects = Array.from(range.getClientRects()).filter(
        (rect) => rect.width > 0 && rect.height > 0,
      );
      const box = node.getBoundingClientRect();
      const bar = node.closest("div.v8-message")?.getBoundingClientRect();
      return {
        lines: rects.length,
        text: (node.textContent ?? "").trim(),
        box: [
          Math.round(box.x),
          Math.round(box.y),
          Math.round(box.width),
          Math.round(box.height),
        ],
        inside: bar
          ? box.x >= bar.x - 1 && box.right <= bar.right + 1
          : null,
      };
    });
    expect(
      dismissGeometry.lines,
      `「${dismissGeometry.text}」被排成 ${dismissGeometry.lines} 行`,
    ).toBe(1);
    expect(dismissGeometry.inside, "那颗按钮掉出了提示带").toBe(true);
    console.log(
      `提示带按钮：「${dismissGeometry.text}」行盒 ${dismissGeometry.lines} 个，盒子 ${JSON.stringify(dismissGeometry.box)}`,
    );
    await shoot(page, "04", "today", "④ 点这里看 AI 做过什么", [
      { testId: "hub-ai-work", action: "点这里看 AI" },
    ]);

    // ⑤ 面板：这台部署 AI 关着，这句话必须印在图上
    await page.getByTestId("hub-ai-work").click();
    await expect(page.getByTestId("agent-work-feed")).toBeVisible({ timeout: 15_000 });
    await expect(page.getByTestId("agent-work-feed")).toHaveAttribute("data-feed-state", "ready", {
      timeout: 20_000,
    });
    await shoot(
      page,
      "05",
      "ai-panel",
      "⑤ 这里只写服务器确证过的事",
      [{ testId: "agent-work-no-run", action: "暂无真实运行" }],
      "测试环境 AI 未启用；当前没有真实运行",
    );

    // ⑥ 底栏「行程」→ 该页入口
    await page.goto("/v8/trips", { waitUntil: "load" });
    await page.waitForTimeout(2500);
    /* 先摊事实再断言：上一版这里要么挂在"点不到 tab"四分钟，要么直接红，都看不出为什么。
     * 行程页的 tab 条要等 `/experience` 回来才渲染，那一格 500 的时候整屏是错误态——
     * 所以把屏上真有的 testid 与错误文案打出来，再决定是修产品还是改用例。 */
    const onScreen = await page.evaluate(() => ({
      testIds: Array.from(document.querySelectorAll("[data-testid]"))
        .map((el) => el.getAttribute("data-testid"))
        .slice(0, 40),
      body: (document.body.innerText || "").slice(0, 200).replace(/\s+/g, " "),
    }));
    console.log(`guide 06 现场 ${JSON.stringify(onScreen)}`);
    await expect(page.getByTestId("agent-work-entry-trip"), "行程页没有 AI 工作动态入口").toBeVisible({
      timeout: 20_000,
    });
    await shoot(page, "06", "trip-entry", "⑥ 行程页也有同一颗入口", [
      { testId: "trip-ai-work", action: "点这里" },
    ]);

    // ⑦ 面板里的「再查一次」
    await page.getByTestId("trip-ai-work").click();
    await expect(page.getByTestId("agent-work-feed")).toBeVisible({ timeout: 15_000 });
    await shoot(page, "07", "trip-panel", "⑦ 不确定就点这里再查", [
      { testId: "agent-work-retry", action: "再查一次" },
    ]);

    // ⑧ 最常见的失败：住宿查不到 —— 圈出当前真能点的恢复按钮
    /* 失败态只能由一次真的查询产生：`hub-stay-retry` 只在 搜索中/没找到/失败 三态里出现，
     * 直接开 /v8/hub 时它是 idle，屏上本来就没有那颗按钮（上一版就是这么量出"没有恢复按钮"的，
     * 那是用例没走对，不是产品少了出口）。所以这里再走一遍创建：这一次把住宿查询打成 503。 */
    await page.route("**/api/v1/journeys/*/stay-options/generate", (route) =>
      route.fulfill({
        status: 503,
        contentType: "application/json",
        body: JSON.stringify({
          error: {
            code: "SERVICE_UNAVAILABLE",
            message: "stay provider unavailable",
            message_key: "error.service_unavailable",
            trace_id: "guide-08",
            details: null,
          },
        }),
      }),
    );
    await page.evaluate(() => localStorage.removeItem("citynexus.v8.journey_id"));
    await page.goto("/v8", { waitUntil: "load" });
    await expect(page.getByTestId("trial-setup")).toBeVisible({ timeout: 25_000 });
    await page.waitForTimeout(800);
    /* 向导记得上一趟填过的答案，这是产品的既有行为而不是用例的捷径：所以再开 /v8 可能落在第 1 页
     * （空白），也可能直接停在「确认创建」（记得答案）。两种屏都得走到创建，否则 ⑧ 会去等一格
     * 本来就不在这张屏上的输入框——上一版就是这么超时在 `trial-city` 上的。 */
    if ((await page.getByTestId("trial-city").count()) > 0) {
      await page.getByTestId("trial-city").fill("北京");
      await page.getByTestId("trial-arrival").fill("北京南站");
      await page.getByTestId("trial-departure").fill("大兴国际机场");
      await page.waitForTimeout(400);
      await page.getByTestId("trial-next").click();
      await page.waitForTimeout(500);
      await page.getByTestId("trial-next").click();
    }
    await expect(page.getByTestId("trial-create")).toBeVisible({ timeout: 15_000 });
    const second = page.waitForResponse(
      (res) => res.request().method() === "POST" && /\/api\/v1\/journeys$/.test(res.url()),
      { timeout: 60_000 },
    );
    await page.getByTestId("trial-create").click();
    expect((await second).status(), "第二趟没建成，失败态就无从可拍").toBe(201);
    await expect(page.getByTestId("hub-stay-retry").first(), "失败之后没有可点的恢复按钮").toBeVisible({
      timeout: 40_000,
    });
    await shoot(page, "08", "stay-retry", "⑧ 查不到时点这里重试", [
      { testId: "hub-stay-retry", action: "点这里重试" },
    ]);

    // ⑨ 会话还在、指针没了：从「我的行程」这一格回到已经有的一趟
    /* 这一屏只在"有凭据"时才存在：没有签名会话时这一格整块不出现（`MyTripsEntry` 里那条规则），
     * 而走到这里之前已经建过两趟，所以名单上应当有两行——教程要给人看的正是"不止一趟可选"那个形状。 */
    await page.evaluate(() => localStorage.removeItem("citynexus.v8.journey_id"));
    await page.goto("/v8", { waitUntil: "load" });
    await expect(page.getByTestId("my-trips-list"), "向导旁边没有「我的行程」名单").toBeVisible({
      timeout: 30_000,
    });
    const rows = await page.getByTestId("my-trips-list").locator("li[data-cnx-journey]").count();
    console.log(`guide 09 名单里的行程 ${rows} 枚`);
    /* 先把这一格滚进视口再拍。第一版 ⑨ 拍出来是"没有这一格的向导"：截图取的是视口
     * （390×844），而 `boundingBox()` 给的是文档坐标（这一格在 y=860 起），于是圈的位置
     * 落在画面之外——图上是空的，圈却"量到了"。滚上来之后两者同一个坐标系，才量得对。 */
    await page.getByTestId("my-trips").evaluate((node) => node.scrollIntoView({ block: "start" }));
    await page.waitForTimeout(500);
    await shoot(
      page,
      "09",
      "my-trips",
      "⑨ 点这里回到已有的一趟",
      [{ testId: "my-trips-open", action: "打开这趟" }],
      "这一格只列服务器认给你这个人的行程；换手机或重新登录之后，先从这一步回去。",
    );

    writeFileSync(
      MANIFEST,
      JSON.stringify({ generatedAt: new Date().toISOString(), shots }, null, 2) + "\n",
      "utf-8",
    );
    console.log(`guide manifest -> ${MANIFEST} (${shots.length} 张)`);
    expect(shots.length).toBe(9);
    for (const shot of shots) {
      expect(
        shot.targets.filter((item) => item.box).length,
        `${shot.id} 这张没有量到任何可圈的目标，标注就会画空`,
      ).toBeGreaterThan(0);
      /* 教程圈出去的东西，必须在这张图上真的看得见：祖先的入场动画已经放完、自己不是
         visibility:hidden、并且真的写着字。这一道闸是上一版那张"白屏"换来的。 */
      for (const target of shot.targets) {
        const paint = target.paint;
        expect(paint, `${shot.id} 的 ${target.testId} 没量到渲染状态`).toBeTruthy();
        expect(paint!.fadedBy, `${shot.id} 的 ${target.testId} 截在入场动画中途`).toEqual([]);
        expect(
          [paint!.visibility === "visible", Number(paint!.opacity) >= 0.4,
           paint!.paintedText.length > 0],
          `${shot.id} 的 ${target.testId} 在截图那一刻没画全：${JSON.stringify(paint)}`,
        ).toEqual([true, true, true]);
      }
      /* 每一张都不许把字典缺键拍进教程：这一条正是第 ⑥ 张 `catalog.count.zero` 换来的。 */
      expect(shot.paintedKeys, `${shot.id} 这张屏上印着机器键`).toEqual([]);
    }
  });
});
