/* Issue #31 A/B（Qoder）：真签发的会话 + 建完行程立刻进可操作的 Today。
 *
 * 这一条打的是**真后端**（`playwright.qoder31-session.config.ts` 现起的一台 uvicorn，
 * 加载时现生成一次性 `CITYNEXUS_TRAVELER_AUTH_SECRET`）。所以这里断言的不是"页面以为服务器会怎么答"，
 * 而是服务器真的签了一枚、真的按签名拒了一次。唯一注入的是 B 臂里那一记 6 秒延迟：
 * 它落在 `route.fallback()` 之前，请求仍由真后端答，只是把可选住宿查询故意拖慢，
 * 让"不在关键路径上"这件事可测——不拖慢就只能靠运气量。
 *
 * 覆盖 Issue #31 A 点名的四件事，逐条对应：
 *   1. 新建 Traveler 之后拿到可被服务器认出的签名会话，且令牌只在这一个标签页的
 *      `sessionStorage` 里（绝不进 `localStorage`），后续请求确实带上它；
 *   2. 同一个签名旅行者可以开第二趟 Journey，而不再新造一个人；
 *   3. 旧 Journey 指针不再授权：设备上留着的 uuid 换到第二个人手里，服务器按签名拒
 *      `JOURNEY_POINTER_NOT_OURS`，前端擦掉那枚指针与该行程的 Agent 记录，但**不**把
 *      第二个人登出——错的是上一位留下的指针，不是她；
 *   4. 凭证本身无效时令牌与 Agent 记录一起擦；
 *   5. 反控臂：不带凭证的请求行为逐字不变（共享预览不会因为开身份而变黑）。
 */
import { expect, test, type Page } from "@playwright/test";

const JOURNEY_POINTER = "citynexus.v8.journey_id";
const SESSION_POINTER = "citynexus.v8.traveler.session";
/* 改前这两串会把整段对话与工具轨迹按行程号落到盘上（Issue #27 的载体，也是这里要跟着擦的）。 */
const LEGACY_TRANSCRIPT = "citynexus.copilot.history.";
const LEGACY_TIMELINE = "citynexus.native-hermes.timeline.";

function baseOf(): string {
  const fromProject = test.info().project.use?.baseURL;
  const raw = (typeof fromProject === "string" && fromProject) || process.env.CNX_E2E_BASE || "http://127.0.0.1:8131";
  return raw.replace(/\/+$/, "");
}

/** 每一臂起手：中文、亮档、清掉上一臂留在盘上的东西（同一 context 会串）。
 *
 *  清盘只做一次：`addInitScript` 每一次导航都会重放，第一版我把「清 storage」写在里面，
 *  于是臂二 reload 时把自己刚拿到的签名会话擦了、臂五 reload 时把行程指针擦了——量的就不再
 *  是产品，而是我的夹具。`window.name` 跟着标签页活，用它当一次性开关。 */
async function seedPhone(page: Page, init: Record<string, string> = {}) {
  await page.context().addInitScript((bag) => {
    if (window.name === "cnx31-seeded") return;
    try {
      localStorage.clear();
      sessionStorage.clear();
    } catch {
      /* 空设备上没什么可清的 */
    }
    localStorage.setItem("citynexus.theme", "light");
    localStorage.setItem("citynexus.locale", "zh-CN");
    for (const [key, value] of Object.entries(bag)) {
      if (key.startsWith("ss:")) sessionStorage.setItem(key.slice(3), value);
      else localStorage.setItem(key, value);
    }
    window.name = "cnx31-seeded";
  }, init);
  await page.emulateMedia({ colorScheme: "light", media: "screen" });
}

async function shoot(page: Page, name: string) {
  /* 现场照先落，再断言：断言一红这一轮当场中止，图就永远留不下来。 */
  await page.screenshot({ path: `e2e/.qoder31-${name}.png`, fullPage: true });
}

/** 向导可能还停在第 3 页：`step` 活在壳里，重新打开并不会回到第 1 页（第一版我就把 fill
 *  拍在一个根本没渲染的输入框上，量到的是 180 秒超时）。按「改这一项：目的地」跳回去。 */
async function ensureStep1(page: Page) {
  await expect(page.getByTestId("trial-setup")).toBeVisible({ timeout: 25_000 });
  if (await page.getByTestId("trial-city").isVisible().catch(() => false)) return;
  await page.getByRole("button", { name: "改这一项：目的地" }).click();
  await expect(page.getByTestId("trial-city"), "跳不回第 1 页").toBeVisible({ timeout: 15_000 });
}

async function fillStep1AndReview(
  page: Page,
  city: string,
  arrival: string,
  departure: string,
) {
  await page.getByTestId("trial-city").fill(city);
  await page.getByTestId("trial-arrival").fill(arrival);
  await page.getByTestId("trial-departure").fill(departure);
  await page.getByTestId("trial-next").click();
  await page.waitForTimeout(300);
  await page.getByTestId("trial-next").click();
  await expect(page.getByTestId("trial-create")).toBeVisible({ timeout: 15_000 });
}

/** 按下创建并等到服务器真的回一枚行程号。
 *
 *  B 改完之后指针写得比屏幕更早：拿"指针非空"当第二趟的终点，会被第一趟那枚旧指针**立刻**满足
 *  （第四版就是这么量出"行程 1 枚"的假阴性）。所以要等的是响应本身，不是屏幕上的余温。 */
async function createAndAwaitJourney(page: Page): Promise<string> {
  const answer = page.waitForResponse(
    (res) => res.request().method() === "POST" && /\/api\/v1\/journeys$/.test(res.url()),
    { timeout: 60_000 },
  );
  await page.getByTestId("trial-create").click();
  const res = await answer;
  expect(res.status(), "创建行程没有得到 201").toBe(201);
  const id = String(((await res.json().catch(() => ({}))) as { id?: string }).id ?? "");
  expect(id, "创建回来的答案里没有行程号").not.toBe("");
  return id;
}

/** 真走一遍创建向导（与 e2e/qoder-onboarding-failure.spec.ts 同一把入口）。 */
async function walkTheWizard(page: Page, city: string, arrival: string, departure: string) {
  await page.goto("/v8", { waitUntil: "load" });
  await ensureStep1(page);
  await fillStep1AndReview(page, city, arrival, departure);
}

async function readBack(page: Page, key: string, where: "local" | "session") {
  return page.evaluate(
    ([k, store]) => {
      const bag = store === "session" ? window.sessionStorage : window.localStorage;
      return bag ? bag.getItem(k) : null;
    },
    [key, where] as const,
  );
}

/** 现读这台部署能不能签：`session_state` 由服务器说，不由测试假设。 */
async function signingAvailable(page: Page): Promise<boolean> {
  const answer = await page.request.post(`${baseOf()}/api/v1/travelers`, {
    data: { display_name: "Issue 31 probe", locale: "zh-CN", timezone: "Asia/Shanghai" },
  });
  expect(answer.status(), answer.text()).toEqual(201);
  const body = await answer.json();
  return body.session_state === "SIGNED" && typeof body.access_token === "string";
}

test.describe("Issue #31 A/B：真签发的旅行者会话，与不再被住宿查询扣住的 Today", () => {
  test.setTimeout(180_000);

  test("建完人就把会话交给这一个标签页：令牌只在 sessionStorage，之后的请求真的带着它", async ({ page }) => {
    await seedPhone(page);
    await walkTheWizard(page, "Tianjin", "Tianjin West Station", "Tianjin Binhai Airport");

    const bearerSeen: string[] = [];
    page.on("request", (req) => {
      const header = req.headers()["authorization"];
      if (header && req.url().includes("/api/v1/")) bearerSeen.push(header);
    });

    await page.getByTestId("trial-create").click();
    await page.waitForFunction(() => !!localStorage.getItem("citynexus.v8.journey_id"), null, { timeout: 40_000 });

    const stored = await readBack(page, SESSION_POINTER, "session");
    expect(stored, "创建之后 sessionStorage 里没有会话").not.toBeNull();
    const session = JSON.parse(stored as string) as { travelerId: string; token: string };
    expect(session.token.split(".").length, "令牌形状不对（应为 payload.签名 两段）").toBe(2);

    /* 令牌不能落到盘上：localStorage 活得比一次交接久，那是 Issue #27 整件事的起因。 */
    const leaked = await page.evaluate((token) =>
      Object.keys(window.localStorage).filter((k) => (window.localStorage.getItem(k) ?? "").includes(token)),
    session.token);
    const diskKeys = await page.evaluate(() => Object.keys(window.localStorage));
    await shoot(page, "signed-session-after-create");
    expect(leaked, `令牌出现在 localStorage 的键里：${leaked.join(", ")}`).toEqual([]);
    expect(diskKeys.length, "localStorage 键数读不出来").toBeGreaterThan(0);
    expect(bearerSeen.length, "创建之后的请求一次都没带 Authorization").toBeGreaterThan(0);
    /* 只比前缀，而且只取 "Bearer " 这 7 个字符：整串相等一旦失败，Playwright 会把令牌打进日志
     * ——令牌不该出现在任何日志里。 */
    expect(bearerSeen[0].slice(0, 7), "Authorization 不是 Bearer 形状").toBe("Bearer ");
    expect(bearerSeen[0].slice(7, 13), "带的不是这一枚令牌").toBe(session.token.slice(0, 6));
  });

  test("同一个签名旅行者开第二趟：不再新造一个人", async ({ page }) => {
    await seedPhone(page);
    await walkTheWizard(page, "Tianjin", "Tianjin West Station", "Tianjin Binhai Airport");

    let travelerPosts = 0;
    page.on("request", (req) => {
      if (req.method() === "POST" && /\/api\/v1\/travelers$/.test(req.url())) travelerPosts += 1;
    });

    const firstId = await createAndAwaitJourney(page);
    const firstSession = await readBack(page, SESSION_POINTER, "session");
    expect(firstSession, "第一趟之后没有签名会话").not.toBeNull();
    expect(travelerPosts, "第一趟没造人").toBe(1);

    /* B 改完之后指针写得比屏幕更早：这一臂要按 Today 真的能操作了再找入口，
     * 否则会量的都是自己抢在渲染之前读到的那一瞬间（第一版就是这么假阴性了一次）。 */
    await expect(page.getByTestId("hub-secondary-actions"), "Today 没打开").toBeVisible({ timeout: 20_000 });

    /* 第二趟的入口：Today 上那一颗「试用其他城市」（`hub-new-journey`，按钩子不按文案）。 */
    const entry = page.getByTestId("hub-new-journey");
    let route = "today-button";
    if (await entry.isVisible().catch(() => false)) {
      await entry.scrollIntoViewIfNeeded();
      await entry.click();
    } else {
      route = "pointer-cleared-reload";
      await page.evaluate(() => localStorage.removeItem("citynexus.v8.journey_id"));
      await page.goto("/v8", { waitUntil: "load" });
    }
    await ensureStep1(page);
    await fillStep1AndReview(page, "Beijing", "Beijing South Station", "Beijing Capital Airport");
    const secondId = await createAndAwaitJourney(page);
    await expect(page.getByTestId("hub-secondary-actions"), "第二趟之后 Today 没回来").toBeVisible({ timeout: 20_000 });
    const secondRaw = await readBack(page, SESSION_POINTER, "session");
    await shoot(page, "two-journeys-one-traveler");
    console.log(`第二趟的入口：${route} | 造人次数 ${travelerPosts} | 行程两枚 ${firstId.slice(0, 8)}… / ${secondId.slice(0, 8)}…`);
    /* 只比"人 + 凭证"这一对：挂载时那一次核身会把服务器给的 `expires_at` 补回记录里，
     * 序列化后的字符串本来就该变。断言写成整串相等，量的就是格式而不是身份了
     * （而且失败信息会把令牌打进日志——这里刻意一个字符都不打）。 */
    const pair = (raw: string | null) => {
      if (!raw) return null;
      const parsed = JSON.parse(raw) as { travelerId: string; token: string };
      return `${parsed.travelerId}|${parsed.token.slice(0, 6)}`;
    };
    expect(travelerPosts, "第二趟又造了一个人：签名会话没被复用").toBe(1);
    expect(pair(secondRaw), "第二趟换了一个签名旅行者").toBe(pair(firstSession));
    expect(secondId, "第二趟拿回的是同一枚行程号").not.toBe(firstId);
  });

  test("换人不换行程：旧指针被服务器按签名拒掉，指针擦了就绪、人不被登出", async ({ page }) => {
    /* 先真造一个人、真建一趟行程，拿到真的行程号（不是写死的夹具）。 */
    const probe = await page.request.post(`${baseOf()}/api/v1/travelers`, {
      data: { display_name: "Issue 31 owner", locale: "zh-CN", timezone: "Asia/Shanghai" },
    });
    expect(probe.status(), probe.text()).toEqual(201);
    const owner = await probe.json();
    expect(owner.session_state, "这台部署没开签发，这一臂量不到东西").toEqual("SIGNED");
    const trip = await page.request.post(`${baseOf()}/api/v1/journeys`, {
      headers: { Authorization: `Bearer ${owner.access_token}`, "Content-Type": "application/json" },
      data: {
        traveler_id: owner.id,
        title: "Tianjin · journey",
        city_code: "CN-TIANJIN",
        timezone: "Asia/Shanghai",
        start_at: "2026-11-01T09:00:00+08:00",
        end_at: "2026-11-02T18:00:00+08:00",
        budget: { amount_minor: 120000, currency: "CNY" },
        stay_budget: { amount_minor: 60000, currency: "CNY" },
        party_size: 2,
        occupancy: { adults: 2, rooms: 1 },
        arrival_anchor: { at: "2026-11-01T09:00:00+08:00", location: "Tianjin West Station" },
        departure_anchor: { at: "2026-11-02T18:00:00+08:00", location: "Tianjin Binhai Airport" },
      },
    });
    expect(trip.status(), trip.text()).toEqual(201);
    const journey = await trip.json();

    /* 第二个人接手同一台设备：她有自己的签名会话，指针却还是上一位那趟。 */
    const second = await page.request.post(`${baseOf()}/api/v1/travelers`, {
      data: { display_name: "Issue 31 next holder", locale: "zh-CN", timezone: "Asia/Shanghai" },
    });
    const guest = await second.json();
    expect(guest.session_state).toEqual("SIGNED");

    let refused: { status: number; reason: string | null } | null = null;
    page.on("response", async (res) => {
      if (/\/api\/v1\/journeys\/[^/]+\/experience$/.test(res.url()) && res.status() === 403) {
        const body = await res.json().catch(() => ({}));
        refused = { status: res.status(), reason: body?.error?.reason_code ?? null };
      }
    });

    const legacyKey = `${LEGACY_TRANSCRIPT}${journey.id}`;
    const legacyRun = `${LEGACY_TIMELINE}${journey.id}.run-31`;
    await seedPhone(page, {
      [JOURNEY_POINTER]: journey.id,
      ["ss:" + SESSION_POINTER]: JSON.stringify({ travelerId: guest.id, token: guest.access_token, expiresAt: null }),
    });
    await page.goto("/v8", { waitUntil: "load" });
    await page.waitForTimeout(3500);

    const pointerNow = await readBack(page, JOURNEY_POINTER, "local");
    const sessionNow = await readBack(page, SESSION_POINTER, "session");
    const legacyNow = await page.evaluate(
      ([a, b]) => [window.localStorage.getItem(a), window.localStorage.getItem(b)],
      [legacyKey, legacyRun] as const,
    );
    await shoot(page, "foreign-pointer");
    expect(refused, "服务器没有对旧指针给出 403").not.toBeNull();
    expect((refused as { reason: string | null }).reason).toBe("JOURNEY_POINTER_NOT_OURS");
    expect(pointerNow, "被拒之后旧指针还留在盘上").toBeNull();
    expect(sessionNow, "换人不该把第二个人登出").not.toBeNull();
    expect(JSON.parse(sessionNow as string).travelerId).toBe(guest.id);
    expect(legacyNow, "上一位的 Agent 记录还在 localStorage 里").toEqual([null, null]);
  });

  test("凭证无效：令牌与 Agent 记录一起擦，屏上说的是被拒而不是还在分析", async ({ page }) => {
    /* 上一版这一臂只塞了坏凭证没塞行程指针，于是 `/experience` 根本没被请求，"没清"量的其实是
     * 我的夹具。现在两样都给：屏上先摆着这位"曾经"看过的行程与其对话记录，再看服务器拒绝之后还剩什么。 */
    const fakeJourney = "33333333-3333-4333-8333-333333333333";
    await seedPhone(page, {
      [JOURNEY_POINTER]: fakeJourney,
      [LEGACY_TRANSCRIPT + fakeJourney]: JSON.stringify([{ role: "assistant", content: "上一位旅行者的对话" }]),
      [LEGACY_TIMELINE + fakeJourney + ".run-31"]: JSON.stringify([{ event_id: "evt-31" }]),
      ["ss:" + SESSION_POINTER]: JSON.stringify({
        travelerId: "11111111-1111-4111-8111-111111111111",
        token: "not.a.real.credential",
        expiresAt: null,
      }),
    });
    await page.goto("/v8", { waitUntil: "load" });
    await page.waitForTimeout(3500);
    const sessionNow = await readBack(page, SESSION_POINTER, "session");
    const pointerNow = await readBack(page, JOURNEY_POINTER, "local");
    const diskKeys = await page.evaluate(() => Object.keys(window.localStorage));
    await shoot(page, "invalid-credential");
    expect(sessionNow, "无效凭证没有被清掉").toBeNull();
    expect(pointerNow, "凭证死了却把旧行程指针留下了：匿名请求会把它重新打开").toBeNull();
    expect(
      diskKeys.some((k) => k.startsWith(LEGACY_TRANSCRIPT) || k.startsWith(LEGACY_TIMELINE)),
      "会话被拒之后仍有 Agent 记录留在盘上",
    ).toBe(false);
  });

  test("反控：不带凭证的请求逐字照旧（开身份不会把已有画面变黑）", async ({ page }) => {
    const available = await signingAvailable(page);
    test.skip(!available, "这台部署没配签名密钥——这一臂要的量不到");
    await seedPhone(page);
    await walkTheWizard(page, "Tianjin", "Tianjin West Station", "Tianjin Binhai Airport");
    await page.getByTestId("trial-create").click();
    await page.waitForFunction(() => !!localStorage.getItem("citynexus.v8.journey_id"), null, { timeout: 40_000 });

    /* 把这一趟的会话从这个标签页拿走（等价于另开一个没签名的标签页），指针留着。 */
    await page.evaluate(() => sessionStorage.clear());
    let status = 0;
    let bearer = "NONE";
    page.on("response", (res) => {
      if (/\/api\/v1\/journeys\/[^/]+\/experience$/.test(res.url())) {
        status = res.status();
        bearer = res.request().headers()["authorization"] ?? "NONE";
      }
    });
    await page.reload({ waitUntil: "load" });
    await page.waitForTimeout(3000);
    await shoot(page, "anonymous-still-works");
    expect(bearer, "匿名请求不应该带上 Authorization").toBe("NONE");
    expect(status, "匿名请求被拒了：范围规则误伤了没有凭证的既有流程").toBe(200);
  });

  test("Issue #31 B：住宿查询慢成 6 秒，Today 照样立刻打开并给出真的出口", async ({ page }) => {
    await seedPhone(page);
    /* 只延迟，不伪造：`fallback()` 之后仍是真后端自己答，所以屏上那些词还是服务器给的事实。 */
    await page.route("**/api/v1/journeys/*/stay-options/generate", async (route) => {
      await new Promise((resolve) => setTimeout(resolve, 6000));
      await route.fallback();
    });
    await walkTheWizard(page, "Tianjin", "Tianjin West Station", "Tianjin Binhai Airport");
    await page.getByTestId("trial-create").click();

    /* 行程一写入就量 Today：这一步必须远早于那 6 秒，否则"移出关键路径"是句空话。 */
    await page.waitForFunction(() => !!localStorage.getItem("citynexus.v8.journey_id"), null, { timeout: 20_000 });
    const openedAt = Date.now();
    await expect(page.getByTestId("hub-secondary-actions"), "行程建好后 Today 没打开").toBeVisible({ timeout: 5000 });
    const waited = Date.now() - openedAt;
    const wizardGone = await page.getByTestId("trial-setup").isVisible().catch(() => false);
    /* 「搜索中」这一格要在那 6 秒还没到之前量：上一版我先睡了 7 秒再回头看，量的已经是结果态，
     * 于是把"查询真的在后台跑着、屏上看得出来"这条本该证明的事自己睡掉了。 */
    const searching = await page.getByTestId("hub-stay-searching").isVisible().catch(() => false);
    await shoot(page, "today-opens-without-stays");
    expect(wizardGone, "住宿查询还挂着，向导就没让位给 Today").toBe(false);
    expect(waited, `Today 打开用了 ${waited} 毫秒，那 6 秒的等待并没被移出关键路径`).toBeLessThan(5000);
    expect(searching, "查询仍在后台跑的时候，Today 上没有『搜索中』这一格").toBe(true);

    /* 6 秒之后真答案回来：这一条要拦的是"无穷转圈"，不是逼服务器给出某一种结果。
     * 所以判据是「搜索中那一格必须退场」，退场之后落在哪一格（有offers／没找到／被拒）都按服务器给的读，
     * 只有落在"被拒"时才额外要求屏上有一颗能点的再查一次。 */
    await expect(page.getByTestId("hub-stay-searching"), "6 秒后仍在转：可选住宿没有终态")
      .toBeHidden({ timeout: 40_000 });
    const refused = await page.getByTestId("hub-stay-refused").isVisible().catch(() => false);
    const empty = await page.getByTestId("hub-no-stays").isVisible().catch(() => false);
    if (refused) {
      await expect(page.getByTestId("hub-stay-retry").first(), "失败之后屏上没有可点的出口").toBeVisible();
    }
    const outcome = refused ? "被拒+可重试" : empty ? "没找到+可重试" : "有可选住宿";
    console.log(`Today 打开耗时 ${waited} 毫秒 | 查询在跑时看得见搜索中=${searching} | 终态=${outcome}`);
  });
});
