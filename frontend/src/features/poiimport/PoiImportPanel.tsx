import { useState } from "react";
import { useT } from "../../i18n/LocaleContext";
import { namedCodeIn } from "../../lib/rawFacts";
import { rejectionWithFacts, RejectionWithFacts } from "../../lib/rejectionFacts";
import { PoiCandidateCard } from "../../components/PoiCandidateCard";

/**
 * ORD-0437 — the second step of the POI entry chain: paste text or links, get places.
 *
 * Shapes are taken line by line from `D:/moodle/_apk_analysis_pi_travel/MAP/map_findings.md:150`
 * (the F24 chain), and the ones this build cannot honour are said out loud instead of being skipped:
 *
 *   two parallel input modes — 文本或链接识别 is wired; 截图识别 is presented and refused by name,
 *     because a screenshot needs OCR and this order ships none.
 *   the result card carries all three phases in one place — `loading`, `error` and `success` render
 *     inside the same region, and 重试 stays mounted in every one of them. A card that only shows a
 *     retry after failing is how a traveller ends up reloading the whole screen.
 *   a verification warning sits above the success list permanently — the extraction is ours, so the
 *     traveller, not the product, is the last authority on what a line meant.
 *   the automatic day is disclosed before it happens — not adding a chosen day means the plan's own
 *     first day, and the sentence says so next to the button rather than in the result.
 *   links are named, not fetched — the parse response carries `unsupported_forms` and `link_hosts`,
 *     and the panel prints both. This is the red line: extraction is our own local channel, so a
 *     小红书 or 公众号 link is reported as unread rather than quietly dropped.
 *   加入 is not a client-side colour — after the write, the record is read back from the server and
 *     only the ids that come back are called 已加入.
 */

type Item = {
  title: string;
  note: string | null;
  char_count: number;
  status: "RESOLVED" | "AMBIGUOUS" | "UNRESOLVED";
  place_id: string | null;
  place_name: string | null;
  latitude: number | null;
  longitude: number | null;
  coordinate_system: string | null;
  matches: string[];
  addable: boolean;
};

type ParseResponse = {
  source_channel: "LOCAL_TEXT_PARSER";
  forms: string[];
  unsupported_forms: string[];
  link_hosts: string[];
  counts: Record<string, number>;
  items: Item[];
  char_count: number;
};

type AddResponse = {
  journey_id: string;
  plan_version_id: string;
  day: string;
  day_source: string;
  added: { id: string; title: string; place_id: string }[];
  already_present: string[];
  readback_path: string;
};

type Phase = "idle" | "loading" | "error" | "success";

/* ORD-0437 r4 (commander's ruling of 11:27, section 3): the two `<small>` details below used to print
   `cause.message`, and my own `call()` built that message out of the answer's body text -- so an
   upstream sentence reached the traveller twice. The house carrier is `rejectionWithFacts`: it parses
   the body for machine tokens and the contract receipt field, keeps what this device measured, and
   drops the prose. The exposure ruler counts that as 12 cells on the line and 14 on my branch; this
   edit is what brings it back to 12 by adding none. */
const REFUSAL_CODES = [
  "JOURNEY_NOT_FOUND",
  "NO_ACTIVE_PLAN",
  "IMPORT_DAY_REQUIRED",
  "IMPORT_PLACE_UNKNOWN",
  "IMPORT_PLACE_NOT_VISITABLE",
] as const;

type RefusalCode = (typeof REFUSAL_CODES)[number];

/** What the screen may show: a named condition, and this device's own reading of the status. Never a
 * sentence that arrived in the answer. */
type Failure = { code: RefusalCode | "NO_RESPONSE_FROM_ORIGIN" | "UNNAMED_REFUSAL"; status: number | null };

function describeRejection(cause: unknown): Failure {
  if (cause instanceof RejectionWithFacts) {
    const envelope = (cause.envelope as { error?: { reason_code?: string } } | null)?.error;
    const fromEnvelope = typeof envelope?.reason_code === "string" ? envelope.reason_code : null;
    const scanned = namedCodeIn(cause.message, REFUSAL_CODES);
    // `namedCodeIn` answers `string | null`; the union is what the dictionary lookup needs.
    const code: RefusalCode | null =
      (fromEnvelope && (REFUSAL_CODES as readonly string[]).includes(fromEnvelope)
        ? (fromEnvelope as RefusalCode)
        : null) ??
      ((REFUSAL_CODES as readonly string[]).includes(scanned ?? "") ? (scanned as RefusalCode) : null);
    return { code: code ?? "UNNAMED_REFUSAL", status: cause.http_status };
  }
  return { code: "NO_RESPONSE_FROM_ORIGIN", status: null };
}

/** One sentence per named condition, all of them ours. A condition with no dictionary line does not
 * get to borrow the answer's wording -- it gets `errUnnamed`, and the machine token stays visible in
 * the detail so the screen is still diagnosable. */
const FAILURE_SENTENCE: Record<Failure["code"], string> = {
  JOURNEY_NOT_FOUND: "poiImport.errJourneyNotFound",
  NO_ACTIVE_PLAN: "poiImport.errNoActivePlan",
  IMPORT_DAY_REQUIRED: "poiImport.errDayRequired",
  IMPORT_PLACE_UNKNOWN: "poiImport.errPlaceUnknown",
  IMPORT_PLACE_NOT_VISITABLE: "poiImport.errPlaceNotVisitable",
  NO_RESPONSE_FROM_ORIGIN: "poiImport.errNoResponse",
  UNNAMED_REFUSAL: "poiImport.errUnnamed",
};

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    ...init,
  });
  if (!response.ok) {
    throw await rejectionWithFacts(response);
  }
  return (await response.json()) as T;
}

export function PoiImportPanel({
  journeyId,
  firstDay = null,
  onOpenPlan,
}: {
  journeyId: string;
  /** The day the plan itself starts on: what the automatic landing would pick. */
  firstDay?: string | null;
  onOpenPlan: () => void;
}) {
  const t = useT();
  const [mode, setMode] = useState<"text" | "screenshot">("text");
  const [text, setText] = useState("");
  const [phase, setPhase] = useState<Phase>("idle");
  const [parsed, setParsed] = useState<ParseResponse | null>(null);
  const [failure, setFailure] = useState<Failure | null>(null);
  const [selected, setSelected] = useState<string[]>([]);
  const [day, setDay] = useState("");
  const [adding, setAdding] = useState(false);
  const [added, setAdded] = useState<{ ids: string[]; day: string; daySource: string } | null>(null);
  const [alreadyPresent, setAlreadyPresent] = useState<string[]>([]);
  const [readBackFailure, setReadBackFailure] = useState<Failure | "MISMATCH" | null>(null);

  const addableIds = parsed?.items.filter((i) => i.addable && i.place_id).map((i) => i.place_id as string) ?? [];
  const chosen = selected.filter((id) => addableIds.includes(id));

  const runParse = async () => {
    setPhase("loading");
    setFailure(null);
    setAdded(null);
    setAlreadyPresent([]);
    setReadBackFailure(null);
    try {
      const next = await call<ParseResponse>(`/api/v1/journeys/${journeyId}/poi-import/parse`, {
        method: "POST",
        body: JSON.stringify({ text }),
      });
      setParsed(next);
      setSelected(next.items.filter((i) => i.addable && i.place_id).map((i) => i.place_id as string));
      setPhase("success");
    } catch (cause) {
      setFailure(describeRejection(cause));
      setPhase("error");
    }
  };

  const runAdd = async () => {
    setAdding(true);
    setReadBackFailure(null);
    try {
      const written = await call<AddResponse>(`/api/v1/journeys/${journeyId}/poi-import/add`, {
        method: "POST",
        body: JSON.stringify({ place_ids: chosen, day: day || null }),
      });
      /* The write's own 201 is not what makes a place 已加入. The record has to come back from the
         server, so the ids are re-read from the projection the plan is actually drawn from. */
      const projected = await call<{ active_plan?: { activities?: { id: string }[] } | null }>(
        written.readback_path,
      );
      const serverIds = new Set((projected?.active_plan?.activities ?? []).map((a) => a.id));
      const confirmed = written.added.filter((a) => serverIds.has(a.id)).map((a) => a.id);
      if (written.added.length && confirmed.length !== written.added.length) {
        setReadBackFailure("MISMATCH");
        setAdded(null);
      } else {
        setAdded({ ids: confirmed, day: written.day, daySource: written.day_source });
      }
      setAlreadyPresent(written.already_present);
    } catch (cause) {
      setReadBackFailure(describeRejection(cause));
    } finally {
      setAdding(false);
    }
  };

  const toggle = (placeId: string) =>
    setSelected((prev) => (prev.includes(placeId) ? prev.filter((x) => x !== placeId) : [...prev, placeId]));

  const unsupportedForms = parsed?.unsupported_forms ?? [];

  return (
    <section className="v8-page" data-testid="poi-import">
      <div className="v8-page-intro compact">
        <div>
          <p className="v8-kicker">{t("poiImport.kicker")}</p>
          <h1>{t("poiImport.title")}</h1>
          <p className="v8-lede">{t("poiImport.lede")}</p>
        </div>
        <span className="v8-evidence-label">
          <span className="status-dot" />
          {t("poiImport.channelLocal")}
        </span>
      </div>

      <div className="v8-agent-composer-card">
        <div className="v8-agent-copy">
          <span className="v8-agent-mark">{t("poiImport.brand")}</span>
          <h2>{t("poiImport.modesTitle")}</h2>
          <p>{t("poiImport.modesSub")}</p>
          <div className="v8-agent-boundary">
            <b>{t("poiImport.boundary")}</b>
            <span>{t("poiImport.boundarySub")}</span>
          </div>
        </div>
        <div className="v8-agent-input">
          <div className="v8-mode-chips" role="radiogroup" aria-label={t("poiImport.modesTitle")}>
            <button
              type="button"
              role="radio"
              aria-checked={mode === "text"}
              className={mode === "text" ? "active" : ""}
              data-testid="poi-import-mode-text"
              onClick={() => setMode("text")}
            >
              {t("poiImport.modeText")}
            </button>
            <button
              type="button"
              role="radio"
              aria-checked={mode === "screenshot"}
              className={mode === "screenshot" ? "active" : ""}
              data-testid="poi-import-mode-screenshot"
              onClick={() => setMode("screenshot")}
            >
              {t("poiImport.modeScreenshot")}
            </button>
          </div>
          {mode === "screenshot" ? (
            <p className="v8-message" role="status" data-testid="poi-import-mode-unsupported">
              {t("poiImport.screenshotNotSupported")}
            </p>
          ) : (
            <>
              <label htmlFor="poi-import-text">{t("poiImport.intent")}</label>
              <textarea
                id="poi-import-text"
                data-testid="poi-import-text"
                value={text}
                placeholder={t("poiImport.placeholder")}
                onChange={(event) => setText(event.target.value)}
              />
              <p data-testid="poi-import-char-count">
                {t("poiImport.charCount", { n: text.length })}
              </p>
              {/* The reference input box states its supported scope in the hint (map_findings.md Q3:
                  小红书笔记 / 公众号内容 / 已公开权限的飞书文档). Saying it here is what keeps an
                  unread link from reading as a failure of the traveller's paste -- and the sentence has
                  to say we do not open those pages, or the list would be a promise this build breaks. */}
              <p className="v8-sheet-note" data-testid="poi-import-scope-hint">
                {t("poiImport.scopeHint")}
              </p>
            </>
          )}
          <div className="v8-agent-toolbar">
            <button
              className="v8-primary"
              data-testid="poi-import-parse"
              disabled={mode !== "text" || phase === "loading" || text.trim().length < 2}
              onClick={() => void runParse()}
            >
              {phase === "loading" ? t("poiImport.parsing") : t("poiImport.parseAction")}
            </button>
          </div>
          {/* Outside the result card on purpose: which day an import would land on has to be said
              before the traveller asks for anything, so it cannot live in a region that only exists
              after the press. ORD-0437's own gate caught it there on the first run. */}
          <p className="v8-sheet-note" data-testid="poi-import-day-disclosure">
            <b>{t("poiImport.autoDayLabel")}</b>{" "}
            {day || firstDay || t("poiImport.autoDayUnknown")} — {t("poiImport.autoDayNote")}
          </p>
          {mode === "text" && text.trim().length < 2 ? (
            <p className="v8-sheet-note">{t("poiImport.needTextHint")}</p>
          ) : null}
        </div>
      </div>

      {/* One region, three phases, and the retry control stays mounted through all of them. */}
      {phase !== "idle" ? (
        <div className="v8-intelligence-grid" data-testid="poi-import-card" data-phase={phase}>
          <article className="v8-intel-hero">
            <span className="v8-status-pill violet" data-testid="poi-import-phase">
              {phase === "loading"
                ? t("poiImport.phaseLoading")
                : phase === "error"
                  ? t("poiImport.phaseError")
                  : t("poiImport.phaseSuccess")}
            </span>
            {phase === "loading" ? (
              <p data-testid="poi-import-loading-text">{t("poiImport.loadingWhere")}</p>
            ) : null}
            {phase === "error" && failure ? (
              <p role="alert" data-testid="poi-import-error">
                {t("poiImport.loadFailed")}
                {/* The condition is this screen's own sentence. The only value painted next to it is
                    the status this device measured -- the named code stays inside the component,
                    because it is read out of the answer's envelope and the exposure rule forbids
                    anything derived from the body reaching the DOM by any route, filtering included.
                    (r7b counted my first attempt as a cell for exactly that reason.) */}
                <span data-testid="poi-import-error-why">{t(FAILURE_SENTENCE[failure.code])}</span>
                {failure.status ? (
                  <small data-testid="poi-import-error-detail">HTTP {failure.status}</small>
                ) : (
                  <small data-testid="poi-import-error-detail">{t("poiImport.errNoResponse")}</small>
                )}
              </p>
            ) : null}
            {phase === "success" ? (
              <p data-testid="poi-import-counts">
                {t("poiImport.counts", {
                  extracted: parsed?.counts.extracted ?? 0,
                  resolved: parsed?.counts.resolved ?? 0,
                  unresolved: parsed?.counts.unresolved ?? 0,
                  ambiguous: parsed?.counts.ambiguous ?? 0,
                })}
              </p>
            ) : null}
            <button
              className="v8-outline-button"
              data-testid="poi-import-retry"
              disabled={phase === "loading" || mode !== "text"}
              onClick={() => void runParse()}
            >
              {t("poiImport.retry")}
            </button>
          </article>
          <div className="v8-intel-facts">
            <div>
              <span>{t("poiImport.channelLabel")}</span>
              <b>{parsed?.source_channel ?? "LOCAL_TEXT_PARSER"}</b>
              <small>{t("poiImport.channelNote")}</small>
            </div>
            {unsupportedForms.length ? (
              <div data-testid="poi-import-unsupported">
                <span>{t("poiImport.unsupportedLabel")}</span>
                <b>{unsupportedForms.join(" · ")}</b>
                <small>
                  {parsed?.link_hosts.length
                    ? t("poiImport.unsupportedHosts", { hosts: parsed.link_hosts.join(", ") })
                    : t("poiImport.unsupportedNoFetch")}
                </small>
              </div>
            ) : null}
            <div data-testid="poi-import-day-result">
              <span>{t("poiImport.autoDayLabel")}</span>
              <b>{day || firstDay || t("poiImport.autoDayUnknown")}</b>
              <small>{t("poiImport.autoDayNote")}</small>
            </div>
          </div>
        </div>
      ) : null}

      {phase === "success" && parsed && parsed.items.length === 0 ? (
        <p className="v8-message" role="status" data-testid="poi-import-empty">
          {t("poiImport.emptyExtracted")}
        </p>
      ) : null}

      {phase === "success" && parsed && parsed.items.length > 0 ? (
        <>
          {/* Permanent while results are on screen: what was recognised still needs a human eye. */}
          <p className="v8-sheet-note" role="status" data-testid="poi-import-verify-warning">
            {t("poiImport.verifyWarning")}
          </p>
          <div className="v8-stay-layout">
            <div className="v8-stay-list" data-testid="poi-import-results">
              {parsed.items.map((item, index) => (
                <PoiCandidateCard
                  key={`${item.title}-${index}`}
                  index={index + 1}
                  phrase={item.title}
                  status={item.status}
                  placeId={item.place_id}
                  placeName={item.place_name}
                  category={null}
                  coordinateSystem={item.coordinate_system}
                  note={item.note}
                  addable={item.addable}
                  selected={!!item.place_id && selected.includes(item.place_id)}
                  onToggle={item.place_id ? () => toggle(item.place_id as string) : null}
                  ambiguousNames={item.matches}
                />
              ))}
            </div>
            <aside className="v8-boundary-card">
              <b>{t("poiImport.exitsTitle")}</b>
              <p data-testid="poi-import-selection-count">
                {t("poiImport.selectedCount", { n: chosen.length, total: addableIds.length })}
              </p>
              <label htmlFor="poi-import-day">{t("poiImport.dayLabel")}</label>
              <input
                id="poi-import-day"
                type="date"
                data-testid="poi-import-day"
                value={day}
                onChange={(event) => setDay(event.target.value)}
              />
              <button
                className="v8-primary"
                data-testid="poi-import-add"
                disabled={adding || chosen.length === 0}
                onClick={() => void runAdd()}
              >
                {adding ? t("poiImport.adding") : t("poiImport.addToPlan")}
              </button>
              {/* A touch screen never shows a tooltip, so an inert exit explained only by `title` is an
                  exit that says nothing. Both reasons are painted here instead -- and neither button is
                  enabled, because 收藏 has no door on this line and 新建计划 would mean inventing the
                  dates and budget the traveller has not given us yet. */}
              <button
                className="v8-outline-button"
                data-testid="poi-import-favorite"
                disabled
                aria-describedby="poi-import-favorite-why"
              >
                {t("poiImport.favorite")}
              </button>
              <small id="poi-import-favorite-why" data-testid="poi-import-favorite-why">
                {t("poiImport.favoriteNotWired")}
              </small>
              <button
                className="v8-quiet-button"
                data-testid="poi-import-new-journey"
                disabled
                aria-describedby="poi-import-new-journey-why"
              >
                {t("poiImport.newJourney")}
              </button>
              <small id="poi-import-new-journey-why" data-testid="poi-import-new-journey-why">
                {t("poiImport.newJourneyNotWired")}
              </small>
              <button className="v8-quiet-button" data-testid="poi-import-open-plan" onClick={onOpenPlan}>
                {t("poiImport.openPlan")}
              </button>
              {/* A replay adds nothing, so it has no right to a success sentence: this used to read
                  `added ? ...` and painted "0 places are on 2026-12-05 — read back from the server"
                  under the 本来就在 line, which is the second success the order forbids -- measured in
                  the gate's own replay arm. What a replay may say is what was already there. */}
              {added && added.ids.length > 0 ? (
                <p data-testid="poi-import-added">
                  {t("poiImport.addedCount", { n: added.ids.length, day: added.day })}
                  <small data-testid="poi-import-added-source">{added.daySource}</small>
                </p>
              ) : null}
              {alreadyPresent.length ? (
                <p data-testid="poi-import-already-present">
                  {t("poiImport.alreadyPresent", { n: alreadyPresent.length })}
                </p>
              ) : null}
              {readBackFailure ? (
                <p role="alert" data-testid="poi-import-readback-failed">
                  {readBackFailure === "MISMATCH"
                    ? t("poiImport.readBackFailed")
                    : t(FAILURE_SENTENCE[readBackFailure.code])}
                  {readBackFailure !== "MISMATCH" && readBackFailure.status ? (
                    <small data-testid="poi-import-readback-detail">HTTP {readBackFailure.status}</small>
                  ) : null}
                </p>
              ) : null}
            </aside>
          </div>
        </>
      ) : null}
    </section>
  );
}
