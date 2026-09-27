import { useLocale } from "../../i18n/LocaleContext";
import { derivePretripChecklist, emptyStateCopy, type PretripSources } from "../../lib/pretripChecklist";
import "./pretripChecklist.css";

type Props = {
  /** Read from the same payloads the screen already holds; nothing is fetched here. */
  sources: PretripSources;
  onNavigate: (route: string) => void;
};

/**
 * ORD-0384 -- what the server says is still outstanding before this trip.
 *
 * Deliberately without a tick box. The list is a projection of fields the server already answers, so an
 * item disappears when the underlying fact changes -- a "done" the traveller could press would be a
 * second, weaker source of truth about the same thing, and the panel would then be able to say "done"
 * while the server still says otherwise. That is the one failure mode this screen may not have.
 */
export function PretripChecklistPanel({ sources, onNavigate }: Props) {
  const { locale } = useLocale();
  const zh = locale.startsWith("zh");
  const items = derivePretripChecklist(sources);
  const read = { experience: sources.experience !== null && sources.experience !== undefined, wallet: sources.wallet !== null && sources.wallet !== undefined };

  return (
    <section
      className="cn-pretrip"
      data-testid="pretrip-checklist"
      data-cnx-field="checklist_items"
      data-count={items.length}
      aria-label={zh ? "行前清单" : "Pre-trip checklist"}
    >
      <div className="cn-pretrip-head">
        <div>
          <span className="v8-kicker">{zh ? "行前清单" : "Before you go"}</span>
          <h2>{zh ? "服务端说还差这些" : "What the server still reports as outstanding"}</h2>
        </div>
        <p className="cn-pretrip-note">
          {zh
            ? "这里只列服务端已经答出来的事；完成状态由那些事实自己消失，不需要你打勾，我们也不会替你没跑过的检查打勾。"
            : "Only what the server has already answered appears here. Items disappear when the underlying fact changes -- nothing is ticked by hand, and no check that was not run is ever shown as passed."}
        </p>
      </div>

      {!read.wallet && (
        /* A list built from one of two sources must not look finished. The wallet leg answers on its own
           schedule, so until it lands the two booking-derived rules have not been looked at -- and
           "nothing outstanding" would be a claim this screen has not earned. */
        <p className="cn-pretrip-why" data-testid="pretrip-source-pending">
          {zh
            ? "还有一项来源没有读到（预订与承诺），所以与它相关的条目此刻列不出来。"
            : "One source has not been read yet (reservations and commitments), so the items that depend on it cannot be listed right now."}
        </p>
      )}
      {items.length === 0 ? (
        <div className="cn-pretrip-empty" data-testid="pretrip-empty">
          <span>{emptyStateCopy(zh, read)}</span>
          <button
            type="button"
            className="v8-quiet-button"
            data-testid="pretrip-empty-action"
            onClick={() => onNavigate("studio")}
          >
            {zh ? "去看方案" : "Open the plan"}
          </button>
        </div>
      ) : (        <ul className="cn-pretrip-list">
          {items.map((item) => (
            <li key={item.key} data-testid="pretrip-item" data-cnx-key={item.key}>
              <strong className="cn-pretrip-title">{zh ? item.title.zh : item.title.en}</strong>
              <p className="cn-pretrip-why">{zh ? item.why.zh : item.why.en}</p>
              <p className="cn-pretrip-basis">
                <span>{zh ? "依据：" : "Basis: "}</span>
                <code data-cnx-field="basis_endpoint">{item.basis.endpoint}</code>
                <span> {"→ "} </span>
                <code data-cnx-field="basis_field">{item.basis.field}</code>
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
