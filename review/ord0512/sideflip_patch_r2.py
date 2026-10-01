"""ORD-0512 r2 -- give the names a second side, by exact anchor, or refuse.

Measured on r1's own bytes at 390x844: 9 located stops, 9 label nodes, 3 names on the glass, and the
reasons were `off_map` four times over. The chip only ever reached to the right of its pin (`anchor:
"left"`, `offset: [16, 0]`), so any stop whose pin sat within ~120 px of the map's right edge had its
word fall off the surface -- a placement rule throwing away names the phone has room for on the *other*
side of the pin. This patch tries right first and then left, which is what a real map does.

Every edit is one exact anchor, applied once, with the file's sha256 printed after the pass, so a stale
anchor is an error rather than a silent no-op -- the failure this lane already recorded against its own
ORD-0477 mutant (`screen_stops_asking` printed "No matches found" while the suite stayed green).

usage: python ord0512_sideflip_r2.py            (dry run: refuses or reports)
       python ord0512_sideflip_r2.py --apply
"""
import hashlib
import os
import pathlib
import sys

TREE = pathlib.Path(os.environ.get("ORD0512_TREE") or r"D:/moodle/_qoder_b_ord0417_20260928/ord0512cut_1c785a2d")

LIB = "frontend/src/lib/mapStopLabels.ts"
PANEL = "frontend/src/components/v8/MapPanel.tsx"
SPEC = "frontend/e2e/qoder-0512-stop-names-on-the-glass.spec.ts"

EDITS = [
    (LIB,
     '''export type LabelCandidate = {
  id: string;
  box: LabelBox;
  /** higher wins; ties break on `order` ascending so the first stop of the day keeps its name */
  priority: number;
  order: number;
};''',
     '''export type LabelCandidate = {
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

export type LabelVerdict = { placement: LabelPlacement; side: number };'''),

    (LIB,
     '''export function placeLabels(
  candidates: LabelCandidate[],
  frame: LabelBox | null,
  reserved: LabelBox[] = [],
): Map<string, LabelPlacement> {
  const ordered = [...candidates].sort(
    (a, b) => b.priority - a.priority || a.order - b.order || a.id.localeCompare(b.id),
  );
  const verdicts = new Map<string, LabelPlacement>();
  const placed: { box: LabelBox; kind: "name" | "control" }[] = reserved.map((box) => ({
    box,
    kind: "control" as const,
  }));
  for (const candidate of ordered) {
    const { box } = candidate;
    if (!Number.isFinite(box.w) || !Number.isFinite(box.h) || box.w <= 0 || box.h <= 0) {
      verdicts.set(candidate.id, "no_box");
      continue;
    }
    if (frame && !inside(box, frame)) {
      verdicts.set(candidate.id, "off_map");
      continue;
    }
    const blocker = placed.find((entry) => overlaps(box, entry.box));
    if (blocker) {
      verdicts.set(candidate.id, blocker.kind === "name" ? "over_a_name" : "over_a_control");
      continue;
    }
    placed.push({ box, kind: "name" });
    verdicts.set(candidate.id, "shown");
  }
  return verdicts;
}''',
     '''export function placeLabels(
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
}'''),

    (PANEL,
     '''  const labelNodes = useRef<
    { el: HTMLElement; key: string; at: [number, number]; priority: number; order: number }[]
  >([]);''',
     '''  const labelNodes = useRef<
    {
      el: HTMLElement;
      marker: import("maplibre-gl").Marker;
      key: string;
      at: [number, number];
      priority: number;
      order: number;
    }[]
  >([]);'''),

    (PANEL,
     '''        const at: [number, number] = [point.longitude, point.latitude];
        labelMarkers.current.push(
          new maplibregl.Marker({ element: chip, anchor: "left", offset: [16, 0] })
            .setLngLat(at)
            .addTo(mapInstance),
        );
        labelNodes.current.push({
          el: chip,
          key: point.id ?? `stay-${index}`,
          at,
          priority: point.id && point.id === selectedRef.current ? 3 : point.current ? 2 : 1,
          order: index,
        });''',
     '''        const at: [number, number] = [point.longitude, point.latitude];
        const chipMarker = new maplibregl.Marker({ element: chip })
          .setLngLat(at)
          .addTo(mapInstance);
        labelMarkers.current.push(chipMarker);
        labelNodes.current.push({
          el: chip,
          marker: chipMarker,
          key: point.id ?? `stay-${index}`,
          at,
          priority: point.id && point.id === selectedRef.current ? 3 : point.current ? 2 : 1,
          order: index,
        });'''),

    (PANEL,
     '''    const verdicts = placeLabels(
      labelNodes.current.map((node) => {
        const box = node.el.getBoundingClientRect();
        return { id: node.key, box: { x: box.x, y: box.y, w: box.width, h: box.height }, priority: node.priority, order: node.order };
      }),
      frame,
      reserved,
    );
    for (const node of labelNodes.current) {
      /* `data-placement` carries the reason because the reason is a fact about the camera, not about
         the stop — and a machine word belongs in an attribute, which is where this family already puts
         them. */
      const verdict = verdicts.get(node.key) ?? "no_box";
      node.el.setAttribute("data-placement", verdict);
      node.el.classList.toggle("label-hidden", verdict !== "shown");
    }''',
     '''    /* Both sides are built from the pin's anchor point rather than measured off the element, because
       the element sits wherever the *previous* fit put it -- its width is stable, its position is not. */
    const candidates = labelNodes.current.map((node) => {
      const size = node.el.getBoundingClientRect();
      const pin = map.project(node.at);
      const cx = frame.x + pin.x;
      const cy = frame.y + pin.y;
      return {
        id: node.key,
        sides: [
          { x: cx + LABEL_GAP_PX, y: cy - size.height / 2, w: size.width, h: size.height },
          { x: cx - LABEL_GAP_PX - size.width, y: cy - size.height / 2, w: size.width, h: size.height },
        ],
        priority: node.priority,
        order: node.order,
      };
    });
    const verdicts = placeLabels(candidates, frame, reserved);
    for (const node of labelNodes.current) {
      /* `data-placement` carries the reason and `data-side` the branch that was used: both are facts
         about this camera, not about the stop, and a machine word belongs in an attribute -- which is
         where this family already puts them. */
      const verdict = verdicts.get(node.key) ?? { placement: "no_box" as const, side: 0 };
      const size = node.el.getBoundingClientRect();
      const pin = map.project(node.at);
      const reach = LABEL_GAP_PX + size.width / 2;
      node.marker.setOffset(verdict.side === 1 ? [-reach, 0] : [reach, 0]);
      node.el.setAttribute("data-placement", verdict.placement);
      node.el.setAttribute("data-side", verdict.side === 1 ? "left" : "right");
      node.el.classList.toggle("label-hidden", verdict.placement !== "shown");
    }'''),

    (PANEL,
     '''    const canvas = host.current;
    const panel = canvas?.closest(".v8-map-panel") ?? null;
    if (!canvas || !panel) return;''',
     '''    const canvas = host.current;
    const panel = canvas?.closest(".v8-map-panel") ?? null;
    const map = mapRef.current;
    if (!canvas || !panel || !map) return;'''),

    (PANEL,
     '''  const applyLabels = () => {''',
     '''  /* The chip clears its pin's own 28 px box by a few pixels, and the same number is used on both
     sides so a name flipped left does not sit closer than one that stayed right. */
  const LABEL_GAP_PX = 18;
  const applyLabels = () => {'''),

    (SPEC,
     '''type LabelReading = {
  ordinal: string;
  text: string;
  source: string | null;
  placement: string | null;
  visible: boolean;''',
     '''type LabelReading = {
  ordinal: string;
  text: string;
  source: string | null;
  placement: string | null;
  side: string | null;
  visible: boolean;'''),

    (SPEC,
     '''          placement: el.getAttribute("data-placement"),''',
     '''          placement: el.getAttribute("data-placement"),
          side: el.getAttribute("data-side"),'''),

    (SPEC,
     '''  expect(shown.length, node("A1", "no stop name reached the glass at all")).toBeGreaterThan(0);''',
     '''  expect(shown.length, node("A1", "no stop name reached the glass at all")).toBeGreaterThan(0);
  /* r1 measured 3 of 9 names on the glass at this shape and four of the six misses were `off_map` --
     the placement rule dropping a word that fits on the other side of its pin. Five is the floor that
     reading sets, not a wish: a build that goes back to one-sided placement falls under it. */
  expect(shown.length, node("A1", `only ${shown.length} of ${read.labelNodeCount} names on the glass is r1's one-sided placement, not this rule`)).toBeGreaterThanOrEqual(5);'''),
]


def main() -> int:
    apply = "--apply" in sys.argv
    for rel, old, new in EDITS:
        path = TREE / rel
        text = path.read_text(encoding="utf-8")
        hits = text.count(old)
        if hits != 1:
            print("REFUSE: anchor occurs %d times in %s :: %r" % (hits, rel, old[:70]))
            return 3
        if apply:
            path.write_text(text.replace(old, new), encoding="utf-8", newline="")
    seen = []
    for rel in {r for r, _, _ in EDITS}:
        digest = hashlib.sha256((TREE / rel).read_bytes()).hexdigest()
        seen.append((rel, digest))
    print("EDITS=%d APPLIED=%s" % (len(EDITS), apply))
    for rel, digest in sorted(seen):
        print("FILE %s sha256=%s" % (rel, digest[:16]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
