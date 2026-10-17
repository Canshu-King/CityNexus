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
 *
 * Issue #33 Q1 在这个 runner 里再加两臂（同一台真后端，同一次启动）：
 *   6. 指针被擦之后，向导旁边的「我的行程」能把名下的行程列出来并真的打开它；
 *   7. 窗口将尽的会话由页面自己去 `/travelers/session/refresh` 续上——人和行程都不掉
 *      （只有 `CNX_QODER31_TTL=60` 起的那一台才跑，见 config 里那行 TTL）。
 */
import { expect, test, type Page } from "@playwright/test";
import { mkdirSync, writeFileSync } from "node:fs";

/* 图文教程（Issue #31 C 要求的"真实截图"）用的图就落在这个目录里：屏幕上是真渲染出来的，
 * 不是我贴上去的形状。目录先建，因为 Playwright 写图之前不会替你建目录。 */
const DOC_EVIDENCE = "docs/assets/evidence";
mkdirSync(DOC_EVIDENCE, { recursive: true });

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

  test("去掉凭证不再是出路：私有行程的匿名读被具名拒绝，屏上给的是可恢复的一屏", async ({ page }) => {
    const available = await signingAvailable(page);
    test.skip(!available, "这台部署没配签名密钥——这一臂要的量不到");
    await seedPhone(page);
    await walkTheWizard(page, "Tianjin", "Tianjin West Station", "Tianjin Binhai Airport");
    await page.getByTestId("trial-create").click();
    await page.waitForFunction(() => !!localStorage.getItem("citynexus.v8.journey_id"), null, { timeout: 40_000 });

    /* 把这一趟的会话从这个标签页拿走（等价于另开一个没签名的标签页），指针留着。
     * GPT P0-SEC 之前，这一臂钉的是"匿名照旧 200"——那条断言现在看是给漏洞发的绿牌：
     * 去掉 header 就能读别人的私有行程，等于授权由客户端决定。现在钉的是新语义。 */
    await page.evaluate(() => sessionStorage.clear());
    let status = 0;
    let bearer = "NONE";
    let reason: string | null = null;
    page.on("response", async (res) => {
      if (/\/api\/v1\/journeys\/[^/]+\/experience$/.test(res.url())) {
        status = res.status();
        bearer = res.request().headers()["authorization"] ?? "NONE";
        const body = await res.json().catch(() => ({}));
        reason = body?.error?.reason_code ?? null;
      }
    });
    await page.reload({ waitUntil: "load" });
    await page.waitForTimeout(3000);
    const body = await page.locator("body").innerText();
    await shoot(page, "anonymous-refused-by-name");
    expect(bearer, "匿名请求不应该带上 Authorization").toBe("NONE");
    expect(status, "去掉凭证仍然读到了私有行程").toBe(401);
    expect(reason).toBe("TRAVELER_CREDENTIALS_MISSING");
    /* 拒得对，还要看得见下一步：这一屏不能是一片空白。 */
    expect(body, "被拒之后屏上没有可恢复的下一步").toMatch(/重新|开始|创建|新行程/);
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

  test("Issue #31 C：Today 上的「AI 工作动态」打开的是这台服务器关于这一趟的事件流", async ({ page }) => {
    await seedPhone(page);
    await walkTheWizard(page, "Tianjin", "Tianjin West Station", "Tianjin Binhai Airport");
    await page.screenshot({ path: `${DOC_EVIDENCE}/01-trip-setup.png`, fullPage: true });
    const journeyId = await createAndAwaitJourney(page);
    await expect(page.getByTestId("hub-secondary-actions"), "Today 没打开").toBeVisible({ timeout: 20_000 });
    await page.screenshot({ path: `${DOC_EVIDENCE}/02-today.png`, fullPage: true });

    /* 先把"服务器到底回了什么"单独读一遍，再拿屏上去对：
     * 这一臂要拦的是"面板写了一个服务器没给过的数"，所以对照的是两个独立来源，不是自己看自己。 */
    const session = JSON.parse((await readBack(page, SESSION_POINTER, "session")) as string) as { token: string };
    const headers = { Authorization: `Bearer ${session.token}` };
    const feed = await (await page.request.get(
      `${baseOf()}/api/v1/journeys/${journeyId}/agent-feed?limit=30`, { headers })).json();
    const runtime = await (await page.request.get(
      `${baseOf()}/api/v1/agent/runtime-status`, { headers })).json();
    const serverEvents = Array.isArray(feed.events) ? feed.events.length : -1;

    /* GPT P0-UX：住宿有结果也不再自动弹规划抽屉。上一版这一臂是被那片遮罩拖到 180 秒超时的，
     * 当时的处置是"先把遮罩合掉再量"——那等于把产品的坏体验写进用例。现在正面钉：
     * Today 交出来那一刻，屏上不该有任何盖住它的抽屉。 */
    await expect(page.getByTestId("plan-ai-sheet"), "Today 刚打开就被规划抽屉盖住").toHaveCount(0);
    await page.waitForTimeout(700);
    const hubDiag = await page.evaluate(() => {
      const name = (node: Element | null) =>
        node
          ? `${node.tagName.toLowerCase()}.${node.getAttribute("class") ?? ""}#${node.getAttribute("data-testid") ?? ""}`
          : "none";
      const button = document.querySelector('[data-testid="hub-ai-work"]');
      const r = button ? button.getBoundingClientRect() : null;
      return {
        matches: document.querySelectorAll('[data-testid="hub-ai-work"]').length,
        buttonBox: r ? [Math.round(r.x), Math.round(r.y), Math.round(r.width), Math.round(r.height)] : null,
        hit: r ? name(document.elementFromPoint(r.x + r.width / 2, r.y + r.height / 2)) : "none",
        viewport: [window.innerWidth, window.innerHeight],
        docHeight: document.documentElement.scrollHeight,
      };
    });
    console.log(`Today 入口诊断 ${JSON.stringify(hubDiag)}`);
    expect(hubDiag.hit, "入口中心点命中的不是这颗按钮（被别的东西盖住了）").toContain("#hub-ai-work");
    await page.getByTestId("hub-ai-work").click({ timeout: 20_000 });
    const panel = page.getByTestId("agent-work-feed");
    await expect(panel, "入口点不开面板").toBeVisible({ timeout: 15_000 });
    await expect(panel).toHaveAttribute("data-feed-state", "ready", { timeout: 20_000 });
    await expect(panel).toHaveAttribute("data-feed-events", String(serverEvents));
    await expect(panel).toHaveAttribute("data-feed-source", String(feed.source));

    /* P1-TRUTH：审计事件流里既有"AI／工具动过手"的，也有"人建了行程"这种行程系统自己的事。
     * 面板分成两段，所以这里对的是**Agent 那一段**的行数，而不是整条流的条数。 */
    const agentEvents = (Array.isArray(feed.events) ? feed.events : []).filter((item) =>
      /(agent|tool|run|approval|replan|guardian|gateway|hermes|proposal)/i.test(String(item?.event_type ?? "")),
    );
    await expect(panel).toHaveAttribute("data-feed-agent-events", String(agentEvents.length));
    const rows = await page.locator(".cn-agent-rail li").count();
    expect(rows, "轨迹条行数与服务器给的 Agent/工具事件数对不上（面板最多显 12 行）")
      .toBe(Math.min(12, agentEvents.length));
    if (agentEvents.length === 0) {
      await expect(page.getByTestId("agent-work-no-run"), "没有真实运行时没有老实说'暂无真实运行'")
        .toContainText("暂无真实运行");
    }
    /* 落地门那条 `CODES_ON_SCREEN` 的同一类：人读的正文里不许铺内部机器码。
     * 码本身留在 `data-*` 与可展开的「技术详情」里，读的人不必看。 */
    const painted = await panel.innerText();
    for (const code of ["DISABLED_BY_OPS", "NATIVE_DEEPSEEK_TOOL_LOOP", "Journey.created", "audit_log"]) {
      expect(painted, `屏上铺了内部机器码：${code}`).not.toContain(code);
    }
    /* AI 可用性那一格必须写服务器自报的那个词（在 data 上），而不是页面猜的。 */
    await expect(page.locator('[data-testid="agent-work-facts"] dd').first())
      .toHaveAttribute("data-ai-state", String(runtime.ai_state ?? "NOT_READ"));
    /* 面板与那颗悬浮的 Copilot 药丸不许叠在一起。这里量的是两个盒子，不是靠一条 CSS 把药丸
     * 藏掉再宣称没问题——药丸自己会 `yield-to-surface`，那就让它真的让开，让不开就红。
     *
     * 这一格以前有个洞：`boundingBox().catch(() => null)` 之后整段判语包在 `if (panelBox && dockBox)`
     * 里，于是"这一屏根本没量到药丸"也走成通过。07:28 现读把它照出来了：390x844 上面板占
     * 17,473 起 356x398，药丸停在 336,634 的 44x44 —— **真的压着面板的说明行**，而这一格一直绿着。
     * 现在分母先钉住（药丸必须在场、必须量得到盒子），再判重叠。
     *
     * 同一屏上还有一枚 `sim-float`（演示台那颗浮球，330,522 的 48x60），它归 simulation 车道，
     * 这一格不替它判——但它的盒子逐轮打出来，谁接这枚球都拿得到现读坐标。 */
    const dock = page.getByTestId("v18-copilot-dock");
    expect(await dock.count(), "这一屏上没有那颗 Copilot 药丸：重叠这一格量不到东西，不许当通过").toBe(1);
    /* 两把尺不在同一个坐标面上：Playwright 的 `boundingBox()` 给的是**页面**坐标（含 scrollY），
     * 而 `getBoundingClientRect()` 给的是**视口**坐标。药丸是 fixed、面板在流里 —— 拿页面坐标比
     * 两者会各差一个 scrollY，重叠能被比成"没有"。所以这一格的两枚盒子必须在同一次 evaluate 里取。 */
    const boxes = await page.evaluate(() => {
      const rect = (el: Element | null) => {
        if (!el) return null;
        const r = el.getBoundingClientRect();
        return { x: Math.round(r.x), y: Math.round(r.y), width: Math.round(r.width), height: Math.round(r.height) };
      };
      return {
        panel: rect(document.querySelector('[data-testid="agent-work-feed"]')),
        dock: rect(document.querySelector('[data-testid="v18-copilot-dock"]')),
        scrollY: Math.round(window.scrollY),
        viewport: { width: window.innerWidth, height: window.innerHeight },
      };
    });
    console.log(`视口量具 ${JSON.stringify(boxes)}`);
    const panelBox = boxes.panel;
    const dockBox = boxes.dock;
    expect(dockBox, "药丸在场却量不到盒子").not.toBeNull();
    const dockPainted = await dock.isVisible().catch(() => false);
    const cells = [
      !!panelBox && !!dockBox && dockBox.x < panelBox.x + panelBox.width,
      !!panelBox && !!dockBox && panelBox.x < dockBox.x + dockBox.width,
      !!panelBox && !!dockBox && dockBox.y < panelBox.y + panelBox.height,
      !!panelBox && !!dockBox && panelBox.y < dockBox.y + dockBox.height,
    ];
    const overlaps = dockPainted && cells.every(Boolean);
    console.log(
      `重叠判语 画出来=${String(dockPainted)} 四格=${cells.map(String).join(",")} 判重叠=${String(overlaps)} ` +
        `panel=${JSON.stringify(panelBox)} dock=${JSON.stringify(dockBox)}`,
    );
    expect(
      overlaps,
      `面板与 Copilot 药丸重叠（四格=${cells.map(String).join(",")}）panel=${JSON.stringify(panelBox)} dock=${JSON.stringify(dockBox)} yield=${await dock.getAttribute("data-yield-to-surface")}`,
    ).toBe(false);
    const floaters = await page.evaluate(() => {
      const rows: Array<{ id: string; pos: string; box: { x: number; y: number; width: number; height: number } }> = [];
      for (const el of Array.from(document.querySelectorAll<HTMLElement>("[data-testid]"))) {
        const style = getComputedStyle(el);
        if (style.position !== "fixed" && style.position !== "sticky") continue;
        const rect = el.getBoundingClientRect();
        if (rect.width < 8 || rect.height < 8) continue;
        if (rect.bottom < 0 || rect.top > window.innerHeight) continue;
        rows.push({
          id: el.getAttribute("data-testid") || "",
          pos: style.position,
          box: { x: Math.round(rect.x), y: Math.round(rect.y), width: Math.round(rect.width), height: Math.round(rect.height) },
        });
      }
      return rows;
    });
    console.log(
      `Today 浮层 ${floaters.length} 枚 panel=${JSON.stringify(panelBox)} yield=${await dock.getAttribute("data-yield-to-surface")} ` +
        floaters.map((row) => `${row.id}[${row.pos} ${row.box.x},${row.box.y} ${row.box.width}x${row.box.height}]`).join(" "),
    );
    await page.waitForTimeout(400);
    await page.screenshot({ path: `${DOC_EVIDENCE}/03-ai-work-today.png` });
    console.log(
      `Today 面板：服务器事件 ${serverEvents} 条（Agent/工具 ${agentEvents.length} 条）| 轨迹 ${rows} 行 | source=${feed.source} | ai_state=${runtime.ai_state}`,
    );
  });

  test("Issue #33 Q1：轨道不替服务器造句——派生出来的那句要被人话顶掉", async ({ page }) => {
    await seedPhone(page);
    await walkTheWizard(page, "Tianjin", "Tianjin West Station", "Tianjin Binhai Airport");
    const journeyId = await createAndAwaitJourney(page);
    /* 这一臂用的是**贴了标签的夹具**：审计行没带摘要时，服务器的投影会把事件类型本身当成摘要发回来
     * （`journey.created` → "Journey.created"，这台部署上现量到过）。这台部署 AI 是关的，跑不出真的
     * Agent 行，所以把那条假设有凭据的样子喂进去，量的是**屏上怎么显示**，不是服务器会不会这么答——
     * 后者已经量过了。 */
    await page.route(`**/api/v1/journeys/${journeyId}/agent-feed*`, (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          journey_id: journeyId,
          source: "audit_log",
          events: [
            {
              id: "11111111-1111-4111-8111-111111111111",
              timestamp: "2026-10-18T09:12:00+08:00",
              event_type: "agent_tool_requested",
              type: "agent_tool_requested",
              // 服务器在没有真摘要时发出的就是这一串：类型的换形。
              summary: "Agent tool requested",
              actor_type: "agent",
              actor_id: null,
              tool: "replan",
              journey_id: journeyId,
              proposal_id: null,
              entity_type: null,
              entity_id: null,
              decision: null,
              reason_codes: [],
              trace_id: "qoder33-fixture-derived",
              source: "audit_log",
              facts: {},
            },
            {
              id: "22222222-2222-4222-8222-222222222222",
              timestamp: "2026-10-18T09:13:00+08:00",
              event_type: "replan_requested",
              type: "replan_requested",
              summary: "已经把明天上午的出发时间往前挪了一小时",
              actor_type: "agent",
              actor_id: null,
              tool: null,
              journey_id: journeyId,
              proposal_id: null,
              entity_type: null,
              entity_id: null,
              decision: null,
              reason_codes: [],
              trace_id: "qoder33-fixture-human",
              source: "audit_log",
              facts: {},
            },
          ],
        }),
      }),
    );
    await page.goto("/v8", { waitUntil: "load" });
    await page.getByTestId("hub-ai-work").click();
    const rail = page.locator(".cn-agent-rail");
    await expect(rail, "轨道没有画出来").toBeVisible({ timeout: 20_000 });
    const labels = (await rail.locator("li b").allInnerTexts()).map((text) => text.trim());
    await page.screenshot({ path: `${DOC_EVIDENCE}/07-rail-no-derived-prose.png`, fullPage: true });
    /* 一红一绿成对：第一行不许是那句英文换形，第二行必须原样保留人写的摘要。
     * 只满足其中一条的改法（比如"永远不显示 summary"）会红在另一条上。 */
    expect(labels[0], `派生出来的句子被当成人话铺上屏了：${labels[0]}`).toBe("AI 请求使用一个工具");
    expect(labels[1], "服务器真写过的摘要被顶掉了").toBe("已经把明天上午的出发时间往前挪了一小时");
    console.log(`轨道两行读数：${JSON.stringify(labels)}`);
  });

  test("Issue #31 C：行程页的入口在行程之上，不是滚过整份行程才够得着", async ({ page }) => {
    await seedPhone(page);
    await walkTheWizard(page, "Tianjin", "Tianjin West Station", "Tianjin Binhai Airport");
    const journeyId = await createAndAwaitJourney(page);
    await page.goto("/v8/trips", { waitUntil: "load" });
    const tab = page.getByTestId("trips-tab-itinerary");
    if (!(await page.getByTestId("agent-work-entry-trip").isVisible().catch(() => false))) {
      await tab.click();
    }
    const entry = page.getByTestId("agent-work-entry-trip");
    await expect(entry, "行程页上没有 AI 工作动态的入口").toBeVisible({ timeout: 20_000 });
    /* 上一版这一臂没有失败在断言上，而是失败在"点不下去/量不到"：`scrollIntoViewIfNeeded`、
     * `boundingBox`、`click` 这些会自动等"元素稳定"的定位器动作一起拖到 180 秒超时。
     * 这个形状有两种常见成因（这一屏在反复重渲染 / 按钮被别的东西盖住），所以先用
     * 不问稳定性的 `page.evaluate` 把事实摊开：几枚、按钮盒在哪、400 毫秒之内会不会动、
     * 按钮中心点处命中的是谁。不许用 `force` 把任何一种可能糊过去。 */
    await page.waitForTimeout(1200);
    const diag = await page.evaluate(async () => {
      const name = (node: Element | null) =>
        node
          ? `${node.tagName.toLowerCase()}.${node.getAttribute("class") ?? ""}#${node.getAttribute("data-testid") ?? ""}`
          : "none";
      const rect = (node: Element | null) => {
        if (!node) return null;
        const r = node.getBoundingClientRect();
        return [Math.round(r.x), Math.round(r.y), Math.round(r.width), Math.round(r.height)];
      };
      const entries = Array.from(document.querySelectorAll('[data-testid="agent-work-entry-trip"]'));
      const button = entries[0]?.querySelector("button") ?? null;
      const first = rect(button);
      await new Promise((resolve) => setTimeout(resolve, 400));
      const second = rect(button);
      const plan =
        document.querySelector('[data-testid="trip-itinerary"]') ??
        document.querySelector('[data-testid="trip-itinerary-empty"]');
      const bb = button ? button.getBoundingClientRect() : null;
      return {
        matches: entries.length,
        buttonBox: first,
        buttonMoved: JSON.stringify(first) !== JSON.stringify(second),
        buttonHit: name(bb ? document.elementFromPoint(bb.x + bb.width / 2, bb.y + bb.height / 2) : null),
        planBox: rect(plan),
        planTestId: plan?.getAttribute("data-testid") ?? "none",
        viewport: [window.innerWidth, window.innerHeight],
      };
    });
    console.log(`行程页入口诊断 ${JSON.stringify(diag)}`);
    await page.getByTestId("trip-ai-work").click({ timeout: 15_000 });
    const panel = page.getByTestId("agent-work-feed");
    await expect(panel).toBeVisible({ timeout: 15_000 });
    await expect(panel).toHaveAttribute("data-feed-state", "ready", { timeout: 20_000 });
    await page.screenshot({ path: `${DOC_EVIDENCE}/04-ai-work-trip.png`, fullPage: true });
    if (diag.buttonBox && diag.planBox) {
      expect(diag.buttonBox[1], "入口排在整份行程之下").toBeLessThan(diag.planBox[1]);
    }
    console.log(`行程页入口 y=${diag.buttonBox ? diag.buttonBox[1] : "n/a"} | ${diag.planTestId} y=${diag.planBox ? diag.planBox[1] : "n/a"} | 面板已开=${await panel.isVisible()}`);
  });

  /* Issue #33 Q1 的两臂。共同的前提是：这一台后端是真签名的，所以"续上了"与"找回来了"都是
   * 服务器的事实，不是页面的自我感觉。 */

  test("Issue #33 Q1：指针被擦之后，向导旁边能把名下的行程找回来", async ({ page }) => {
    await seedPhone(page);
    await walkTheWizard(page, "Tangshan", "Tangshan Station", "Tangshan South Station");
    const journeyId = await createAndAwaitJourney(page);
    /* 复刻 ORD-0687 的清除：设备上那枚指针不是了（换人、被拒都会走到这一步），会话还在——
     * 还是同一个标签页、同一个人。以前这种状态只剩"新建一趟"一条路，而屏幕上的按钮写着「选一趟行程」。 */
    await page.evaluate(() => localStorage.removeItem("citynexus.v8.journey_id"));
    await page.goto("/v8", { waitUntil: "load" });

    const panel = page.getByTestId("my-trips");
    await expect(panel, "向导旁边没有「我的行程」这一格").toBeVisible({ timeout: 25_000 });
    await expect(page.getByTestId("my-trips-list")).toBeVisible({ timeout: 20_000 });
    const listed = await page
      .getByTestId("my-trips-list")
      .locator("li[data-cnx-journey]")
      .evaluateAll((nodes) => nodes.map((n) => n.getAttribute("data-cnx-journey") ?? ""));
    /* 这份名单是带凭证读出来的：里面只该有这台服务器认给这个人的行程。 */
    expect(listed.length, "名下的行程一枚都没列出来").toBeGreaterThan(0);
    expect(listed, `刚建的那趟不在名单里：${JSON.stringify(listed)}`).toContain(journeyId);
    await page.screenshot({ path: `${DOC_EVIDENCE}/05-my-trips-restore.png`, fullPage: true });
    /* 教程要圈这一格，坐标必须由这一臂现取（`scripts/annotate_first_trip_guide_r1.py` 的同一条件：
     * 人不猜坐标）。记的是渲染盒与视口宽，标注脚本再按 `PNG 宽 / 视口宽` 缩放。 */
    const geometry = await page
      .getByTestId("my-trips")
      .boundingBox()
      .then((box) => ({ panel: box, viewport: [page.viewportSize()?.width ?? 390, page.viewportSize()?.height ?? 844], shotHeight: null }));
    const button = await page.getByTestId("my-trips-open").first().boundingBox();
    writeFileSync(
      `${DOC_EVIDENCE}/05-my-trips-restore.json`,
      JSON.stringify({ ...geometry, openButton: button }, null, 2),
      "utf-8",
    );

    await page.getByTestId("my-trips-open").first().click();
    await expect
      .poll(() => readBack(page, JOURNEY_POINTER, "local"), { timeout: 25_000 })
      .toBe(listed[0]);
    await expect(page.getByTestId("trial-setup"), "点了「打开这趟」还停在向导上").toBeHidden({
      timeout: 20_000,
    });
    /* 进了行程之内才算数：这枚 testid 只在壳层（有行程可读）里出现。 */
    await expect(page.getByTestId("hub-new-journey"), "打开之后没有落到行程里").toBeVisible({
      timeout: 25_000,
    });
    const stillSigned = await readBack(page, SESSION_POINTER, "session");
    expect(stillSigned, "找回行程的过程中把人丢了").not.toBeNull();
    console.log(`找回旧行程：名单 ${listed.length} 枚，指针→${listed[0]}，本次新建的是 ${journeyId}`);
  });

  test(
    "Issue #33 Q1：窗口将尽的会话自己续上，人不被请出去",
    async ({ page }) => {
      /* 这一臂要的是"服务器给的窗口本来就短"，而那由部署的 TTL 决定，不由测试编造：
       * 只有用 `CNX_QODER31_TTL=60` 起的那一台才成立（60 秒 < 前端 300 秒的续期余量）。
       * 默认那一台里它正确地跳过——没有短窗口就没有该触发的续期，硬造一个只会测到我的桩。 */
      test.skip(
        process.env.CNX_QODER31_TTL !== "60",
        "需要 CITYNEXUS_TRAVELER_AUTH_TTL_SECONDS=60 的那一台（CNX_QODER31_TTL=60）",
      );
      await seedPhone(page);
      await walkTheWizard(page, "Qinhuangdao", "Qinhuangdao Station", "Qinhuangdao Beidaihe Airport");
      const journeyId = await createAndAwaitJourney(page);
      const firstRaw = await readBack(page, SESSION_POINTER, "session");
      expect(firstRaw, "创建之后没有签名会话可续").not.toBeNull();
      const first = JSON.parse(firstRaw as string) as {
        travelerId: string;
        token: string;
        expiresAt: number | null;
      };

      /* 这枚签名是逐秒确定的（`{v,aud,sub,iat,exp}` + HMAC，没有随机数）：同一秒里续出来的
       * 那枚与原样逐字节相同。这不是缺陷——窗口不会倒退，也不会凭空多出一秒——但它意味着要
       * 观察"窗口往前走了"就必须真的跨过一秒，所以我等的是钟，不是桩。 */
      await page.waitForTimeout(1_500);
      const refreshed = page.waitForResponse(
        (res) =>
          res.request().method() === "POST" &&
          /\/api\/v1\/travelers\/session\/refresh$/.test(res.url()),
        { timeout: 40_000 },
      );
      await page.goto("/v8", { waitUntil: "load" });
      const answer = await refreshed;
      expect(answer.status(), await answer.text()).toBe(200);
      const body = await answer.json();
      await page.screenshot({ path: `${DOC_EVIDENCE}/06-session-renewed.png`, fullPage: true });

      const secondRaw = await readBack(page, SESSION_POINTER, "session");
      expect(secondRaw, "续期之后这一页没有会话了").not.toBeNull();
      const second = JSON.parse(secondRaw as string) as typeof first;
      /* 续期买到的只有"更晚的到期"：人还是那个人，指针还是那趟。 */
      expect(second.travelerId, "续期换了人").toBe(first.travelerId);
      expect(body.traveler_id).toBe(first.travelerId);
      expect(second.token, "续期没有给出新凭据").not.toBe(first.token);
      expect(typeof body.expires_at).toBe("number");
      expect(second.expiresAt).toBe(body.expires_at);
      if (first.expiresAt !== null) expect(body.expires_at).toBeGreaterThan(first.expiresAt);
      expect(await readBack(page, JOURNEY_POINTER, "local"), "续期把行程指针弄丢了").toBe(journeyId);
      /* 新凭据真的被后续请求用上——不是存起来好看。 */
      const bearer = await page.evaluate(
        () => (sessionStorage.getItem("citynexus.v8.traveler.session") ?? ""),
      );
      expect(JSON.parse(bearer).token).toBe(second.token);
      console.log(
        `会话续期：窗口 ${first.expiresAt}→${second.expiresAt} 秒（TTL 60），旅行者 ${first.travelerId.slice(0, 8)}… 未变`,
      );
    },
  );
});
