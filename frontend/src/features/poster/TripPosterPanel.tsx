/**
 * ORD-0472 — the trip poster entry, and the sheet it opens.
 *
 * One quiet bar at the top of the Trips > Itinerary screen. Pressing it opens the poster sheet,
 * which shows what the picture will contain: the trip's own title, its city, the day count the
 * panel already quotes, every stop on its own day with the times the panel already prints, and the
 * attribution line the map carries.
 *
 * The bar renders only when a plan with at least one stop exists, so the sheet can never open onto
 * an empty poster. The drawing lives in `posterCanvas.ts`.
 */
import { useMemo, useState } from "react";
import { useLocale } from "../../i18n/LocaleContext";
import { progressContractCopy } from "../progress/journeyProgress";
import { buildTripPoster } from "./posterModel";
import type { V8Data } from "../../app/v8Types";
import "./trip-poster.css";

export function TripPosterPanel({ data }: { data: V8Data }) {
  const { locale, t } = useLocale();
  const [open, setOpen] = useState(false);
  const poster = useMemo(() => buildTripPoster(data, locale), [data, locale]);

  if (!poster) return null;

  const zh = locale.startsWith("zh");

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
        <section className="v8-page cn-poster" data-testid="trip-poster">
          <div className="v8-page-intro compact">
            <div>
              <p className="v8-kicker">{t("poster.kicker")}</p>
              <h1 data-testid="poster-title">{poster.title}</h1>
              <p className="v8-lede" data-testid="poster-subtitle">
                {poster.dayTotal === null
                  ? t("poster.daysUnknown", { city: poster.city })
                  : t("poster.cityAndDays", { city: poster.city, days: poster.dayTotal })}
              </p>
              <p className="v8-lede" data-testid="poster-progress">
                {progressContractCopy(poster.progress, zh)}
              </p>
            </div>
          </div>

          <ol className="cn-poster-days" data-testid="poster-days">
            {poster.days.map((day, index) => (
              <li className="cn-poster-day" key={day.key} data-testid={`poster-day-${index + 1}`}>
                <div className="cn-poster-day-head">
                  <b>{day.label}</b>
                  <small>{t("poster.dayStops", { n: day.stops.length })}</small>
                </div>
                <ul className="cn-poster-stops">
                  {day.stops.map((stop, stopIndex) => (
                    <li
                      className="cn-poster-stop"
                      key={`${day.key}-${stopIndex}`}
                      data-testid="poster-stop"
                    >
                      <time className="cn-poster-stop-time">{`${stop.from} – ${stop.to}`}</time>
                      <span className="cn-poster-stop-title">{stop.title}</span>
                    </li>
                  ))}
                </ul>
              </li>
            ))}
          </ol>

          <p className="cn-poster-attribution" data-testid="poster-attribution">
            {t("poster.attributionLabel")} · {t("mapComp.attribution")}
          </p>
        </section>
      )}
    </>
  );
}
