/* Reachability domain · lane 8ac89982 (修复地图停靠点显名) · the status banner's dismiss button must
 * clear the 44px phone touch contract.
 *
 * Why: `.v8-message button` (`shell.dismiss`, "知道了") is a bare text-sized <button> with padding:0.
 * The phone 44px floor at frontend/src/styles.css:279 enumerated `.v8-quiet-button`, `.v8-primary`,
 * `summary`, `.v8-close-button` … but never `.v8-message button`, so on a phone the only visible way to
 * clear a status message measured ~14px tall — a tap target below the contract. This is a CSS-contract
 * ruler: it reads stylesheets + tokens, decides whether the floor reaches that control, and decides it
 * from the tip's own bytes too (leg 2), so a green run proves the fix is load-bearing, not decorative.
 *
 * This is NOT an on-glass pixel measurement. It asserts the applied CSS contract; the rendered-box read
 * (mirroring qoder-every-summary-is-tappable.spec.ts) is the declared next cell and needs the dev stack.
 */
import { execSync } from "node:child_process";
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { expect, test } from "@playwright/test";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = join(HERE, "..", "..");
const CSS_PATH = "frontend/src/styles.css";
const TOKENS_PATH = "frontend/src/design-tokens.css";
const CSS_ABS = join(ROOT, "frontend", "src", "styles.css");
const TOKENS_ABS = join(ROOT, "frontend", "src", "design-tokens.css");
const BASE = "f5ecd9d854000e7eaa6ca07c55bd0436d4f80c68"; // immutable parent of this candidate
const EVIDENCE = process.env.CITYNEXUS_TOUCHFLOOR_EVIDENCE ?? "";
const RUN = process.env.CITYNEXUS_TOUCHFLOOR_RUN ?? "touchfloor-unset";

function readTip(rel: string): string {
  return execSync(`git -C ${JSON.stringify(ROOT)} show ${BASE}:${rel}`, {
    encoding: "utf8",
    maxBuffer: 64 * 1024 * 1024,
  });
}

/** Balanced-brace capture of every `@media (max-width: 680px) { … }` body in the sheet. */
function mobileFloorBlocks(css: string): string[] {
  const out: string[] = [];
  const re = /@media\s*\(\s*max-width:\s*680px\s*\)\s*\{/g;
  let m: RegExpExecArray | null;
  while ((m = re.exec(css))) {
    let i = m.index + m[0].length;
    let depth = 1;
    const start = i;
    while (i < css.length && depth > 0) {
      const c = css[i];
      if (c === "{") depth += 1;
      else if (c === "}") depth -= 1;
      i += 1;
    }
    out.push(css.slice(start, i - 1));
  }
  return out;
}

/** The stylesheet with every `@media … { … }` block removed, so only top-level rules remain. */
function topLevelOnly(css: string): string {
  let i = 0;
  let out = "";
  while (i < css.length) {
    const at = css.indexOf("@media", i);
    if (at === -1) {
      out += css.slice(i);
      break;
    }
    out += css.slice(i, at);
    let j = at;
    while (j < css.length && css[j] !== "{") j += 1; // to the opening brace of the media block
    let depth = 0;
    while (j < css.length) {
      const c = css[j];
      if (c === "{") depth += 1;
      else if (c === "}") {
        depth -= 1;
        if (depth === 0) {
          j += 1;
          break;
        }
      }
      j += 1;
    }
    i = j;
  }
  return out;
}

/** Does any mobile block apply `min-height: var(--cn-touch-min)` to a rule that selects `.v8-message button`? */
function messageButtonFlooredOnPhone(css: string): boolean {
  return mobileFloorBlocks(css).some((block) =>
    /(^|[,;{}\s])\.v8-message\s+button\b[^{}]*\{[^}]*min-height:\s*var\(--cn-touch-min\)/.test(block),
  );
}

/** The base (media-independent) `.v8-message button { … }` declaration — the part desktop sees. */
function baseMessageButtonRule(css: string): string {
  const top = topLevelOnly(css);
  const m = /\.v8-message\s+button\s*\{([^}]*)\}/.exec(top);
  return m ? m[1] : "";
}

test("candidate bytes: the phone floor reaches the dismiss button and desktop stays compact", () => {
  const css = readFileSync(CSS_ABS, "utf8");
  expect(
    messageButtonFlooredOnPhone(css),
    "the `@media (max-width: 680px)` block must give `.v8-message button` a `min-height: var(--cn-touch-min)` — the hole the banner dismiss fell into"
  ).toBe(true);
  // Desktop must NOT inherit the floor: the base rule (outside any media query) has no min-height.
  const base = baseMessageButtonRule(css);
  expect(base.length, "the base `.v8-message button` rule vanished — desktop compactness cannot be proven").toBeGreaterThan(0);
  expect(
    /min-height/.test(base),
    "the base `.v8-message button` rule carries a min-height, which leaks the 44px phone floor onto desktop (Amendment F-2 keeps desktop compact)"
  ).toBe(false);
});

test("counter arm: on the tip's own bytes the same ruler finds the hole (floor absent, button un-floored)", () => {
  const tipCss = readTip(CSS_PATH);
  expect(
    messageButtonFlooredOnPhone(tipCss),
    "the tip already floors `.v8-message button` — if this is true the fix would be a no-op and this ruler is decorative"
  ).toBe(false);
  // And confirm the control really exists on the tip with no min-height anywhere near it: it is the defect.
  const base = baseMessageButtonRule(tipCss);
  expect(base.length, "the `.v8-message button` base rule is not on the tip — premise wrong").toBeGreaterThan(0);
  expect(/min-height/.test(base), "the tip's base rule already floors the dismiss button").toBe(false);
});

test("the contract value is really 44px, not a redefined token", () => {
  const tokens = readFileSync(TOKENS_ABS, "utf8");
  const m = /--cn-touch-min:\s*(\d+)px/.exec(tokens);
  expect(m, "--cn-touch-min is not declared in design-tokens.css").toBeTruthy();
  expect(Number(m![1]), "--cn-touch-min is no longer 44").toBe(44);
});

test("evidence carries both readings (candidate and tip)", () => {
  if (EVIDENCE) {
    mkdirSync(dirname(EVIDENCE), { recursive: true });
    const wt = messageButtonFlooredOnPhone(readFileSync(CSS_ABS, "utf8"));
    const tp = messageButtonFlooredOnPhone(readTip(CSS_PATH));
    writeFileSync(EVIDENCE, JSON.stringify({
      generatedBy: "8ac89982",
      ruler: "message-dismiss-touch-floor-r1",
      run: RUN,
      base_pin: BASE,
      candidate_floored_on_phone: wt,
      tip_floored_on_phone: tp,
      desktop_base_has_min_height: /min-height/.test(baseMessageButtonRule(readFileSync(CSS_ABS, "utf8"))),
      cn_touch_min_px: Number((/--cn-touch-min:\s*(\d+)px/.exec(readFileSync(TOKENS_ABS, "utf8")) ?? [])[1]),
    }, null, 1), "utf8");
  }
  expect(readFileSync(CSS_ABS, "utf8").includes(".v8-message button { min-height"), "the floor edit did not land").toBe(true);
});
