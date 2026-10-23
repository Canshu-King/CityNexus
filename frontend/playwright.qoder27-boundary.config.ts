/* Issue #27 的私有 runner：只跑 `e2e/qoder27-timeline-identity-boundary.spec.ts`。
 *
 * 它不起任何东西、不占端口：这一条要的是"真浏览器 + 真前端 + 真后端答应的行程"，
 * 而工具轨迹与授权答复由用例里的 route 明确模拟成两个成员（A=200、B=403）。
 * 默认打指挥线自己的开发端口（:8121 前端、:8011 后端），共享的 :8000/:4781/:4782/:8693 一律不碰。
 * 这里没有 webServer，也没有可默认掉的端口变量 —— 把这条指到别人的端口上，量的就不是同一件事了。
 *
 * 不是验收闸：能签验收的仍然只有 `playwright.config.ts`。
 */
import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  testMatch: /qoder27-timeline-identity-boundary\.spec\.ts/,
  timeout: 180_000,
  workers: 1,
  reporter: [["list"], ["json", { outputFile: process.env.CNX_QODER27_REPORT ?? "e2e/.qoder27-report.json" }]],
});
