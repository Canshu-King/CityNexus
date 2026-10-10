/* ORD-0557 browser probe: can an empty Content-Type ever reach the page?
 *
 * Why this question decides the screen-reading leg.  The two Chinese fallbacks this order moved are
 * only painted when `attribution.content_type` is absent, and the classification drops the field when
 * the value handed to it is falsy-but-not-nullish, i.e. the empty string.  So the fallback cell has
 * exactly one production door: an answer whose Content-Type header exists and is empty.  Whether that
 * door exists at all is not a reading-comprehension question about this file -- it is a property of
 * the browser's fetch layer, so it gets measured here, on the Chromium Playwright actually drives.
 *
 * Run: node review/taichenggong/content_type_probe_r1.mjs
 * Prints one line per arm; exit 0 always (this is a measurement, not a gate).
 */

import { createRequire } from "node:module";
import path from "node:path";
import { writeFileSync } from "node:fs";

const HERE = import.meta.dirname;
const REPO = path.resolve(HERE, "..", "..");
const OUT = path.join(HERE, "content_type_probe_r1.txt");
// Playwright lives under frontend/node_modules; resolve from there so this runs from any cwd.
const { chromium } = createRequire(path.join(REPO, "frontend", "package.json"))("@playwright/test");

const ARMS = [
  { id: "empty", send: "", expect: "the header is present and empty" },
  { id: "absent", send: null, expect: "no Content-Type at all" },
  { id: "html", send: "text/html", expect: "a real media type" },
];

const rows = [];
const say = (line) => { rows.push(line); console.log(line); };

const browser = await chromium.launch();
const page = await browser.newPage();

/* A relative fetch needs a real origin, and the product dev server is not this measurement's
   subject, so the script serves its own one-line page on a loopback port. */
const http = await import("node:http");
const server = http.createServer((_req, res) => {
  res.writeHead(200, { "content-type": "text/plain" });
  res.end("probe host");
});
await new Promise((done) => server.listen(0, "127.0.0.1", done));
const port = server.address().port;
await page.goto(`http://127.0.0.1:${port}/host`);

for (const arm of ARMS) {
  await page.route("**/__probe**", async (route) => {
    const init = { status: 200, body: "<html>not json</html>" };
    if (arm.send === null) init.headers = {};
    else init.headers = { "content-type": arm.send };
    await route.fulfill(init);
  });
  const got = await page.evaluate(async () => {
    const res = await fetch("/__probe?" + Math.random());
    return { raw: res.headers.get("content-type"), all: JSON.stringify(res.headers) };
  });
  say(`arm=${arm.id} sent=${JSON.stringify(arm.send)} -> `
    + `page saw ${JSON.stringify(got.raw)} (typeof ${typeof got.raw}) :: ${arm.expect}`);
}

await browser.close();
say("");
say("read this back: the fallback cell can only paint if some arm above yields an empty string that "
  + "survives into Response.headers.get(); 'null' means the classification's own fallback phrase is "
  + "what reaches the screen instead.");
writeFileSync(OUT, rows.join("\n") + "\n", "utf8");
