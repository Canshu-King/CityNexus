/**
 * ORD-0472 — the trip poster entry, and the sheet it opens.
 *
 * One quiet bar at the top of the Trips > Itinerary screen. Pressing it opens the poster sheet, which
 * shows what the picture contains -- the trip's own title, its city, the day count the panel already
 * quotes, every stop on its own day with the times the panel already prints, and the attribution line
 * the map carries. Pressing it again draws that same list onto a canvas and hands back one PNG.
 *
 * The bar renders only when a plan with at least one stop exists, so the sheet can never open onto an
 * empty poster. The list the sheet renders and the list the canvas draws are the same value, built
 * once here: a picture of something else than the traveller is reading would be a second answer.
 */
import { useMemo, useRef, useState } from "react";
import { useLocale } from "../../i18n/LocaleContext";
import { progressContractCopy } from "../progress/journeyProgress";
import {
  drawTripPoster,
  savePosterBlob,
  type PosterFailureStep,
  type PosterLines,
} from "./posterCanvas";
import { buildTripPoster } from "./posterModel";
import type { V8Data } from "../../app/v8Types";
import "./trip-poster.css";

const POSTER_FILE_NAME = "citynexus-trip-poster.png";

/* Which sentence each step answers, spelled out rather than built from the step name: `t()` returns
   the key itself when a key is missing, so a composed key could put `poster.fail.MissingTokens` on
   the screen. Written as a table, the compiler checks every step has words and none of them can leak.

   The drawing layer's own `detail` (a byte count, `null`, a pixel width) is deliberately not
   rendered and not put in the DOM at all: the line a traveller reads is the dictionary sentence and
   nothing else, which is what the Q64 arm caught me breaking -- the first version appended
   ` · null` to "长图没有生成：画布没有交出 PNG 字节。". The detail still comes back on the result
   object for whoever instruments the canvas, it just never reaches the screen. */
const FAILURE_COPY: Record<PosterFailureStep, string> = {
  NoCanvasContext: "poster.fail.noCanvas",
  NoMeasuredWidth: "poster.fail.noWidth",
  MissingTokens: "poster.fail.missingTokens",
  BlankAfterDraw: "poster.fail.blank",
  NoPngBytes: "poster.fail.noBytes",
  NoDownloadRoute: "poster.fail.noDownload",
};

type DrawState =
  | { phase: "idle" }
  | { phase: "working" }
  | { phase: "made"; bytes: number; width: number; height: number }
  | { phase: "failed"; step: PosterFailureStep };

export function TripPosterPanel({ data }: { data: V8Data }) {
  const { locale, t } = useLocale();
  const [open, setOpen] = useState(false);
  const [state, setState] = useState<DrawState>({ phase: "idle" });
  const sheet = useRef<HTMLElement | null>(null);

  const poster = useMemo(() => buildTripPoster(data, locale), [data, locale]);

  /* One value for the screen and for the picture. Every string here is what the DOM already shows. */
  const lines = useMemo<PosterLines | null>(() => {
    if (!poster) return null;
    const zh = locale.startsWith("zh");
    return {
      kicker: t("poster.kicker"),
      title: poster.title,
      subtitle:
        poster.dayTotal === null
          ? t("poster.daysUnknown", { city: poster.city })
          : t("poster.cityAndDays", { city: poster.city, days: poster.dayTotal }),
      progress: progressContractCopy(poster.progress, zh),
      attribution: `${t("poster.attributionLabel")} · ${t("mapComp.attribution")}`,
      days: poster.days.map((day) => ({
        label: day.label,
        count: t("poster.dayStops", { n: day.stops.length }),
        stops: day.stops.map((stop) => ({
          time: `${stop.from} – ${stop.to}`,
          title: stop.title,
        })),
      })),
    };
  }, [poster, locale, t]);

  if (!poster || !lines) return null;

  const makePoster = async () => {
    setState({ phase: "working" });
    const measuredWidth = sheet.current ? sheet.current.getBoundingClientRect().width : 0;
    const result = await drawTripPoster(lines, measuredWidth);
    /* Tested by which arm the value carries rather than by `ok`, because this project type-checks
       with `strict: false` (`tsconfig.typecheck.json:2`) and a boolean discriminant does not narrow
       a union here -- the failure fields would read as missing. */
    if ("step" in result) {
      setState({ phase: "failed", step: result.step });
      return;
    }
    if (!savePosterBlob(result.blob, POSTER_FILE_NAME)) {
      setState({ phase: "failed", step: "NoDownloadRoute", detail: "" });
      return;
    }
    setState({
      phase: "made",
      bytes: result.blob.size,
      width: result.width,
      height: result.height,
    });
  };

  return (
    <>
      <div className="cn-poster-bar" data-testid="trip-poster-bar">
        <p className="cn-poster-bar-note">{t("poster.barNote")}</p>
        <button
          type="button"
          className="cn-poster-open"
          data-testid="poster-open"
          data-contrast-role="control"
          aria-expanded={open}
          onClick={() => setOpen((next) => !next)}
        >
          {open ? t("poster.close") : t("poster.action")}
        </button>
      </div>

      {open && (
        <section className="v8-page cn-poster" data-testid="trip-poster" ref={sheet}>
          <div className="v8-page-intro compact">
            <div>
              <p className="v8-kicker">{lines.kicker}</p>
              <h1 data-testid="poster-title">{lines.title}</h1>
              <p className="v8-lede" data-testid="poster-subtitle">
                {lines.subtitle}
              </p>
              <p className="v8-lede" data-testid="poster-progress">
                {lines.progress}
              </p>
            </div>
          </div>

          <ol className="cn-poster-days" data-testid="poster-days">
            {lines.days.map((day, index) => (
              <li className="cn-poster-day" key={`${day.label}-${index}`} data-testid={`poster-day-${index + 1}`}>
                <div className="cn-poster-day-head">
                  <b>{day.label}</b>
                  <small>{day.count}</small>
                </div>
                <ul className="cn-poster-stops">
                  {day.stops.map((stop, stopIndex) => (
                    <li
                      className="cn-poster-stop"
                      key={`${day.label}-${stopIndex}`}
                      data-testid="poster-stop"
                    >
                      <time className="cn-poster-stop-time">{stop.time}</time>
                      <span className="cn-poster-stop-title">{stop.title}</span>
                    </li>
                  ))}
                </ul>
              </li>
            ))}
          </ol>

          <p className="cn-poster-attribution" data-testid="poster-attribution">
            {lines.attribution}
          </p>

          <button
            type="button"
            className="v8-primary-button cn-poster-download"
            data-testid="poster-download"
            data-contrast-role="control"
            disabled={state.phase === "working"}
            onClick={() => {
              void makePoster();
            }}
          >
            {state.phase === "working" ? t("poster.working") : t("poster.download")}
          </button>

          {state.phase === "made" && (
            <p className="cn-poster-outcome" data-testid="poster-result" data-state="made">
              {t("poster.made", {
                bytes: state.bytes,
                width: state.width,
                height: state.height,
              })}
            </p>
          )}
          {state.phase === "failed" && (
            <p
              className="cn-poster-outcome cn-poster-outcome--failed"
              data-testid="poster-result"
              data-state="failed"
            >
              {`${t("poster.failPrefix")}${t(FAILURE_COPY[state.step])}`}
            </p>
          )}
        </section>
      )}
    </>
  );
}
