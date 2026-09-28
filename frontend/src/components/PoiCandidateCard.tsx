import { useT } from "../i18n/LocaleContext";
import { PlaceProvenance } from "./PlaceProvenance";

/**
 * ORD-0437: the one card a place arrives on, whether it came from a pasted note (this order) or from
 * the batch picker (ORD-0435).
 *
 * The markup contract is lifted from the discovery panel's result card as it stands on the base of
 * this branch -- `frontend/src/features/discovery/RealCityDiscoveryPanel.tsx:239-252` at
 * 8d038b21f09477b933cff3b1c7b09845c542373b -- rather than written afresh, because two cards that
 * look alike are how a screen starts answering the same question twice. It is extracted, not forked:
 * nothing on the discovery side was touched, so ORD-0435 can move onto this component in one edit of
 * its own instead of merging two implementations.
 *
 * Selection is a pair, never a state: the reference chain's own rule (map_findings.md:150) is that
 * every 选中态 needs its 未选中态, so the control is always mounted and `aria-checked` is what moves.
 */
export type PoiCardStatus = "RESOLVED" | "AMBIGUOUS" | "UNRESOLVED";

export function PoiCandidateCard({
  index,
  phrase,
  status,
  placeId,
  placeName,
  category,
  coordinateSystem,
  note,
  addable,
  selected,
  onToggle,
  ambiguousNames = [],
}: {
  index: number;
  /** The words the traveller actually wrote, kept visible so a match can be argued with. */
  phrase: string;
  status: PoiCardStatus;
  placeId?: string | null;
  placeName?: string | null;
  category?: string | null;
  coordinateSystem?: string | null;
  note?: string | null;
  addable: boolean;
  selected: boolean;
  /** null where the surface has no selection yet, so the card degrades to a read-only row. */
  onToggle: (() => void) | null;
  ambiguousNames?: string[];
}) {
  const t = useT();
  const label = placeName || phrase;
  const stateWord =
    status === "RESOLVED"
      ? t("poiImport.cardMatched")
      : status === "AMBIGUOUS"
        ? t("poiImport.cardAmbiguous")
        : t("poiImport.cardUnresolved");
  return (
    <article
      className={selected ? "v8-stay-card selected" : "v8-stay-card"}
      data-testid="poi-candidate-card"
      data-poi-status={status}
      data-poi-addable={addable ? "yes" : "no"}
    >
      <div className="v8-stay-card-body">
        <div className="v8-stay-card-title">
          <div>
            <span className="v8-rank">{status === "RESOLVED" ? "✓" : "—"}</span>
            <h3>{label}</h3>
          </div>
          <span className="v8-selected-label" data-testid="poi-candidate-state">
            {stateWord}
          </span>
        </div>
        <PlaceProvenance
          name={label}
          category={category ?? "poi"}
          providerKey={null}
          coordinateSystem={coordinateSystem ?? null}
          sourceCoordinateSystem={null}
          host={null}
        />
        {note ? <p data-testid="poi-candidate-note">{note}</p> : null}
        {status !== "RESOLVED" ? (
          <p className="v8-sheet-note" data-testid="poi-candidate-reason">
            {status === "AMBIGUOUS"
              ? t("poiImport.cardAmbiguousWhy", { names: ambiguousNames.slice(0, 3).join(" / ") })
              : t("poiImport.cardUnresolvedWhy")}
          </p>
        ) : null}
        <div className="v8-stay-impact">
          <span data-testid="poi-candidate-phrase">{t("poiImport.cardPhrase", { phrase })}</span>
          <b>{t("poiImport.cardIndex", { n: index })}</b>
          {onToggle ? (
            <button
              type="button"
              role="checkbox"
              aria-checked={selected}
              disabled={!addable}
              data-testid="poi-card-select"
              onClick={onToggle}
            >
              {selected ? t("poiImport.cardDeselect") : t("poiImport.cardSelect")}
            </button>
          ) : null}
        </div>
      </div>
    </article>
  );
}
