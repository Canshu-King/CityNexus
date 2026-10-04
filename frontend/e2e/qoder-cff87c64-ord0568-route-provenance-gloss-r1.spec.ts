/* ORD-0568 standing ruler (lane cff87c64) — the evidence source keeps its code and gains its words.
 *
 * The ruling (commander, 13:5x): `mock-mobility` is a provider key and stays as written, because the
 * backend logs and the contract name it; `RUNTIME_CAPTURE` is an evidence-source enum, and the traveller
 * has to be told what it means. So the cell reads `mock-mobility · RUNTIME_CAPTURE（运行时取证）`.
 *
 * The set of names is not invented here: it is read out of the expression the server uses to write the
 * field, so a fifth branch appearing in `main.py` without a wording fails this ruler rather than silently
 * reaching a screen as a gap sentence.
 *
 * Reads two source files; no backend, no front, no store. Not the acceptance gate.
 */
import { expect, test } from "@playwright/test";
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..", "..");
const FILES = {
  routes: join(ROOT, "backend", "app", "main.py"),
  vocabulary: join(ROOT, "frontend", "src", "lib", "displayVocabulary.ts"),
  panel: join(ROOT, "frontend", "src", "features", "recovery", "V14RecoveryTruthPanel.tsx"),
};
const EVIDENCE = process.env.CITYNEXUS_PROV_EVIDENCE ?? "";
const RUN = process.env.CITYNEXUS_PROV_RUN ?? "prov-unset";

const ENUM_NAME = String.raw`[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)*`;

function read(name: keyof typeof FILES): string {
  return readFileSync(FILES[name], "utf8");
}

/** Every value the recovery route can write into `route_provenance`: the named local's own assignment
 *  expression, bounded so a literal elsewhere in the file cannot join the denominator. */
function emittedProvenances(): string[] {
  const src = read("routes");
  const at = src.indexOf("recovery_route_provenance = (");
  if (at < 0) {
    throw new Error("main.py: `recovery_route_provenance` is gone or renamed -- this ruler is bound to that name, a rename has to re-anchor it rather than empty it.");
  }
  /* The expression closes on its own line, indented. Searching for a bare newline-plus-paren runs past it
     and sweeps the rest of a fifteen-thousand-line file into the denominator -- measured: 61 literals
     instead of six, which is a blind ruler, not a drifting table. */
  const lines = src.slice(at).split("\n");
  const stop = lines.findIndex((line, i) => i > 0 && /^\s*\)\s*$/.test(line));
  if (stop < 0) throw new Error("main.py: the provenance expression has no closing paren this ruler can bound.");
  const body = lines.slice(0, stop).join("\n");
  /* The same expression tests `trigger_event.event_type in {"CLOSURE", "WEATHER"}`: those are event types
     the branch reads, not values it writes, so a brace-enclosed set is dropped before the literals are
     collected. Without this the denominator is eight and two of them can never have a wording. */
  const writable = body.replace(/\{[^{}]*\}/g, " ");
  const found = [...writable.matchAll(new RegExp(String.raw`"(?:(${ENUM_NAME}))"`, "g"))].map((m) => m[1]);
  if (found.length < 2) {
    throw new Error(`main.py: only ${found.length} literal(s) parsed inside the provenance expression -- a shape change blinds this ruler.`);
  }
  // the mobility default names the same field on another path
  const defaults = [...src.matchAll(/route_provenance=str\(chosen\.get\("route_provenance"\) or "([A-Z_]+)"\)/g)].map((m) => m[1]);
  return [...new Set([...found, ...defaults])].sort();
}

function labelledProvenances(): Record<string, { zh: string; en: string }> {
  const src = read("vocabulary");
  const at = src.indexOf("const ROUTE_PROVENANCE: Record<RouteProvenance, Label> = {");
  if (at < 0) throw new Error("displayVocabulary.ts: the route-provenance table was renamed. This ruler is bound to that name.");
  const end = src.indexOf("\n};", at);
  const body = src.slice(at, end);
  const out: Record<string, { zh: string; en: string }> = {};
  const row = new RegExp(String.raw`^\s*(${ENUM_NAME})\s*:\s*\{\s*zh:\s*"([^"]*)"\s*,\s*en:\s*"([^"]*)"\s*,?\s*\},?\s*$`, "gm");
  for (const m of body.matchAll(row)) out[m[1]] = { zh: m[2], en: m[3] };
  if (Object.keys(out).length === 0) throw new Error("displayVocabulary.ts: the provenance table parsed empty.");
  return out;
}

const emitted = emittedProvenances();
const labelled = labelledProvenances();

test("every route_provenance the server can write has a traveller wording, in both languages", () => {
  expect(emitted.length, "one provenance value would not be worth a ruler").toBeGreaterThan(2);
  expect(Object.keys(labelled).sort(), "the table and the server's own set drifted apart").toEqual(emitted);
  const offenders: string[] = [];
  for (const [name, label] of Object.entries(labelled)) {
    if (!label.zh.trim() || !label.en.trim()) offenders.push(`${name}: an empty side`);
    for (const side of ["zh", "en"] as const) {
      const hit = new RegExp(String.raw`[A-Z][A-Z0-9_]{3,}`).exec(label[side]);
      if (hit) offenders.push(`${name}.${side} paints "${hit[0]}" -- the wording repeats the enum`);
    }
  }
  expect(offenders, "a provenance wording that is just the code again says nothing to a traveller").toEqual([]);
});

test("the lookup is closed: an unlisted provenance is never answered with its own word", () => {
  const src = read("vocabulary");
  const at = src.indexOf("export function routeProvenanceLabel");
  if (at < 0) throw new Error("displayVocabulary.ts: routeProvenanceLabel is gone or renamed -- this arm would pass on nothing.");
  const body = src.slice(at, src.indexOf("\n}", at));
  expect(body, "routed through the shared pick()/rawChannel() fallback").not.toMatch(/\bpick\(|\brawChannel\(/);
  expect(body, "the lookup returns the value it was handed").not.toMatch(/return\s+(?:String\()?(?:value|raw)\b/);
  expect(body, "the closed table is what answers").toContain("ROUTE_PROVENANCE[");
});

test("the panel keeps the provider key and the enum and adds the words beside them", () => {
  const panel = read("panel");
  expect(panel, "the provider key stopped being printed; the audit reading needs it").toMatch(/source_provider/);
  expect(panel, "the enum stopped being printed; the contract name needs to stay visible").toMatch(/route_provenance \?\? "—"/);
  expect(panel, "the gloss disappeared -- the traveller is back to reading a code alone")
    .toContain("routeProvenanceLabel(incident.route_provenance, zh)");
  expect(panel.replace(/\s+/g, " "), "the gloss is no longer wrapped in brackets")
    .toContain("（${routeProvenanceLabel(incident.route_provenance, zh)}）");
});

test("the ruler read what it claims to have read", () => {
  if (EVIDENCE) {
    mkdirSync(dirname(EVIDENCE), { recursive: true });
    writeFileSync(EVIDENCE, JSON.stringify({
      generatedBy: "cff87c64",
      ruler: "ord0568-route-provenance-gloss-r1",
      run: RUN,
      emitted_provenances: emitted,
      labelled_provenances: labelled,
      main_py_bytes: read("routes").length,
      vocabulary_bytes: read("vocabulary").length,
      panel_bytes: read("panel").length,
    }, null, 1), "utf8");
  }
  expect(emitted.length, "the denominator must not be empty").toBeGreaterThan(2);
});
