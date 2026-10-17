/* Issue #27（Qoder P0）：同一台手机上换人，不得回放上一位旅行者的 AI 工具轨迹。
 *
 * 这一条测的是真实缺陷链，不是样式：
 *   `AgentComposer.tsx` 用 `citynexus.copilot.history.<journeyId>` 把整段对话（含
 *   `response.agent_run` 与它的 `initial_events`）从 localStorage 播回来；
 *   `CopilotDock.tsx` 再用 `citynexus.native-hermes.timeline.<journeyId>.<runId>`
 *   把事件表播回来。两把键都只绑行程号 —— 而行程是成员共用的，所以"换人不换行程"正好命中。
 *   服务器审计时间线原先被 `.catch(() => {})` 静默吞掉，于是 403 到了屏幕上仍是
 *   "正在核对行程事实"，既没有错误也没有停。
 *
 * 身份怎么模拟：这台部署里没有任何接口告诉前端"当前签名查看者是谁"（查过：只有
 * `/members`、`/share-grants`、`/acl/roles`、`/member-role-limits` 这类"这一趟有谁"的门，
 * 没有 whoami/me/session 那一类）。所以两个成员用**授权答复**来区分：A 那一臂服务器答 200 并给
 * A 的事件；B 那一臂同一 run 的时间线与状态都答 403。这是可审计的模拟双成员，
 * **不代替 live**：它证明的是"前端不再从盘上回放"与"403 不再被渲染成还在分析"。
 *
 * 服务器与行程都不能写死。第一版两处都写死了，于是这条被验收配置 `playwright.config.ts`
 * 收走之后三臂全红——它量的是另一台服务器上的另一条行程。现在的口径：
 *   · 端口跟着 `test.info().project.use.baseURL` 走；私有 runner 不给 baseURL，才退回指挥线开发端口；
 *   · 行程号先读这一次运行自己种进 storageState 的指针，没有才向 `GET /api/v1/journeys` 要第一条，
 *     再没有才退回演示夹具。
 *
 * 跑法：私有 runner `playwright.qoder27-boundary.config.ts`（默认 :8121 前端 + :8011 后端），
 * 或验收配置 `playwright.config.ts --project=chromium -g "Issue #27"`。共享的 :8000/:4781/:4782/:8693 一律不碰。
 */
import { test, expect, type BrowserContext, type Page } from "@playwright/test";

const FALLBACK_JOURNEY = "22222222-2222-4222-8222-222222222222";
const RUN_ID = "run-qoder27-boundary-1";
/* 只属于成员 A 那一趟工具调用的记号：friendly_label 会原样上屏（工具名不在词表里时，
 * 屏上那行就是它），所以它既是断言目标，也是"这条确实来自 A"的证据。 */
const A_TOKEN = "A-ONLY-9f4c2b7e";

/** 打哪台服务器：跟着这一次运行的 baseURL 走。 */
function baseOf(): string {
  const fromProject = test.info().project.use?.baseURL;
  const raw = (typeof fromProject === "string" && fromProject) || process.env.CNX_E2E_BASE || "http://127.0.0.1:8121";
  return raw.replace(/\/+$/, "");
}

/** 用哪条行程：先读这次运行种下的指针，再问服务器，最后才用夹具。 */
async function resolveJourney(page: Page): Promise<string> {
  return page.evaluate(async (fallback) => {
    const stored = window.localStorage.getItem("citynexus.v8.journey_id");
    if (typeof stored === "string" && stored.length > 0) return stored;
    try {
      const res = await fetch("/api/v1/journeys");
      const rows = await res.json();
      const first = Array.isArray(rows) && typeof rows[0]?.id === "string" ? rows[0].id : null;
      if (first) window.localStorage.setItem("citynexus.v8.journey_id", first);
      return first ?? fallback;
    } catch {
      return fallback;
    }
  }, FALLBACK_JOURNEY);
}

function hermesGlob(journey: string): string {
  return `**/api/v1/journeys/${journey}/agent/hermes/runs/${RUN_ID}`;
}

function aEvent(sequence: number): Record<string, unknown> {
  return {
    event_type: "tool.started",
    run_id: RUN_ID,
    event_id: `evt-a-${sequence}`,
    sequence,
    /* 故意用词表里没有的工具名：屏上那行会退回 friendly_label，
     * 于是这个记号只可能来自被回放的那一份，不可能由本页自己拼出来。 */
    tool_name: "qoder27_probe_tool",
    friendly_label: `${A_TOKEN}-${sequence}`,
    status: "RUNNING",
    timestamp: "2026-10-17T06:30:00+00:00",
    duration_ms: 120,
    source: "HERMES_NATIVE",
  };
}

function copilotRunPayload(base: string, journey: string) {
  return {
    message: "已经替你把这一趟看过了。",
    intent: "INSPECT",
    confidence: 0.9,
    protected_commitments: [],
    evidence: {},
    recommendations: [],
    agent_run: {
      run_id: RUN_ID,
      status: "RUNNING",
      runtime_identity: "HERMES_NATIVE",
      provider_key: "qoder27_probe",
      model_key: "probe",
      events_url: "",
      timeline_url: `${base}/api/v1/journeys/${journey}/agent/hermes/runs/${RUN_ID}/timeline`,
      initial_events: [aEvent(1), aEvent(2)],
    },
  };
}

/** 这台设备的起手：只摆主题与语言。行程指针刻意不写——它属于这一次运行。 */
async function seedDevice(ctx: BrowserContext) {
  await ctx.addInitScript(() => {
    window.localStorage.setItem("citynexus.theme", "light");
    window.localStorage.setItem("citynexus.locale", "zh-CN");
  });
}

/** 成员 A：这一趟的工具轨迹服务器认，200 给事件。 */
async function stubAsMemberA(ctx: BrowserContext, base: string, journey: string) {
  await ctx.route(`**/api/v1/journeys/${journey}/copilot/messages`, (r) =>
    r.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(copilotRunPayload(base, journey)) }));
  await ctx.route(hermesGlob(journey) + "/timeline", (r) =>
    r.fulfill({
      status: 200, contentType: "application/json",
      body: JSON.stringify({ run_id: RUN_ID, journey_id: journey, runtime_identity: "HERMES_NATIVE",
        events: [aEvent(1), aEvent(2), aEvent(3)] }),
    }));
  await ctx.route(hermesGlob(journey), (r) =>
    r.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ run_id: RUN_ID, status: "RUNNING" }) }));
}

/** 成员 B：同一个 run，服务器按授权拒绝（403）。这是换人之后真实会发生的那一类答复。 */
async function stubAsMemberB(ctx: BrowserContext, journey: string) {
  const denied = JSON.stringify({ detail: "JOURNEY_MEMBER_FORBIDDEN", reason: "当前会话不是这一趟的成员" });
  await ctx.route(hermesGlob(journey) + "/timeline", (r) => r.fulfill({ status: 403, contentType: "application/json", body: denied }));
  await ctx.route(hermesGlob(journey), (r) => r.fulfill({ status: 403, contentType: "application/json", body: denied }));
  await ctx.route(`**/api/v1/journeys/${journey}/copilot/messages`, (r) =>
    r.fulfill({ status: 403, contentType: "application/json", body: denied }));
}

/** 手机档那一档只能开抽屉走入口（桌面导航项在窄视口没有包围盒）。 */
async function enterDrawerTarget(page: Page, key: string) {
  await page.evaluate(() => {
    const e = document.querySelector('[data-testid="v8-mobile-menu"]');
    if (e) (e as HTMLElement).click();
  });
  await page.waitForTimeout(700);
  await page.evaluate((k) => {
    const e = document.querySelector(`[data-testid="v8-drawer-entry-${k}"]`);
    if (e) (e as HTMLElement).click();
  }, key);
  await page.waitForTimeout(1200);
}

async function openCopilot(page: Page, base: string) {
  await page.goto(base + "/", { waitUntil: "networkidle" });
  await page.waitForTimeout(1800);
  await enterDrawerTarget(page, "agent");
  await expect(page.getByTestId("v15-copilot")).toBeVisible();
}

async function replayKeysOnDisk(page: Page) {
  return page.evaluate(() =>
    Object.keys(window.localStorage).filter((k) =>
      /^citynexus\.(copilot\.history|native-hermes\.timeline)\./.test(k)));
}

/* 一张整屏照 + 一张 copilot 面板自己的照。
 * 只有整屏照会漏证：面板在窄视口里落在折叠线以下，第一版我截到的"改前现场"
 * 其实看不见被回放的那几行工具轨迹 —— 断言红了，图却是干净的，这种图不能交。 */
async function shoot(page: Page, name: string) {
  await page.screenshot({ path: `e2e/${name}.png`, fullPage: true });
  const dock = page.getByTestId("v15-copilot");
  await dock.scrollIntoViewIfNeeded();
  await dock.screenshot({ path: `e2e/${name}-dock.png` });
}

test.describe("Issue #27 换人不换行程：Agent 轨迹不得从盘上回放到第二个人", () => {
  test.setTimeout(180_000);

  /* 工单要求"桌面、390×844 手机端各实际走一次"，所以这一条按两档视口各跑一遍。 */
  const PROFILES = [
    { name: "桌面 1280×900", viewport: { width: 1280, height: 900 }, hasTouch: false, isMobile: false },
    { name: "手机 390×844", viewport: { width: 390, height: 844 }, hasTouch: true, isMobile: true },
  ];

  for (const profile of PROFILES) {
    test(`A 走完留下缓存 → 同一台设备换 B 回到同一入口：屏上不得出现 A 的任一工具行（${profile.name}）`, async ({ browser }) => {
      const base = baseOf();
      const ctxA = await browser.newContext({ viewport: profile.viewport, hasTouch: profile.hasTouch, isMobile: profile.isMobile });
      await seedDevice(ctxA);
      const pProbe = await ctxA.newPage();
      await pProbe.goto(base + "/", { waitUntil: "networkidle" });
      const journey = await resolveJourney(pProbe);
      console.log(`[qoder27] base=${base} journey=${journey}`);
      await pProbe.close();
      await stubAsMemberA(ctxA, base, journey);

      const pA = await ctxA.newPage();
      await openCopilot(pA, base);
      await pA.getByTestId("v15-copilot-input").fill("帮我核对今天的安排");
      await pA.getByTestId("v15-copilot-submit").click();
      await expect(pA.getByText(`${A_TOKEN}-1`)).toBeVisible();
      /* 记下这一臂有没有往盘上落东西：改前它是 > 0（缺陷的载体），改后它必须是 0。 */
      const keysAfterA = await replayKeysOnDisk(pA);
      await shoot(pA, `.qoder27-memberA-${profile.name.slice(0, 2)}`);
      const deviceState = await ctxA.storageState();
      await ctxA.close();

      const ctxB = await browser.newContext({
        viewport: profile.viewport, hasTouch: profile.hasTouch, isMobile: profile.isMobile, storageState: deviceState,
      });
      await seedDevice(ctxB);
      await stubAsMemberB(ctxB, journey);
      const pB = await ctxB.newPage();
      await openCopilot(pB, base);
      /* 截图必须断在断言之前：断言一红，用例当场中止，那张"改前屏上真的放着 A 的行"
         的现场照就永远留不下来（第一版我把截图放在断言之后，于是改前那一臂留下的
         memberB 图其实是改后那一次没被覆盖的旧图 —— 现场证据不能靠文件没被覆盖）。 */
      await pB.waitForTimeout(1500);
      await shoot(pB, `.qoder27-memberB-${profile.name.slice(0, 2)}`);
      /* B 什么都没发。任何一行 A 的记号出现在屏上，都是这一条要拦的事。 */
      for (const seq of [1, 2, 3]) {
        await expect(pB.getByText(`${A_TOKEN}-${seq}`), `成员 B 看到了成员 A 的第 ${seq} 行工具轨迹`)
          .toHaveCount(0);
      }
      await ctxB.close();

      expect(keysAfterA.length, "A 那一臂本不该把会话与事件表写到 localStorage").toBe(0);
    });
  }

  test("服务器答 403 时，屏上是可恢复的说明，不是「还在核对事实」", async ({ browser }) => {
    const base = baseOf();
    const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, hasTouch: true, isMobile: true });
    await seedDevice(ctx);
    const pProbe = await ctx.newPage();
    await pProbe.goto(base + "/", { waitUntil: "networkidle" });
    const journey = await resolveJourney(pProbe);
    await pProbe.close();
    await stubAsMemberA(ctx, base, journey);
    const p = await ctx.newPage();
    await openCopilot(p, base);
    await p.getByTestId("v15-copilot-input").fill("帮我核对今天的安排");
    await p.getByTestId("v15-copilot-submit").click();
    await expect(p.getByText(`${A_TOKEN}-1`)).toBeVisible();
    /* 换人：这台设备之后的答复全部改成 403，然后在同一页里走出再走回同一个入口。
     * 这里刻意不整页刷新：刷新会把本页内存一起清掉，那是第一条用例量过的路；
     * 这一条要量的是"同一页里回到同一个入口"时被拒绝会不会仍被演成还在分析。
     * （第一版我就是用了整页刷新，于是那几句断言其实是靠一片空白通过的——已改，
     * 并补上"必须真看得见可恢复说明"的正面断言。） */
    await stubAsMemberB(ctx, journey);
    await enterDrawerTarget(p, "hub");
    await p.waitForTimeout(900);
    await enterDrawerTarget(p, "agent");
    await p.waitForTimeout(1600);
    /* 同一条规矩：现场照先落，再断言。 */
    await shoot(p, ".qoder27-forbidden");
    const body = await p.locator('[data-testid="v15-copilot"]').innerText();
    /* 空态那句和块头那两句都在禁列里：块头原先无论服务器答什么都写
     * 「正在为你处理 / 已按你的行程事实执行」，那正是工单点名的"把 403 演成还在分析"。
     * 注意这里不能松到「正在处理」——那一列里每一行本来就写着它自己那条事件的用时。 */
    expect(body, "被拒绝之后屏上仍写着还在分析/已按事实执行这一类话")
      .not.toMatch(/正在核对|正在为你处理|已按你的行程事实|checking your journey|working on your request|ran against your journey/i);
    /* 正面断言：这一臂必须真把可恢复的说明摆出来。只有"没有那句错话"是不够的——
     * 那可以靠一片空白通过。 */
    await expect(p.getByTestId("agent-history-error"), "服务器拒绝之后屏上没有可恢复的说明").toBeVisible();
    /* 那句说明必须说清是谁拒的：只写"出错了"的兜底既不可恢复，也不区分 403 与断网。 */
    await expect(p.getByTestId("agent-history-error")).toContainText("403");
    await ctx.close();
  });
});
