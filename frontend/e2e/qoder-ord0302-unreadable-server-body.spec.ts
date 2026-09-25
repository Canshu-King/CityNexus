/**
 * ORD-0302 — a server answer this screen cannot parse must stay an HTTP answer, not become a network claim.
 *
 * Root cause, read off `dc964086c9d412573ac19d70b24b30e6c3ee6168` before touching anything: the two envelope
 * helpers read `body.detail` with a cast but no optional chaining (`:147`, `:155`), while the leg that owns
 * them sets `body = null` for a non-JSON answer (`:531`).  So a genuine `502 Bad Gateway` from an HTML
 * proxy threw *inside* the `!response.ok` branch (`:539`), the throw was swallowed by the sheet's big catch
 * (`:738`) and that catch wrote `status: "NETWORK", failureReason: null` (`:748`) -- which both blames the
 * network for a server answer and, because 技术详情 is gated on `failureReason || summary` (`:936`), removes
 * the one panel that could have explained it.  The 0280 arms missed it because every one of them answered
 * with JSON: the only quantity that distinguishes these states is whether the body holds a JSON object,
 * which is neither the status code nor the elapsed time (Q25).
 *
 * Three arms, one per claim in the order:
 *   N1  non-JSON 500  -> status stays HTTP_500, the block still renders, and it says this device has no
 *                       server wording (never 「服务器给出的原因」, never 「连不上服务端」).
 *   N2  positive control: a 4xx that DOES carry `error.message` -> still green after the fix: the server's
 *                       sentence is shown verbatim under the attribution label (`==`, not `in`).
 *   N3  a real network failure (the request is aborted) -> NETWORK, and ② is what this measures: the detail
 *                       block is still there, carrying a device-composed line.
 */
import { expect, test, type Page, type Route } from "@playwright/test";
import { writeFileSync } from "node:fs";
import { evidencePath } from "./_qoderEvidence";

const FILE = "e2e/qoder-ord0302-unreadable-server-body.spec.ts";
const node = (id: string, detail: string) => `${FILE} :: ${id} — ${detail}`;
const clean = (v: string | null | undefined) => String(v ?? "").replace(/\s+/g, " ").trim();

const SERVER_LABEL_ZH = "服务器给出的原因";
const SERVER_LABEL_EN = "Reason the server gave";
const NETWORK_COPY = "连不上服务端";
const USER_SENTENCE = "帮我排三天，喜欢美食和特色景点。";
const SERVER_SENTENCE = "该目的地的候选目录尚未就绪，请稍后重试。";

type Force = { status: number; contentType: string; body: string } | { abort: true };
type ArmId = "N1" | "N2" | "N3";
const readings: Record<string, unknown> = {};

async function bootAndAsk(page: Page, force: Force, arm: ArmId) {
  const scene = (await (await page.request.get("/api/v1/demo/scene")).json()) as { journey_id?: string };
  const journeyId = String(scene.journey_id ?? "");
  expect(journeyId.length > 0, node(arm, "the stage named no journey")).toBe(true);
  await page.addInitScript((id) => {
    localStorage.clear();
    localStorage.setItem("citynexus.v8.journey_id", id as string);
    localStorage.setItem("citynexus.locale", "zh-CN");
  }, journeyId);
  await page.setViewportSize({ width: 390, height: 844 });

  const seen: string[] = [];
  await page.route("**/api/v1/journeys/*/plans", async (r: Route) => {
    if (r.request().method() !== "GET") return r.fallback();
    seen.push("GET /plans(baseline)");
    await r.fulfill({ status: 200, contentType: "application/json", body: "[]" });
  });
  await page.route("**/api/v1/journeys/*/agent/commands", async (r: Route) => {
    if (r.request().method() !== "POST") return r.fallback();
    seen.push("POST /agent/commands");
    if ("abort" in force) return r.abort();
    await r.fulfill({ status: force.status, contentType: force.contentType, body: force.body });
  });

  await page.goto("/v8/hub", { waitUntil: "load" });
  await expect(page.getByTestId("today-hero"), node(arm, "the hub never rendered")).toBeVisible({
    timeout: 30_000,
  });
  await page.getByTestId("hub-plan-with-ai").click();
  await page.getByTestId("plan-ai-input").fill(USER_SENTENCE);
  await page.getByTestId("plan-ai-submit").click();
  const result = page.getByTestId("plan-ai-result");
  await expect(result, node(arm, "the sheet never answered")).toBeVisible({ timeout: 120_000 });

  const cardText = clean(await result.innerText());
  const status = (await result.getAttribute("data-result-status")) ?? "";
  /* `count()` first: on the buggy tree the block is not in the DOM at all, and waiting for it would hang for
     30 s and then read as a timeout instead of the finding it is. */
  const details = page.getByTestId("plan-ai-detail-toggle");
  const blockAttached = (await details.count()) > 0;
  let label = "";
  let origin = "";
  let reason = "";
  if (blockAttached) {
    await details.click();
    label = clean(await page.getByTestId("plan-ai-detail-kind").innerText());
    origin = (await page.getByTestId("plan-ai-detail-kind").getAttribute("data-reason-origin")) ?? "";
    reason = clean(await page.getByTestId("plan-ai-reason").innerText());
  }
  return { arm, status, detail_block_attached: blockAttached, label, origin, reason, card_text: cardText,
    legs: seen };
}

function decide(arm: ArmId, read: Awaited<ReturnType<typeof bootAndAsk>>): { verdict: string; rows: unknown[] } {
  const rows: { claim: string; ok: boolean; got: unknown }[] = [];
  const add = (claim: string, ok: boolean, got: unknown) => rows.push({ claim, ok, got });
  if (arm === "N1") {
    add("an unreadable answer stays HTTP_500 and never becomes NETWORK", read.status === "HTTP_500",
      { status: read.status });
    add("the technical-detail block is still in the DOM", read.detail_block_attached,
      { detail_block_attached: read.detail_block_attached });
    add("the reading is labelled as this device's, not the server's",
      read.origin === "device" && read.label !== SERVER_LABEL_ZH && read.label !== SERVER_LABEL_EN,
      { label: read.label, origin: read.origin });
    add("the card does not blame the network", !read.card_text.includes(NETWORK_COPY),
      { card_head: read.card_text.slice(0, 40) });
    add("a device-composed line is still shown (this is not a mute-the-error fix)",
      read.reason.length > 0, { reason: read.reason });
  } else if (arm === "N2") {
    add("a refusal that carries the server's sentence still renders under the attribution label",
      read.label === SERVER_LABEL_ZH && read.origin === "server", { label: read.label, origin: read.origin });
    add("the server's words are passed through verbatim (equality, not containment)",
      read.reason === clean(SERVER_SENTENCE), { reason: read.reason, expected: clean(SERVER_SENTENCE) });
    add("status is the HTTP answer it is", read.status === "HTTP_422", { status: read.status });
  } else {
    add("a request that really never got an answer is NETWORK", read.status === "NETWORK",
      { status: read.status });
    add("ORD-0302 ②: even then the detail block is still there", read.detail_block_attached,
      { detail_block_attached: read.detail_block_attached });
    add("and it carries a device line rather than nothing",
      read.reason.length > 0 && read.origin === "device", { reason: read.reason, origin: read.origin });
  }
  const bad = rows.filter((r) => !r.ok);
  return { verdict: bad.length === 0 ? "MET" : "NOT_MET", rows: rows.map((r) => ({ ...r, ok: r.ok })) ,
    ...(bad.length ? { failed: bad.map((b) => b.claim) } : {}) } as { verdict: string; rows: unknown[] };
}

const ARMS: { id: ArmId; force: Force }[] = [
  { id: "N1", force: { status: 500, contentType: "text/html; content-type=text/plain",
                       body: "<html><body>502 Bad Gateway</body></html>" } },
  { id: "N2", force: { status: 422, contentType: "application/json",
                       body: JSON.stringify({ error: { code: "request.invalid", message: SERVER_SENTENCE,
                         message_key: "request.invalid", details: null } }) } },
  { id: "N3", force: { abort: true } },
];

for (const { id, force } of ARMS) {
  test(`ord0302-${id} ${id === "N1" ? "a non-JSON 5xx stays an HTTP answer with a visible device reading"
    : id === "N2" ? "a 4xx with the server's sentence still quotes it verbatim (positive control)"
      : "a genuine network failure keeps NETWORK and still renders the detail block"}`, async ({ page }) => {
    const read = await bootAndAsk(page, force, id);
    const { verdict, rows } = decide(id, read);
    readings[id] = { want: id === "N2" ? "server" : "device", force_shape: force, read, verdict, rows };
    expect(rows.filter((r: { ok: boolean }) => !r.ok), node(id, JSON.stringify({ verdict, read }))).toEqual([]);
  });
}

test.afterAll(() => {
  writeFileSync(
    evidencePath("ord0302", "unreadable_body_arms.json"),
    JSON.stringify({ file: FILE, runId: process.env.CITYNEXUS_E2E_RUN_ID ?? "", arms: readings }, null, 1),
  );
});
