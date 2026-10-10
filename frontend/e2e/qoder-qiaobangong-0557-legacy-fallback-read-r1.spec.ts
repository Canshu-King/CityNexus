import { expect, test, type Page } from "@playwright/test";
import { createHash } from "crypto";
import { existsSync, mkdirSync, writeFileSync } from "fs";
import { resolve } from "path";
import { ensureDemoJourney } from "./_qoderShellSeed";

/* ORD-0557 · 撬板工 · frontend/src/main.tsx 那 21 枚「服务端没给时前端自己造」的兜底串。
 *
 * 这单只问一句话：这些话走不走字典。所以屏读要交三样东西：
 *   一、真景到不到：/legacy 在产品自己的门口下读不到正文，成因是坐标可取的，不是「我没跑」。
 *   二、正文里那 19 枚在 zh 与 en 两语下各读到什么——两语必须逐字相同，因为这单没换措辞。
 *   三、串确实从字典来：键没接上时 t() 会把键名画到屏上，第二条尺咬得住。
 * 桩景不是骗绿：这 19 枚本来就是 null 分支。桩只补三样——twin 的活动版本、那份计划里的两枚演示活动、
 * 以及把表里点名的字段抹成 null；其余回话仍由真后端出，boot 用的 id 一概不碰。
 * 整屏文本另落一份 text_<树标>_<景>_<语>.txt，同一把尺在现尖字节与候选字节各跑一遍即可逐字对拍。
 */

const OUT_DIR = resolve("review/撬板工-0557/screens");
const TREE_TAG = process.env.CITYNEXUS_0557_TREE_TAG ?? "candidate";
const STUB_PLAN_ID = "plan-stub-0557";
/* SSE 帧分隔符用常量拼，不写转义串：这文件是 bash 里的 heredoc 生成的，反斜杠 n 会被解成真换行（本轮真踩过一次）。 */
const LF = String.fromCharCode(10);

const KEYS: Array<[string, string]> = [
  ["legacy.persistedOperationUpdate", "Persisted operation update"],
  ["legacy.generalRecovery", "general recovery"],
  ["legacy.standingMissionHint", "Activate a standing mission once; subsequent city signals can launch recovery without a new chat message."],
  ["legacy.noDominantFailureMode", "No dominant failure mode"],
  ["legacy.notEvaluated", "not evaluated"],
  ["legacy.validatedActivity", "validated Activity"],
  ["legacy.noActionableTarget", "no actionable target"],
  ["legacy.outcomeEvidence", "outcome evidence"],
  ["legacy.explicitWins", "explicit wins"],
  ["legacy.notReported", "not reported"],
  ["legacy.noUpcomingActivity", "no upcoming activity"],
  ["legacy.noActiveC4", "No active C4"],
  ["legacy.notAvailable", "not available"],
  ["legacy.unnamedCommitment", "未命名承诺 · 服务器没给名字"],
  ["legacy.verifiedFeasible", "verified feasible"],
  ["legacy.notFeasible", "not feasible"],
  ["legacy.notPreserved", "not preserved"],
  ["legacy.verifiedEvidenceAttached", "verified evidence attached"],
  ["legacy.evidenceUnavailable", "evidence unavailable"],
];

/* 只抹表里点名字段；boot 用的 id／活动版本／活动 place_id 都不在名单里。 */
const NULL_FIELDS = [
  "reasoning_summary", "maturity_stage", "resolution", "explanation", "title",
  "selected_activity_id", "next_commitment_buffer_min",
];
const EMPTY_FIELDS = ["dominant_failure_modes", "objective_codes"];

function nullify(node: unknown, depth = 0): unknown {
  if (depth > 12 || node === null || typeof node !== "object") return node;
  if (Array.isArray(node)) return node.map((item) => nullify(item, depth + 1));
  const out: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(node as Record<string, unknown>)) {
    if (NULL_FIELDS.includes(key)) out[key] = null;
    else if (EMPTY_FIELDS.includes(key)) out[key] = [];
    else out[key] = nullify(value, depth + 1);
  }
  return out;
}

const STUB_ACTIVITIES = [
  { id: "a-river", place_id: "place-river-cruise", title: null, start_at: null, status: null },
  { id: "a-art", place_id: "place-tech-art", title: null, start_at: null, status: null },
];

function dump(name: string, payload: unknown) {
  if (!existsSync(OUT_DIR)) mkdirSync(OUT_DIR, { recursive: true });
  writeFileSync(resolve(OUT_DIR, name + ".json"), JSON.stringify(payload, null, 2), "utf8");
}

function dumpText(mode: string, locale: string, text: string) {
  if (!existsSync(OUT_DIR)) mkdirSync(OUT_DIR, { recursive: true });
  const tag = locale === "en" ? "en" : "zh";
  const file = resolve(OUT_DIR, `text_${TREE_TAG}_${mode}_${tag}.txt`);
  writeFileSync(file, text, "utf8");
  return { file, sha1: createHash("sha1").update(text).digest("hex"), chars: text.length };
}

function judge(text: string) {
  const painted: string[] = [];
  const notPainted: string[] = [];
  for (const [key, literal] of KEYS) (text.includes(literal) ? painted : notPainted).push(key);
  return { painted, notPainted };
}

function proposalFixture(shape: "nullA" | "richB" | "nullC") {
  /* 一枚提案要能渲染就得带上 proposalDiffText／proposalDeltaText 读的数（src/main.tsx:126、:140），
     这五枚都是数值／数组，不是本单的字。两个形态各覆盖三元运算的一侧：
       nullA —— 硬约束没过、受保护的没保住、证据没附、可执行目标没给 → not feasible／not preserved／
                evidence unavailable／no actionable target
       richB —— 过了、保住了、证据附了、给了目标但成熟度没写 → verified feasible／verified evidence
                attached／validated Activity（而 "preserved" 那一句不在本单表里，形态 B 不追它） */
  const passed = shape === "richB";
  return [
    {
      id: "p-0557",
      status: "PRESENTED",
      trigger_event_id: "ev-0557",
      hard_constraints_passed: passed,
      locked_commitments_preserved: passed,
      utility_score: 0.5,
      score_breakdown: {},
      diff: {
        candidate_family: "shift_morning",
        removed: [],
        added: [],
        preserved_protected: [],
        cost_delta_minor: 0,
        travel_delta_min: 0,
        end_time_delta_min: 0,
        /* nullC 把整枚 verified_evidence 抹成 null——「证据没附」那一支只有在这里才走得到，
           而它一走到，impact_resolution 那两枚同文兄弟就必然走不到，所以形态要分三档而不是两档。 */
        verified_evidence: shape === "nullC"
          ? null
          : passed
            ? { impact_resolution: { status: null, maturity_stage: null, selected_activity_id: "a-art" } }
            : { impact_resolution: { status: null, maturity_stage: null, selected_activity_id: null } },
      },
    },
  ];
}

const TRAVELER_TWIN_FIXTURE = {
  /* explicit_preferences 这枚也必须给：渲染处直接数它的 length（src/main.tsx:1455 一带），
     缺了它整棵树在渲染期抛掉，屏读回零字节。第一版夹具就栽在这，靠「渲染期不许抛」那格逮到的。 */
  explicit_preferences: [],
  confidence: 0.5,
  evidence_count: 1,
  learned_soft_preferences: [
    { dimension: "quiet_mornings", direction: null, strength: 0.4, evidence_count: 2, last_evidence_at: null, explanation: null },
  ],
  conflicts: [{ dimension: "budget", directions: ["cheap", "central"], resolution: null }],
};

const AGENT_RUN_FIXTURE = {
  id: "run-0557",
  status: "COMPLETED",
  provider_key: "stub",
  model_key: "stub",
  outcome: null,
  failure_reason: null,
  tool_steps: [],
  mission: {
    id: "m-0557",
    status: "STANDBY",
    user_text: "x",
    objective_codes: [],
    max_cost_delta_minor: 0,
    max_loss_minor: 0,
    max_schedule_drift_min: 0,
    protected_activity_ids: [],
  },
};

async function openLegacy(page: Page, locale: string, mode: "real" | "stub", shape: "nullA" | "richB" | "nullC" = "nullA") {
  const pageErrors: string[] = [];
  page.on("pageerror", (err) => pageErrors.push(String(err).slice(0, 200)));
  await page.setViewportSize({ width: 1280, height: 1400 });
  /* 门先走真产品：/v8 那枚演示按钮造旅行者与行程，存壳自己的键 `citynexus.v8.journey_id`；
     LegacyApp 认的是 `citynexus.demo.journey_id`（src/main.tsx:52），不接就退回 bootstrap 那条腿，
     而 bootstrap 第一脚就是 POST /demo/reset，权威模式下要具名 token。 */
  await ensureDemoJourney(page);
  await page.evaluate((code) => {
    const id = localStorage.getItem("citynexus.v8.journey_id");
    if (id) {
      localStorage.setItem("citynexus.demo.journey_id", id);
      /* 持久化 run 那格要这把键才去回读（src/main.tsx:54），有了它才走得到 general recovery 那一支。 */
      localStorage.setItem("citynexus.demo.agent_run_id", "run-0557");
    }
    localStorage.setItem("citynexus.locale", code);
  }, locale);
  if (mode === "stub") {
    await page.route("**/api/v1/**", async (route) => {
      const url = route.request().url();
      /* 事件流不是 JSON，route.fetch() 会一直等下一帧。这里只接 operations/stream：
         送一帧不带 summary 的无名帧，让「服务端没给那句摘要」这一支真走到（src/main.tsx:565）。 */
      if (url.includes("/operations/stream")) {
        return route.fulfill({
          status: 200,
          headers: { "content-type": "text/event-stream", "cache-control": "no-cache" },
          body: 'data: {"event_type":"city_signal_received"}' + LF + LF,
        });
      }
      if (url.includes("/stream")) return route.fallback();
      let fetched;
      try {
        fetched = await route.fetch();
      } catch {
        return route.fallback();
      }
      let body: unknown = null;
      try {
        body = await fetched.json();
      } catch {
        return route.fallback();
      }
      const send = (payload: unknown) =>
        route.fulfill({ status: 200, headers: { "content-type": "application/json" }, body: JSON.stringify(payload) });
      if (url.endsWith("/traveler-twin")) return send(TRAVELER_TWIN_FIXTURE);
      if (url.includes("/agent/runs/")) return send(AGENT_RUN_FIXTURE);
      if (url.endsWith("/replans")) return send(proposalFixture(shape));
      if (url.endsWith("/twin")) {
        const twin = (body ?? {}) as Record<string, unknown>;
        return send({
          ...nullify(twin),
          active_plan_version_id: STUB_PLAN_ID,
          current_activity_id: "a-river",
          upcoming_commitments: [
            { id: "c-unresolved", level: "SOFT", activity_id: null,
              policy: { semantic_key: "sk-not-on-this-plan", scheduled_start_at: null } },
            { id: "c-c4", level: "C4_Anchored", activity_id: null,
              policy: { semantic_key: "sk-not-on-this-plan", scheduled_start_at: null } },
          ],
          context: {
            feasibility_envelope: { next_commitment_buffer_min: null, budget_remaining_minor: 0, robust: null },
            /* 同文两址：`opportunity_window` 缺失时那一句也写 "not available"（src/main.tsx:1576 那一支），
               与本单点名的 `next_commitment_buffer_min` 那枚逐字相同。给窗口补上形状，屏上出现的
               "not available" 就只能来自本单搬走的那一处。 */
            opportunity_window: {
              must_depart_by: "2026-10-10T09:00:00+08:00",
              must_arrive_by: "2026-10-10T11:00:00+08:00",
              available_minutes: 120,
            },
            degraded_providers: [],
          },
        });
      }
      if (url.includes("/plans/") || url.endsWith("/plans")) {
        /* `plan?.total_cost.currency` 与 `twin?.context.feasibility_envelope` 取的是非可选属性
           （src/main.tsx:347、:359），把 total_cost 抹成 null 会让整棵树在渲染期抛掉，屏读回空——
           第一版我就栽在这里，量到的是「什么都没有」而不是「服务端没给」。 */
        return send({ id: STUB_PLAN_ID, total_cost: { currency: "CNY", amount_minor: 0 }, activities: STUB_ACTIVITIES });
      }
      return send(nullify(body));
    });
  }
  await page.goto("/legacy", { waitUntil: "networkidle", timeout: 90_000 });
  await page.waitForTimeout(4_000);
  const seen = await page.evaluate(() => {
    const text = document.body.innerText || "";
    return {
      text,
      h1: (document.querySelector("h1")?.textContent || "").trim(),
      mounted: !!document.querySelector("main.shell"),
      lang_attr: document.documentElement.lang,
      leak: (text.match(/legacy\.[A-Za-z]+/g) || []).slice(0, 8),
    };
  });
  const written = dumpText(mode + (mode === "stub" ? "_" + shape : ""), locale, seen.text);
  await page.screenshot({ path: resolve(OUT_DIR, `shot_${TREE_TAG}_${mode}${mode === "stub" ? "_" + shape : ""}_${locale === "en" ? "en" : "zh"}.png`) });
  return { ...seen, written, pageErrors };
}

test(`ORD-0557 现读成因 · 产品门口下 /legacy 正文到不了，且那句错误读法没被我改（${TREE_TAG}）`, async ({ page }) => {
  const seen = await openLegacy(page, "zh-CN", "real");
  dump(`real_${TREE_TAG}`, {
    h1: seen.h1, mounted: seen.mounted, chars: seen.text.length,
    error_line: (seen.text.match(/ERROR · [^\n]{0,60}/) || [null])[0],
    painted: judge(seen.text).painted,
    not_painted: judge(seen.text).notPainted,
  });
  expect(seen.mounted, "/legacy 至少要把 LegacyApp 挂上").toBe(true);
  /* 这条不是「红了算过」：它量的是这台库到不了正文这一事实，且顺带证明模块层那两枚的读法我没动。
     若哪天正文能到了，这条会红，那时该重排的是这张单子，不是这条断言。 */
  expect(seen.h1).toBe("Journey connection unavailable");
  expect(seen.text).toContain("ERROR · CityNexus request failed");
  expect(seen.leak, "错误页上也不许出现字典键名").toEqual([]);
});

for (const shape of ["nullA", "richB", "nullC"] as const) {
  test(`ORD-0557 桩景·形态 ${shape} · 兜底在 zh 与 en 两语下逐字相同、键名不泄漏（${TREE_TAG}）`, async ({ page }) => {
    const zh = await openLegacy(page, "zh-CN", "stub", shape);
    expect(zh.pageErrors, "渲染期不许抛：抛了屏读回空，量到的是尺的毛病不是码的").toEqual([]);
    expect(zh.mounted).toBe(true);
    expect(zh.h1, "桩景必须读到正文").not.toBe("Journey connection unavailable");
    await page.unrouteAll({ behavior: "ignoreErrors" }).catch(() => undefined);
    const en = await openLegacy(page, "en", "stub", shape);
    const jzh = judge(zh.text);
    const jen = judge(en.text);
    dump(`stub_${shape}_${TREE_TAG}`, {
      shape,
      zh_h1: zh.h1, en_h1: en.h1,
      zh_lang: zh.lang_attr, en_lang: en.lang_attr,
      zh_page_errors: zh.pageErrors, en_page_errors: en.pageErrors,
      zh_painted: jzh.painted, zh_not_painted: jzh.notPainted,
      en_painted: jen.painted,
      count_painted_zh: jzh.painted.length,
      count_painted_en: jen.painted.length,
      denominator_keys: KEYS.length,
      zh_text: zh.written, en_text: en.written,
      key_leak_zh: zh.leak, key_leak_en: en.leak,
    });
    expect(jzh.painted.length + jzh.notPainted.length).toBe(KEYS.length);
    expect(zh.leak, "屏上不许出现字典键名：键没接上时 t() 会把键名原样画出来").toEqual([]);
    expect(en.leak).toEqual([]);
    expect(jen.painted, "两语下露出的兜底集合必须相同").toEqual(jzh.painted);
    expect(en.written.sha1, "整屏文本两语逐字相同（这单只搬字不换词）").toBe(zh.written.sha1);
    expect(jzh.painted.length, "桩景至少要露出若干枚兜底原文").toBeGreaterThan(0);
  });
}
