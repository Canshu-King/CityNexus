/* ORD-0570 same-tree A/B: read the three migrated keys through pendingCopy() before (tip blob)
   and after (my tree), plus untouched keys and a bogus key, in both locales.
   The "before" arm is fed to esbuild through stdin with resolveDir pointed at the real module
   directory, so the pristine blob resolves the same ../../lib/plural the tip did and the working
   tree is never overwritten. */
const fs = require("fs");
const path = require("path");
const { execFileSync } = require("child_process");
const esbuild = require(path.join(__dirname, "frontend", "node_modules", "esbuild"));

const REPO = "D:/moodle/CityNexus";
const TIP = "ae2d96198bb346af5712810ddad3013928e62aa4";
const REL = "frontend/src/features/pending/pendingSetCopy.ts";
const SRC = path.join(__dirname, "frontend", "src", "features", "pending");
const REAL = path.join(SRC, "pendingSetCopy.ts");
const OUT = path.join(__dirname, "_ab_readings_0570.txt");
const TMP = path.join(__dirname, "_ab_tmp");
const KEYS = ["pending.title", "pending.sub", "pending.loading",
              "pending.filter", "pending.empty", "pending.not.a.key"];
const LOCALES = ["en", "zh-CN"];

const tipText = execFileSync("git", ["-C", REPO, "show", TIP + ":" + REL],
                             { encoding: "utf8", maxBuffer: 64 * 1024 * 1024 });
if (!tipText.includes("pendingSetCopy")) throw new Error("ABORT tip blob empty/unexpected");
const mine = fs.readFileSync(REAL, "utf8");
if (mine === tipText) throw new Error("ABORT working file is identical to tip -- no change to read");

const lines = [];
lines.push("tip=" + TIP);
lines.push("before_bytes=" + Buffer.byteLength(tipText) + " after_bytes=" + Buffer.byteLength(mine));
lines.push("interpreter=" + process.version);
fs.rmSync(TMP, { recursive: true, force: true });
fs.mkdirSync(TMP, { recursive: true });

(async () => {
  const arms = [
    ["before", { stdin: { contents: tipText, resolveDir: SRC, loader: "ts",
                          sourcefile: "pendingSetCopy_before.ts" } }],
    ["after", { entryPoints: [REAL] }],
  ];
  for (const [arm, opts] of arms) {
    const bundle = path.join(TMP, "bundle_" + arm + ".cjs");
    await esbuild.build(Object.assign({ bundle: true, format: "cjs", platform: "node",
                                       outfile: bundle, jsx: "automatic", logLevel: "silent" }, opts));
    const mod = require(bundle);
    for (const locale of LOCALES) {
      for (const key of KEYS) {
        lines.push(arm + " | " + locale + " | " + key + " | " + JSON.stringify(mod.pendingCopy(locale, key)));
      }
    }
  }
  fs.writeFileSync(OUT, lines.join("\n") + "\n", "utf8");
  console.log("WROTE " + OUT + " lines=" + lines.length);
})().catch((e) => { console.error("FAILED " + e.message); process.exit(1); });
