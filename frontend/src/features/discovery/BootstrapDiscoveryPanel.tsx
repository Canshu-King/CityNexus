import { useState } from "react";
import {
  cityNexusApi,
  type BootstrapDiscoveryCandidate,
  type BootstrapDiscoveryResponse,
} from "../../api/citynexus";

type SourceKind = "FOREGROUND_GPS" | "MANUAL_PUBLIC_CENTER";

export function BootstrapDiscoveryPanel({
  journeyId,
  cityCode,
  onCompleted,
  onCancel,
}: {
  journeyId: string;
  cityCode: string;
  onCompleted: (placeId: string) => Promise<void>;
  onCancel?: () => void;
}) {
  const [sourceKind, setSourceKind] = useState<SourceKind>("MANUAL_PUBLIC_CENTER");
  const [query, setQuery] = useState("cafe");
  const [latitude, setLatitude] = useState(39.12);
  const [longitude, setLongitude] = useState(117.20);
  const [accuracy, setAccuracy] = useState<number | undefined>();
  const [providerConsent, setProviderConsent] = useState(false);
  const [result, setResult] = useState<BootstrapDiscoveryResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [selecting, setSelecting] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const useForegroundGps = () => {
    setMessage(null);
    if (!navigator.geolocation) {
      setMessage("Foreground location is unavailable. Choose a public map center instead.");
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (position) => {
        setSourceKind("FOREGROUND_GPS");
        setLatitude(position.coords.latitude);
        setLongitude(position.coords.longitude);
        setAccuracy(position.coords.accuracy > 0 ? position.coords.accuracy : undefined);
        setMessage("Location is held for this search only; it is not saved as presence or a route origin.");
      },
      () => setMessage("Foreground location was not granted. Choose a public map center instead."),
      { enableHighAccuracy: true, maximumAge: 60_000, timeout: 8_000 },
    );
  };

  const search = async () => {
    if (!providerConsent) {
      setMessage("Confirm the OpenStreetMap/Overpass provider disclosure before searching.");
      return;
    }
    if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) {
      setMessage("Enter a valid public WGS84 search center.");
      return;
    }
    setBusy(true);
    setMessage(null);
    try {
      const next = await cityNexusApi.bootstrapDiscovery(journeyId, {
        query: query.trim() || "cafe",
        radius_m: 2500,
        limit: 3,
        source_kind: sourceKind,
        provider_consent: true,
        latitude,
        longitude,
        coordinate_system: "WGS84",
        accuracy_m: accuracy,
        mode: "live",
      });
      setResult(next);
      if (next.status === "PROVIDER_UNAVAILABLE") {
        setMessage("The public provider is unavailable. Use a public map center and try again later.");
      } else if (next.status === "PROVIDER_DISABLED") {
        setMessage("Live public discovery is unavailable in this environment. No provider request was made.");
      } else if (next.status === "LIVE_ZERO_RESULTS") {
        setMessage("No named public places were returned for that center.");
      }
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Discovery could not be completed.");
    } finally {
      setBusy(false);
    }
  };

  const selectCandidate = async (candidate: BootstrapDiscoveryCandidate) => {
    if (!result?.receipt_id) return;
    setSelecting(candidate.candidate_id);
    setMessage(null);
    try {
      const selected = await cityNexusApi.selectBootstrapCandidate(
        journeyId,
        result.receipt_id,
        candidate.candidate_id,
      );
      await onCompleted(selected.selected_place_id);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "That place is no longer selectable.");
    } finally {
      setSelecting(null);
    }
  };

  const mapFallback =
    Number.isFinite(latitude) && Number.isFinite(longitude)
      ? `https://www.openstreetmap.org/?mlat=${encodeURIComponent(latitude)}&mlon=${encodeURIComponent(longitude)}#map=16/${encodeURIComponent(latitude)}/${encodeURIComponent(longitude)}`
      : "https://www.openstreetmap.org/";

  return (
    <main className="v8-join-entry" data-testid="bootstrap-discovery">
      <section className="v8-loading" aria-labelledby="bootstrap-discovery-title">
        <div className="v8-brand-mark">CN</div>
        <h1 id="bootstrap-discovery-title">Discover your first public place</h1>
        <p>
          This new {cityCode} Journey is still a draft with no plan. Search one public center,
          review source-linked results, then choose exactly one place.
        </p>
        <p>
          A manual center is only a public search center. It never becomes your GPS observation,
          group presence, or route origin. Opening hours, price, and ETA remain UNKNOWN until evidence exists.
        </p>
        <div className="v8-actions">
          <button
            type="button"
            data-testid="bootstrap-source-manual"
            aria-pressed={sourceKind === "MANUAL_PUBLIC_CENTER"}
            onClick={() => setSourceKind("MANUAL_PUBLIC_CENTER")}
          >
            Use public map center
          </button>
          <button
            type="button"
            data-testid="bootstrap-source-gps"
            aria-pressed={sourceKind === "FOREGROUND_GPS"}
            onClick={useForegroundGps}
          >
            Use foreground GPS
          </button>
        </div>
        <label>
          Public place query
          <input
            data-testid="bootstrap-query"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            maxLength={120}
          />
        </label>
        <div className="v8-form-grid">
          <label>
            Latitude (WGS84)
            <input
              data-testid="bootstrap-latitude"
              inputMode="decimal"
              value={latitude}
              onChange={(event) => setLatitude(Number(event.target.value))}
            />
          </label>
          <label>
            Longitude (WGS84)
            <input
              data-testid="bootstrap-longitude"
              inputMode="decimal"
              value={longitude}
              onChange={(event) => setLongitude(Number(event.target.value))}
            />
          </label>
        </div>
        <label>
          <input
            type="checkbox"
            data-testid="bootstrap-provider-consent"
            checked={providerConsent}
            onChange={(event) => setProviderConsent(event.target.checked)}
          />
          I understand that this search sends the query and public center to OpenStreetMap/Overpass.
        </label>
        <div className="v8-actions">
          <button type="button" data-testid="bootstrap-search" disabled={busy} onClick={() => void search()}>
            {busy ? "Searching…" : "Search public places"}
          </button>
          {onCancel ? (
            <button type="button" data-testid="bootstrap-cancel" onClick={onCancel} disabled={busy}>
              Cancel
            </button>
          ) : null}
        </div>
        {message ? <p role="status">{message}</p> : null}
        {result?.status === "PROVIDER_UNAVAILABLE" || result?.status === "PROVIDER_DISABLED" ? (
          <p>
            <a href={mapFallback} target="_blank" rel="noreferrer" data-testid="bootstrap-map-fallback">
              Open a public map fallback
            </a>
          </p>
        ) : null}
        {result?.candidates?.length ? (
          <div data-testid="bootstrap-results">
            <h2>Source-linked public candidates</h2>
            {result.candidates.slice(0, 3).map((candidate) => (
              <article key={candidate.candidate_id} data-testid={`bootstrap-candidate-${candidate.candidate_id}`}>
                <h3>{candidate.name}</h3>
                <p>
                  {candidate.category} · opening {candidate.opening_state} · price UNKNOWN · ETA UNKNOWN
                </p>
                {candidate.selection_state !== "READY_FOR_NATIVE_PLAN" ? (
                  <p role="status" data-testid={`bootstrap-opening-blocker-${candidate.candidate_id}`}>
                    OpenStreetMap did not provide grounded opening hours for this place. Verify the
                    source below, then search again, or choose another candidate before starting a Journey.
                  </p>
                ) : null}
                <p>
                  {candidate.source_url ? (
                    <a href={candidate.source_url} target="_blank" rel="noreferrer">
                      OpenStreetMap source
                    </a>
                  ) : null}
                </p>
                <button
                  type="button"
                  data-testid={`bootstrap-select-${candidate.candidate_id}`}
                  disabled={selecting !== null || candidate.selection_state !== "READY_FOR_NATIVE_PLAN"}
                  onClick={() => void selectCandidate(candidate)}
                >
                  {selecting === candidate.candidate_id
                    ? "Adding…"
                    : candidate.selection_state === "READY_FOR_NATIVE_PLAN"
                      ? "Choose this place"
                      : "Verify opening hours first"}
                </button>
              </article>
            ))}
          </div>
        ) : null}
      </section>
    </main>
  );
}
