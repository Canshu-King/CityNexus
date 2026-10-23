/* a68b0631 - the execution clock on screen must name the zone the server actually used.
 *
 * The server's execution clock answers three things in one payload: `now` is the instant,
 * `timezone` is the zone the journey asked for, and `used_timezone` says the zone that instant
 * is actually in, with `timezone_honoured` saying whether the two are the same.  A screen that
 * renders `now` in `timezone` and prints `timezone` underneath shows two facts that can disagree:
 * the number in one zone, the label naming another.  When the journey's zone could not be used the
 * server says so -- and the screen has to say it too, instead of printing a zone that was never
 * granted.
 *
 * The arm measures the tree it is pointed at: it loads the real module and asks the real function
 * what the screen would say, so the same arm can be run against a tree with the change reverted
 * and must go red there.
 *
 * Usage: node clock_zone_attribution_arm_r1.mjs [tree-root]
 */
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { createRequire } from "node:module";

const require_ = createRequire(import.meta.url);
const ARM_DIR = path.dirname(fileURLToPath(import.meta.url));
const OWN_TREE = path.resolve(ARM_DIR, "..", "..");
const ROOT = path.resolve(process.argv[2] || OWN_TREE);
const FRONTEND = path.join(ROOT, "frontend");
const LIB_ZONE = path.join(FRONTEND, "src", "lib", "clockZone.ts");
const PANEL = path.join(
  FRONTEND,
  "src",
  "features",
  "execution",
  "V10LiveExecutionPanel.tsx",
);

const findings = [];

/* The zone the server used, and the flag that says whether the request was granted. */
const NOT_HONOURED = {
  timezone: "Asia/Shanghai",
  used_timezone: "UTC",
  timezone_honoured: false,
};
const HONOURED = {
  timezone: "Asia/Shanghai",
  used_timezone: "Asia/Shanghai",
  timezone_honoured: true,
};
/* An older server: the payload carries the requested zone and nothing else. */
const OLDER_SERVER = { timezone: "Asia/Shanghai" };

function loadReader() {
  if (!fs.existsSync(LIB_ZONE)) return null;
  const esbuild = require_(path.join(OWN_TREE, "frontend", "node_modules", "esbuild"));
  const work = fs.mkdtempSync(path.join(os.tmpdir(), "cnx-clockzone-"));
  /* The dictionary sheet pulls in React, and the tree under measurement may have no
     node_modules.  A stub keeps the bundle hermetic: the module under measurement only calls
     `createContext` at load time, and nothing on the measured path renders. */
  const stub = path.join(work, "react-stub.js");
  fs.writeFileSync(
    stub,
    [
      "export const createContext = (value) => ({ _currentValue: value, Provider: null, Consumer: null });",
      "export const useContext = (ctx) => ctx && ctx._currentValue;",
      "export const useState = (init) => [typeof init === 'function' ? init() : init, () => {}];",
      "export const useCallback = (fn) => fn;",
      "export const useEffect = () => {};",
      "export default {};",
    ].join("\n"),
    "utf8",
  );
  const out = path.join(work, "clockZone.cjs");
  esbuild.buildSync({
    entryPoints: [LIB_ZONE],
    bundle: true,
    format: "cjs",
    platform: "node",
    outfile: out,
    alias: { react: stub },
    logLevel: "silent",
  });
  return require_(out);
}

const reader = loadReader();
let caption = null;
if (!reader) {
  findings.push(
    "frontend/src/lib/clockZone.ts is missing: the screen has no way to learn which zone the " +
      "server used, so it can only render the zone the journey asked for",
  );
} else {
  const readClockZone = reader.readClockZone;

  const notHonoured = readClockZone(NOT_HONOURED);
  if (notHonoured.zone !== "UTC") {
    findings.push(
      `a moment the server placed in UTC was rendered in ${JSON.stringify(notHonoured.zone)}`,
    );
  }
  if (notHonoured.honoured !== false) {
    findings.push("the refused zone was not reported as refused");
  }

  const honoured = readClockZone(HONOURED);
  if (honoured.zone !== "Asia/Shanghai") {
    findings.push(
      `a granted zone was not rendered in the granted zone: ${JSON.stringify(honoured.zone)}`,
    );
  }
  if (honoured.honoured !== true) {
    findings.push("the granted zone was not reported as granted");
  }

  const older = readClockZone(OLDER_SERVER);
  if (older.zone !== "Asia/Shanghai") {
    findings.push(`an older server's zone was not rendered: ${JSON.stringify(older.zone)}`);
  }
  if (older.honoured !== null) {
    findings.push(
      "a payload that does not say whether the zone was granted was reported as if it did",
    );
  }

  if (typeof reader.clockZoneCaption !== "function") {
    findings.push("there is no function that decides the words under the clock");
  } else {
    caption = reader.clockZoneCaption;
    const refused = caption(NOT_HONOURED, false);
    if (!/UTC/.test(refused.label)) {
      findings.push(
        `the words under the clock do not say the moment is in UTC: ${JSON.stringify(refused.label)}`,
      );
    }
    if (!/Shanghai time/.test(refused.label)) {
      findings.push(
        `the words under the clock do not name the zone that was refused: ${JSON.stringify(refused.label)}`,
      );
    }
    if (refused.honoured !== false) {
      findings.push("the caption does not report the refused zone as refused");
    }
    const granted = caption(HONOURED, false);
    if (/could not be used/.test(granted.label)) {
      findings.push(
        `a granted zone is announced as refused: ${JSON.stringify(granted.label)}`,
      );
    }
    if (!/Shanghai time|Coordinated universal time/.test(granted.label)) {
      findings.push(
        `the granted zone is not named in traveller words: ${JSON.stringify(granted.label)}`,
      );
    }
    const refusedZh = caption(NOT_HONOURED, true);
    if (!/UTC/.test(refusedZh.label)) {
      findings.push(
        `the Chinese arm does not say the moment is in UTC: ${JSON.stringify(refusedZh.label)}`,
      );
    }
    if (!/上海时间/.test(refusedZh.label)) {
      findings.push(
        `the Chinese arm does not name the zone that was refused: ${JSON.stringify(refusedZh.label)}`,
      );
    }
    const grantedZh = caption(HONOURED, true);
    if (/用不了/.test(grantedZh.label)) {
      findings.push(
        `the Chinese arm announces a granted zone as refused: ${JSON.stringify(grantedZh.label)}`,
      );
    }
  }
}

/* The panel must render the moment in the zone the reader resolved. */
let panel = null;
try {
  panel = fs.readFileSync(PANEL, "utf8");
} catch {
  findings.push("the live execution panel is missing");
}
if (panel !== null) {
  if (!/clockZoneCaption/.test(panel)) {
    findings.push("the live execution panel does not read the zone the server used");
  }
  if (!/timeZone:\s*clockZone\.zone/.test(panel)) {
    findings.push(
      "the live execution panel does not render the moment in the zone the server used",
    );
  }
}

console.log(`tree root        : ${ROOT}`);
console.log(`reader present   : ${reader ? "yes" : "no"}`);
if (caption) {
  console.log(`refused caption  : ${JSON.stringify(caption(NOT_HONOURED, false).label)}`);
  console.log(`granted caption  : ${JSON.stringify(caption(HONOURED, false).label)}`);
}
console.log(`FINDINGS ${findings.length}`);
for (const finding of findings) console.log(`FAILED ${finding}`);
if (findings.length) process.exit(1);
console.log(
  "PASS the screen names the zone the server used, and says when it was not the requested one",
);
process.exit(0);
