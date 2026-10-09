import { useRef } from "react";
import type { V8Data, V8Mode } from "../../app/v8Types";
import { v8Modes } from "../../app/v8Types";
import { useT, useLocale } from "../../i18n/LocaleContext";
import { formatMinorMoney } from "../../lib/money";
import { useModalLayer } from "../../lib/useModalLayer";

export function MobilitySheet({ facts, selectedMode, onSelect, onClose }: { facts: V8Data["mobility_facts"]; selectedMode: V8Mode; onSelect: (mode: V8Mode) => void; onClose: () => void }) {
  const t = useT();
  const { locale } = useLocale();
  const sheetRef = useRef<HTMLElement | null>(null);
  /* Esc, backdrop, the close button and picking a mode all leave the same way, so the sheet is never
     dismissed without its exit animation. */
  const { closing, requestClose, onBackdropMouseDown } = useModalLayer({ open: true, onClose, sheetRef });
  return <div className="v8-sheet-backdrop" role="presentation" data-state={closing ? "closing" : "open"} onMouseDown={onBackdropMouseDown}><section ref={sheetRef} className="v8-mobility-sheet" role="dialog" aria-modal="true" aria-labelledby="mobility-sheet-title" data-state={closing ? "closing" : "open"} onClick={(event) => event.stopPropagation()}><div className="v8-sheet-handle" /><div className="v8-sheet-heading"><div><p className="v8-kicker">{t("mobility.kicker")}</p><h2 id="mobility-sheet-title">{t("mobility.title")}</h2></div><button className="v8-close-button" onClick={requestClose} aria-label={t("mobility.closeLabel")}>×</button></div><div className="v8-mode-comparison">{v8Modes.map((mode) => { const fact = facts.find((item) => item.mode === mode); const unavailable = !fact; return <button key={mode} className={selectedMode === mode ? "v8-mode-option active" : "v8-mode-option"} disabled={unavailable} onClick={() => { if (!unavailable) { onSelect(mode); requestClose(); } }}><strong>{mode.replace("_", " ")}</strong><span>{unavailable ? t("mobility.unavailable") : `${fact.duration_min} min · ${fact.walking_min} min walk`}</span><b>{unavailable ? "—" : fact.cost_amount_minor == null ? t("mobility.costUnknown") : money(fact.cost_amount_minor, fact.currency ?? "CNY", locale)}</b><small>{unavailable ? t("mobility.noProvider") : `${fact.transfers} transfers · ${fact.weather_exposure.toLowerCase()} exposure · ${Math.round(fact.reliability_score * 100)}% reliability`}</small></button>; })}</div><button className="v8-primary v8-sheet-primary" onClick={() => { onSelect("TRANSIT"); requestClose(); }}>{t("mobility.letChoose")}</button><p className="v8-sheet-note">{t("mobility.note")}</p></section></div>;
}

function money(minor: number, currency: string, locale: string) { return formatMinorMoney(minor, currency, locale); }
