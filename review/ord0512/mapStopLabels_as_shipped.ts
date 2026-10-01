/**
 * ORD-0512 — what the map paints beside a pin, decided in one place.
 *
 * Until now this rule existed only on the ruler side. `e2e/_mapLabelRules.ts` says which classes of
 * string may never be painted on the glass, and `qoder-ord0415-label-string-origin.spec.ts` measured
 * that nothing on the product path consulted it: the v8 panel drew a pin per stop and put the stop's
 * name in `aria-label`, so the name was announced and never shown. The number alone answers "which
 * one is this" only against a list the traveller has to read somewhere else.
 *
 * Two separate rules live here, and they are kept apart because they answer different questions:
 *
 *   `stopLabel()` — which *server-sent field* the painted word comes from. `backend/app/schemas.py`
 *      (`SharedStop`) already states the screen's rule: the place's own name first, the plan's title
 *      only when the store has no name, because a title is what a planner typed and is not always the
 *      name of the thing itself. A stop with neither gets no word rather than an invented one — an
 *      absent name is a fact, and the pin's ordinal still identifies it.
 *
 *   `placeLabels()` — which of those words fit on the glass at this exact zoom. Two chips of text
 *      smeared over each other read as neither name, so a crowded view shows the stops the traveller
 *      cares about most and hides the rest. Hiding is a placement decision about *text*, never about
 *      the stop: the pin, its hit target and its node all stay, which is what the accepted map gates
 *      count as the proof that a located stop is still pickable (see `src/map-selection.css`, the
 *      `.filtered-out` note from ORD-0497).
 *
 * What is deliberately NOT here: the whitelist of forbidden classes. That stays in
 * `e2e/_mapLabelRules.ts`, where ORD-0415 put it, because the compliance list is a judgement the gate
 * makes about whatever ends up painted — copying it into the product would give the rule two owners.
 */

export type MapNameableStop = {
  /** the place row's own name, when the payload carries one */
  place_name?: string | null;
  /** what this plan calls the stop */
  title?: string | null;
};

export type MapLabelSource = "place_name" | "title" | "none";

export type MapStopLabel = { text: string; from: MapLabelSource };

/** Trim a server string the way the glass needs it: an empty or whitespace-only name is no name. */
function named(value: string | null | undefined): string | null {
  const text = (value ?? "").trim();
  return text.length > 0 ? text : null;
}

export function stopLabel(stop: MapNameableStop): MapStopLabel | null {
  const fromPlace = named(stop.place_name);
  if (fromPlace) return { text: fromPlace, from: "place_name" };
  const fromTitle = named(stop.title);
  if (fromTitle) return { text: fromTitle, from: "title" };
  return null;
}

export type LabelBox = { x: number; y: number; w: number; h: number };

export type LabelCandidate = {
  id: string;
  /**
   * The boxes this word could take, in the order it may try them -- a chip reaching right of its pin
   * first, then left. r1 painted only to the right and `off_map` was then the commonest reason a name
   * was missing at 390 px, which was the placement rule's own doing rather than the map's.
   */
  sides: LabelBox[];
  /** higher wins; ties break on `order` ascending so the first stop of the day keeps its name */
  priority: number;
  order: number;
};

export type LabelVerdict = { placement: LabelPlacement; side: number };

/**
 * Why a word is not on the glass. Named rather than boolean, because the traveller's question and the
 * gate's question are the same one: "this stop has no name" and "there is no room for this name here"
 * are different facts, and a screen that hides both the same way teaches neither.
 */
export type LabelPlacement = "shown" | "off_map" | "over_a_name" | "over_a_control" | "no_box";

const EPSILON_PX = 1;

function overlaps(a: LabelBox, b: LabelBox): boolean {
  const w = Math.min(a.x + a.w, b.x + b.w) - Math.max(a.x, b.x);
  const h = Math.min(a.y + a.h, b.y + b.h) - Math.max(a.y, b.y);
  return w > EPSILON_PX && h > EPSILON_PX;
}

function inside(box: LabelBox, frame: LabelBox): boolean {
  return (
    box.x >= frame.x - EPSILON_PX &&
    box.y >= frame.y - EPSILON_PX &&
    box.x + box.w <= frame.x + frame.w + EPSILON_PX &&
    box.y + box.h <= frame.y + frame.h + EPSILON_PX
  );
}

/**
 * Where each word goes, in priority order, greedily.
 *
 * `frame` is the box labels are allowed to live in — the map surface itself; a chip running off it
 * would paint half a place name, and half a name is not an answer. `reserved` is what the panel has
 * already claimed on the glass (the basemap attribution, the caption and notice stack, the named
 * control): a name painted underneath one of those is invisible, so it is not a name.
 *
 * Every candidate comes back, shown or not: the caller paints the verdict onto the element it belongs
 * to, which is what lets the screen say *why* and the gate read *what*.
 */
export function placeLabels(
  candidates: LabelCandidate[],
  frame: LabelBox | null,
  reserved: LabelBox[] = [],
): Map<string, LabelVerdict> {
  const ordered = [...candidates].sort(
    (a, b) => b.priority - a.priority || a.order - b.order || a.id.localeCompare(b.id),
  );
  const verdicts = new Map<string, LabelVerdict>();
  const placed: { box: LabelBox; kind: "name" | "control" }[] = reserved.map((box) => ({
    box,
    kind: "control" as const,
  }));
  for (const candidate of ordered) {
    const usable = candidate.sides
      .map((box, index) => ({ box, index }))
      .filter(({ box }) =>
        Number.isFinite(box.w) && Number.isFinite(box.h) && box.w > 0 && box.h > 0);
    if (!usable.length) {
      verdicts.set(candidate.id, { placement: "no_box", side: 0 });
      continue;
    }
    const inFrame = usable.filter(({ box }) => !frame || inside(box, frame));
    if (!inFrame.length) {
      /* Every side this word could take leaves the map surface: painted here it would be half a name. */
      verdicts.set(candidate.id, { placement: "off_map", side: usable[0].index });
      continue;
    }
    const free = inFrame.find(({ box }) => !placed.some((entry) => overlaps(box, entry.box)));
    if (!free) {
      const blocker = placed.find((entry) => overlaps(inFrame[0].box, entry.box));
      verdicts.set(candidate.id, {
        placement: blocker?.kind === "name" ? "over_a_name" : "over_a_control",
        side: inFrame[0].index,
      });
      continue;
    }
    placed.push({ box: free.box, kind: "name" });
    verdicts.set(candidate.id, { placement: "shown", side: free.index });
  }
  return verdicts;
}
