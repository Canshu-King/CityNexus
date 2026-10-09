/* ORD-0549 · lane 电工-0470 · one inline ternary in the recovery panel's fold title starts reading
 * the dictionary cell the commander's table names, and the words on the glass cannot move.
 *
 * Why this file reads source instead of clicking: the cell lives inside a `<details>` that opens only
 * when the panel holds failure facts, and the deterministic suite runs with external AI disabled, so no
 * scripted session paints it on demand here. "屏上文案一字不改" is proven at the strongest distance
 * available: the two strings the ternary carried are compared, byte for byte, against the two dictionary
 * cells this change now reads -- if either side drifts, this arm goes red. A live render is NOT part of
 * this delivery and the block says so.
 *
 * The pre-change literals come from BEFORE_READING.txt, which was written out of the tip object
 * da846e54e73b839c9882dc45a18ed73c93c26bc5 rather than off this lane's working tree.
 */
import { expect, test } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";

const ROOT = path.join(process.cwd(), "..");
const read = (rel: string) => fs.readFileSync(path.join(ROOT, rel), "utf-8").replace(/\r\n/g, "\n");

const TARGET = "frontend/src/features/recovery/V14RecoveryTruthPanel.tsx";
const DICTIONARY = "frontend/src/i18n/LocaleContext.tsx";
const BEFORE = "review/diangong-0470-0549-r1/BEFORE_READING.txt";
const OUT_DIR = path.join(ROOT, "review", "diangong-0470-0549-r1");

const KEY = "hub.continuationTechnicalDetail";

const src = read(TARGET).split("\n");
const dict = read(DICTIONARY).split("\n");
const split = dict.findIndex((l) => l.startsWith("const zhCN"));

const cellLines = (key: string) => {
  const hits = dict.map((l, i) => ({ l, n: i + 1 })).filter((x) => x.l.includes(`"${key}":`));
  expect(hits.length, `${key} must be defined exactly once per book, saw ${hits.length}`).toBe(2);
  const value = (line: string) => {
    const m = line.match(/:\s*"(.*)"\s*,?\s*$/);
    expect(m, `${key} cell is not the shape this arm reads: ${line}`).not.toBeNull();
    return m![1];
  };
  return {
    en: value(hits[0].l), zh: value(hits[1].l),
    enLine: hits[0].n, zhLine: hits[1].n,
    enBook: hits[0].n < split, zhBook: hits[1].n > split,
  };
};

const literal = (name: "zh" | "en") => {
  const m = read(BEFORE).match(new RegExp(`^${name}=(.*)$`, "m"));
  expect(m, `BEFORE_READING.txt carries no ${name}= line`).not.toBeNull();
  return m![1];
};

fs.mkdirSync(OUT_DIR, { recursive: true });
fs.writeFileSync(path.join(OUT_DIR, "AFTER_READING.txt"), "", "utf-8");
const note = (line: string) => fs.appendFileSync(path.join(OUT_DIR, "AFTER_READING.txt"), line + "\n", "utf-8");

test("ORD-0549 A1 那一行不再含 zh ?，改读点名的键，且本文件这一形制归零", () => {
  const stillTernary = src.map((l, i) => ({ l, n: i + 1 })).filter((x) => x.l.includes("zh ?"));
  expect(stillTernary.length, `this file still carries ${stillTernary.length} inline ternaries at lines `
    + stillTernary.map((x) => x.n).join(",")).toBe(0);
  const readsKey = src.map((l, i) => ({ l, n: i + 1 })).filter((x) => x.l.includes(`t("${KEY}")`));
  expect(readsKey.length, `${KEY} is not read by this file at all`).toBe(1);
  expect(readsKey[0].l, `the line that reads the key is not the summary: ${readsKey[0].l}`).not.toContain("zh ?");
  note(`A1 ${TARGET.split("/").pop()} line ${readsKey[0].n}: ${readsKey[0].l.trim()} | ternaries left in file: 0`);
});

test("ORD-0549 A2 屏上文案一字不改：改前两串与字典两格逐字相同", () => {
  const cell = cellLines(KEY);
  expect(cell.enBook && cell.zhBook, "the two cells are not one per book as this arm reads them").toBe(true);
  expect(cell.zh, `the zh cell is not the word that was painted: ${cell.zh}`).toBe(literal("zh"));
  expect(cell.en, `the en cell is not the word that was painted: ${cell.en}`).toBe(literal("en"));
  note(`A2 zh cell line ${cell.zhLine} = ${cell.zh} | en cell line ${cell.enLine} = ${cell.en}`);
});

test("ORD-0549 A3 没自造键名：本文件每一个 t() 键在两本字典里都真有", () => {
  const keys = [...read(TARGET).matchAll(/\bt\("([^"]+)"\)/g)].map((m) => m[1]);
  expect(keys.length, "this file reads no t() key at all -- re-read it").toBeGreaterThan(0);
  const missing = keys.filter((k) => dict.filter((l) => l.includes(`"${k}":`)).length !== 2);
  expect(missing, `keys this screen uses but the books do not both define: ${missing.join(", ")}`).toEqual([]);
  note(`A3 t() keys used by this file: ${new Set(keys).size}, each defined in both books`);
});
