/* Issue #33（主人新增令：UI 简洁）：中立口径那句话只说一遍。
 *
 * 这一臂盯的是一处**重复**，不是一处缺失：第 1 页的提示里已经把中立口径逐项列出来
 * （`CN / 人民币（CNY）/ Asia/Shanghai`），确认页又原样列第二遍——在 390 宽的手机上那一行
 * 折成三行，把「确认创建」那颗主按钮往下推。ORD-0350 的决定是"这一屏也要说"，不是"再说一遍清单"，
 * 所以这里保留提示本身、砍掉重复的枚举。
 *
 * 两条断言互为反控：少了任何一条，另一条就会红——只删第 1 页那份会红在"逐项还在"上，
 * 只删确认页那份会红在"这一屏仍然说"上。
 */
import { expect, test } from "@playwright/test";
import { mkdirSync } from "node:fs";

const DOC_EVIDENCE = "docs/assets/evidence";
mkdirSync(DOC_EVIDENCE, { recursive: true });

test.describe("Issue #33：确认页不重述第 1 页那份口径清单", () => {
  test.setTimeout(180_000);

  test("认不出的城市：第 1 页逐项说一次，确认页只留一句短提示", async ({ page }) => {
    await page.context().addInitScript(() => {
      try {
        localStorage.clear();
        sessionStorage.clear();
      } catch {
        /* 空设备上没什么可清的 */
      }
      localStorage.setItem("citynexus.theme", "light");
      localStorage.setItem("citynexus.locale", "zh-CN");
    });
    await page.emulateMedia({ colorScheme: "light", media: "screen" });
    await page.goto("/v8", { waitUntil: "load" });

    await expect(page.getByTestId("trial-city")).toBeVisible({ timeout: 25_000 });
    await page.getByTestId("trial-city").fill("zzz-没有这座城");
    await page.getByTestId("trial-arrival").fill("北京南站");
    await page.getByTestId("trial-departure").fill("大兴国际机场");
    await page.waitForTimeout(500);

    const step1 = (
      await page.getByTestId("trial-city-warning").innerText().catch(() => "")
    ).replace(/\s+/g, " ").trim();
    await page.screenshot({ path: `${DOC_EVIDENCE}/07-step1-neutral-basis.png` });
    expect(step1, "第 1 页那份逐项清单是这件事唯一该被说出来的地方").toContain("中立口径");
    expect(step1, "逐项清单要真的列出口径的三项").toMatch(/\/.+\/.+/);

    await page.getByTestId("trial-next").click();
    await page.waitForTimeout(400);
    await page.getByTestId("trial-next").click();
    await expect(page.getByTestId("trial-create")).toBeVisible({ timeout: 15_000 });

    const review = page.getByTestId("review-city-warning");
    await expect(review, "确认页仍然要说这一项没被识别（ORD-0350）").toBeVisible({ timeout: 15_000 });
    const reviewText = (await review.innerText()).replace(/\s+/g, " ").trim();
    await page.screenshot({ path: `${DOC_EVIDENCE}/08-review-neutral-basis.png` });
    expect(reviewText, "确认页要留着这句提示").toContain("未识别");
    /* 这一屏不该再把第 1 页那串清单抄一遍：数的是"有没有第二个斜杠"，不是字数。 */
    expect(
      reviewText.split("/").length - 1,
      `确认页重述了逐项清单：${reviewText}`,
    ).toBe(0);
    console.log(`中立口径措辞：第 1 页 ${step1.length} 字（逐项）| 确认页 ${reviewText.length} 字（${reviewText}）`);
  });
});
