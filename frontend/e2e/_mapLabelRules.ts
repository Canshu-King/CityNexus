/**
 * ORD-0415 — this file is a re-export, and the reason it exists changed.
 *
 * r1 (09-29 08:27) moved the list out of `src/lib/` and onto the gate side because nothing on the
 * product path consulted it: `mapLabelTextField()` had one mention in the whole repo -- its own
 * definition -- and the module's only importers were `e2e/qoder-map-ord0403-*.spec.ts` and
 * `e2e/qoder-map-ord0412-*.spec.ts`.  Keeping it under `frontend/src/lib/` at that time claimed a
 * runtime authority it did not have.
 *
 * The wiring r1 predicted as "the moment to move this back" has now happened: the product reads the
 * list before it paints.  `src/lib/mapStopLabels.ts` decides the painted word through
 * `takeOffGlass()`, `components/JourneyMap.tsx` scrubs the `title` it hands to its own `symbol`
 * layer (`"text-field": ["get", "title"]`), and `components/v8/MapPanel.tsx` paints the chip and its
 * pin's accessible name from that one word.  So the definition lives in the product tree, and this
 * path stays as a re-export so the gates that already import `./_mapLabelRules` keep reading the
 * same single list rather than a second copy of it.
 *
 * Naming note for whoever reads the `scope-declared` arm next: that arm still asserts
 * `src/lib/mapLabels.ts` does not exist.  It is a filename, not the premise -- the premise it was
 * written to protect ("no product code consults this rule") is now false, and the arm is answered by
 * `qoder-map-ord0415-forbidden-off-the-glass.spec.ts`, which measures painted hits on the running
 * screen instead of looking for a file.
 */

export {
  MAP_LABEL_FIELDS,
  MAP_LABEL_FORBIDDEN,
  MAP_LABEL_SCOPE,
  mapLabelTextField,
  mapLabelSpanViolations,
  mapLabelViolations,
  takeOffGlass,
} from "../src/lib/mapLabelRules";
export type { MapLabelField, MapLabelScopeSurface } from "../src/lib/mapLabelRules";
