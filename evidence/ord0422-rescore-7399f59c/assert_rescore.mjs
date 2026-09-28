/* ORD-0422 two-arm acceptance, r3 round: merges the commander's corrected instrument
 * (untranslated_scan_r3.js, blob 3dad6f0e70c2a0dcce936499f277313618d6b807) with this lane's own
 * leaf-level readings, and reports each of the 22 inventory rows under BOTH matchers.
 *
 * Why two matchers stay in the artifact instead of one being "the answer":
 *   r3 asks each row as a substring of the screen text. That is the strict negative for the Chinese
 *   arm (English hiding inside a longer sentence still counts as a leak) and it is what the
 *   commander's corrected order names as the comparison arm for English.
 *   This lane's ruler asks each row as a WHOLE rendered leaf. That is what keeps "CHANGED" -- the diff
 *   badge behind the proposal branch -- from being counted as read simply because the kicker
 *   "V14 · REALITY CHANGED" is on screen.
 * Both are printed; neither is silently preferred.
 */
import fs from "node:fs";
import { execFileSync } from "node:child_process";

const inv = JSON.parse(execFileSync("git",
  ["-C", "D:/moodle/CityNexus", "cat-file", "-p", "353d1c4f96945de517cacf1ef1c8856345d812f8"],
  { encoding: "utf-8", maxBuffer: 1 << 24 }));
const rep = JSON.parse(fs.readFileSync("D:/moodle/_qoder_q_ord0422/final6/final_readings_r6.json", "utf-8"));
const r3 = ["twin", "authoritative", "discover"].map((route) => JSON.parse(fs.readFileSync(
  `D:/moodle/_qoder_q_ord0422/r3_rescore/untranslated_${route}_r3.json`, "utf-8")));

const PANEL_OF = { "TwinPanel.tsx": "twin", "V14RecoveryTruthPanel.tsx": "authoritative",
  "RealCityDiscoveryPanel.tsx": "discover" };
const panelOf = (f) => Object.entries(PANEL_OF).find(([n]) => f.endsWith(n))?.[1] ?? "UNKNOWN";

const src = fs.readFileSync("D:/moodle/_qoder_q_ord0422/wt/frontend/src/i18n/LocaleContext.tsx", "utf-8");
const KEY = /^ {2}"([a-z][A-Za-z0-9_]*(?:\.[A-Za-z0-9_]+)+)": "((?:[^"\\]|\\.)*)",$/gm;
const grab = (name) => {
  const i = src.indexOf(`const ${name}: Dict = {`);
  const out = new Map();
  for (const m of src.slice(i, src.indexOf("\n};", i)).matchAll(KEY)) out.set(m[1], m[2].replace(/\\"/g, '"'));
  return out;
};
const enDict = grab("en"), zhDict = grab("zhCN");
const zhOf = new Map();
for (const [k, v] of enDict) if (zhDict.has(k)) zhOf.set(v, zhDict.get(k));
const tplOf = (row) => {
  const hit = [...enDict.entries()].find(([, v]) => v !== row && v.includes(row) && /\{[a-z_]+\}/.test(v));
  if (!hit) return null;
  const widen = (v) => new RegExp(`^${v.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")
    .replace(/\\\{[a-z_]+\\\}/g, "[\\d.,]+")}$`);
  return { key: hit[0], en: widen(hit[1]), zh: zhOf.get(hit[1]) ? widen(zhOf.get(hit[1])) : null };
};

const r3Route = (panel) => r3.find((x) => x.route === panel);
const leavesFor = (panel, locale) => rep.readings.filter((x) => x.route === panel && x.locale === locale)
  .flatMap((x) => x.leaves ?? []);

const rows = inv.rows.map((r) => {
  const panel = panelOf(r.file);
  const zhLeaves = leavesFor(panel, "zh-CN"), enLeaves = leavesFor(panel, "en");
  const tpl = tplOf(r.string);
  const zhText = zhOf.get(r.string) ?? (tpl?.zh ? zhDict.get(tpl.key) : null);
  const rec = r3Route(panel);
  const sub = (arm) => {
    const hit = rec?.[arm]?.expect?.find((e) => e.text === r.string);
    return hit ? hit.on_screen : "NOT_ASKED";
  };
  return {
    file: r.file.split("/").pop(), panel, line: r.line, string: r.string, zh_text: zhText,
    lane_en_exact_leaf: enLeaves.includes(r.string) || (tpl ? enLeaves.some((l) => tpl.en.test(l)) : false),
    lane_zh_exact_leaf: zhLeaves.includes(r.string),
    lane_zh_substring_leak: zhLeaves.some((l) => l.includes(r.string)),
    lane_zh_pair_readable: zhText ? zhLeaves.includes(zhText) || (tpl?.zh
      ? zhLeaves.some((l) => tpl.zh.test(l)) : false) : null,
    r3_en_substring: sub("en"), r3_zh_substring: sub("zh"),
    branch_gated: !!r.branch_gated,
  };
});

const zhLeakLane = rows.filter((r) => r.lane_zh_substring_leak);
const zhLeakR3 = rows.filter((r) => r.r3_zh_substring === true);
const enR3 = rows.filter((r) => r.r3_en_substring === true);
const enLane = rows.filter((r) => r.lane_en_exact_leaf);

/* One rule the r3 matcher needs and does not have: a row asked as a substring is "read" whenever it
 * sits inside ANY leaf, including the leaf of another inventory row -- "CHANGED" is inside
 * "V14 · REALITY CHANGED". Detected mechanically here (the hit leaf is itself another row's own
 * English string), named, and dropped from the REACHED set rather than being argued away. */
const enLeafStrings = (panel) => leavesFor(panel, "en");
const inflated = rows.filter((r) => {
  if (r.r3_en_substring !== true || r.lane_en_exact_leaf) return false;
  const others = inv.rows.filter((o) => o !== r && panelOf(o.file) === r.panel).map((o) => o.string);
  return enLeafStrings(r.panel).some((l) => l.includes(r.string) && others.some((o) => l === o));
});
for (const r of inflated) r.matcher_inflated_by = "substring hit lands on another inventory row's leaf";

const enEither = rows.filter((r) => (r.r3_en_substring === true || r.lane_en_exact_leaf)
  && !inflated.includes(r));
const unpaid = enEither.filter((r) => r.lane_zh_pair_readable !== true);
const anchors = r3.map((x) => ({ route: x.route, arms_comparable: x.arms_comparable,
  zh_entry: x.zh.entry_used, en_entry: x.en.entry_used,
  zh_path: x.zh.reached_route, en_path: x.en.reached_route }));

console.log("inventory rows                                    :", rows.length);
console.log("r3 anchor proof | every arm on its requested route:",
  anchors.every((a) => a.arms_comparable), JSON.stringify(anchors.map((a) => a.route + ":" + a.en_entry)));
console.log("ZH LEAK  lane whole-leaf / substring              :", rows.filter((r) => r.lane_zh_exact_leaf).length,
  "/", zhLeakLane.length);
console.log("ZH LEAK  r3 substring                             :", zhLeakR3.length);
console.log("EN READ  r3 substring                             :", enR3.length);
console.log("EN READ  lane whole-leaf                          :", enLane.length);
console.log("EN READ  either instrument                        :", enEither.length,
  "| of those, zh counterpart readable:", enEither.length - unpaid.length);
console.log("NOT_REACHED by both instruments                   :", rows.length - enEither.length);
console.log("r3 substring hits that are another row's leaf     :", inflated.length,
  JSON.stringify(inflated.map((x) => x.string)));
if (zhLeakLane.length || zhLeakR3.length) console.log("LEAKS:", JSON.stringify([...zhLeakLane, ...zhLeakR3], null, 1));
if (unpaid.length) console.log("ZH UNPAID:", JSON.stringify(unpaid, null, 1));

const verdict = !anchors.every((a) => a.arms_comparable)
  ? "ABORT_ARMS_NOT_COMPARABLE_ANCHOR_FAILED"
  : (zhLeakLane.length === 0 && zhLeakR3.length === 0 && unpaid.length === 0 && enEither.length > 0
      ? "PASS" : "FAIL");
fs.writeFileSync("D:/moodle/_qoder_q_ord0422/final6/assert_rescore.json", JSON.stringify({
  inventory_rows: rows.length, zh_leak_lane: zhLeakLane.length, zh_leak_r3: zhLeakR3.length,
  en_reachable_r3: enR3.length, en_reachable_lane: enLane.length, en_reachable_either: enEither.length,
  reached_with_zh_pair_readable: enEither.length - unpaid.length,
  not_reached_rows: rows.length - enEither.length,
  matcher_inflated_rows: inflated.length,
  matcher_inflated: inflated.map((x) => ({ row: x.string, panel: x.panel, why: x.matcher_inflated_by })), anchors, verdict, rows,
}, null, 1));
console.log("verdict:", verdict, "-> final6/assert_rescore.json");
