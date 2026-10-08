/**
 * ORD-0403 — one named producer for what may be painted on the map glass.
 *
 * The rule the order sets: on the map itself only the stop's name, its category, and its role in
 * the day (start / end / which day) may be drawn. Times, money and provider/source text stay off
 * the glass, because a pin that carries a clock or a price reads as a *promise* about a value the
 * planner may not actually have computed — and on a phone the label is the first thing covering
 * the map.
 *
 * This module is the single place that says so. `lib/rawFacts.ts` already owns a whitelist, but
 * that one is about failure readouts on a different surface; reusing its name for a different
 * domain would make two things look like one.
 *
 * `MAP_LABEL_FIELDS` is deliberately a set of *field names*, not a list of finished strings: the
 * gate asserts against the values a running screen actually paints, and a field list is what lets
 * it say which allowed field a hit came from.
 *
 * ORD-0415 (this file's second generation): the list used to live at `e2e/_mapLabelRules.ts`,
 * because when ORD-0415 moved it there in r1 nothing on the product path consulted it, so a module
 * under `src/lib/` was claiming a runtime authority it did not have. That premise is now gone:
 * `lib/mapStopLabels.ts` decides the painted word with `takeOffGlass()`, `components/JourneyMap.tsx`
 * scrubs the `title` it feeds to its own `symbol` layer, and `components/v8/MapPanel.tsx` uses the
 * same word for the chip and for its pin's accessible name. The rule moved back for exactly the
 * reason its own header gave, and `e2e/_mapLabelRules.ts` is now a re-export of this module, so the
 * gates still read one definition rather than a copy.
 */

/**
 * ORD-0412 — the scope of `MAP_LABEL_FORBIDDEN`: which strings this rule has any authority over.
 *
 * The `source` class matches `openstreetmap`, `©` and `provider`, and that is precisely the text the
 * ORD-A compliance obligation REQUIRES on screen (basemap provider attribution, per the tile
 * licence).  The two only stay out of each other's way because this rule judges strings painted on
 * the map glass while that sentence is DOM text.  Saying so here is what stops a later reader from
 * pointing the list at the whole map panel, reading a required compliance sentence as a violation,
 * and "fixing" it by deleting the sentence.  `e2e/qoder-map-ord0412-label-scope.spec.ts` asserts
 * both halves: the scope is declared, and the two surfaces hold at the same time on one screen.
 */
export const MAP_LABEL_SCOPE = {
  /** Feed only these to `mapLabelViolations` -- label text drawn on the canvas. */
  judged: ["canvas-label-strings"],
  /** Never judged here. The basemap attribution lives in the DOM and must stay readable. */
  notJudged: ["dom-attribution", "dom-panel-text"],
  /* The obligation this carve-out protects, carried in the rule's own data: deleting it makes the
     gate red rather than quietly turning a required sentence into a reported violation. */
  becauseOf: "ORD-A basemap provider attribution must stay readable on screen",
} as const;
export type MapLabelScopeSurface = keyof typeof MAP_LABEL_SCOPE;

/** maplibre expression for the symbol layer that labels a stop on the map. */
export function mapLabelTextField(): string[] {
  return ["get", "title"];
}

/** Patterns that must never appear in text painted on the map canvas. Each carries the reason the
 *  order gives: a clock, a currency, or a provider/source attribution.  Canvas only -- see
 *  `MAP_LABEL_SCOPE`; the DOM basemap attribution is not a violation of this list. */
export const MAP_LABEL_FORBIDDEN: ReadonlyArray<{ name: string; source: string; pattern: RegExp }> = [
  { name: "clock-time", source: "start_at / end_at", pattern: /\b\d{1,2}:\d{2}\b/ },
  { name: "duration", source: "travel_from_prev_min", pattern: /\d+\s*(?:分钟|min)\b/i },
  { name: "money", source: "estimated_cost", pattern: /[¥$€£]|CNY|USD|\d+\s*元/ },
  { name: "source", source: "basemap/provider attribution", pattern: /openstreetmap|openfreemap|©|provider/i },
];

/** Which forbidden classes are present in a painted string. Empty array means the string is clean.
 *  The argument must come from `MAP_LABEL_SCOPE.judged`; passing DOM text -- in particular the
 *  basemap attribution the ORD-A gate requires to be readable -- makes a required sentence count as
 *  a violation, which is the misdelete this declaration exists to prevent. */
export function mapLabelViolations(painted: string): string[] {
  return MAP_LABEL_FORBIDDEN.filter((rule) => rule.pattern.test(painted)).map((rule) => rule.name);
}

/**
 * ORD-0415 — take the forbidden classes off the glass, keep the rest of the word.
 *
 * The list above was a judgement with no effect: nothing cut the strings before they were painted,
 * so a stop whose server-sent name carried a clock or a price reached the traveller with that clock
 * or price on it. This is the cut.
 *
 * What it does is subtractive and stays inside one word: every span a forbidden pattern matches is
 * taken out and the remaining text is kept verbatim, so "天津之眼 19:30 摩天轮" paints as
 * 「天津之眼 摩天轮」 rather than as nothing. It never substitutes: no token is reworded, no
 * placeholder is inserted, and the string the traveller did not get is not replaced by a string the
 * product invented. What comes back in `removed` is the list of classes actually taken out, which is
 * what lets a gate tell "the rule fired" apart from "this name happened to be clean" — the two read
 * identically in a painted corpus of zero hits.
 *
 * When the whole word is forbidden (`text` comes back empty) the caller paints nothing rather than
 * inventing a name; the pin and its ordinal still identify the stop, which is the same rule
 * `placeLabels()` already follows when there is no room for a word.
 *
 * Scope: this function is for `MAP_LABEL_SCOPE.judged` strings only. Feeding it the DOM basemap
 * attribution would delete a sentence the tile licence requires (`MAP_LABEL_SCOPE.becauseOf`).
 */
export function takeOffGlass(painted: string): { text: string; removed: string[] } {
  const removed: string[] = [];
  let text = painted;
  for (const rule of MAP_LABEL_FORBIDDEN) {
    if (!rule.pattern.test(text)) continue;
    removed.push(rule.name);
    /* A global copy because a label can carry the same class twice ("08:30 ... 10:15"), and the
       patterns in this list are written without the flag on purpose: `mapLabelViolations` asks
       "is this class present", which must not inherit a lastIndex from the previous call. */
    const every = new RegExp(rule.pattern.source, `${rule.pattern.flags.replace("g", "")}g`);
    text = text.replace(every, " ");
  }
  return { text: text.replace(/\s+/g, " ").trim(), removed };
}
