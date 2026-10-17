/* Reachability domain · lane 8ac89982 (修复地图停靠点显名) · desktop sidebar must paint the union.
 *
 * Why: on `mirror/integration-frontend-apple-pass1` at f614e68c1b2736bca36a42dafb85cc128348447d the
 * desktop sidebar iterates `desktopRoutes` while the phone drawer iterates `drawerRoutes` (the union
 * of desktopRoutes + mobile-only routes). Two screens -- `trips` and `me` -- are in the phone shape
 * but not in the desktop shape, so at desktop width nothing in the UI points at them; only a typed
 * address reaches them. This ruler reads the two source files and decides whether the desktop
 * sidebar's entry set equals the drawer's. It is a source-level gate: no backend, no dev server.
 *
 * The counter arm is leg 3: the same ruler, run against the tip's own bytes (git show, not the
 * working tree), must name `me` and `trips` as the entries the desktop shape is missing. If it
 * does not, the ruler is decorative and this whole spec fails on its own premise.
 */
import { execSync } from "node:child_process";
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { expect, test } from "@playwright/test";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = join(HERE, "..", "..");
const SRC_PATH = "frontend/src/app/V8Experience.tsx";
const ROUTES_PATH = "frontend/src/routes/v8Routes.ts";
const SRC_ABS = join(ROOT, SRC_PATH);
const ROUTES_ABS = join(ROOT, ROUTES_PATH);
const TIP = "f614e68c1b2736bca36a42dafb85cc128348447d";
const EVIDENCE = process.env.CITYNEXUS_SIDEBAR_EVIDENCE ?? "";
const RUN = process.env.CITYNEXUS_SIDEBAR_RUN ?? "sidebar-unset";

function readWorking(p: string): string {
  return readFileSync(p, "utf8");
}

function readTip(relPath: string): string {
  return execSync(`git -C ${JSON.stringify(ROOT)} show ${TIP}:${relPath}`, {
    encoding: "utf8",
    maxBuffer: 64 * 1024 * 1024,
  });
}

/** Parse a `export const <name> = [ ... ];` block and pull every `key: "..."` in order. */
function routeKeysFrom(source: string, name: string): string[] {
  const m = new RegExp(`export const ${name} = \\[([\\s\\S]*?)\\n\\](?: as const)?;`).exec(source);
  if (!m) throw new Error(`no \`export const ${name} = [\` block found in v8Routes.ts`);
  return [...m[1].matchAll(/\bkey:\s*"([^"]+)"/g)].map((x) => x[1]);
}

/** Which array does the desktop sidebar (the `<nav className="v8-nav">` block) iterate? */
function sidebarIterates(source: string): "drawerRoutes" | "desktopRoutes" | "unknown" {
  const m = /<nav className="v8-nav"[^>]*>([\s\S]*?)<\/nav>/.exec(source);
  if (!m) throw new Error("no `<nav className=\"v8-nav\">` sidebar block in V8Experience.tsx");
  const body = m[1];
  if (/\bdrawerRoutes\.map\b/.test(body)) return "drawerRoutes";
  if (/\bdesktopRoutes\.map\b/.test(body)) return "desktopRoutes";
  return "unknown";
}

/** The union the drawer already paints: desktopRoutes keys plus any mobileRoutes key not in desktopRoutes. */
function unionKeys(desktop: string[], mobile: string[]): string[] {
  const set = new Set(desktop);
  return [...desktop, ...mobile.filter((k) => !set.has(k))];
}

/** The declared drawerRoutes construction (a two-spread list) -- this is the shape the sidebar must copy. */
function drawerRoutesSpreadBody(source: string): string {
  const m = /\bconst drawerRoutes = \[([\s\S]*?)\];/.exec(source);
  if (!m) throw new Error("drawerRoutes definition not found in V8Experience.tsx");
  return m[1];
}

function verdictOn(source: string, routesSrc: string) {
  const desktop = routeKeysFrom(routesSrc, "desktopRoutes");
  const mobile = routeKeysFrom(routesSrc, "mobileRoutes");
  const union = unionKeys(desktop, mobile);
  const iterated = sidebarIterates(source);
  const drawn = iterated === "drawerRoutes" ? union : iterated === "desktopRoutes" ? desktop : [];
  const missing = union.filter((k) => !drawn.includes(k));
  return { desktop, mobile, union, iterated, drawn, missing };
}

test("candidate working-tree bytes: desktop sidebar paints the union so trips and me answer", () => {
  const src = readWorking(SRC_ABS);
  const routes = readWorking(ROUTES_ABS);
  const v = verdictOn(src, routes);
  expect(
    v.iterated,
    "the desktop sidebar must iterate `drawerRoutes` (the union) so both shapes share the entry set"
  ).toBe("drawerRoutes");
  expect(
    v.missing,
    `desktop sidebar is missing entries for: ${v.missing.join(", ") || "(none)"} -- it paints ${v.drawn.length} of the ${v.union.length} declared screens`
  ).toEqual([]);
  expect(v.union.includes("trips"), "trips not in the union -- the fix's premise is wrong").toBe(true);
  expect(v.union.includes("me"), "me not in the union -- the fix's premise is wrong").toBe(true);
});

test("drawerRoutes really is a spread of desktopRoutes then mobile-only extras (so the change is load-bearing)", () => {
  const src = readWorking(SRC_ABS);
  const routes = readWorking(ROUTES_ABS);
  const desktop = routeKeysFrom(routes, "desktopRoutes");
  const mobile = routeKeysFrom(routes, "mobileRoutes");
  expect(desktop.includes("trips"), "trips already in desktopRoutes, so the fix would be a no-op").toBe(false);
  expect(desktop.includes("me"), "me already in desktopRoutes, so the fix would be a no-op").toBe(false);
  expect(mobile.includes("trips") && mobile.includes("me"), "trips/me not in mobileRoutes").toBe(true);
  const body = drawerRoutesSpreadBody(src);
  expect(body, "drawerRoutes must spread desktopRoutes first").toMatch(/\.\.\.desktopRoutes\b/);
  expect(body, "drawerRoutes must spread mobileRoutes through a filter").toMatch(/\.\.\.\s*mobileRoutes\s*\.\s*filter\s*\(/);
  expect(body, "the filter must drop mobile keys already present in desktopRoutes").toMatch(/!desktopRoutes\s*\.\s*some\s*\(/);
  expect(body, "the de-dup compares on the route key").toMatch(/entry\s*\.\s*key\s*===\s*item\s*\.\s*key/);
});

test("counter arm: the same ruler, run against the tip's own bytes, names trips and me as the missing entries", () => {
  /* Read what is on the authoritative line, NOT the working tree. This leg proves the ruler is
     not decorative: on the tip's `desktopRoutes.map` sidebar it must call out exactly the two
     screens the desktop shape is missing, with the same message shape leg 1 would have produced. */
  const tipSrc = readTip(SRC_PATH);
  const tipRoutes = readTip(ROUTES_PATH);
  const v = verdictOn(tipSrc, tipRoutes);
  expect(
    v.iterated,
    "the tip iterates `desktopRoutes` on the sidebar -- if this flips, the ruler below is stale"
  ).toBe("desktopRoutes");
  expect(
    v.missing.slice().sort(),
    "the tip's sidebar is missing these entries: the ruler names them so a green run of this spec really means the gap is closed"
  ).toEqual(["me", "trips"]);
  expect(v.drawn.length, "the tip paints the wrong number of rows").toBeLessThan(v.union.length);
});

test("evidence file carries the two readings (working tree and tip)", () => {
  if (EVIDENCE) {
    mkdirSync(dirname(EVIDENCE), { recursive: true });
    const wt = verdictOn(readWorking(SRC_ABS), readWorking(ROUTES_ABS));
    const tp = verdictOn(readTip(SRC_PATH), readTip(ROUTES_PATH));
    writeFileSync(EVIDENCE, JSON.stringify({
      generatedBy: "8ac89982",
      ruler: "desktop-sidebar-union-r1",
      run: RUN,
      tip: TIP,
      working_tree: { iterated: wt.iterated, drawn_size: wt.drawn.length, union_size: wt.union.length, missing: wt.missing },
      tip_bytes:    { iterated: tp.iterated, drawn_size: tp.drawn.length, union_size: tp.union.length, missing: tp.missing },
      desktop_keys: wt.desktop,
      mobile_keys:  wt.mobile,
      union_keys:   wt.union,
    }, null, 1), "utf8");
  }
  expect(readFileSync(SRC_ABS, "utf8").includes("drawerRoutes.map"), "the sidebar edit did not land").toBe(true);
});
