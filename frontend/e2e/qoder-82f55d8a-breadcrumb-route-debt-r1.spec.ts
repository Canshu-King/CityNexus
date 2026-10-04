import { test, expect } from "@playwright/test";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

/* ORD-0567 second batch, resident ruler (source-only, starts nothing, opens no port).
 *
 * The shell paints the top-bar name as  t("nav." + (route in {…whitelist…} ? route : "hub")).  Any screen
 * outside that object literal therefore shows the hub's own name -- "Today" / 「今天」 -- while its card header
 * says something else. Four screens were read doing exactly that, in both arms, on the shipped generation.
 *
 * This ruler does not pretend the debt is paid. It names the four rows, demands that every row stay true,
 * and refuses any *new* screen that lands outside the whitelist without being judged into one of the two
 * tables. Fix one of the four and this goes red until its row is deleted, which is the point.
 */

const HERE = dirname(fileURLToPath(import.meta.url));
const FRONTEND = resolve(HERE, "..");
const read = (rel: string) => readFileSync(resolve(FRONTEND, rel), "utf8");

const ROUTES_FILE = "src/routes/v8Routes.ts";
const SHELL_FILE = "src/app/V8Experience.tsx";
const LOCALE_FILE = "src/i18n/LocaleContext.tsx";

/** Screens whose row must be judged: the two drawer tables the shell mounts. `tokenRoutes` is a URL that
 *  must not be drawn in the chrome at all, so it is excluded by name and checked in its own arm. */
const MOUNTED_TABLES = ["desktopRoutes", "mobileRoutes"] as const;

/** Read `export const <table> = [ … ] ` and return its `key:` values, in file order, deduped. */
function tableKeys(src: string, table: string): string[] {
  const start = src.indexOf(`export const ${table}`);
  expect(start, `${table} is missing from ${ROUTES_FILE} -- the ruler would pass on an empty denominator`).toBeGreaterThanOrEqual(0);
  const open = src.indexOf("[", start);
  expect(open, `${table} has no array literal`).toBeGreaterThan(start);
  let depth = 0;
  let end = -1;
  for (let i = open; i < src.length; i += 1) {
    if (src[i] === "[") depth += 1;
    else if (src[i] === "]") {
      depth -= 1;
      if (depth === 0) { end = i; break; }
    }
  }
  expect(end, `${table}'s array literal never closes`).toBeGreaterThan(open);
  const body = src.slice(open, end);
  const keys: string[] = [];
  for (const m of body.matchAll(/\bkey:\s*"([A-Za-z0-9_]+)"/g)) {
    if (!keys.includes(m[1])) keys.push(m[1]);
  }
  return keys;
}

/** Pull the object literal out of `route in { … }` in the shell, by shape rather than by line number. */
function whitelistRoutes(src: string): string[] {
  const at = src.search(/\broute\s+in\s*\{/);
  expect(at, "the shell no longer picks its top-bar name out of a `route in { … }` literal").toBeGreaterThanOrEqual(0);
  const open = src.indexOf("{", at);
  let depth = 0;
  let end = -1;
  for (let i = open; i < src.length; i += 1) {
    if (src[i] === "{") depth += 1;
    else if (src[i] === "}") {
      depth -= 1;
      if (depth === 0) { end = i; break; }
    }
  }
  expect(end, "the whitelist literal never closes").toBeGreaterThan(open);
  const keys: string[] = [];
  for (const m of src.slice(open, end).matchAll(/^\s*([A-Za-z0-9_]+):\s*1,?\s*$/gm)) keys.push(m[1]);
  expect(keys.length, "the whitelist literal parsed to zero rows").toBeGreaterThan(0);
  return keys;
}

/** The fallback the shell uses for anything outside the whitelist. */
function fallbackKey(src: string): string {
  const m = /\?\s*route\s*:\s*"([A-Za-z0-9_]+)"/.exec(src);
  expect(m, "the shell's breadcrumb fallback literal is unreadable").not.toBeNull();
  return m![1];
}

function dictionaryBlock(src: string, name: string): string {
  const start = src.search(new RegExp(`^const ${name}\\b`, "m"));
  expect(start, `dictionary ${name} is missing from ${LOCALE_FILE}`).toBeGreaterThanOrEqual(0);
  const next = src.slice(start + 1).search(/^const [A-Za-z0-9_]+\b/m);
  return next < 0 ? src.slice(start) : src.slice(start, start + 1 + next);
}

function navName(block: string, route: string): string | null {
  const m = new RegExp(`^\\s*"nav\\.${route}":\\s*"((?:[^"\\\\]|\\\\.)*)"`, "m").exec(block);
  return m ? m[1] : null;
}

/**
 * Named debt. `wrong_name` = the screen mounts the shell chrome, so a top-bar name is painted, and what it
 * paints is the fallback screen's name while `nav.<route>` already exists in both arms. Deleting a row here
 * without adding the route to the whitelist is what this file is built to catch.
 */
const DEBT: Array<{ route: string; kind: "wrong_name"; reads: string; zh: string }> = [
  { route: "import", kind: "wrong_name", reads: "Import places", zh: "导入地点" },
  { route: "footprints", kind: "wrong_name", reads: "Footprints", zh: "足迹" },
  { route: "trash", kind: "wrong_name", reads: "Recycle bin", zh: "回收站" },
  { route: "access", kind: "wrong_name", reads: "Members and access", zh: "成员与权限" },
];

const routesSrc = read(ROUTES_FILE);
const shellSrc = read(SHELL_FILE);
const localeSrc = read(LOCALE_FILE);
const mounted = [...new Set(MOUNTED_TABLES.flatMap((t) => tableKeys(routesSrc, t)))];
const whitelisted = whitelistRoutes(shellSrc);
const fallback = fallbackKey(shellSrc);
const enBlock = dictionaryBlock(localeSrc, "en");
const zhBlock = dictionaryBlock(localeSrc, "zhCN");

test("arm 1 -- both sides parsed to a real denominator", () => {
  expect(mounted.length).toBeGreaterThanOrEqual(13);
  expect(whitelisted.length).toBeGreaterThanOrEqual(13);
  expect(mounted.filter((r) => !whitelisted.includes(r)).length).toBe(DEBT.length);
});

test("arm 2 -- no mounted screen may sit outside the whitelist unless it is judged here", () => {
  const outside = mounted.filter((r) => !whitelisted.includes(r)).sort();
  expect(outside).toEqual(DEBT.map((d) => d.route).sort());
});

test("arm 3 -- every debt row is still true, so paying one off must delete it", () => {
  for (const d of DEBT) {
    expect(whitelisted, `${d.route} is now whitelisted: delete its debt row`).not.toContain(d.route);
    expect(mounted, `${d.route} is no longer a mounted screen: delete its debt row`).toContain(d.route);
  }
});

test("arm 4 -- every debt row already has a name in both arms, so the fix is a whitelist row not new copy", () => {
  for (const d of DEBT) {
    expect(navName(enBlock, d.route), `${d.route} lost its English name`).toBe(d.reads);
    expect(navName(zhBlock, d.route), `${d.route} lost its Chinese name`).toBe(d.zh);
  }
});

test("arm 5 -- the whitelist carries no ghost row", () => {
  const ghosts = whitelisted.filter((r) => !mounted.includes(r));
  expect(ghosts, `routes whitelisted but not mounted: ${ghosts.join(" ")}`).toEqual([]);
});

test("arm 6 -- the fallback is the hub, which is why the debt reads as the hub's own name", () => {
  expect(fallback).toBe("hub");
  expect(navName(enBlock, fallback)).toBe("Today");
  expect(navName(zhBlock, fallback)).toBe("今天");
});

test("arm 7 -- tokenRoutes are not mounted screens and the shell really short-circuits them", () => {
  const tokens = tableKeys(routesSrc, "tokenRoutes");
  expect(tokens.length).toBeGreaterThanOrEqual(1);
  for (const t of tokens) {
    expect(mounted, `${t} is in both tables -- the debt list would be lying`).not.toContain(t);
    expect(
      new RegExp(`route\\s*===\\s*"${t}"`).test(shellSrc),
      `${t} is not short-circuited by the shell, so it does paint a top-bar name`
    ).toBe(true);
  }
});
