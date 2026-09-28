/**
 * ORD-0382 evidence harness -- serves MY built bundle with /api answered from payloads captured
 * read-only off the live preview, and holds the two mutating legs locally so nothing pressed in this
 * harness can create a mission, a plan or a row on the store the traveller is watching.
 *
 * Every capture below came from a GET on 127.0.0.1:4781 (byte counts in the receipt).  POST
 * /agent/commands and POST /plans/generate are never forwarded: the preflight line the traveller
 * reads in these frames is the server's real current value (`ai_state: DISABLED_BY_OPS`), while the
 * leg that would have consumed an AI answer is withheld here and named as such.
 *
 *   node harness_r1.mjs [distDir] [port]      bundle on <port>, arm switch on <port>+1
 */
import http from "node:http";
import { readFileSync, existsSync } from "node:fs";
import { join, normalize, resolve } from "node:path";

/* resolve(), so the containment test below compares like with like: join() emits backslashes on
   Windows and a forward-slash constant would reject every asset. */
const DIST = resolve(process.argv[2] ?? "D:/moodle/_qoder_q_ord0382_snap/frontend/dist");
const CAP = resolve("D:/moodle/_qoder_q_ord0382_evidence");
const PORT = Number(process.argv[3] ?? 4789);
/* Two named scenarios, both captured read-only off the live chain.  `guangzhou-frozen` is the sealed
   journey as it stood at 02:42; the 03:55 `POST /api/v1/demo/reset` wiped it from `_preview.db`, so
   that scenario now exists ONLY as the files below -- which is also why this harness never touches
   :8693 or :4781 and can be replayed on a machine with no backend at all.  `cnx-demo` is the
   scenario the chain actually serves now, captured at 04:0x.

     node harness_r1.mjs <distDir> <port> [guangzhou-frozen|cnx-demo]
*/
const SCENARIOS = {
  "guangzhou-frozen": {
    journey: "9c6c3d73-8b8e-4f71-beaf-32bc87aba035",
    scene: "live_scene.json",
    status: "live_runtime-status.json",
    experience: "live_journeys_9c6c3d73-8b8e-4f71-beaf-32bc87aba035_experience.json",
    journeyBody: "live_journeys_9c6c3d73-8b8e-4f71-beaf-32bc87aba035.json",
    plans: "live_plans.json",
    feed: "live_agentfeed.json",
    places: "live_places.json",
  },
  "cnx-demo": {
    journey: "22222222-2222-4222-8222-222222222222",
    scene: "live2_scene.json",
    status: "live2_status.json",
    experience: "live2_experience.json",
    journeyBody: "live2_scene.json",
    plans: "live2_plans.json",
    feed: "live2_agentfeed.json",
    places: "live2_places.json",
  },
};
const SCENARIO = SCENARIOS[process.argv[4] ?? "guangzhou-frozen"];
if (!SCENARIO) throw new Error(`unknown scenario ${process.argv[4]}`);
const JOURNEY = SCENARIO.journey;

const cap = (name) => readFileSync(join(CAP, name));
const STATUS = cap(SCENARIO.status);
const SCENE = cap(SCENARIO.scene);
const EXPERIENCE = cap(SCENARIO.experience);
const PLANS = cap(SCENARIO.plans);
const ROWS = JSON.parse(PLANS.toString("utf-8"));
const FEED = cap(SCENARIO.feed);
const JOURNEY_BODY = cap(SCENARIO.journeyBody);
const PLACES = cap(SCENARIO.places);
const utf8 = (value) => Buffer.from(value, "utf-8");

const MIME = {
  ".js": "text/javascript",
  ".css": "text/css",
  ".html": "text/html",
  ".svg": "image/svg+xml",
  ".webmanifest": "application/manifest+json",
  ".png": "image/png",
};

const DEFAULTS = {
  commandDelayMs: 9_000,
  commandStatus: 200,
  /** `{}` is the answer the existing gate arm `plan-ai-cancel-aborts-request` already uses, so this
   *  harness is not inventing a fourth envelope nobody has measured. */
  commandBody: "{}",
  generateStatus: 422,
  generateBody: JSON.stringify({ error: { code: "MOBILITY_DATA_UNAVAILABLE" } }),
  plansBody: PLANS,
  /** Swapped in at the command leg, so the run's own baseline read is the "before" side. */
  growsTo: null,
};
const arm = { ...DEFAULTS, hit: { commands: 0, generates: 0, plansReads: 0 } };

const json = (res, status, body, type = "application/json") => {
  res.writeHead(status, { "content-type": `${type}; charset=utf-8`, "content-length": body.length });
  res.end(body);
};

const product = http.createServer((req, res) => {
  const url = (req.url ?? "").split("?")[0];
  const method = req.method ?? "GET";

  if (url.startsWith("/api/v1")) {
    if (url === "/api/v1/agent/runtime-status") return json(res, 200, STATUS);
    if (url === "/api/v1/demo/scene") return json(res, 200, SCENE);
    if (url === `/api/v1/journeys/${JOURNEY}/experience`) return json(res, 200, EXPERIENCE);
    if (url === `/api/v1/journeys/${JOURNEY}/agent-feed`) return json(res, 200, FEED);
    if (url === `/api/v1/journeys/${JOURNEY}` && method === "GET") return json(res, 200, JOURNEY_BODY);
    if (url === "/api/v1/places" && method === "GET") return json(res, 200, PLACES);
    if (url === `/api/v1/journeys/${JOURNEY}/plans` && method === "GET") {
      arm.hit.plansReads += 1;
      return json(res, 200, arm.plansBody);
    }
    if (url === `/api/v1/journeys/${JOURNEY}/agent/commands`) {
      arm.hit.commands += 1;
      const grows = arm.growsTo;
      const timer = grows ? setTimeout(() => { arm.plansBody = grows; }, 1_000) : null;
      return new Promise((r) => setTimeout(r, arm.commandDelayMs)).then(() => {
        if (timer) clearTimeout(timer);
        if (grows) arm.plansBody = grows;
        return json(res, arm.commandStatus, utf8(arm.commandBody));
      });
    }
    if (url === `/api/v1/journeys/${JOURNEY}/plans/generate`) {
      arm.hit.generates += 1;
      return new Promise((r) => setTimeout(r, 1_500)).then(() =>
        json(res, arm.generateStatus, utf8(arm.generateBody)),
      );
    }
    console.log(`UNSERVED ${method} ${req.url}`);
    return json(res, 404, utf8('{"detail":"not served by the ORD-0382 harness"}'));
  }

  /* SPA: /v8/* is the shell; every other path is a static asset. */
  const asset = url === "/" || url.startsWith("/v8")
    ? "index.html"
    : normalize(url).replace(/^(\.\.[/\\])+/, "").replace(/^[\\/]+/, "");
  const file = join(DIST, asset);
  if (!file.startsWith(DIST) || !existsSync(file)) {
    res.writeHead(404).end("no asset");
    return;
  }
  res.writeHead(200, {
    "content-type": MIME[file.slice(file.lastIndexOf("."))] ?? "application/octet-stream",
    "cache-control": "no-store",
  });
  res.end(readFileSync(file));
});

/** The driver flips arms over HTTP, so the browser is never relaunched between states. */
http.createServer((req, res) => {
  const query = new URL(req.url ?? "", "http://x").searchParams;
  const done = (extra = {}) => {
    res.writeHead(200, { "content-type": "application/json" });
    res.end(JSON.stringify({ ok: true, ...extra }));
  };
  if (query.has("hits")) return done({ hit: arm.hit });
  if (query.has("reset")) Object.assign(arm, DEFAULTS, { hit: arm.hit });
  /* two_sided: the baseline the run reads holds the real captured rows minus one SUPERSEDED row, and
     the read-back after the interruption sees the full set -- which is the only way to reach the
     「已经生成的部分还在」 branch without writing anything.  `appeared` drops the ACTIVE row instead. */
  if (query.has("twoSided")) {
    const without = query.get("twoSided") === "appeared" ? ROWS.slice(0, -1) : ROWS.slice(1);
    arm.plansBody = utf8(JSON.stringify(without));
    arm.growsTo = PLANS;
  }
  for (const key of ["commandDelayMs", "commandStatus", "generateStatus"]) {
    if (query.has(key)) arm[key] = Number(query.get(key));
  }
  if (query.has("commandBody")) arm.commandBody = String(query.get("commandBody"));
  return done({ arm: { commandStatus: arm.commandStatus, commandDelayMs: arm.commandDelayMs, plansBytes: arm.plansBody.length } });
}).listen(PORT + 1, "127.0.0.1", () => console.log(`ARM http://127.0.0.1:${PORT + 1}`));

product.listen(PORT, "127.0.0.1", () =>
  console.log(`BUNDLE http://127.0.0.1:${PORT}/v8 from ${DIST} scenario=${process.argv[4] ?? "guangzhou-frozen"} journey=${JOURNEY}`),
);
