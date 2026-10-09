/* ORD-0549 · lane 电工-0470 · the simulation stage's retry button reads the dictionary cell the
 * commander's table names; the words on the glass cannot move, and the seven格 that still need a
 * new key are left standing on purpose.
 *
 * Why source-reading instead of clicking: this button only mounts while the stage holds a scene that
 * can be re-read, and the deterministic suite runs with external AI disabled, so a scripted session
 * cannot raise that state here. "屏上文案一字不改" is proven at the strongest distance available --
 * the two strings the ternary carried are compared, byte for byte, against the two cells this change
 * now reads, so either side drifting turns this arm red. No live render is claimed, and the block
 * says so.
 *
 * The pre-change literals come from BEFORE_READING.txt, written out of the line's own object
 * b461897465b07a4d5e8d99e618f59034652f81f2 rather than off this lane's working tree.
 */
import { expect, test } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";

const ROOT = path.join(process.cwd(), "..");
const read = (rel: string) => fs.readFileSync(path.join(ROOT, rel), "utf-8").replace(/\r\n/g, "\n");

const TARGET = "frontend/src/features/simulation/SimulationPanel.tsx";
const DICTIONARY = "frontend/src/i18n/LocaleContext.tsx";
const BEFORE = "review/diangong-0470-0549-r1/BEFORE_READING.txt";
const OUT_DIR = path.join(ROOT, "review", "diangong-0470-0549-r1");

const KEY = "shared.refresh";
const TERNARIES_WAS = 8;

const src = read(TARGET).split("\n");
const dict = read(DICTIONARY).split("\n");
const split = dict.findIndex((l) => l.startsWith("const zhCN"));
const numbered = (text: string[]) => text.map((l, i) => ({ l, n: i + 1 }));
const ternaries = numbered(src).filter((x) => x.l.includes("zh ?"));

const literal = (name: "zh" | "en") => {
  const m = read(BEFORE).match(new RegExp(`^${name}=(.*)$`, "m"));
  expect(m, `BEFORE_READING.txt carries no ${name}= line`).not.toBeNull();
  return m![1];
};

fs.mkdirSync(OUT_DIR, { recursive: true });
fs.writeFileSync(path.join(OUT_DIR, "AFTER_READING.txt"), "", "utf-8");
const note = (line: string) => fs.appendFileSync(path.join(OUT_DIR, "AFTER_READING.txt"), line + "\n", "utf-8");

test("ORD-0549 A1 那一行不再含 zh ?，改读点名的键，且文件只剩没键的那几枚", () => {
  const readsKey = numbered(src).filter((x) => x.l.includes(`t("${KEY}")`));
  expect(readsKey.length, `${KEY} is not read by this file at all`).toBe(1);
  expect(readsKey[0].l, `the line reading the key is not the button: ${readsKey[0].l}`).not.toContain("zh ?");
  expect(ternaries.length, `this file went from ${TERNARIES_WAS} inline ternaries to ${ternaries.length}, expected one fewer`)
    .toBe(TERNARIES_WAS - 1);
  note(`A1 line ${readsKey[0].n}: ${readsKey[0].l.trim()} | ternaries left: ${ternaries.length}`);
});

test("ORD-0549 A2 屏上文案一字不改：改前两串与字典两格逐字相同", () => {
  const hits = numbered(dict).filter((x) => x.l.includes(`"${KEY}":`));
  expect(hits.length, `${KEY} must be defined exactly once per book, saw ${hits.length}`).toBe(2);
  const value = (line: string) => {
    const m = line.match(/:\s*"(.*)"\s*,?\s*$/);
    expect(m, `${KEY} cell is not the shape this arm reads: ${line}`).not.toBeNull();
    return m![1];
  };
  const en = hits.find((x) => x.n < split)!;
  const zh = hits.find((x) => x.n > split)!;
  expect(value(zh.l), `the zh cell is not the word that was painted: ${value(zh.l)}`).toBe(literal("zh"));
  expect(value(en.l), `the en cell is not the word that was painted: ${value(en.l)}`).toBe(literal("en"));
  note(`A2 en cell line ${en.n} = ${value(en.l)} | zh cell line ${zh.n} = ${value(zh.l)}`);
});

test("ORD-0549 A3 没自造键名：本文件每一个 t() 键在两本字典里都真有", () => {
  const keys = [...read(TARGET).matchAll(/\bt\("([^"]+)"\)/g)].map((m) => m[1]);
  expect(keys.length, "this file reads no t() key at all -- re-read it").toBeGreaterThan(0);
  const missing = keys.filter((k) => dict.filter((l) => l.includes(`"${k}":`)).length !== 2);
  expect(missing, `keys this screen uses but the books do not both define: ${missing.join(", ")}`).toEqual([]);
  note(`A3 t() keys used by this file: ${new Set(keys).size}, each defined in both books`);
});

test("ORD-0549 A4 没建键也没顺手改：needs_new_key 那七枚仍站在原处", () => {
  expect(ternaries.length, "the bucket this lane must not touch moved").toBe(7);
  for (const x of ternaries) {
    expect(x.l, `a bucket ternary now reads the dictionary -- a key was invented somewhere: line ${x.n}`)
      .not.toContain("t(");
  }
  note(`A4 untouched bucket ternaries at lines ${ternaries.map((x) => x.n).join(",")}`);
});
