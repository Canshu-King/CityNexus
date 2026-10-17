/* Issue #27（Qoder P0）：同一台手机上换人，不得回放上一位旅行者的 AI 工具轨迹。
 *
 * 这一条测的是真实缺陷链，不是样式：
 *   `AgentComposer.tsx:58` 用 `citynexus.copilot.history.<journeyId>` 把整段对话（含
 *   `response.agent_run` 与它的 `initial_events`）从 localStorage 播回来；
 *   `CopilotDock.tsx:170 / :185` 再用 `citynexus.native-hermes.timeline.<journeyId>.<runId>`
 *   把事件表播回来。两把键都只绑行程号 —— 而行程是成员共用的，所以"换人不换行程"正好命中。
 *   服务器审计时间线在 `:203-216` 被 `.catch(() => {})` 静默吞掉，于是 403 到了屏幕上仍是
 *   "正在核对行程事实"（`:403-409` 的空态文案），既没有错误也没有停。
 *
 * 身份怎么模拟：这台部署里没有任何接口告诉前端"当前签名查看者是谁"（查过：只有
 * `/members`、`/share-grants`、`/acl/roles`、`/member-role-limits` 这类"这一趟有谁"的门，
 * 没有 whoami/me/session 那一类）。所以两个成员用**授权答复**来区分：A 那一臂服务器答 200 并给
 * A 的事件；B 那一臂同一 run 的时间线与状态都答 403。这是可审计的模拟双成员，
 * **不代替 live**：它证明的是"前端不再从盘上回放"与"403 不再被渲染成还在分析"。
 *
 * 跑法：私有 runner `playwright.qoder27-boundary.config.ts`，默认打指挥线的开发端口
 * （:8121 前端 + :8011 后端），不碰共享的 :8000/:4781/:4782/:8693。
 */
import { test, expect, type BrowserContext, type Page } from "@playwright/test";

const BASE = process.env.CNX_E2E_BASE ?? "http://127.0.0.1:8121";
const JOURNEY = process.env.CNX_E2E_JOURNEY ?? "22222222-2222-4222-8222-222222222222";
const RUN_ID = "run-qoder27-boundary-1";
/* 只属于成员 A 那一趟工具调用的记号：friendly_label 会原样上屏（工具名不在词表里时，
 * 屏上那行就是它），所以它既是断言目标，也是"这条确实来自 A"的证据。 */
const A_TOKEN = "A-ONLY-9f4c2b7e";

const HERMES = `**/api/v1/journeys/${JOURNEY}/agent/hermes/runs/${RUN_ID}`;

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

function copilotRunPayload() {
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
      timeline_url: `${BASE}/api/v1/journeys/${JOURNEY}/agent/hermes/runs/${RUN_ID}/timeline`,
      initial_events: [aEvent(1), aEvent(2)],
    },
  };
}

/** 同一台设备的起手：行程指针、主题、语言都按手机那一档摆好。 */
async function seedDevice(ctx: BrowserContext) {
  await ctx.addInitScript((journeyId) => {
    window.localStorage.setItem("citynexus.v8.journey_id", journeyId);
    window.localStorage.setItem("citynexus.theme", "light");
    window.localStorage.setItem("citynexus.locale", "zh-CN");
  }, JOURNEY);
}

/** 成员 A：这一趟的工具轨迹服务器认，200 给事件。 */
async function stubAsMemberA(ctx: BrowserContext) {
  await ctx.route(`**/api/v1/journeys/${JOURNEY}/copilot/messages`, (r) =>
    r.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(copilotRunPayload()) }));
  await ctx.route(HERMES + "/timeline", (r) =>
    r.fulfill({
      status: 200, contentType: "application/json",
      body: JSON.stringify({ run_id: RUN_ID, journey_id: JOURNEY, runtime_identity: "HERMES_NATIVE",
        events: [aEvent(1), aEvent(2), aEvent(3)] }),
    }));
  await ctx.route(HERMES, (r) =>
    r.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ run_id: RUN_ID, status: "RUNNING" }) }));
}

/** 成员 B：同一个 run，服务器按授权拒绝（403）。这是换人之后真实会发生的那一类答复。 */
async function stubAsMemberB(ctx: BrowserContext) {
  const denied = JSON.stringify({ detail: "JOURNEY_MEMBER_FORBIDDEN", reason: "当前会话不是这一趟的成员" });
  await ctx.route(HERMES + "/timeline", (r) => r.fulfill({ status: 403, contentType: "application/json", body: denied }));
  await ctx.route(HERMES, (r) => r.fulfill({ status: 403, contentType: "application/json", body: denied }));
  await ctx.route(`**/api/v1/journeys/${JOURNEY}/copilot/messages`, (r) =>
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

async function openCopilot(page: Page) {
  await page.goto(BASE + "/", { waitUntil: "networkidle" });
  await page.waitForTimeout(1800);
  await enterDrawerTarget(page, "agent");
  await expect(page.getByTestId("v15-copilot")).toBeVisible();
}

async function replayKeysOnDisk(page: Page) {
  return page.evaluate(() =>
    Object.keys(window.localStorage).filter((k) =>
      /^citynexus\.(copilot\.history|native-hermes\.timeline)\./.test(k)));
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
      const ctxA = await browser.newContext({ viewport: profile.viewport, hasTouch: profile.hasTouch, isMobile: profile.isMobile });
      await seedDevice(ctxA);
      await stubAsMemberA(ctxA);
      const pA = await ctxA.newPage();
      await openCopilot(pA);
      await pA.getByTestId("v15-copilot-input").fill("帮我核对今天的安排");
      await pA.getByTestId("v15-copilot-submit").click();
      await expect(pA.getByText(`${A_TOKEN}-1`)).toBeVisible();
      /* 记下这一臂有没有往盘上落东西：改前它是 > 0（缺陷的载体），改后它必须是 0。 */
      const keysAfterA = await replayKeysOnDisk(pA);
      await pA.screenshot({ path: `e2e/.qoder27-memberA-${profile.name.slice(0, 2)}.png` });
      const deviceState = await ctxA.storageState();
      await ctxA.close();

      const ctxB = await browser.newContext({
        viewport: profile.viewport, hasTouch: profile.hasTouch, isMobile: profile.isMobile, storageState: deviceState,
      });
      await seedDevice(ctxB);
      await stubAsMemberB(ctxB);
      const pB = await ctxB.newPage();
      await openCopilot(pB);
      /* B 什么都没发。任何一行 A 的记号出现在屏上，都是这一条要拦的事。 */
      for (const seq of [1, 2, 3]) {
        await expect(pB.getByText(`${A_TOKEN}-${seq}`), `成员 B 看到了成员 A 的第 ${seq} 行工具轨迹`)
          .toHaveCount(0);
      }
      await pB.screenshot({ path: `e2e/.qoder27-memberB-${profile.name.slice(0, 2)}.png` });
      await ctxB.close();

      expect(keysAfterA.length, "A 那一臂本不该把会话与事件表写到 localStorage").toBe(0);
    });
  }

  test("服务器答 403 时，屏上是可恢复的说明，不是「还在核对事实」", async ({ browser }) => {
    const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, hasTouch: true, isMobile: true });
    await seedDevice(ctx);
    await stubAsMemberA(ctx);
    const p = await ctx.newPage();
    await openCopilot(p);
    await p.getByTestId("v15-copilot-input").fill("帮我核对今天的安排");
    await p.getByTestId("v15-copilot-submit").click();
    await expect(p.getByText(`${A_TOKEN}-1`)).toBeVisible();
    /* 换人：这台设备之后的答复全部改成 403，然后在同一页里走出再走回同一个行程入口。
     * 这里刻意不整页刷新：刷新会把本页内存一起清掉，那是第一条用例量过的路；
     * 这一条要量的是"同一页里回到同一个入口"时被拒绝会不会仍被演成还在分析。
     * （第一版我就是用了整页刷新，于是那几句断言其实是靠一片空白通过的——已改，
     * 并补上"必须真看得见可恢复说明"的正面断言。） */
    await stubAsMemberB(ctx);
    await enterDrawerTarget(p, "hub");
    await p.waitForTimeout(900);
    await enterDrawerTarget(p, "agent");
    await p.waitForTimeout(1600);
    const body = await p.locator('[data-testid="v15-copilot"]').innerText();
    expect(body, "被拒绝之后仍写着「正在核对行程事实」，等于把 403 报成还在分析").not.toMatch(/正在核对|checking/i);
    /* 正面断言：这一臂必须真把可恢复的说明摆出来。只有"没有那句错话"是不够的——
     * 那可以靠一片空白通过。 */
    await expect(p.getByTestId("agent-history-error"), "服务器拒绝之后屏上没有可恢复的说明").toBeVisible();
    await p.screenshot({ path: "e2e/.qoder27-forbidden.png" });
    await ctx.close();
  });
});
