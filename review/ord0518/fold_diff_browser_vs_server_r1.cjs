// ORD-0518 -- the other half of the fold measurement.
//
// Reads `fold_casefold_server_r1.json` (Python's `casefold` for every code point where it changes the
// character, produced by the server's own interpreter) and asks V8 the same question with
// `String.prototype.toLowerCase`.  The output is the deny-list `journeyOrderVerdict.ts` ships: code
// points where the two answers are not the same string, so the screen cannot re-check the door's
// `TITLE` order over a title that carries one.
//
//   node review/ord0518/fold_diff_browser_vs_server_r1.cjs
//
// Prints the count, the code points as compact ranges, and a check on the characters this tree's own
// fixtures use, so the guard is known to pass the rows the gate seeds.
const fs = require("fs");
const path = require("path");

const HERE = __dirname;
const CASEFOLD = JSON.parse(fs.readFileSync(path.join(HERE, "fold_casefold_server_r1.json"), "utf8"));

const SURROGATE_FIRST = 0xd800;
const SURROGATE_LAST = 0xdfff;
const MAX = 0x10ffff;

const divergent = [];
let checked = 0;
for (let cp = 0; cp <= MAX; cp += 1) {
  if (cp >= SURROGATE_FIRST && cp <= SURROGATE_LAST) continue;
  checked += 1;
  const character = String.fromCodePoint(cp);
  const js = character.toLowerCase();
  const python = Object.prototype.hasOwnProperty.call(CASEFOLD, String(cp)) ? CASEFOLD[String(cp)] : character;
  if (js !== python) divergent.push(cp);
}

function ranges(list) {
  const out = [];
  let start = null;
  let previous = null;
  for (const cp of list) {
    if (start === null) {
      start = cp;
      previous = cp;
      continue;
    }
    if (cp === previous + 1) {
      previous = cp;
      continue;
    }
    out.push(start === previous ? [start, start] : [start, previous]);
    start = cp;
    previous = cp;
  }
  if (start !== null) out.push(start === previous ? [start, start] : [start, previous]);
  return out;
}

const groups = ranges(divergent);

// The characters this tree's fixtures actually put in a title, checked one by one, so the guard is
// known to leave them verifiable rather than hoped to.
const SAMPLES = [
  "Tianjin \u00b7 stay-aware weekend",
  "O518-zh \u5317\u4eac delta Alpha charlie",
  "a\u0307 A\u0391 \u00df \u03a3 \u03c2 \ufb01 \u0149 \u0345 \u1e9e \u0587 \uff21 \u3000201020",
];

const lines = [];
lines.push("checked_code_points " + checked);
lines.push("divergent_code_points " + divergent.length);
lines.push("divergent_ranges " + groups.length);
lines.push("ranges " + JSON.stringify(groups));
for (const sample of SAMPLES) {
  let blocked = [];
  for (const character of sample) {
    const cp = character.codePointAt(0);
    const js = character.toLowerCase();
    const python = Object.prototype.hasOwnProperty.call(CASEFOLD, String(cp))
      ? CASEFOLD[String(cp)]
      : character;
    if (js !== python) blocked.push("U+" + cp.toString(16).toUpperCase().padStart(4, "0"));
  }
  lines.push("sample " + JSON.stringify(sample) + " blocked_by " + JSON.stringify([...new Set(blocked)]));
}
const text = lines.join("\n") + "\n";
fs.writeFileSync(path.join(HERE, "fold_diff_browser_vs_server_r1.txt"), text, "utf8");
process.stdout.write(text);
