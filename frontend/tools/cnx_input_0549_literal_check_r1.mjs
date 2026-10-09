/* ORD-0549 · JourneyTrialSetup literal-parity ruler.

   The order's acceptance line says the rendered text must not change by a single character.
   That cannot be argued by eye, so this ruler reads, from disk:
     - the three replaced lines on the base commit (`git show`), and pulls both literals out
       of the `zh ? "…" : "…"` shape it finds there;
     - the key each line now asks the dictionary for, read from the working tree;
     - that key's two arms, read from the two dictionaries and the traveller-label table.
   It then compares bytes, arm by arm.  A control pair that is known to differ has to be
   reported unequal, otherwise a green here would only prove the ruler never fires.
*/
import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import path from "node:path";

const ROOT = path.resolve(import.meta.dirname, "..", "..");
const BASE = process.env.CNX_BASE || "3b1504e696a04b9ce4f25443e0efb03fd7e1b93e";
const TARGET = "frontend/src/features/setup/JourneyTrialSetup.tsx";

const read = (p) => readFileSync(path.join(ROOT, p), "utf8").replace(/\r\n/g, "\n");
const baseSrc = execFileSync("git", ["show", `${BASE}:${TARGET}`], { cwd: ROOT, encoding: "utf8" }).replace(/\r\n/g, "\n");
const workSrc = read(TARGET);
const dictSrc = read("frontend/src/i18n/LocaleContext.tsx");
const labelsSrc = read("frontend/src/i18n/travelerLabels.ts");

/* `zh ? "A" : "B"` — same quote kind on both arms, nothing else on the pair. */
function pairFrom(line) {
  const m = line.match(/zh\s*\?\s*"([^"]*)"\s*:\s*"([^"]*)"/);
  return m ? { zh: m[1], en: m[2] } : null;
}

function dictArms(key) {
  const hits = [];
  for (const line of dictSrc.split("\n")) {
    const m = line.match(new RegExp('^\\s*"' + key.replace(/\./g, "\\.") + '":\\s*"([^"]*)",\\s*$'));
    if (m) hits.push(m[1]);
  }
  if (hits.length !== 2) return { arms: null, count: hits.length };
  return { arms: { en: hits[0], zh: hits[1] }, count: hits.length };
}

function roleArms(token) {
  const m = labelsSrc.match(new RegExp("\\b" + token + ":\\s*\\{\\s*zh:\\s*\"([^\"]*)\",\\s*en:\\s*\"([^\"]*)\"\\s*\\}"));
  return m ? { zh: m[1], en: m[2] } : null;
}

/* Which line in the working tree now carries the replacement, and what does it ask for? */
function currentForm(needle) {
  for (const line of workSrc.split("\n")) {
    if (line.includes(needle)) return line.trim();
  }
  return null;
}

const cases = [
  {
    name: "arrival",
    baseNeedle: 'zh ? "抵达" : "Arrival"',
    workNeedle: "reviewEdit(\"arrival\")",
    kind: "role",
    token: "ARRIVAL",
  },
  {
    name: "technical-detail",
    baseNeedle: 'zh ? "技术详情" : "Technical detail"',
    workNeedle: 't("hub.continuationTechnicalDetail")',
    kind: "dict",
    key: "hub.continuationTechnicalDetail",
  },
  {
    name: "stop-waiting",
    baseNeedle: 'zh ? "停止等待" : "Stop waiting"',
    workNeedle: 't("agent.aiRunStop")',
    kind: "dict",
    key: "agent.aiRunStop",
  },
];

let red = 0;
for (const c of cases) {
  const baseLine = baseSrc.split("\n").find((l) => l.includes(c.baseNeedle));
  if (!baseLine) { console.log(`RED ${c.name}: base line not found on ${BASE.slice(0, 10)}`); red += 1; continue; }
  const before = pairFrom(baseLine);
  if (!before) { console.log(`RED ${c.name}: base line is not the named two-arm shape`); red += 1; continue; }

  const workLine = currentForm(c.workNeedle);
  if (!workLine) { console.log(`RED ${c.name}: replacement line absent in the working tree`); red += 1; continue; }
  if (/zh\s*\?/.test(workLine)) { console.log(`RED ${c.name}: the working line still carries a zh ? ternary: ${workLine}`); red += 1; continue; }

  const arms = c.kind === "dict" ? dictArms(c.key).arms : roleArms(c.token);
  if (!arms) {
    const n = c.kind === "dict" ? dictArms(c.key).count : 0;
    console.log(`RED ${c.name}: arms unreadable (dictionary hits ${n}, expected 2)`);
    red += 1;
    continue;
  }
  const zhSame = arms.zh === before.zh;
  const enSame = arms.en === before.en;
  if (zhSame && enSame) {
    console.log(`OK  ${c.name}: base zh "${before.zh}" == dict zh "${arms.zh}" and base en "${before.en}" == dict en "${arms.en}"`);
  } else {
    console.log(`RED ${c.name}: zh ${zhSame ? "same" : "DIFFERS"} / en ${enSame ? "same" : "DIFFERS"}`);
    red += 1;
  }
}

/* Control: the ruler must be able to say "not equal".  Compare one case's Chinese arm against
   a different key's Chinese arm — those two strings genuinely differ, so a ruler that reports
   equality here is not measuring anything. */
const tech = dictArms("hub.continuationTechnicalDetail").arms;
const stop = dictArms("agent.aiRunStop").arms;
if (!tech || !stop) {
  console.log("RED control: both control keys must be readable");
  red += 1;
} else if (tech.zh === stop.zh) {
  console.log(`RED control: two different keys returned the same Chinese arm "${tech.zh}" — the reader is broken`);
  red += 1;
} else {
  console.log(`OK  control: "${tech.zh}" != "${stop.zh}", so the byte comparison can and does fire`);
}

/* Control two: a leftover ternary anywhere in this file must be visible to the ruler.  The order
   only named three rows, so remaining ternaries are expected — this prints how many are left so
   nobody reads "green" as "the file is clean". */
const left = workSrc.split("\n").filter((l) => /zh\s*\?\s*"/.test(l)).length;
console.log(`NOTE remaining inline ternaries in this file: ${left} (not this cell's scope)`);

console.log(red === 0 ? "PROVEN rendered text cannot change for the three named keys" : `ABORT ${red} case(s) red`);
process.exit(red === 0 ? 0 : 1);
