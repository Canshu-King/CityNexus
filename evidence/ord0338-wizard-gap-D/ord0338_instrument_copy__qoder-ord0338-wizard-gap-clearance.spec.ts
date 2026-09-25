/**
 * ORD-0338 · 移动向导里「步骤条与目的地之间」的空白带必须有上界，且挪走的 clearance 仍然管用
 *
 * 定性见收据 `evidence/ord0338-wizard-gap-D/ord0338_gap_anatomy_r1.json`：那 229px 不是插槽，
 * 是 `.cn-onboarding .trial-steps` 在 ≤680px 下的 padding-bottom（76 + `--cn-sim-float-clearance` 实算 136）。
 * 同一枚实验又证明它当前是 load-bearing：把它直接置 0，`qoder-wizard-advanced-is-tappable.spec.ts`
 * 的 `ord0264` 当场红。所以修法不是删，是 **挪** —— clearance 交给真正结束在 sticky 条附近的
 * `.trial-card` 底部留白，步骤条那条在 ≤680px 下取消（>680px 那一条一字不动，因为本单没量过桌面）。
 *
 * 四枚节点，双向：
 *   G1 带上界 —— 390×844 下带高必须 ≤ 60px（正控：步骤条与目的地标签都还在，标签文字仍是「目的地」）
 *   G2 不许「占高不显示」—— 带内既没有内容节点，也没有任何 >60px 的透明节点（塌布局但占高过不了这一关）
 *   G3 clearance 仍管用 —— 走 `ord0264` 同一条人路径（打字 → 滚轮滚到入口 → 量中心命中谁），
 *      入口必须命到自己；这条红就说明留白挪错了地方
 *   G4 反向臂 —— 用 addStyleTag 把旧形状（步骤条 76+132、卡片 84）装回去，带高必须回到 >200px；
 *      G1 若对这条不敏感，它就是一枚没有牙齿的门
 *
 * 判据全部读渲染几何；G4 只动页面，落盘产品字节 0 改。
 */
import { expect, test, type Page } from "@playwright/test";
import { writeFileSync } from "node:fs";
import { evidencePath } from "./_qoderEvidence";

const FILE = "e2e/qoder-ord0338-wizard-gap-clearance.spec.ts";
const node = (id: string, detail: string) => `${FILE} :: ${id} — ${detail}`;
const BAND_BOUND = 60;

/* same context the accepted ORD-0261/0264 gates run in: phone viewport *and* touch, because
   hit-testing differs without it and a gate measured in a different medium is not the same promise */
test.use({ viewport: { width: 390, height: 844 }, hasTouch: true });

async function clean(page: Page) {
  return page.evaluate(() => {
    const norm = (v: string | null | undefined) => String(v ?? "").replace(/\s+/g, " ").trim();
    const steps = document.querySelector('[data-testid="trial-steps"]');
    const city = document.querySelector('[data-testid="trial-city"]');
    if (!steps || !city) return { missing: "trial-steps 或 trial-city 不在 DOM" };
    const items = Array.from(steps.querySelectorAll("li"));
    const label = city.closest("label")?.querySelector("span") ?? city;
    const bandTop = Math.round(Math.max(...items.map((li) => li.getBoundingClientRect().bottom)));
    const bandBottom = Math.round(label.getBoundingClientRect().top);
    const members: Array<Record<string, unknown>> = [];
    for (const el of Array.from(document.querySelectorAll("body *"))) {
      const r = el.getBoundingClientRect();
      if (r.height <= 0 || r.width <= 0) continue;
      // only things that *fit inside* the band count; a wrapper that spans it is not content there
      if (r.top < bandTop - 1 || r.bottom > bandBottom + 1) continue;
      if (el.contains(steps) || el.contains(label) || steps.contains(el) || label.contains(el)) continue;
      const own = norm(
        Array.from(el.childNodes).filter((n) => n.nodeType === 3).map((n) => n.textContent).join(" "),
      );
      members.push({
        tag: el.tagName.toLowerCase(),
        testid: el.getAttribute("data-testid"),
        role: el.getAttribute("role"),
        ownText: own.slice(0, 40),
        height: Math.round(r.height),
      });
    }
    return {
      viewport: { width: window.innerWidth, height: window.innerHeight },
      band: { top: bandTop, bottom: bandBottom, height: bandBottom - bandTop },
      label: norm(label.textContent),
      stepLabels: items.map((li) => norm(li.textContent)),
      members,
      tallestMember: members.reduce((m, e) => Math.max(m, Number(e.height)), 0),
      computed: {
        stepsPaddingBottom: getComputedStyle(steps).paddingBottom,
        cardPaddingBottom: getComputedStyle(document.querySelector(".trial-card")!).paddingBottom,
      },
    };
  });
}

async function openWizard(page: Page) {
  await page.addInitScript(() => {
    localStorage.clear();
    localStorage.setItem("citynexus.locale", "zh-CN");
  });
  await page.goto("/v8/hub", { waitUntil: "load" });
  await page.waitForSelector('[data-testid="trial-setup"]', { timeout: 60_000 });
  await page.waitForSelector('[data-testid="trial-city"]', { timeout: 30_000 });
}

/** The human path ORD-0264 uses: fill a draft, roll a real wheel to the control, then ask who the
 *  centre of that control hits. Re-using it keeps this gate from inventing a promise of its own. */
async function reachAndProbe(page: Page, selector: string) {
  await page.evaluate(() => window.scrollTo(0, 0));
  for (let i = 0; i < 40; i += 1) {
    const found = await page.evaluate((sel) => {
      const el = document.querySelector(sel);
      if (!el) return false;
      const r = el.getBoundingClientRect();
      return r.top > 40 && r.bottom < window.innerHeight - 40;
    }, selector);
    if (found) break;
    await page.mouse.wheel(0, 120);
    await page.waitForTimeout(60);
  }
  return page.evaluate((sel) => {
    const el = document.querySelector(sel);
    if (!el) return { present: false };
    const r = el.getBoundingClientRect();
    const cx = Math.round(r.left + r.width / 2);
    const cy = Math.round(r.top + r.height / 2);
    const landed = document.elementFromPoint(cx, cy);
    return {
      present: true,
      centre: [cx, cy],
      hitTag: landed ? landed.tagName.toLowerCase() : "NONE",
      hitText: landed ? String(landed.textContent ?? "").replace(/\s+/g, " ").trim().slice(0, 24) : "",
      hitsItself: !!landed && (landed === el || el.contains(landed)),
      scrollY: Math.round(window.scrollY),
    };
  }, selector);
}

function writeArm(arm: string, payload: Record<string, unknown>) {
  writeFileSync(
    evidencePath(`ord0338-gate-${arm}.json`),
    JSON.stringify(
      {
        generatedBy: "e345b9d6",
        file: FILE,
        arm,
        order: "ORD-0338",
        run: process.env.CITYNEXUS_E2E_RUN_ID ?? "dev",
        tree_sha: process.env.CNX_TREE_SHA ?? "CNX_TREE_SHA-unset",
        bound_px: BAND_BOUND,
        ...payload,
      },
      null,
      1,
    ),
  );
}

test("G1 带上界：步骤条与第一格之间不许再出现一整块空白", async ({ page }) => {
  test.setTimeout(300_000);
  await openWizard(page);
  const g = await clean(page);
  writeArm("G1-band-bound", g);
  expect(g.missing, node("G1", `向导没挂全：${g.missing}`)).toBeUndefined();
  expect(g.label, node("G1", `带下方不是「目的地」而是「${g.label}」，量错位置了`)).toContain("目的地");
  expect(g.band.height <= BAND_BOUND, node(
    "G1",
    `带高 ${g.band.height}px 超过上界 ${BAND_BOUND}px；computed=${JSON.stringify(g.computed)}`)).toBe(true);
});

test("G2 不许「占高但不显示」：带内既无内容节点也无 >60px 的透明节点", async ({ page }) => {
  test.setTimeout(300_000);
  await openWizard(page);
  const g = await clean(page);
  writeArm("G2-no-invisible-reserved", g);
  expect(g.members.filter((m: any) => m.ownText).length, node(
    "G2", `带里有带文字的节点：${JSON.stringify(g.members)}`)).toBe(0);
  expect(g.tallestMember <= BAND_BOUND, node(
    "G2", `带里有 ${g.tallestMember}px 高的节点却不显示内容（塌布局占高）：${JSON.stringify(g.members)}`)).toBe(true);
});

test("G3 挪过去的 clearance 仍然挡住 sticky 条（走 ord0264 那条人路径）", async ({ page }) => {
  test.setTimeout(300_000);
  await openWizard(page);
  await page.getByTestId("trial-city").fill("天津");
  await page.getByTestId("trial-arrival").fill("天津站");
  await page.getByTestId("trial-departure").fill("天津西站");
  const opener = await reachAndProbe(page, '[data-testid="trial-show-advanced"]');
  writeArm("G3-clearance-still-clears", { opener, cardPadding: (await clean(page)).computed });
  expect(opener.present, node("G3", "高级入口根本没渲染，这一枚量不到东西")).toBe(true);
  expect(opener.hitsItself, node(
    "G3",
    `滚到入口之后它的中心 ${JSON.stringify(opener.centre)} 命中的是 <${opener.hitTag}> `
    + `“${opener.hitText}” —— clearance 挪错了地方`)).toBe(true);
});

test("G4 反向臂：把旧形状装回页面，带高必须回到一整块（证明 G1 有牙齿）", async ({ page }) => {
  test.setTimeout(300_000);
  await openWizard(page);
  const fixed = await clean(page);
  await page.addStyleTag({
    content:
      "@media (max-width: 680px) { .cn-onboarding .trial-steps { padding-bottom: calc(76px + "
      + "var(--cn-sim-float-clearance, 132px) + env(safe-area-inset-bottom, 0px)) !important; } "
      + ".cn-onboarding .trial-card { padding-bottom: 84px !important; } }",
  });
  await page.waitForTimeout(250);
  const retro = await clean(page);
  writeArm("G4-reverse-arm", { fixed, retrofitted_to_old_shape: retro });
  expect(retro.band.height > 200, node(
    "G4",
    `装回旧形状之后带高只有 ${retro.band.height}px —— 那 G1 量的就不是这条声明`)).toBe(true);
  expect(fixed.band.height <= BAND_BOUND, node(
    "G4", `正控失效：候选树上带高已经是 ${fixed.band.height}px，G1 与 G4 就不是同一件事`)).toBe(true);
});
