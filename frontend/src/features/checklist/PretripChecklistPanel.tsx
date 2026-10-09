import { useLocale } from "../../i18n/LocaleContext";
import {
  derivePretripChecklist,
  emptyStateCopy,
  EMPTY_STATE_ACTION,
  ANCHORED_CHECKLIST_KEYS,
  type PretripSources,
} from "../../lib/pretripChecklist";
import "./pretripChecklist.css";

type Props = {
  /** Read from the payload the screen already holds; nothing is fetched here. */
  sources: PretripSources;
  onNavigate: (route: string) => void;
};

/**
 * ORD-0384 -- the two outstanding things the server can be held to.
 *
 * The heading used to promise "what the server still reports as outstanding", which overstates a list
 * built from two fields. It now says which two, because the honest boundary is the finding of this
 * order: nine candidate classes were measured and seven of them name a field no contract declares, so
 * they are not shown and are handed over as a list instead.
 *
 * Deliberately without a tick box. The list is a projection of fields the server answers, so an item
 * disappears when the fact changes -- a "done" the traveller could press would be a second, weaker
 * source of truth about the same thing, and this screen would then be able to say "done" while the
 * server still says otherwise. That is the one failure mode this panel may not have.
 */
export function PretripChecklistPanel({ sources, onNavigate }: Props) {
  const { locale, t } = useLocale();
  const zh = locale.startsWith("zh");
  const items = derivePretripChecklist(sources);

  return (
    <section
      className="cn-pretrip"
      data-testid="pretrip-checklist"
      data-cnx-field="checklist_items"
      data-cnx-allowed-keys={ANCHORED_CHECKLIST_KEYS.join(" ")}
      data-count={items.length}
      aria-label={t("detail.pretripAria")}
    >
      <div className="cn-pretrip-head">
        <div>
          <span className="v8-kicker">{t("detail.pretripKicker")}</span>
          <h2>{t("detail.pretripHeading")}</h2>
        </div>
        {/* ORD-0401 ①: the note explains a list that is not on screen. With nothing outstanding it is
            dropped, and the empty state becomes one row -- the heading above, one sentence, the
            action. Measured at 390x844: 325 px (zh) / 440 px (en) -> 143 px / 207 px. */}
        {items.length > 0 && (
          <p className="cn-pretrip-note">{t("detail.pretripNote")}</p>
        )}
      </div>

      {items.length === 0 ? (
        <div className="cn-pretrip-empty" data-testid="pretrip-empty">
          <span>{emptyStateCopy(zh)}</span>
          <button
            type="button"
            className="v8-quiet-button"
            data-testid="pretrip-empty-action"
            onClick={() => onNavigate(EMPTY_STATE_ACTION.route)}
          >
            {zh ? EMPTY_STATE_ACTION.label.zh : EMPTY_STATE_ACTION.label.en}
          </button>
        </div>
      ) : (
        <ul className="cn-pretrip-list">
          {items.map((item) => (
            <li key={item.key} data-testid="pretrip-item" data-cnx-key={item.key}>
              <strong className="cn-pretrip-title">{zh ? item.title.zh : item.title.en}</strong>
              <p className="cn-pretrip-why">{zh ? item.why.zh : item.why.en}</p>
              <p className="cn-pretrip-basis">
                <span>{t("detail.basisPrefix")}</span>
                <code data-cnx-field="basis_endpoint">{item.basis.endpoint}</code>
                <span> {"→ "} </span>
                <code data-cnx-field="basis_field">{item.basis.field}</code>
              </p>
              <p className="cn-pretrip-anchor">
                <span>{t("detail.anchorPrefix")}</span>
                <code data-cnx-anchor={`${item.basis.anchor.file}:${item.basis.anchor.line}`}>
                  {`${item.basis.anchor.file}:${item.basis.anchor.line}`}
                </code>
              </p>
              <button
                type="button"
                className="v8-quiet-button"
                data-testid={`pretrip-goto-${item.key}`}
                onClick={() => onNavigate(item.target.route)}
              >
                {zh ? item.target.label.zh : item.target.label.en}
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
