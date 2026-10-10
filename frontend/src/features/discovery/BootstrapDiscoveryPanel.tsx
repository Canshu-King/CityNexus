import { useEffect, useState } from "react";
import {
  cityNexusApi,
  type BootstrapDiscoveryCandidate,
  type BootstrapMapPreviewResponse,
  type BootstrapDiscoveryResponse,
  type BootstrapShortlistItem,
  type BootstrapShortlistResumeIntent,
  type BootstrapShortlistPreviewResponse,
} from "../../api/citynexus";
import { readTravelerBearer } from "../../lib/travelerSession";

type SourceKind = "FOREGROUND_GPS" | "MANUAL_PUBLIC_CENTER";
type PendingMapPreview = {
  kind: "candidate" | "shortlist";
  purpose: "PIN" | "WALKING";
  candidateId?: string;
  shortlistId?: string;
  receiptId?: string;
  latitude: number;
  longitude: number;
};

function safeHttpsSourceUrl(value: string | undefined): string | null {
  if (!value) return null;
  try {
    const url = new URL(value);
    if (url.protocol !== "https:" || !url.hostname || url.username || url.password) return null;
    return url.toString();
  } catch {
    return null;
  }
}

function validatedPublicMapUrl(value: string | undefined, expectedLatitude: number, expectedLongitude: number): string | null {
  if (!value) return null;
  try {
    const url = new URL(value);
    const queryKeys = [...url.searchParams.keys()];
    const latitudeFromQuery = Number(url.searchParams.get("mlat"));
    const longitudeFromQuery = Number(url.searchParams.get("mlon"));
    const hashParts = url.hash.match(/^#map=([^/]+)\/([^/]+)\/([^/]+)$/);
    const zoomFromHash = hashParts ? Number(hashParts[1]) : NaN;
    const latitudeFromHash = hashParts ? Number(hashParts[2]) : NaN;
    const longitudeFromHash = hashParts ? Number(hashParts[3]) : NaN;
    if (
      url.protocol !== "https:" ||
      url.hostname !== "www.openstreetmap.org" ||
      url.pathname !== "/" ||
      url.port !== "" ||
      url.username !== "" ||
      url.password !== "" ||
      queryKeys.some((key) => key !== "mlat" && key !== "mlon") ||
      queryKeys.length !== 2 ||
      url.searchParams.getAll("mlat").length !== 1 ||
      url.searchParams.getAll("mlon").length !== 1 ||
      !Number.isFinite(latitudeFromQuery) ||
      !Number.isFinite(longitudeFromQuery) ||
      !hashParts ||
      !Number.isFinite(zoomFromHash) ||
      !Number.isFinite(latitudeFromHash) ||
      !Number.isFinite(longitudeFromHash) ||
      Math.abs(latitudeFromQuery - expectedLatitude) > 1e-6 ||
      Math.abs(longitudeFromQuery - expectedLongitude) > 1e-6 ||
      Math.abs(latitudeFromHash - expectedLatitude) > 1e-6 ||
      Math.abs(longitudeFromHash - expectedLongitude) > 1e-6
    ) {
      return null;
    }
    return url.toString();
  } catch {
    return null;
  }
}

function validatedPublicWalkingUrl(value: string | null | undefined, expectedLatitude: number, expectedLongitude: number): string | null {
  if (!value) return null;
  try {
    const url = new URL(value);
    const keys = [...url.searchParams.keys()];
    const destination = url.searchParams.get("destination")?.split(",") ?? [];
    const latitude = Number(destination[0]);
    const longitude = Number(destination[1]);
    if (
      url.protocol !== "https:" ||
      url.hostname !== "www.google.com" ||
      url.pathname !== "/maps/dir/" ||
      url.port !== "" ||
      url.username !== "" ||
      url.password !== "" ||
      keys.length !== 3 ||
      keys.some((key) => !["api", "destination", "travelmode"].includes(key)) ||
      url.searchParams.getAll("destination").length !== 1 ||
      url.searchParams.get("api") !== "1" ||
      url.searchParams.get("travelmode") !== "walking" ||
      destination.length !== 2 ||
      !Number.isFinite(latitude) ||
      !Number.isFinite(longitude) ||
      Math.abs(latitude - expectedLatitude) > 1e-6 ||
      Math.abs(longitude - expectedLongitude) > 1e-6
    ) {
      return null;
    }
    return url.toString();
  } catch {
    return null;
  }
}

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
  const [pendingMapPreview, setPendingMapPreview] = useState<PendingMapPreview | null>(null);
  const [mapConsent, setMapConsent] = useState(false);
  const [mapBusy, setMapBusy] = useState(false);
  const [exploreNotice, setExploreNotice] = useState<string | null>(null);
  const [mapFallbackUrl, setMapFallbackUrl] = useState<string | null>(null);
  const [lastNavigationLaunched, setLastNavigationLaunched] = useState(false);
  const [shortlist, setShortlist] = useState<BootstrapShortlistItem[]>([]);
  const [shortlistLoading, setShortlistLoading] = useState(true);
  const [shortlistBusy, setShortlistBusy] = useState<string | null>(null);
  const [resumeIntent, setResumeIntent] = useState<BootstrapShortlistResumeIntent | null>(null);
  const travelerBearer = readTravelerBearer();

  useEffect(() => {
    let active = true;
    setShortlist([]);
    setResumeIntent(null);
    setPendingMapPreview(null);
    setMapConsent(false);
    setMapFallbackUrl(null);
    setLastNavigationLaunched(false);
    setExploreNotice(null);
    setShortlistLoading(true);
    const loadShortlist = async (initial = false) => {
      if (initial) setShortlistLoading(true);
      try {
        const saved = await cityNexusApi.getBootstrapShortlist(journeyId);
        if (!active) return;
        const restorable = saved.resume && saved.items.some((item) => item.shortlist_id === saved.resume?.shortlist_id)
          ? saved.resume
          : null;
        setShortlist(saved.items);
        setResumeIntent(restorable);
      } catch {
        // A draft without a signed member simply has no restorable board yet.
        if (active) {
          setShortlist([]);
          setResumeIntent(null);
          setPendingMapPreview(null);
          setMapConsent(false);
          setMapFallbackUrl(null);
          setLastNavigationLaunched(false);
          setExploreNotice(null);
        }
      } finally {
        if (active && initial) setShortlistLoading(false);
      }
    };
    void loadShortlist(true);
    const refreshOnReturn = () => {
      if (readTravelerBearer() !== travelerBearer) {
        setPendingMapPreview(null);
        setMapConsent(false);
        setMapFallbackUrl(null);
        setLastNavigationLaunched(false);
        setExploreNotice(null);
      }
      if (document.visibilityState === "visible") void loadShortlist(false);
    };
    document.addEventListener("visibilitychange", refreshOnReturn);
    window.addEventListener("focus", refreshOnReturn);
    return () => {
      active = false;
      document.removeEventListener("visibilitychange", refreshOnReturn);
      window.removeEventListener("focus", refreshOnReturn);
    };
  }, [journeyId, travelerBearer]);

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
      setPendingMapPreview(null);
      setMapConsent(false);
      setExploreNotice(null);
      setMapFallbackUrl(null);
      setLastNavigationLaunched(false);
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

  const saveCandidate = async (candidate: BootstrapDiscoveryCandidate) => {
    if (!result?.receipt_id) {
      setMessage("Search again before saving a public place.");
      return;
    }
    if (shortlist.some((item) => item.external_id === candidate.external_id)) return;
    if (shortlist.length >= 3) {
      setMessage("Your private draft shortlist already has three places. Remove one before saving another.");
      return;
    }
    setShortlistBusy(candidate.candidate_id);
    setMessage(null);
    try {
      const saved = await cityNexusApi.saveBootstrapShortlistItem(journeyId, {
        receipt_id: result.receipt_id,
        candidate_id: candidate.candidate_id,
      });
      setShortlist((items) => items.some((item) => item.shortlist_id === saved.shortlist_id) ? items : [...items, saved]);
      setExploreNotice("Saved to your private draft shortlist. This is not a Place, PlanVersion, visit, booking, or payment authorization.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "This public place could not be saved.");
    } finally {
      setShortlistBusy(null);
    }
  };

  const removeShortlistItem = async (item: BootstrapShortlistItem) => {
    setShortlistBusy(item.shortlist_id);
    setMessage(null);
    try {
      await cityNexusApi.removeBootstrapShortlistItem(journeyId, item.shortlist_id);
      if (pendingMapPreview?.shortlistId === item.shortlist_id) cancelMapPreview();
      setShortlist((items) => items.filter((saved) => saved.shortlist_id !== item.shortlist_id));
      if (resumeIntent?.shortlist_id === item.shortlist_id) setResumeIntent(null);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "That saved place could not be removed.");
    } finally {
      setShortlistBusy(null);
    }
  };

  const beginMapPreview = (candidate: BootstrapDiscoveryCandidate) => {
    if (!result?.receipt_id) {
      setMessage("Search again before opening a public map preview.");
      return;
    }
    setMessage(null);
    setExploreNotice(null);
    setMapFallbackUrl(null);
    setLastNavigationLaunched(false);
    setMapConsent(false);
    setPendingMapPreview({
      kind: "candidate",
      purpose: "PIN",
      candidateId: candidate.candidate_id,
      receiptId: result.receipt_id,
      latitude: candidate.latitude,
      longitude: candidate.longitude,
    });
  };

  const rememberAndBeginShortlistPreview = async (
    item: Pick<BootstrapShortlistItem, "shortlist_id" | "latitude" | "longitude"> | BootstrapShortlistResumeIntent,
    purpose: "PIN" | "WALKING",
  ) => {
    setMessage(null);
    setExploreNotice(null);
    setMapFallbackUrl(null);
    setLastNavigationLaunched(false);
    setMapConsent(false);
    try {
      const remembered = await cityNexusApi.rememberBootstrapShortlistItem(journeyId, item.shortlist_id);
      setResumeIntent(remembered);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "This saved place could not be resumed.");
      return;
    }
    setPendingMapPreview({
      kind: "shortlist",
      purpose,
      shortlistId: item.shortlist_id,
      latitude: item.latitude,
      longitude: item.longitude,
    });
  };

  const beginShortlistMapPreview = (item: BootstrapShortlistItem) => {
    void rememberAndBeginShortlistPreview(item, "PIN");
  };

  const beginShortlistNavigation = (item: BootstrapShortlistItem) => {
    void rememberAndBeginShortlistPreview(item, "WALKING");
  };

  const cancelMapPreview = () => {
    setPendingMapPreview(null);
    setMapConsent(false);
  };

  const confirmMapPreview = async () => {
    if (!pendingMapPreview) return;
    if (!mapConsent) {
      setMessage("Confirm this one-time public map release before opening it.");
      return;
    }
    if (pendingMapPreview.kind === "candidate") {
      const current = result?.candidates.find((item) => item.candidate_id === pendingMapPreview.candidateId);
      if (
        !current ||
        !result?.receipt_id ||
        result.receipt_id !== pendingMapPreview.receiptId ||
        current.latitude !== pendingMapPreview.latitude ||
        current.longitude !== pendingMapPreview.longitude
      ) {
        cancelMapPreview();
        setMessage("This map preview is stale. Search again and choose the candidate again.");
        return;
      }
    } else {
      const saved = shortlist.find((item) => item.shortlist_id === pendingMapPreview.shortlistId);
      if (!saved || saved.latitude !== pendingMapPreview.latitude || saved.longitude !== pendingMapPreview.longitude) {
        cancelMapPreview();
        setMessage("This saved map destination changed. Reload the private shortlist and try again.");
        return;
      }
    }
    setMapBusy(true);
    setMessage(null);
    setMapFallbackUrl(null);
    // Reserve a tab while this click still has user activation.  Mobile browsers
    // may reject a later async window.open after the receipt request completes.
    const pendingWindow = window.open("about:blank", "_blank");
    try {
      if (pendingWindow) pendingWindow.opener = null;
    } catch {
      // The opener relationship is advisory; the destination is still validated below.
    }
    let openedAutomatically = false;
    try {
      const released: BootstrapMapPreviewResponse | BootstrapShortlistPreviewResponse = pendingMapPreview.kind === "candidate"
        ? await cityNexusApi.previewBootstrapCandidate(journeyId, {
            receipt_id: pendingMapPreview.receiptId!,
            candidate_id: pendingMapPreview.candidateId!,
            public_map_consent: true,
            latitude: pendingMapPreview.latitude,
            longitude: pendingMapPreview.longitude,
            coordinate_system: "WGS84",
          })
        : pendingMapPreview.purpose === "WALKING"
          ? await cityNexusApi.navigateBootstrapShortlistItem(journeyId, pendingMapPreview.shortlistId!)
          : await cityNexusApi.previewBootstrapShortlistItem(journeyId, pendingMapPreview.shortlistId!);
      const publicMapUrl = pendingMapPreview.purpose === "WALKING"
        ? validatedPublicWalkingUrl(
            "navigation_url" in released ? released.navigation_url : null,
            pendingMapPreview.latitude,
            pendingMapPreview.longitude,
          )
        : validatedPublicMapUrl(
            released.destination.map_url,
            pendingMapPreview.latitude,
            pendingMapPreview.longitude,
          );
      if (
        (pendingMapPreview.kind === "candidate" &&
          (!("receipt_id" in released) ||
            !("candidate_id" in released) ||
            released.receipt_id !== pendingMapPreview.receiptId ||
            released.candidate_id !== pendingMapPreview.candidateId)) ||
        (pendingMapPreview.kind === "shortlist" &&
          (!("shortlist_id" in released) ||
            !("authorization_basis" in released) ||
            released.shortlist_id !== pendingMapPreview.shortlistId ||
            released.authorization_basis !== "SAVED_PUBLIC_IDENTITY")) ||
        (pendingMapPreview.purpose === "WALKING" &&
          (!("navigation_mode" in released) || released.navigation_mode !== "WALKING_DIRECTIONS")) ||
        (pendingMapPreview.purpose === "PIN" && pendingMapPreview.kind === "shortlist" &&
          (!("navigation_mode" in released) || released.navigation_mode !== "PUBLIC_PIN")) ||
        Math.abs(released.destination.latitude - pendingMapPreview.latitude) > 1e-6 ||
        Math.abs(released.destination.longitude - pendingMapPreview.longitude) > 1e-6 ||
        !publicMapUrl
      ) {
        try {
          pendingWindow?.close();
        } catch {
          // A browser may have already reclaimed the pre-opened tab.
        }
        throw new Error("The authorized public map destination did not match this candidate; release cancelled.");
      }
      if (pendingWindow && !pendingWindow.closed) {
        try {
          pendingWindow.location.replace(publicMapUrl);
          openedAutomatically = true;
        } catch {
          setMapFallbackUrl(publicMapUrl);
        }
      } else {
        setMapFallbackUrl(publicMapUrl);
      }
      setLastNavigationLaunched(pendingMapPreview.purpose === "WALKING");
      setExploreNotice(
        (openedAutomatically
          ? (pendingMapPreview.purpose === "WALKING" ? "Destination-only walking directions opened. " : "Public destination opened. ")
          : "Your browser blocked the automatic tab. Use the authorized destination link below. ") +
          "Explore first: no Place, PlanVersion, route ETA, arrival, booking, or Journey start was created. Opening is still " +
          (released.opening.verification_state === "EXTERNAL_NOT_ATTESTED" ? "EXTERNAL_NOT_ATTESTED." : "provider-grounded, not freshly rechecked."),
      );
      cancelMapPreview();
    } catch (error) {
      try {
        pendingWindow?.close();
      } catch {
        // A browser may have already reclaimed the pre-opened tab.
      }
      cancelMapPreview();
      setMessage(error instanceof Error ? error.message : "The public map release was cancelled.");
    } finally {
      setMapBusy(false);
    }
  };

  const continueExploring = () => {
    cancelMapPreview();
    setMessage(null);
    setExploreNotice("Continue exploring without committing: this draft has no Place or PlanVersion. Search another candidate when ready.");
  };

  const scrollToShortlist = () => {
    document.querySelector('[data-testid="bootstrap-shortlist"]')?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  const mapFallback =
    sourceKind === "MANUAL_PUBLIC_CENTER" && Number.isFinite(latitude) && Number.isFinite(longitude)
      ? `https://www.openstreetmap.org/?mlat=${encodeURIComponent(latitude)}&mlon=${encodeURIComponent(longitude)}#map=16/${encodeURIComponent(latitude)}/${encodeURIComponent(longitude)}`
      : null;

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
        {resumeIntent ? (
          <section data-testid="bootstrap-resume" aria-labelledby="bootstrap-resume-title">
            <h2 id="bootstrap-resume-title">Continue exploring</h2>
            <p>
              Last chosen public place: <strong>{resumeIntent.name}</strong>. This is a private draft resume
              pointer, not a route, GPS trace, arrival, or visit record. Returning to CityNexus only means the
              app was opened again; physical arrival remains unverified.
            </p>
            <p>
              {safeHttpsSourceUrl(resumeIntent.source_url) ? (
                <a href={safeHttpsSourceUrl(resumeIntent.source_url)!} target="_blank" rel="noopener noreferrer" data-testid="bootstrap-resume-source">
                  Inspect source for {resumeIntent.name}
                </a>
              ) : null}
            </p>
            <div className="v8-actions">
              <button
                type="button"
                data-testid="bootstrap-resume-map"
                disabled={mapBusy}
                onClick={() => void rememberAndBeginShortlistPreview(resumeIntent, "PIN")}
              >
                Inspect public map again
              </button>
              <button
                type="button"
                data-testid="bootstrap-resume-walking"
                disabled={mapBusy}
                onClick={() => void rememberAndBeginShortlistPreview(resumeIntent, "WALKING")}
              >
                Open walking directions again
              </button>
              <button type="button" data-testid="bootstrap-resume-choose-another" onClick={scrollToShortlist}>
                Choose another saved place
              </button>
              {onCancel ? (
                <button type="button" data-testid="bootstrap-resume-back-to-journey" onClick={onCancel}>
                  Back to Journey draft
                </button>
              ) : null}
            </div>
          </section>
        ) : null}
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
        {exploreNotice ? (
          <>
            <p role="status" data-testid="bootstrap-explore-state">
              {exploreNotice}
            </p>
            {lastNavigationLaunched ? (
              <button
                type="button"
                data-testid="bootstrap-back-to-board"
                onClick={() => {
                  setLastNavigationLaunched(false);
                  document.querySelector('[data-testid="bootstrap-shortlist"]')?.scrollIntoView({ behavior: "smooth", block: "start" });
                }}
              >
                Back to exploration board
              </button>
            ) : null}
          </>
        ) : null}
        {mapFallbackUrl ? (
          <p>
            <a
              href={mapFallbackUrl}
              target="_blank"
              rel="noopener noreferrer"
              data-testid="bootstrap-authorized-map-fallback"
            >
              Open authorized public map
            </a>
          </p>
        ) : null}
        {mapFallback && (result?.status === "PROVIDER_UNAVAILABLE" || result?.status === "PROVIDER_DISABLED") ? (
          <p>
            <a href={mapFallback} target="_blank" rel="noopener noreferrer" data-testid="bootstrap-map-fallback">
              Open the public search center on a map
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
                    Opening is not independently verified. Verify the source, preview the public map, inspect the source,
                    or continue exploring; this candidate cannot start a Journey yet.
                  </p>
                ) : null}
                <p>
                  {candidate.source_url ? (
                    <a
                      href={candidate.source_url}
                      target="_blank"
                      rel="noreferrer"
                      data-testid={`bootstrap-source-${candidate.candidate_id}`}
                    >
                      Open public source to verify
                    </a>
                  ) : null}
                </p>
                <div data-testid={`bootstrap-source-facts-${candidate.candidate_id}`}>
                  <p>
                    Source identity: {candidate.opening_source ?? "OpenStreetMap/Overpass"} · {candidate.external_id} · observed {candidate.opening_observed_at ?? "unknown"}
                  </p>
                  <p>
                    Opening evidence: {candidate.opening_claim ?? "NO_OPENING_TAG"} · {candidate.opening_verification_state === "PROVIDER_GROUNDED" ? "provider-grounded, not freshly rechecked" : "EXTERNAL_NOT_ATTESTED"}
                  </p>
                  {candidate.opening_hours?.raw ? <p>OSM opening_hours: {String(candidate.opening_hours.raw)}</p> : null}
                  {Object.entries(candidate.source_tags ?? {}).map(([key, value]) => {
                    const safeUrl = ["website", "contact:website"].includes(key)
                      ? safeHttpsSourceUrl(value)
                      : null;
                    return (
                      <p key={key}>
                        {key}: {value}{" "}
                        {safeUrl ? (
                          <a href={safeUrl} target="_blank" rel="noopener noreferrer">
                            Open unverified OSM-provided site
                          </a>
                        ) : null}
                      </p>
                    );
                  })}
                </div>
                <button
                  type="button"
                  data-testid={`bootstrap-map-preview-${candidate.candidate_id}`}
                  disabled={selecting !== null || mapBusy}
                  onClick={() => beginMapPreview(candidate)}
                >
                  Preview on public map
                </button>
                <button
                  type="button"
                  data-testid={`bootstrap-save-${candidate.candidate_id}`}
                  disabled={shortlistBusy !== null || shortlist.some((item) => item.external_id === candidate.external_id) || shortlist.length >= 3}
                  onClick={() => void saveCandidate(candidate)}
                >
                  {shortlist.some((item) => item.external_id === candidate.external_id)
                    ? "Saved to private shortlist"
                    : shortlistBusy === candidate.candidate_id
                      ? "Saving…"
                      : "Save to private shortlist"}
                </button>
                {pendingMapPreview?.candidateId === candidate.candidate_id && pendingMapPreview.kind === "candidate" ? (
                  <div className="journey-membership-map-consent" data-testid={`bootstrap-map-consent-${candidate.candidate_id}`}>
                    <p>
                      One-time consent: share only this public destination with OpenStreetMap. No saved origin,
                      query center, or precise foreground GPS will be sent to the map.
                    </p>
                    <label>
                      <input
                        type="checkbox"
                        data-testid="bootstrap-map-consent-checkbox"
                        checked={mapConsent}
                        onChange={(event) => setMapConsent(event.target.checked)}
                      />
                      I agree to open this public destination now.
                    </label>
                    <div className="v8-actions">
                      <button
                        type="button"
                        data-testid="bootstrap-map-preview-confirm"
                        disabled={!mapConsent || mapBusy}
                        onClick={() => void confirmMapPreview()}
                      >
                        {mapBusy ? "Opening…" : "Open public map"}
                      </button>
                      <button
                        type="button"
                        data-testid="bootstrap-map-preview-cancel"
                        disabled={mapBusy}
                        onClick={cancelMapPreview}
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                ) : null}
                <button
                  type="button"
                  data-testid={`bootstrap-continue-exploring-${candidate.candidate_id}`}
                  disabled={mapBusy}
                  onClick={continueExploring}
                >
                  Continue exploring without committing
                </button>
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
        <section data-testid="bootstrap-shortlist">
          <h2>Your private draft shortlist</h2>
          <p>
            {shortlistLoading
              ? "Restoring your saved public places…"
              : `Saved ${shortlist.length} of 3. Only public identity, coordinates, source, capture time, and explicitly supported source facts are retained for this member.`}
          </p>
          {shortlist.map((item) => (
            <article key={item.shortlist_id} data-testid={`bootstrap-shortlist-item-${item.shortlist_id}`}>
              <h3>{item.name}</h3>
              <p>
                {item.category} · opening {item.opening_state || "UNKNOWN"} · price {item.price_state || "UNKNOWN"} · route ETA {item.eta_state || "UNKNOWN"}
              </p>
              <p>
                Source: {item.source_provenance} · captured {item.captured_at}
                {item.distance_basis === "MANUAL_PUBLIC_CENTER" && item.distance_m != null
                  ? ` · ${Math.round(item.distance_m)}m straight-line from the manual public center`
                  : ""}
              </p>
              {safeHttpsSourceUrl(item.source_url) ? (
                <a href={safeHttpsSourceUrl(item.source_url)!} target="_blank" rel="noopener noreferrer">
                  Open public source
                </a>
              ) : null}
              <div className="v8-actions">
                <button
                  type="button"
                  data-testid={`bootstrap-shortlist-map-${item.shortlist_id}`}
                  disabled={mapBusy || shortlistBusy !== null}
                  onClick={() => beginShortlistMapPreview(item)}
                >
                  Inspect public map
                </button>
                <button
                  type="button"
                  data-testid={`bootstrap-shortlist-go-${item.shortlist_id}`}
                  disabled={mapBusy || shortlistBusy !== null}
                  onClick={() => beginShortlistNavigation(item)}
                >
                  Go explore this public place
                </button>
                <button
                  type="button"
                  data-testid={`bootstrap-shortlist-remove-${item.shortlist_id}`}
                  disabled={mapBusy || shortlistBusy !== null}
                  onClick={() => void removeShortlistItem(item)}
                >
                  {shortlistBusy === item.shortlist_id ? "Removing…" : "Remove"}
                </button>
              </div>
              {pendingMapPreview?.shortlistId === item.shortlist_id && pendingMapPreview.kind === "shortlist" ? (
                <div
                  className="journey-membership-map-consent"
                  data-testid={pendingMapPreview.purpose === "WALKING"
                    ? `bootstrap-shortlist-navigation-consent-${item.shortlist_id}`
                    : `bootstrap-shortlist-map-consent-${item.shortlist_id}`}
                >
                  <p>
                    {pendingMapPreview.purpose === "WALKING"
                      ? "Fresh one-time consent: share only this saved public destination with a walking-directions provider. The provider receives no origin, query, receipt, or foreground GPS. Opening, cost, route duration, and arrival remain unknown."
                      : "Fresh one-time consent: share only this saved public destination with OpenStreetMap. No receipt, origin, search center, or foreground GPS is reused or sent."}
                  </p>
                  <label>
                    <input
                      type="checkbox"
                      data-testid={pendingMapPreview.purpose === "WALKING"
                        ? "bootstrap-shortlist-navigation-consent-checkbox"
                        : "bootstrap-shortlist-map-consent-checkbox"}
                      checked={mapConsent}
                      onChange={(event) => setMapConsent(event.target.checked)}
                    />
                    I agree to open this public destination now.
                  </label>
                  <div className="v8-actions">
                    <button
                      type="button"
                      data-testid={pendingMapPreview.purpose === "WALKING"
                        ? "bootstrap-shortlist-navigation-confirm"
                        : "bootstrap-shortlist-map-confirm"}
                      disabled={!mapConsent || mapBusy}
                      onClick={() => void confirmMapPreview()}
                    >
                      {mapBusy ? "Opening…" : pendingMapPreview.purpose === "WALKING" ? "Open walking directions" : "Open public map"}
                    </button>
                    <button
                      type="button"
                      data-testid={pendingMapPreview.purpose === "WALKING"
                        ? "bootstrap-shortlist-navigation-cancel"
                        : "bootstrap-shortlist-map-cancel"}
                      disabled={mapBusy}
                      onClick={cancelMapPreview}
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              ) : null}
            </article>
          ))}
        </section>
      </section>
    </main>
  );
}
