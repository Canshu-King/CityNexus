/* ORD-0422 acceptance assertion r2 -- matches the inventory against the rendered LEAF SETS that
 * final_readings_r2.mjs persisted, so the ruler no longer only asks what the readings script happened
 * to expect. A row the twin screen shows on a second journey is still a row the twin screen shows.
 *
 * Three numbers, all derived, none typed in:
 *   ZH_LEAK   -- inventory rows readable on any Chinese reading of that panel's route. Want 0.
 *                Measured with the strict substring matcher: English hiding inside a longer Chinese
 *                sentence still counts as a leak.
 *   EN_READ   -- inventory rows rendered as an exact leaf on an English reading. A row nobody shows is
 *                NOT_REACHED by measurement; its reason comes from the branch_gated flag and the two
 *                server refusals recorded in the same artifact.
 *   ZH_PAID   -- of the EN_READ rows, the ones whose Chinese dictionary counterpart is actually on the
 *                Chinese screen. Without this, a blank Chinese page would score ZH_LEAK = 0 and read
 *                like a pass.
 */
import fs from "node:fs";
import { execFileSync } from "node:child_process";

const inv = JSON.parse(execFileSync("git",
  ["-C", "D:/moodle/CityNexus", "cat-file", "-p", "353d1c4f96945de517cacf1ef1c8856345d812f8"],
  { encoding: "utf-8", maxBuffer: 1 << 24 }));
const rep = JSON.parse(fs.readFileSync("D:/moodle/_qoder_q_ord0422/final2/final_readings_r2.json", "utf-8"));

const PANEL_OF = { "TwinPanel.tsx": "twin", "V14RecoveryTruthPanel.tsx": "authoritative",
  "RealCityDiscoveryPanel.tsx": "discover" };
const panelOf = (file) => Object.entries(PANEL_OF).find(([n]) => file.endsWith(n))?.[1] ?? "UNKNOWN";

const src = fs.readFileSync("D:/moodle/_qoder_q_ord0422/wt/frontend/src/i18n/LocaleContext.tsx", "utf-8");
const KEY = /^ {2}"((?:twin|v14|discovery)\.[A-Za-z0-9_.]+)": "((?:[^"\\]|\\.)*)",$/gm;
const grab = (name) => {
  const i = src.indexOf(`const ${name}: Dict = {`);
  const out = new Map();
  for (const m of src.slice(i, src.indexOf("\n};", i)).matchAll(KEY))
    out.set(m[1], m[2].replace(/\\"/g, '"'));
  return out;
};
const enDict = grab("en"), zhDict = grab("zhCN");

/* en value -> zh value for the same key, so the Chinese side is checked against the dictionary's own
 * sentence rather than a sentence I typed. Keys present in one dict only are reported separately. */
const zhOf = new Map();
for (const [k, v] of enDict) if (zhDict.has(k)) zhOf.set(v, zhDict.get(k));

const leavesFor = (panel, locale) => rep.readings.filter((r) => r.route === panel && r.locale === locale)
  .flatMap((r) => r.leaves ?? []);

/* A row can be a fragment of an interpolated dictionary value ("{count} hard need(s) ..."), in which
 * case no leaf ever equals it. Only a value that actually interpolates qualifies: "CHANGED" is a
 * substring of the kicker "V14 · REALITY CHANGED" and that is not the CHANGED badge, so a plain
 * substring match would launder one false positive into another. */
const templateFor = (row) => {
  const hit = [...enDict.entries()].find(([, v]) => v !== row && v.includes(row)
    && /\{[a-z_]+\}/.test(v));
  if (!hit) return null;
  const [, value] = hit;
  const zh = zhOf.get(value);
  return { key: hit[0],
    en: new RegExp(`^${value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&").replace(/\\\{[a-z_]+\\\}/g, "[\\d.,]+")}$`),
    zh: zh ? new RegExp(`^${zh.replace(/[.*+?^${}()|[\]\\]/g, "\\$&").replace(/\\\{[a-z_]+\\\}/g, "[\\d.,]+")}$`) : null };
};

const rows = inv.rows.map((r) => {
  const panel = panelOf(r.file);
  const enLeaves = leavesFor(panel, "en"), zhLeaves = leavesFor(panel, "zh-CN");
  const tpl = templateFor(r.string);
  const zhText = zhOf.get(r.string) ?? null;
  const enExact = enLeaves.includes(r.string) || (tpl ? enLeaves.some((l) => tpl.en.test(l)) : false);
  return {
    file: r.file, panel, line: r.line, string: r.string,
    fragment_of: tpl?.key ?? null,
    zh_text: zhText ?? (tpl?.zh ? zhDict.get(tpl.key) : null),
    en_exact_leaf: enExact,
    zh_substring_leak: zhLeaves.some((l) => l.includes(r.string)),
    zh_pair_readable: zhText ? zhLeaves.includes(zhText)
      : (tpl?.zh ? zhLeaves.some((l) => tpl.zh.test(l)) : null),
    branch_gated: !!r.branch_gated,
  };
});

const read = rows.filter((r) => r.en_exact_leaf);
const leak = rows.filter((r) => r.zh_substring_leak);
const unpaid = read.filter((r) => r.zh_pair_readable !== true);
const notReached = rows.filter((r) => !r.en_exact_leaf);
const gatedMismatch = notReached.filter((r) => !r.branch_gated);

console.log("inventory rows from blob 353d1c4f...               :", rows.length);
console.log("ZH_LEAK    rows readable on a zh screen      (0)   :", leak.length);
console.log("EN_READ    rows rendered as an exact en leaf       :", read.length);
console.log("ZH_PAID    of those, zh counterpart on screen      :", read.length - unpaid.length);
console.log("NOT_REACHED                                        :", notReached.length,
  "| inventory branch_gated flags:", rows.filter((r) => r.branch_gated).length);
console.log("NOT_REACHED rows the inventory did NOT flag gated  :", gatedMismatch.length);
if (leak.length) console.log("ZH LEAK:", JSON.stringify(leak, null, 1));
if (unpaid.length) console.log("ZH UNPAID:", JSON.stringify(unpaid, null, 1));
if (gatedMismatch.length) console.log("UNEXPECTED NOT_REACHED:", JSON.stringify(gatedMismatch, null, 1));
console.log("\nNOT_REACHED rows:", JSON.stringify(notReached.map((r) => `${r.panel}:${r.line} ${r.string}`), null, 1));

const reached = read.length;
const verdict = reached === 0
  ? "ABORT_INSTRUMENT_NO_POSITIVE_READING"
  : (leak.length === 0 && unpaid.length === 0 ? "PASS" : "FAIL");

fs.writeFileSync("D:/moodle/_qoder_q_ord0422/final2/assert_r2.json", JSON.stringify({
  inventory_rows: rows.length, zh_rows_readable: leak.length, en_reachable_rows: reached,
  reached_rows_with_zh_pair_readable: reached - unpaid.length,
  not_reached_rows: notReached.length, verdict, rows,
}, null, 1));
console.log("verdict:", verdict, "-> D:/moodle/_qoder_q_ord0422/final2/assert_r2.json");
