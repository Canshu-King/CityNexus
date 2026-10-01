// ORD-0518 -- does the deny-list `journeyOrderVerdict.ts` ships equal the deny-list that was measured?
//
// A 49-range table typed by hand is a claim about a measurement. This re-reads both sides and compares
// them as sets of code points, so a transposed digit cannot survive into the product.
//
//   node review/ord0518/fold_table_check_r1.cjs
const fs = require("fs");
const path = require("path");

const TREE = path.resolve(__dirname, "..", "..");
const SOURCE = fs.readFileSync(
  path.join(TREE, "frontend", "src", "features", "access", "journeyOrderVerdict.ts"),
  "utf8"
);
const MEASURED = fs.readFileSync(path.join(__dirname, "fold_diff_browser_vs_server_r1.txt"), "utf8");

// The declaration, not the first mention: the module's header comment names the table too, and the
// first `];` after that closes an unrelated constant.
const declared = SOURCE.slice(
  SOURCE.indexOf("export const FOLD_DIVERGENT_RANGES"),
  SOURCE.indexOf("];", SOURCE.indexOf("export const FOLD_DIVERGENT_RANGES"))
);
const shipped = [...declared.matchAll(/\[0x([0-9a-f]{4,6}),\s*0x([0-9a-f]{4,6})\]/g)].map((m) => [
  parseInt(m[1], 16),
  parseInt(m[2], 16),
]);

const measured = JSON.parse(MEASURED.match(/ranges (\[\[.*?\]\])/)[1]);

const expand = (groups) => {
  const set = new Set();
  for (const [first, last] of groups) {
    for (let cp = first; cp <= last; cp += 1) set.add(cp);
  }
  return set;
};

const shippedSet = expand(shipped);
const measuredSet = expand(measured);
const onlyShipped = [...shippedSet].filter((cp) => !measuredSet.has(cp));
const onlyMeasured = [...measuredSet].filter((cp) => !shippedSet.has(cp));

const lines = [
  "shipped_ranges " + shipped.length,
  "measured_ranges " + measured.length,
  "shipped_code_points " + shippedSet.size,
  "measured_code_points " + measuredSet.size,
  "only_in_shipped " + JSON.stringify(onlyShipped),
  "only_in_measured " + JSON.stringify(onlyMeasured),
  "verdict " + (onlyShipped.length === 0 && onlyMeasured.length === 0 && shipped.length === measured.length ? "MATCH" : "DIFFERS"),
];
const text = lines.join("\n") + "\n";
fs.writeFileSync(path.join(TREE, "run", "fold_table_check_r1.txt"), text, "utf8");
process.stdout.write(text);
process.exitCode = text.includes("verdict MATCH") ? 0 : 1;
