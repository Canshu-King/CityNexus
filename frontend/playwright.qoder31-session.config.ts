import { defineConfig, devices } from "@playwright/test";
import { randomBytes } from "node:crypto";

/**
 * Issue #31 A/B 的私有 runner（号令者自用）。
 *
 * 这一条不靠桩：它打的是**真后端**（这棵树里的 `backend/app/main.py` 现起的一台 uvicorn），
 * 所以「新建 Traveler 就拿到能被服务器认出的会话」「旧 Journey 指针不再授权」这两件事，
 * 是服务器真的签了、真的拒了，而不是页面自己演的。为此这个 config 在加载时现生成一枚
 * 一次性 `CITYNEXUS_TRAVELER_AUTH_SECRET` —— 值只进子进程的环境，不写文件、不打印、不进日志。
 *
 * 端口另开一对（前端 :8131 / 后端 :8031），不碰指挥线与共享的 :8000/:4781/:4782/:8693，
 * 也不碰我自己那条 :8121/:8011；库名带 run id，且这一对服务都是 `reuseExistingServer: false`
 * ——测的就是现起的这台，不是别人的余温。
 */
const RUN_ID = `qoder31-${Date.now().toString(36)}`;
const FRONTEND_PORT = Number(process.env.CNX_QODER31_WEB ?? 8131);
const BACKEND_PORT = Number(process.env.CNX_QODER31_API ?? 8031);
const DB = process.env.CNX_QODER31_DB ?? `sqlite:///./_e2e_${RUN_ID}.db`;
const PYTHON = process.env.CITYNEXUS_PYTHON ?? "python";
const SECRET = randomBytes(32).toString("hex");

export default defineConfig({
  testDir: "./e2e",
  testMatch: /qoder31-(?:signed-session|first-trip-guide|wizard-wording)\.spec\.ts/,
  timeout: 180_000,
  expect: { timeout: 15_000 },
  workers: 1,
  retries: 0,
  reporter: [["list"]],
  use: {
    baseURL: `http://127.0.0.1:${FRONTEND_PORT}`,
    trace: "off",
    video: "off",
  },
  projects: [
    {
      name: "chromium-phone",
      // 390×844 是 Issue #31 点名的那一档（主人自己的手机宽度）。
      use: {
        ...devices["Desktop Chrome"],
        viewport: { width: 390, height: 844 },
        hasTouch: true,
        isMobile: true,
      },
    },
  ],
  webServer: [
    {
      command: `${PYTHON} -m uvicorn app.main:app --host 127.0.0.1 --port ${BACKEND_PORT}`,
      cwd: "../backend",
      env: {
        ...(process.env as Record<string, string>),
        CITYNEXUS_DATABASE_URL: DB,
        CITYNEXUS_AI_ENABLED: "false",
        CITYNEXUS_DEMO_MODE: "true",
        CITYNEXUS_E2E_RUN_ID: RUN_ID,
        // 值只到这里的子进程环境；不进文件、不进打印、不进收据。
        CITYNEXUS_TRAVELER_AUTH_SECRET: SECRET,
        // Issue #33 Q1：会话续期那一臂需要"服务器给的窗口本来就短"，而这只能由部署的 TTL 决定。
        // 默认 900（与产品配置同值）；`CNX_QODER31_TTL=60` 起的那一台才把窗口缩短到 300 秒余量之下，
        // 于是测试测的是产品自己会不会去续，而不是我把到期字段改短了。
        CITYNEXUS_TRAVELER_AUTH_TTL_SECONDS: process.env.CNX_QODER31_TTL ?? "900",
        PYTHONIOENCODING: "utf-8",
      },
      url: `http://127.0.0.1:${BACKEND_PORT}/api/v1/health`,
      reuseExistingServer: false,
      timeout: 120_000,
      stdout: "ignore",
      stderr: "pipe",
    },
    {
      command: `node node_modules/vite/bin/vite.js --port ${FRONTEND_PORT} --host 127.0.0.1`,
      cwd: ".",
      env: { ...(process.env as Record<string, string>), CITYNEXUS_BACKEND_PORT: String(BACKEND_PORT) },
      url: `http://127.0.0.1:${FRONTEND_PORT}`,
      reuseExistingServer: false,
      timeout: 120_000,
      stdout: "ignore",
      stderr: "pipe",
    },
  ],
});
