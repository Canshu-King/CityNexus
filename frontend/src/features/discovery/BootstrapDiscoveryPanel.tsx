import { useEffect, useLayoutEffect, useRef, useState } from "react";
import {
  cityNexusApi,
  type BootstrapCitySearchResult,
  type BootstrapDiscoveryCandidate,
  type BootstrapMapPreviewResponse,
  type BootstrapDiscoveryResponse,
  type BootstrapShortlistItem,
  type BootstrapShortlistResumeIntent,
  type BootstrapShortlistPreviewResponse,
  type BootstrapTwoStopWalkResponse,
  type BootstrapTwoStopWalkabilityResponse,
  type BootstrapAdaptiveShortWalkResponse,
} from "../../api/citynexus";
import { readTravelerBearer, subscribeTravelerBearer } from "../../lib/travelerSession";
import { PublicCityAreaPicker, type PublicCityCenter } from "./PublicCityAreaPicker";

type SourceKind = "FOREGROUND_GPS" | "MANUAL_PUBLIC_CENTER";
const OUTING_INTENTS = [
  {
    value: "ART_HISTORY",
    label: "Art and history",
    query: "museum/gallery",
    reason: "museum, gallery, or arts centre",
  },
  {
    value: "GREEN_WALK",
    label: "Quiet green walk",
    query: "park/garden",
    reason: "park or garden",
  },
  {
    value: "COFFEE_STROLL",
    label: "Coffee and a short stroll",
    query: "cafe",
    reason: "cafe or coffee stop",
  },
  {
    value: "QUIET_BOOKS",
    label: "Books and quiet",
    query: "library",
    reason: "library",
  },
] as const;
type OutingIntent = (typeof OUTING_INTENTS)[number]["value"];

type PendingMapPreview = {
  kind: "candidate" | "shortlist";
  purpose: "PIN" | "WALKING";
  candidateId?: string;
  shortlistId?: string;
  receiptId?: string;
  latitude: number;
  longitude: number;
};

type DiscoveryFence = {
  bearer: string | null;
  identityGeneration: number;
  discoveryGeneration: number;
  journeyId: string;
  sourceKind: SourceKind;
};

function parsePublicCoordinate(value: string, minimum: number, maximum: number): number | null {
  if (!value.trim()) return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed >= minimum && parsed <= maximum ? parsed : null;
}

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

/**
 * Parse the deliberately narrow offline map-link fallback.  This function only
 * reads a trusted OpenStreetMap URL locally; it never fetches the URL or treats
 * it as a geocoder.  If both query and hash coordinates are present they must
 * agree before the link can become a public search center.
 */
export function parsePublicMapLink(value: string): PublicCityCenter | null {
  if (!value.trim()) return null;
  try {
    const url = new URL(value.trim());
    const queryKeys = [...url.searchParams.keys()];
    const rawLatitude = url.searchParams.get("mlat");
    const rawLongitude = url.searchParams.get("mlon");
    // Number("") is 0; a blank URL coordinate must never become an
    // apparently deliberate public search center at the equator.
    const hasQueryPair =
      queryKeys.length === 2 &&
      queryKeys.every((key) => key === "mlat" || key === "mlon") &&
      url.searchParams.getAll("mlat").length === 1 &&
      url.searchParams.getAll("mlon").length === 1 &&
      rawLatitude !== null &&
      rawLatitude.trim() !== "" &&
      rawLongitude !== null &&
      rawLongitude.trim() !== "";
    const queryLatitude = rawLatitude?.trim() ? Number(rawLatitude) : NaN;
    const queryLongitude = rawLongitude?.trim() ? Number(rawLongitude) : NaN;
    const hashMatch = url.hash.match(/^#map=([^/]+)\/([^/]+)\/([^/]+)$/);
    const hashZoom = hashMatch ? Number(hashMatch[1]) : NaN;
    const hashLatitude = hashMatch ? Number(hashMatch[2]) : NaN;
    const hashLongitude = hashMatch ? Number(hashMatch[3]) : NaN;
    const hasHashCenter =
      !!hashMatch &&
      Number.isFinite(hashZoom) &&
      hashZoom >= 1 &&
      hashZoom <= 20 &&
      Number.isFinite(hashLatitude) &&
      Number.isFinite(hashLongitude);
    if (
      url.protocol !== "https:" ||
      url.hostname !== "www.openstreetmap.org" ||
      url.pathname !== "/" ||
      url.port !== "" ||
      url.username !== "" ||
      url.password !== "" ||
      (url.hash.length > 0 && !hasHashCenter) ||
      (!hasQueryPair && queryKeys.length > 0) ||
      (!hasQueryPair && !hasHashCenter) ||
      (hasQueryPair && !Number.isFinite(queryLatitude)) ||
      (hasQueryPair && !Number.isFinite(queryLongitude))
    ) {
      return null;
    }
    const latitude = hasHashCenter ? hashLatitude : queryLatitude;
    const longitude = hasHashCenter ? hashLongitude : queryLongitude;
    if (
      !Number.isFinite(latitude) ||
      !Number.isFinite(longitude) ||
      latitude < -90 ||
      latitude > 90 ||
      longitude < -180 ||
      longitude > 180 ||
      (hasQueryPair && hasHashCenter &&
        (Math.abs(queryLatitude - latitude) > 1e-6 || Math.abs(queryLongitude - longitude) > 1e-6))
    ) {
      return null;
    }
    return { latitude, longitude, provenance: "OSM_MAP_LINK" };
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

function validatedPublicTwoStopWalkingUrl(
  value: string | null | undefined,
  first: Pick<BootstrapShortlistItem, "latitude" | "longitude">,
  second: Pick<BootstrapShortlistItem, "latitude" | "longitude">,
): string | null {
  if (!value) return null;
  try {
    const url = new URL(value);
    const keys = [...url.searchParams.keys()];
    const parsePair = (raw: string | null) => {
      const pair = raw?.split(",") ?? [];
      // Blank components must not become valid zero-valued coordinates.
      const valid = pair.length === 2 && pair.every((value) => value.trim() !== "");
      return {
        latitude: valid ? Number(pair[0]) : NaN,
        longitude: valid ? Number(pair[1]) : NaN,
        length: pair.length,
      };
    };
    const origin = parsePair(url.searchParams.get("origin"));
    const destination = parsePair(url.searchParams.get("destination"));
    if (
      url.protocol !== "https:" ||
      url.hostname !== "www.google.com" ||
      url.pathname !== "/maps/dir/" ||
      url.port !== "" ||
      url.username !== "" ||
      url.password !== "" ||
      keys.length !== 4 ||
      keys.some((key) => !["api", "origin", "destination", "travelmode"].includes(key)) ||
      url.searchParams.getAll("origin").length !== 1 ||
      url.searchParams.getAll("destination").length !== 1 ||
      url.searchParams.get("api") !== "1" ||
      url.searchParams.get("travelmode") !== "walking" ||
      origin.length !== 2 ||
      destination.length !== 2 ||
      !Number.isFinite(origin.latitude) ||
      !Number.isFinite(origin.longitude) ||
      !Number.isFinite(destination.latitude) ||
      !Number.isFinite(destination.longitude) ||
      Math.abs(origin.latitude - first.latitude) > 1e-6 ||
      Math.abs(origin.longitude - first.longitude) > 1e-6 ||
      Math.abs(destination.latitude - second.latitude) > 1e-6 ||
      Math.abs(destination.longitude - second.longitude) > 1e-6
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
  cityName,
  onCompleted,
  onCancel,
}: {
  journeyId: string;
  cityCode: string;
  cityName?: string;
  onCompleted: (placeId: string) => Promise<void>;
  onCancel?: () => void;
}) {
  const [sourceKind, setSourceKind] = useState<SourceKind>("MANUAL_PUBLIC_CENTER");
  const [outingIntent, setOutingIntent] = useState<OutingIntent | null>(null);
  const [latitude, setLatitude] = useState("");
  const [longitude, setLongitude] = useState("");
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
  const [travelerBearer, setTravelerBearer] = useState<string | null>(() => readTravelerBearer());
  const [mapTileConsent, setMapTileConsent] = useState(false);
  const [mapPickerOpen, setMapPickerOpen] = useState(false);
  const [mapDraftCenter, setMapDraftCenter] = useState<PublicCityCenter | null>(null);
  const [mapLink, setMapLink] = useState("");
  const [mapLinkMessage, setMapLinkMessage] = useState<string | null>(null);
  const [citySearchConsent, setCitySearchConsent] = useState(false);
  const [citySearchQuery, setCitySearchQuery] = useState(() => cityName?.trim() ?? "");
  const [citySearchResults, setCitySearchResults] = useState<BootstrapCitySearchResult[]>([]);
  const [citySearchBusy, setCitySearchBusy] = useState(false);
  const [citySearchMessage, setCitySearchMessage] = useState<string | null>(null);
  const [mapFocusCenter, setMapFocusCenter] = useState<{ latitude: number; longitude: number } | null>(null);
  const [twoStopOrder, setTwoStopOrder] = useState<string[]>([]);
  const [twoStopConsent, setTwoStopConsent] = useState(false);
  const [twoStopBusy, setTwoStopBusy] = useState(false);
  const [twoStopNotice, setTwoStopNotice] = useState<string | null>(null);
  const [twoStopFallbackUrl, setTwoStopFallbackUrl] = useState<string | null>(null);
  const [twoStopWalkabilityConsent, setTwoStopWalkabilityConsent] = useState(false);
  const [twoStopWalkabilityBusy, setTwoStopWalkabilityBusy] = useState(false);
  const [twoStopWalkability, setTwoStopWalkability] = useState<BootstrapTwoStopWalkabilityResponse | null>(null);
  const [adaptiveWalkBudget, setAdaptiveWalkBudget] = useState<number | null>(null);
  const [adaptiveWalkConsent, setAdaptiveWalkConsent] = useState(false);
  const [adaptiveWalkBusy, setAdaptiveWalkBusy] = useState(false);
  const [adaptiveWalkComparison, setAdaptiveWalkComparison] = useState<BootstrapAdaptiveShortWalkResponse | null>(null);
  const identityGeneration = useRef(0);
  const pendingWindowRef = useRef<Window | null>(null);
  const journeyIdRef = useRef(journeyId);
  const sourceKindRef = useRef<SourceKind>("MANUAL_PUBLIC_CENTER");
  const discoveryGeneration = useRef(0);
  const gpsRequestGeneration = useRef(0);
  const citySearchGeneration = useRef(0);
  const twoStopReleaseGeneration = useRef(0);
  const parsedLatitude = parsePublicCoordinate(latitude, -90, 90);
  const parsedLongitude = parsePublicCoordinate(longitude, -180, 180);
  const hasValidSearchCenter = parsedLatitude !== null && parsedLongitude !== null;
  const selectedOutingIntent = outingIntent
    ? OUTING_INTENTS.find((item) => item.value === outingIntent) ?? null
    : null;
  const isCurrentIdentity = (bearer: string | null, generation: number) =>
    identityGeneration.current === generation && readTravelerBearer() === bearer;
  const invalidateDiscovery = () => {
    discoveryGeneration.current += 1;
    gpsRequestGeneration.current += 1;
    citySearchGeneration.current += 1;
    try {
      pendingWindowRef.current?.close();
    } catch {
      // A browser may already have reclaimed the pre-opened tab.
    }
    pendingWindowRef.current = null;
    setResult(null);
    setPendingMapPreview(null);
    setMapConsent(false);
    setMapFallbackUrl(null);
    setLastNavigationLaunched(false);
    setExploreNotice(null);
    setBusy(false);
    setSelecting(null);
    setShortlistBusy(null);
    setMapBusy(false);
    setCitySearchBusy(false);
    setCitySearchResults([]);
    setCitySearchMessage(null);
    setMapFocusCenter(null);
    setTwoStopOrder([]);
    setTwoStopConsent(false);
    setTwoStopBusy(false);
    setTwoStopNotice(null);
    setTwoStopFallbackUrl(null);
    setTwoStopWalkabilityConsent(false);
    setTwoStopWalkabilityBusy(false);
    setTwoStopWalkability(null);
    setAdaptiveWalkBudget(null);
    setAdaptiveWalkConsent(false);
    setAdaptiveWalkBusy(false);
    setAdaptiveWalkComparison(null);
  };
  const captureDiscoveryFence = (): DiscoveryFence => ({
    bearer: travelerBearer,
    identityGeneration: identityGeneration.current,
    discoveryGeneration: discoveryGeneration.current,
    journeyId,
    sourceKind: sourceKindRef.current,
  });
  const isCurrentDiscovery = (fence: DiscoveryFence) =>
    isCurrentIdentity(fence.bearer, fence.identityGeneration) &&
    discoveryGeneration.current === fence.discoveryGeneration &&
    journeyIdRef.current === fence.journeyId &&
    sourceKindRef.current === fence.sourceKind;
  const chooseSearchSource = (next: SourceKind, clearCenter: boolean) => {
    sourceKindRef.current = next;
    invalidateDiscovery();
    setSourceKind(next);
    setMapPickerOpen(false);
    setMapTileConsent(false);
    if (clearCenter) {
      setLatitude("");
      setLongitude("");
      setAccuracy(undefined);
    }
  };
  const chooseOutingIntent = (next: OutingIntent) => {
    invalidateDiscovery();
    setOutingIntent(next);
    setMessage(null);
  };
  const applyPublicCenter = (center: PublicCityCenter) => {
    chooseSearchSource("MANUAL_PUBLIC_CENTER", false);
    setLatitude(center.latitude.toFixed(6));
    setLongitude(center.longitude.toFixed(6));
    setAccuracy(undefined);
    setMapPickerOpen(false);
    setMapTileConsent(false);
    setMapDraftCenter(center);
    setMapLinkMessage(null);
    setMessage(
      center.provenance === "OSM_MAP_LINK"
        ? "Public center loaded from a validated OpenStreetMap link. Confirm the center and provider disclosure before searching."
        : "Public center selected from the map. Confirm the center and provider disclosure before searching.",
    );
  };

  const resetPrivateStateForBearer = (nextBearer: string | null) => {
    identityGeneration.current += 1;
    discoveryGeneration.current += 1;
    gpsRequestGeneration.current += 1;
    citySearchGeneration.current += 1;
    sourceKindRef.current = "MANUAL_PUBLIC_CENTER";
    try {
      pendingWindowRef.current?.close();
    } catch {
      // A browser may already have reclaimed the pre-opened tab.
    }
    pendingWindowRef.current = null;
    setTravelerBearer(nextBearer);
    setResult(null);
    setShortlist([]);
    setResumeIntent(null);
    setPendingMapPreview(null);
    setMapConsent(false);
    setMapFallbackUrl(null);
    setLastNavigationLaunched(false);
    setExploreNotice(null);
    setShortlistBusy(null);
    setSelecting(null);
    setBusy(false);
    setMapBusy(false);
    setProviderConsent(false);
    setSourceKind("MANUAL_PUBLIC_CENTER");
    setOutingIntent(null);
    setLatitude("");
    setLongitude("");
    setAccuracy(undefined);
    setMapTileConsent(false);
    setMapPickerOpen(false);
    setMapDraftCenter(null);
    setMapLink("");
    setMapLinkMessage(null);
    setCitySearchConsent(false);
    setCitySearchQuery(cityName?.trim() ?? "");
    setCitySearchResults([]);
    setCitySearchBusy(false);
    setCitySearchMessage(null);
    setMapFocusCenter(null);
    setTwoStopOrder([]);
    setTwoStopConsent(false);
    setTwoStopBusy(false);
    setTwoStopNotice(null);
    setTwoStopFallbackUrl(null);
    setTwoStopWalkabilityConsent(false);
    setTwoStopWalkabilityBusy(false);
    setTwoStopWalkability(null);
    setAdaptiveWalkBudget(null);
    setAdaptiveWalkConsent(false);
    setAdaptiveWalkBusy(false);
    setAdaptiveWalkComparison(null);
    setShortlistLoading(true);
    setMessage("Session changed; private exploration state was cleared.");
  };

  useEffect(() => {
    let previousBearer = readTravelerBearer();
    const onBearerSignal = () => {
      const nextBearer = readTravelerBearer();
      if (nextBearer === previousBearer) return;
      previousBearer = nextBearer;
      resetPrivateStateForBearer(nextBearer);
    };
    const unsubscribe = subscribeTravelerBearer(onBearerSignal);
    return () => {
      unsubscribe();
    };
  }, []);

  useLayoutEffect(() => {
    if (journeyIdRef.current === journeyId) return;
    journeyIdRef.current = journeyId;
    sourceKindRef.current = "MANUAL_PUBLIC_CENTER";
    discoveryGeneration.current += 1;
    gpsRequestGeneration.current += 1;
    citySearchGeneration.current += 1;
    setSourceKind("MANUAL_PUBLIC_CENTER");
    setOutingIntent(null);
    setLatitude("");
    setLongitude("");
    setAccuracy(undefined);
    setResult(null);
    setPendingMapPreview(null);
    setMapPickerOpen(false);
    setMapTileConsent(false);
    setMapDraftCenter(null);
    setMapLink("");
    setMapLinkMessage(null);
    setCitySearchConsent(false);
    setCitySearchQuery("");
    setCitySearchResults([]);
    setCitySearchBusy(false);
    setCitySearchMessage(null);
    setMapFocusCenter(null);
    setTwoStopOrder([]);
    setTwoStopConsent(false);
    setTwoStopBusy(false);
    setTwoStopNotice(null);
    setTwoStopFallbackUrl(null);
    setTwoStopWalkabilityConsent(false);
    setTwoStopWalkabilityBusy(false);
    setTwoStopWalkability(null);
    setAdaptiveWalkBudget(null);
    setAdaptiveWalkConsent(false);
    setAdaptiveWalkBusy(false);
    setAdaptiveWalkComparison(null);
    setMessage("Journey changed; choose a new public search area.");
  }, [journeyId, cityName]);

  useEffect(() => {
    let active = true;
    const requestBearer = travelerBearer;
    const requestGeneration = identityGeneration.current;
    const stillCurrent = () => active && isCurrentIdentity(requestBearer, requestGeneration);
    setResult(null);
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
        if (!stillCurrent()) return;
        const restorable = saved.resume && saved.items.some((item) => item.shortlist_id === saved.resume?.shortlist_id)
          ? saved.resume
          : null;
        setShortlist(saved.items);
        setResumeIntent(restorable);
      } catch {
        // A draft without a signed member simply has no restorable board yet.
        if (stillCurrent()) {
          setShortlist([]);
          setResumeIntent(null);
          setPendingMapPreview(null);
          setMapConsent(false);
          setMapFallbackUrl(null);
          setLastNavigationLaunched(false);
          setExploreNotice(null);
        }
      } finally {
        if (stillCurrent() && initial) setShortlistLoading(false);
      }
    };
    void loadShortlist(true);
    const refreshOnReturn = () => {
      if (readTravelerBearer() !== travelerBearer) {
        return;
      }
      if (document.visibilityState === "visible" && stillCurrent()) void loadShortlist(false);
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
    chooseSearchSource("FOREGROUND_GPS", true);
    const gpsRequest = ++gpsRequestGeneration.current;
    const requestBearer = travelerBearer;
    const requestIdentityGeneration = identityGeneration.current;
    const requestJourneyId = journeyId;
    setMessage(null);
    if (!navigator.geolocation) {
      setMessage("Foreground location is unavailable. Choose a public map center instead.");
      return;
    }
    const stillCurrent = () =>
      gpsRequestGeneration.current === gpsRequest &&
      identityGeneration.current === requestIdentityGeneration &&
      readTravelerBearer() === requestBearer &&
      journeyIdRef.current === requestJourneyId &&
      sourceKindRef.current === "FOREGROUND_GPS";
    navigator.geolocation.getCurrentPosition(
      (position) => {
        if (!stillCurrent()) return;
        setLatitude(String(position.coords.latitude));
        setLongitude(String(position.coords.longitude));
        setAccuracy(position.coords.accuracy > 0 ? position.coords.accuracy : undefined);
        setMessage("Location is held for this search only; it is not saved as presence or a route origin.");
      },
      () => {
        if (stillCurrent()) setMessage("Foreground location was not granted. Choose a public map center instead.");
      },
      { enableHighAccuracy: true, maximumAge: 60_000, timeout: 8_000 },
    );
  };

  const searchCity = async () => {
    const cityQuery = citySearchQuery.trim();
    if (!citySearchConsent) {
      setCitySearchMessage("Confirm the separate city-search provider disclosure before searching.");
      return;
    }
    if (cityQuery.length < 2) {
      setCitySearchMessage("Enter at least two characters for the city or area.");
      return;
    }
    const generation = ++citySearchGeneration.current;
    const requestBearer = travelerBearer;
    const requestIdentityGeneration = identityGeneration.current;
    const requestJourneyId = journeyId;
    setCitySearchBusy(true);
    setCitySearchMessage(null);
    setCitySearchResults([]);
    try {
      const response = await cityNexusApi.bootstrapCitySearch(journeyId, {
        query: cityQuery,
        provider_consent: true,
        limit: 3,
      });
      const current =
        citySearchGeneration.current === generation &&
        identityGeneration.current === requestIdentityGeneration &&
        readTravelerBearer() === requestBearer &&
        journeyIdRef.current === requestJourneyId;
      if (!current) return;
      setCitySearchResults(response.results);
      setCitySearchMessage(
        response.results.length
          ? "Choose one grounded result to move the camera, then tap the exact public area."
          : response.status === "GEOCODER_DISABLED"
            ? "City search is disabled here. Use the offline OpenStreetMap link or manual WGS84 fields."
              : response.status === "GEOCODER_RATE_LIMITED"
                ? "The configured city provider is rate-limited across the application. Wait and try once later, or use the offline OpenStreetMap link."
                : "No grounded city result was returned. Use the offline OpenStreetMap link or manual WGS84 fields.",
      );
    } catch (error) {
      if (
        citySearchGeneration.current === generation &&
        identityGeneration.current === requestIdentityGeneration &&
        readTravelerBearer() === requestBearer &&
        journeyIdRef.current === requestJourneyId
      ) {
        setCitySearchMessage(error instanceof Error ? error.message : "City search could not be completed.");
      }
    } finally {
      if (citySearchGeneration.current === generation) setCitySearchBusy(false);
    }
  };

  const search = async () => {
    if (!selectedOutingIntent) {
      setMessage("Choose what you want from this outing before searching public places.");
      return;
    }
    if (!providerConsent) {
      setMessage("Confirm the OpenStreetMap/Overpass provider disclosure before searching.");
      return;
    }
    if (parsedLatitude === null || parsedLongitude === null) {
      setMessage("Enter a valid public WGS84 search center.");
      return;
    }
    const fence = captureDiscoveryFence();
    const requestLatitude = parsedLatitude;
    const requestLongitude = parsedLongitude;
    const requestAccuracy = accuracy;
    setBusy(true);
    setMessage(null);
    setResult(null);
    try {
      const next = await cityNexusApi.bootstrapDiscovery(journeyId, {
        query: selectedOutingIntent.query,
        radius_m: 2500,
        limit: 3,
        source_kind: fence.sourceKind,
        provider_consent: true,
        latitude: requestLatitude,
        longitude: requestLongitude,
        coordinate_system: "WGS84",
        accuracy_m: requestAccuracy,
        mode: "live",
      });
      if (!isCurrentDiscovery(fence)) return;
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
      if (isCurrentDiscovery(fence)) {
        setMessage(error instanceof Error ? error.message : "Discovery could not be completed.");
      }
    } finally {
      if (isCurrentDiscovery(fence)) setBusy(false);
    }
  };

  const selectCandidate = async (candidate: BootstrapDiscoveryCandidate) => {
    if (!result?.receipt_id) return;
    const fence = captureDiscoveryFence();
    const receiptId = result.receipt_id;
    setSelecting(candidate.candidate_id);
    setMessage(null);
    try {
      const selected = await cityNexusApi.selectBootstrapCandidate(
        journeyId,
        receiptId,
        candidate.candidate_id,
      );
      if (!isCurrentDiscovery(fence)) return;
      await onCompleted(selected.selected_place_id);
    } catch (error) {
      if (isCurrentDiscovery(fence)) {
        setMessage(error instanceof Error ? error.message : "That place is no longer selectable.");
      }
    } finally {
      if (isCurrentDiscovery(fence)) setSelecting(null);
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
    const fence = captureDiscoveryFence();
    const receiptId = result.receipt_id;
    setShortlistBusy(candidate.candidate_id);
    setMessage(null);
    try {
      const saved = await cityNexusApi.saveBootstrapShortlistItem(journeyId, {
        receipt_id: receiptId,
        candidate_id: candidate.candidate_id,
      });
      if (!isCurrentDiscovery(fence)) return;
      setShortlist((items) => items.some((item) => item.shortlist_id === saved.shortlist_id) ? items : [...items, saved]);
      setExploreNotice("Saved to your private draft shortlist. This is not a Place, PlanVersion, visit, booking, or payment authorization.");
    } catch (error) {
      if (isCurrentDiscovery(fence)) {
        setMessage(error instanceof Error ? error.message : "This public place could not be saved.");
      }
    } finally {
      if (isCurrentDiscovery(fence)) setShortlistBusy(null);
    }
  };

  const removeShortlistItem = async (item: BootstrapShortlistItem) => {
    const fence = captureDiscoveryFence();
    // A removed stop invalidates any already-authorized fallback and an
    // in-flight two-stop release, including before the DELETE returns.
    if (twoStopOrder.includes(item.shortlist_id)) {
      twoStopReleaseGeneration.current += 1;
      try { pendingWindowRef.current?.close(); } catch { /* tab already reclaimed */ }
      pendingWindowRef.current = null;
      setTwoStopOrder((ids) => ids.filter((id) => id !== item.shortlist_id));
      setTwoStopConsent(false);
      setTwoStopBusy(false);
      setTwoStopFallbackUrl(null);
      setTwoStopNotice(null);
      setTwoStopWalkabilityConsent(false);
      setTwoStopWalkabilityBusy(false);
      setTwoStopWalkability(null);
      setAdaptiveWalkBudget(null);
      setAdaptiveWalkConsent(false);
      setAdaptiveWalkBusy(false);
      setAdaptiveWalkComparison(null);
    }
    setShortlistBusy(item.shortlist_id);
    setMessage(null);
    try {
      await cityNexusApi.removeBootstrapShortlistItem(journeyId, item.shortlist_id);
      if (!isCurrentDiscovery(fence)) return;
      if (pendingMapPreview?.shortlistId === item.shortlist_id) cancelMapPreview();
      setShortlist((items) => items.filter((saved) => saved.shortlist_id !== item.shortlist_id));
      if (resumeIntent?.shortlist_id === item.shortlist_id) setResumeIntent(null);
    } catch (error) {
      if (isCurrentDiscovery(fence)) {
        setMessage(error instanceof Error ? error.message : "That saved place could not be removed.");
      }
    } finally {
      if (isCurrentDiscovery(fence)) setShortlistBusy(null);
    }
  };

  const setTwoStopPosition = (shortlistId: string, position: 1 | 2) => {
    twoStopReleaseGeneration.current += 1;
    setTwoStopNotice(null);
    setTwoStopFallbackUrl(null);
    setTwoStopConsent(false);
    setTwoStopWalkabilityConsent(false);
    setTwoStopWalkabilityBusy(false);
    setTwoStopWalkability(null);
    setAdaptiveWalkBudget(null);
    setAdaptiveWalkConsent(false);
    setAdaptiveWalkBusy(false);
    setAdaptiveWalkComparison(null);
    setTwoStopOrder((current) => {
      const without = current.filter((id) => id !== shortlistId);
      if (position === 1) return [shortlistId, ...without].slice(0, 2);
      // Replacing stop 2 must preserve the existing stop 1.  Slicing from
      // the end would silently discard stop 1 when a complete pair already
      // existed (the adaptive suggestion path exercises that transition).
      const preservedFirst = current[0] === shortlistId ? current[1] : current[0];
      return preservedFirst ? [preservedFirst, shortlistId] : [shortlistId];
    });
  };

  const clearTwoStopPosition = (shortlistId: string) => {
    twoStopReleaseGeneration.current += 1;
    setTwoStopNotice(null);
    setTwoStopFallbackUrl(null);
    setTwoStopConsent(false);
    setTwoStopWalkabilityConsent(false);
    setTwoStopWalkabilityBusy(false);
    setTwoStopWalkability(null);
    setAdaptiveWalkBudget(null);
    setAdaptiveWalkConsent(false);
    setAdaptiveWalkBusy(false);
    setAdaptiveWalkComparison(null);
    setTwoStopOrder((current) => current.filter((id) => id !== shortlistId));
  };

  const checkTwoStopWalkability = async () => {
    if (twoStopOrder.length !== 2 || twoStopOrder[0] === twoStopOrder[1]) {
      setMessage("Choose exactly two different saved public places and set their order first.");
      return;
    }
    if (!twoStopWalkabilityConsent) {
      setMessage("Confirm the separate release for both public stop coordinates before checking walking feasibility.");
      return;
    }
    const first = shortlist.find((item) => item.shortlist_id === twoStopOrder[0]);
    const second = shortlist.find((item) => item.shortlist_id === twoStopOrder[1]);
    if (!first || !second) {
      setTwoStopOrder([]);
      setMessage("The saved order is stale. Choose two saved places again.");
      return;
    }
    const fence = captureDiscoveryFence();
    const releaseGeneration = twoStopReleaseGeneration.current;
    const stillCurrent = () =>
      isCurrentDiscovery(fence) && twoStopReleaseGeneration.current === releaseGeneration;
    setTwoStopWalkabilityBusy(true);
    setMessage(null);
    setTwoStopWalkability(null);
    setTwoStopFallbackUrl(null);
    try {
      const released: BootstrapTwoStopWalkabilityResponse = await cityNexusApi.checkBootstrapTwoStopWalkability(
        journeyId,
        {
          first_shortlist_id: first.shortlist_id,
          second_shortlist_id: second.shortlist_id,
          public_route_consent: true,
        },
      );
      if (!stillCurrent()) return;
      if (
        released.authorization_basis !== "TWO_SAVED_PUBLIC_IDENTITIES" ||
        released.navigation_mode !== "PUBLIC_POI_TO_PUBLIC_POI_WALKING" ||
        released.first_stop.shortlist_id !== first.shortlist_id ||
        released.second_stop.shortlist_id !== second.shortlist_id
      ) {
        throw new Error("The walking feasibility response did not match the chosen public stop order.");
      }
      const publicMapUrl = validatedPublicTwoStopWalkingUrl(released.navigation_url, first, second);
      if (!publicMapUrl) {
        throw new Error("The walking feasibility fallback URL did not match both saved public coordinates.");
      }
      if (released.status === "ROUTE_VERIFIED") {
        if (
          released.duration_min === null ||
          released.distance_m === null ||
          !Number.isFinite(released.duration_min) ||
          !Number.isFinite(released.distance_m) ||
          released.duration_min < 0 ||
          released.distance_m < 0 ||
          released.provenance === "UNVERIFIED"
        ) {
          throw new Error("The walking provider returned incomplete route evidence.");
        }
      } else if (released.duration_min !== null || released.distance_m !== null) {
        throw new Error("An unverified walking response cannot contain a duration or distance.");
      }
      setTwoStopWalkability(released);
      if (released.status === "ROUTE_UNVERIFIED") setTwoStopFallbackUrl(publicMapUrl);
      setTwoStopWalkabilityConsent(false);
    } catch (error) {
      if (stillCurrent()) {
        setTwoStopWalkability(null);
        setTwoStopFallbackUrl(null);
        setMessage(error instanceof Error ? error.message : "Walking feasibility could not be checked.");
      }
    } finally {
      if (stillCurrent()) setTwoStopWalkabilityBusy(false);
    }
  };

  const checkAdaptiveShortWalk = async () => {
    if (twoStopOrder.length !== 2 || twoStopOrder[0] === twoStopOrder[1]) {
      setMessage("Choose exactly two different saved public places and set their order first.");
      return;
    }
    if (adaptiveWalkBudget === null) {
      setMessage("Choose a maximum walking time before comparing a second stop.");
      return;
    }
    if (!adaptiveWalkConsent) {
      setMessage("Confirm the separate release for the three public stop coordinates before comparing walking legs.");
      return;
    }
    const first = shortlist.find((item) => item.shortlist_id === twoStopOrder[0]);
    const currentSecond = shortlist.find((item) => item.shortlist_id === twoStopOrder[1]);
    const alternativeSecond = shortlist.find((item) => !twoStopOrder.includes(item.shortlist_id));
    if (!first || !currentSecond || !alternativeSecond) {
      setTwoStopOrder([]);
      setMessage("The saved stop comparison is stale. Choose a first stop, current second stop, and alternative again.");
      return;
    }
    const fence = captureDiscoveryFence();
    const releaseGeneration = twoStopReleaseGeneration.current;
    const stillCurrent = () =>
      isCurrentDiscovery(fence) && twoStopReleaseGeneration.current === releaseGeneration;
    setAdaptiveWalkBusy(true);
    setMessage(null);
    setAdaptiveWalkComparison(null);
    setTwoStopWalkability(null);
    try {
      const released: BootstrapAdaptiveShortWalkResponse = await cityNexusApi.checkBootstrapAdaptiveShortWalk(
        journeyId,
        {
          first_shortlist_id: first.shortlist_id,
          current_second_shortlist_id: currentSecond.shortlist_id,
          alternative_second_shortlist_id: alternativeSecond.shortlist_id,
          max_walk_minutes: adaptiveWalkBudget,
          public_route_consent: true,
        },
      );
      if (!stillCurrent()) return;
      if (
        released.authorization_basis !== "THREE_SAVED_PUBLIC_IDENTITIES" ||
        released.navigation_mode !== "PUBLIC_POI_TO_PUBLIC_POI_WALKING" ||
        released.first_stop.shortlist_id !== first.shortlist_id ||
        released.current_second_stop.shortlist_id !== currentSecond.shortlist_id ||
        released.alternative_second_stop.shortlist_id !== alternativeSecond.shortlist_id ||
        released.max_walk_minutes !== adaptiveWalkBudget
      ) {
        throw new Error("The adaptive walking response did not match the chosen public stop comparison.");
      }
      const publicMapUrl = validatedPublicTwoStopWalkingUrl(released.navigation_url, first, currentSecond);
      const alternativeMapUrl = validatedPublicTwoStopWalkingUrl(
        released.alternative_navigation_url,
        first,
        alternativeSecond,
      );
      if (!publicMapUrl || !alternativeMapUrl) {
        throw new Error("The adaptive walking fallback URLs did not match the saved public coordinates.");
      }
      for (const leg of [released.current_leg, released.alternative_leg]) {
        if (leg.status === "ROUTE_VERIFIED") {
          if (
            leg.duration_min === null ||
            leg.distance_m === null ||
            !Number.isFinite(leg.duration_min) ||
            !Number.isFinite(leg.distance_m) ||
            leg.duration_min < 0 ||
            leg.distance_m < 0 ||
            leg.provenance === "UNVERIFIED"
          ) {
            throw new Error("The adaptive walking provider returned incomplete route evidence.");
          }
        } else if (leg.duration_min !== null || leg.distance_m !== null) {
          throw new Error("An unverified adaptive walking response cannot contain a duration or distance.");
        }
      }
      if (
        released.recommendation_state === "WITHIN_MY_LEG_BUDGET" &&
        released.suggested_second_shortlist_id !== null &&
        released.suggested_second_shortlist_id !== alternativeSecond.shortlist_id
      ) {
        throw new Error("The adaptive walking suggestion did not match the available alternative.");
      }
      setAdaptiveWalkComparison(released);
      if (released.route_state === "ROUTE_UNVERIFIED") setTwoStopFallbackUrl(publicMapUrl);
      setAdaptiveWalkConsent(false);
    } catch (error) {
      if (stillCurrent()) {
        setAdaptiveWalkComparison(null);
        setMessage(error instanceof Error ? error.message : "Adaptive walking comparison could not be checked.");
      }
    } finally {
      if (stillCurrent()) setAdaptiveWalkBusy(false);
    }
  };

  const chooseAdaptiveAlternative = () => {
    const suggestedId = adaptiveWalkComparison?.suggested_second_shortlist_id;
    if (
      !suggestedId ||
      adaptiveWalkComparison?.recommendation_state !== "WITHIN_MY_LEG_BUDGET"
    ) {
      setMessage("No provider-backed short-walk alternative is ready to choose.");
      return;
    }
    const alternative = shortlist.find((item) => item.shortlist_id === suggestedId);
    if (!alternative) {
      setMessage("The suggested public alternative is no longer saved.");
      return;
    }
    setTwoStopPosition(alternative.shortlist_id, 2);
    setMessage("The better second stop is selected in the private draft. Confirm fresh map consent and check the new leg again.");
  };

  const confirmTwoStopWalk = async () => {
    if (twoStopOrder.length !== 2 || twoStopOrder[0] === twoStopOrder[1]) {
      setMessage("Choose exactly two different saved public places and set their order first.");
      return;
    }
    if (!twoStopConsent) {
      setMessage("Confirm the separate release for both public stop coordinates before opening walking directions.");
      return;
    }
    const first = shortlist.find((item) => item.shortlist_id === twoStopOrder[0]);
    const second = shortlist.find((item) => item.shortlist_id === twoStopOrder[1]);
    if (!first || !second) {
      setTwoStopOrder([]);
      setMessage("The saved order is stale. Choose two saved places again.");
      return;
    }
    const fence = captureDiscoveryFence();
    const releaseGeneration = twoStopReleaseGeneration.current;
    const stillCurrent = () =>
      isCurrentDiscovery(fence) && twoStopReleaseGeneration.current === releaseGeneration;
    setTwoStopBusy(true);
    setMessage(null);
    setTwoStopNotice(null);
    setTwoStopFallbackUrl(null);
    const pendingWindow = window.open("about:blank", "_blank");
    pendingWindowRef.current = pendingWindow;
    try {
      if (pendingWindow) pendingWindow.opener = null;
    } catch {
      // The opener relationship is advisory; the release validation is authoritative.
    }
    try {
      const released: BootstrapTwoStopWalkResponse = await cityNexusApi.navigateBootstrapTwoStopWalk(journeyId, {
        first_shortlist_id: first.shortlist_id,
        second_shortlist_id: second.shortlist_id,
        public_map_consent: true,
      });
      if (!stillCurrent()) {
        try { pendingWindow?.close(); } catch { /* browser reclaimed it */ }
        return;
      }
      if (
        released.authorization_basis !== "TWO_SAVED_PUBLIC_IDENTITIES" ||
        released.navigation_mode !== "PUBLIC_POI_TO_PUBLIC_POI_WALKING" ||
        released.first_stop.shortlist_id !== first.shortlist_id ||
        released.second_stop.shortlist_id !== second.shortlist_id
      ) {
        throw new Error("The two-stop release did not match the chosen public stop order.");
      }
      const publicMapUrl = validatedPublicTwoStopWalkingUrl(released.navigation_url, first, second);
      if (!publicMapUrl) {
        throw new Error("The authorized two-stop walking URL did not match both saved public coordinates.");
      }
      let sentToMap = false;
      if (pendingWindow && !pendingWindow.closed) {
        try {
          pendingWindow.location.replace(publicMapUrl);
          sentToMap = true;
        } catch {
          setTwoStopFallbackUrl(publicMapUrl);
        }
      } else {
        setTwoStopFallbackUrl(publicMapUrl);
      }
      setTwoStopNotice(
        (sentToMap
          ? "Public-to-public walking directions handed off to the external map. "
          : "The browser did not open the map automatically; use the authorized link below. ") +
        "Route time, opening, price, arrival, and feasibility remain UNKNOWN; this draft Journey was not started.",
      );
      setTwoStopConsent(false);
    } catch (error) {
      try { pendingWindow?.close(); } catch { /* browser reclaimed it */ }
      if (stillCurrent()) {
        setTwoStopNotice(null);
        setTwoStopFallbackUrl(null);
        setMessage(error instanceof Error ? error.message : "The two-stop walking release was cancelled.");
      }
    } finally {
      if (pendingWindowRef.current === pendingWindow) pendingWindowRef.current = null;
      if (stillCurrent()) setTwoStopBusy(false);
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
    const fence = captureDiscoveryFence();
    setMessage(null);
    setExploreNotice(null);
    setMapFallbackUrl(null);
    setLastNavigationLaunched(false);
    setMapConsent(false);
    try {
      const remembered = await cityNexusApi.rememberBootstrapShortlistItem(journeyId, item.shortlist_id);
      if (!isCurrentDiscovery(fence)) return;
      setResumeIntent(remembered);
    } catch (error) {
      if (isCurrentDiscovery(fence)) {
        setMessage(error instanceof Error ? error.message : "This saved place could not be resumed.");
      }
      return;
    }
    if (!isCurrentDiscovery(fence)) return;
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
    const fence = captureDiscoveryFence();
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
    pendingWindowRef.current = pendingWindow;
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
      if (!isCurrentDiscovery(fence)) {
        try {
          pendingWindow?.close();
        } catch {
          // A browser may already have reclaimed the pre-opened tab.
        }
        if (pendingWindowRef.current === pendingWindow) pendingWindowRef.current = null;
        return;
      }
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
        if (pendingWindowRef.current === pendingWindow) pendingWindowRef.current = null;
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
      if (pendingWindowRef.current === pendingWindow) pendingWindowRef.current = null;
      if (isCurrentDiscovery(fence)) {
        cancelMapPreview();
        setMessage(error instanceof Error ? error.message : "The public map release was cancelled.");
      }
    } finally {
      if (pendingWindowRef.current === pendingWindow) pendingWindowRef.current = null;
      if (isCurrentDiscovery(fence)) setMapBusy(false);
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

  const openPublicAreaPicker = () => {
    invalidateDiscovery();
    const existingCenter = sourceKind === "MANUAL_PUBLIC_CENTER" && parsedLatitude !== null && parsedLongitude !== null
      ? { latitude: parsedLatitude, longitude: parsedLongitude, provenance: "MAP_TAP" as const }
      : null;
    setMapDraftCenter(existingCenter);
    setMapLinkMessage(null);
    setMapPickerOpen(true);
    setMapTileConsent(false);
    setMessage(null);
  };

  const cancelPublicAreaPicker = () => {
    setMapPickerOpen(false);
    setMapTileConsent(false);
    setMapDraftCenter(null);
    setMapLinkMessage(null);
  };

  const handlePublicMapTap = (center: PublicCityCenter) => {
    setMapDraftCenter(center);
    setMapLinkMessage(null);
  };

  const applyPublicMapLink = () => {
    const parsed = parsePublicMapLink(mapLink);
    if (!parsed) {
      setMapLinkMessage("Paste an exact https://www.openstreetmap.org/ link with #map=zoom/latitude/longitude or one mlat/mlon pair.");
      return;
    }
    setMapDraftCenter(parsed);
    setMapLinkMessage("Validated locally. Review the center and confirm it before searching.");
  };

  const confirmPublicArea = () => {
    if (!mapDraftCenter) {
      setMapLinkMessage("Tap the map or apply a validated OpenStreetMap link first.");
      return;
    }
    applyPublicCenter(mapDraftCenter);
  };

  const editManualCoordinate = (axis: "latitude" | "longitude", value: string) => {
    chooseSearchSource("MANUAL_PUBLIC_CENTER", false);
    setMapDraftCenter(null);
    setAccuracy(undefined);
    if (axis === "latitude") setLatitude(value);
    else setLongitude(value);
  };

  const mapFallback =
    sourceKind === "MANUAL_PUBLIC_CENTER" && parsedLatitude !== null && parsedLongitude !== null
      ? `https://www.openstreetmap.org/?mlat=${encodeURIComponent(parsedLatitude)}&mlon=${encodeURIComponent(parsedLongitude)}#map=16/${encodeURIComponent(parsedLatitude)}/${encodeURIComponent(parsedLongitude)}`
      : null;
  const orderedTwoStopItems = twoStopOrder
    .map((shortlistId) => shortlist.find((item) => item.shortlist_id === shortlistId) ?? null)
    .filter((item): item is BootstrapShortlistItem => item !== null);
  const adaptiveAlternativeSecond = shortlist.find((item) => !twoStopOrder.includes(item.shortlist_id)) ?? null;

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
            onClick={openPublicAreaPicker}
          >
            Choose public area on map
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
        {mapPickerOpen ? (
          <section className="journey-membership-map-consent public-city-area-picker-shell" data-testid="bootstrap-public-area-picker" aria-labelledby="bootstrap-public-area-picker-title">
            <h2 id="bootstrap-public-area-picker-title">Choose a public search area</h2>
            <p>
              CityNexus will use one pin as a public discovery center. It will not be treated as your location,
              presence, route origin, arrival, or a confirmed city relation. Map tiles are a separate provider release.
            </p>
            <div className="public-city-search" data-testid="bootstrap-city-search">
              <h3>Find my city (optional)</h3>
              <p>
                This makes one bounded request to the configured city-search provider. It can move the camera only;
                it never chooses a center for you. No request is made on mount or while typing.
              </p>
              <label>
                <input
                  type="checkbox"
                  data-testid="bootstrap-city-search-consent"
                  checked={citySearchConsent}
                  onChange={(event) => setCitySearchConsent(event.target.checked)}
                />
                I agree to ask the configured city-search provider once (source and uncertainty will be shown).
              </label>
              <div className="v8-form-grid">
                <label>
                  City or area name
                  <input
                    data-testid="bootstrap-city-search-query"
                    value={citySearchQuery}
                    onChange={(event) => {
                      citySearchGeneration.current += 1;
                      setCitySearchQuery(event.target.value);
                      setCitySearchResults([]);
                      setCitySearchMessage(null);
                    }}
                    maxLength={120}
                    placeholder="Shanghai or Xujiahui"
                  />
                </label>
                <div className="v8-actions">
                  <button type="button" data-testid="bootstrap-city-search-submit" disabled={citySearchBusy} onClick={() => void searchCity()}>
                    {citySearchBusy ? "Searching…" : "Find my city"}
                  </button>
                </div>
              </div>
              {citySearchMessage ? <p role="status" data-testid="bootstrap-city-search-message">{citySearchMessage}</p> : null}
              {citySearchResults.length ? (
                <ul data-testid="bootstrap-city-search-results">
                  {citySearchResults.map((item, index) => (
                    <li key={item.result_id}>
                      <button
                        type="button"
                        data-testid={`bootstrap-city-result-${index}`}
                        onClick={() => {
                          setMapFocusCenter({ latitude: item.latitude, longitude: item.longitude });
                          setMapDraftCenter(null);
                          setMapTileConsent(false);
                          setMessage("City result selected for camera positioning only. Tap the precise public area next.");
                        }}
                      >
                        {item.name} · {item.display_name}
                      </button>
                      <small>
                        source {item.provider} · {item.provider_provenance} · {item.confidence}; tap a public area to confirm
                      </small>
                      {safeHttpsSourceUrl(item.source_url ?? undefined) ? (
                        <a
                          href={safeHttpsSourceUrl(item.source_url ?? undefined)!}
                          target="_blank"
                          rel="noopener noreferrer"
                          data-testid={`bootstrap-city-source-${index}`}
                        >
                          Inspect source
                        </a>
                      ) : null}
                    </li>
                  ))}
                </ul>
              ) : null}
            </div>
            <label>
              <input
                type="checkbox"
                data-testid="bootstrap-map-tile-consent"
                checked={mapTileConsent}
                disabled={!mapFocusCenter && !mapDraftCenter}
                onChange={(event) => setMapTileConsent(event.target.checked)}
              />
              I agree to load OpenStreetMap tiles for this map picker (tiles.openstreetmap.org).
            </label>
            {mapTileConsent && (mapFocusCenter || mapDraftCenter) ? (
              <PublicCityAreaPicker selectedCenter={mapDraftCenter} focusCenter={mapFocusCenter} onSelect={handlePublicMapTap} />
            ) : (
              <p role="status" data-testid="bootstrap-map-tile-not-loaded">
                {!mapFocusCenter && !mapDraftCenter
                  ? "Choose a grounded city result or use the strict OpenStreetMap link below before loading tiles; the map never opens at 0,0."
                  : "No map tiles will load until this separate disclosure is accepted. The strict link route below works without tiles."}
              </p>
            )}
            <label>
              Paste an OpenStreetMap map link (offline fallback)
              <input
                data-testid="bootstrap-osm-map-link"
                value={mapLink}
                onChange={(event) => {
                  setMapLink(event.target.value);
                  setMapLinkMessage(null);
                }}
                inputMode="url"
                placeholder="https://www.openstreetmap.org/#map=13/31.2304/121.4737"
              />
            </label>
            <div className="v8-actions">
              <button type="button" data-testid="bootstrap-osm-map-link-apply" onClick={applyPublicMapLink}>
                Validate map link
              </button>
            </div>
            {mapLinkMessage ? <p role="status" data-testid="bootstrap-osm-map-link-message">{mapLinkMessage}</p> : null}
            {mapDraftCenter ? (
              <p data-testid="bootstrap-public-area-pending">
                Pending public center: {mapDraftCenter.latitude.toFixed(6)}, {mapDraftCenter.longitude.toFixed(6)} · provenance {mapDraftCenter.provenance}
              </p>
            ) : null}
            <div className="v8-actions">
              <button type="button" data-testid="bootstrap-public-area-confirm" disabled={!mapDraftCenter} onClick={confirmPublicArea}>
                Use this public center
              </button>
              <button type="button" data-testid="bootstrap-public-area-cancel" onClick={cancelPublicAreaPicker}>
                Cancel map selection
              </button>
            </div>
          </section>
        ) : null}
        {hasValidSearchCenter ? (
          <div data-testid="bootstrap-selected-center">
            <p>
              Selected public center: {parsedLatitude.toFixed(6)}, {parsedLongitude.toFixed(6)} · source {sourceKind}
              {accuracy != null ? ` · accuracy ${Math.round(accuracy)}m` : ""}
            </p>
            <p>
              {sourceKind === "FOREGROUND_GPS"
                ? "Foreground GPS is held for this search only; it is not saved as presence or a route origin."
                : "This is a user-selected public search center. City relation is unsupported until separately verified; it is not a route origin, presence claim, or proof of arrival."} Provider disclosure remains separate from this selection.
            </p>
          </div>
        ) : (
          <p data-testid="bootstrap-center-required">
            Choose a public map center or deliberately allow foreground GPS before searching. No provider request will be made yet.
          </p>
        )}
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
        <section data-testid="bootstrap-outing-intents" aria-labelledby="bootstrap-outing-intents-title">
          <h2 id="bootstrap-outing-intents-title">What would make this first outing feel good?</h2>
          <p>
            Choose one preference you are declaring for this search. CityNexus sends only the fixed public category below;
            it does not infer a preference or invent a venue.
          </p>
          <div className="v8-actions" role="radiogroup" aria-label="First outing preference">
            {OUTING_INTENTS.map((item) => (
              <button
                key={item.value}
                type="button"
                role="radio"
                aria-checked={outingIntent === item.value}
                aria-pressed={outingIntent === item.value}
                data-testid={`bootstrap-intent-${item.value}`}
                disabled={busy}
                onClick={() => chooseOutingIntent(item.value)}
              >
                {item.label}
              </button>
            ))}
          </div>
          {selectedOutingIntent ? (
            <p data-testid="bootstrap-intent-selected">
              Selected: <strong>{selectedOutingIntent.label}</strong> · bounded public category <code>{selectedOutingIntent.query}</code> · each result should fit because it is tagged as a {selectedOutingIntent.reason}.
            </p>
          ) : (
            <p role="status" data-testid="bootstrap-intent-required">Choose one preference before the one deliberate public discovery action.</p>
          )}
        </section>
        <div className="v8-form-grid">
          <label>
            Latitude (WGS84) · accessible fallback
            <input
              data-testid="bootstrap-latitude"
              inputMode="decimal"
              value={latitude}
              onChange={(event) => editManualCoordinate("latitude", event.target.value)}
            />
          </label>
          <label>
            Longitude (WGS84) · accessible fallback
            <input
              data-testid="bootstrap-longitude"
              inputMode="decimal"
              value={longitude}
              onChange={(event) => editManualCoordinate("longitude", event.target.value)}
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
          <button type="button" data-testid="bootstrap-search" disabled={busy || !hasValidSearchCenter || !selectedOutingIntent} onClick={() => void search()}>
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
                <p data-testid={`bootstrap-intent-reason-${candidate.candidate_id}`}>
                  Fits your declared intent: {selectedOutingIntent?.reason ?? "the selected public category"}.
                </p>
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
                    Source identity: {candidate.opening_source ?? "OpenStreetMap/Overpass"} · {candidate.external_id} · grade {candidate.provider_provenance} · observed {candidate.opening_observed_at ?? "unknown"}
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
                  data-testid={`bootstrap-two-stop-first-${item.shortlist_id}`}
                  disabled={twoStopBusy || shortlistBusy !== null}
                  onClick={() => setTwoStopPosition(item.shortlist_id, 1)}
                >
                  Set as stop 1
                </button>
                <button
                  type="button"
                  data-testid={`bootstrap-two-stop-second-${item.shortlist_id}`}
                  disabled={twoStopBusy || shortlistBusy !== null}
                  onClick={() => setTwoStopPosition(item.shortlist_id, 2)}
                >
                  Set as stop 2
                </button>
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
              {twoStopOrder.includes(item.shortlist_id) ? (
                <p data-testid={`bootstrap-two-stop-selected-${item.shortlist_id}`}>
                  Selected as stop {twoStopOrder.indexOf(item.shortlist_id) + 1}.{" "}
                  <button type="button" onClick={() => clearTwoStopPosition(item.shortlist_id)} disabled={twoStopBusy}>
                    Remove from two-stop order
                  </button>
                </p>
              ) : null}
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
          <section data-testid="bootstrap-two-stop-walk" aria-labelledby="bootstrap-two-stop-title">
            <h3 id="bootstrap-two-stop-title">Build a two-stop city walk</h3>
            <p>
              Choose and order exactly two saved public places. Stop 1 is the destination for the first leg;
              the separate release below shares only the two public POI coordinates for a walking map.
              No foreground location, arrival, route ETA, booking, or Journey start is inferred.
            </p>
            <ol data-testid="bootstrap-two-stop-order">
              {orderedTwoStopItems.length ? orderedTwoStopItems.map((item, index) => (
                <li key={item.shortlist_id}>{index + 1}. {item.name}</li>
              )) : <li>Choose stop 1 and stop 2 from the saved places above.</li>}
            </ol>
            <p data-testid="bootstrap-two-stop-state">
              {orderedTwoStopItems.length === 2
                ? "Two distinct public stops are ready for your explicit walking release."
                : `Choose ${2 - orderedTwoStopItems.length} more saved public place${2 - orderedTwoStopItems.length === 1 ? "" : "s"}.`}
            </p>
            <button
              type="button"
              data-testid="bootstrap-two-stop-open"
              disabled={twoStopBusy || orderedTwoStopItems.length !== 2}
              onClick={() => {
                setTwoStopConsent(false);
                setTwoStopNotice(null);
                setTwoStopWalkabilityConsent(false);
                // The saved pair has not changed. Preserve the latest
                // provider-backed estimate or honest unavailable fallback
                // while the traveler decides whether to open external maps.
              }}
            >
              Prepare public-to-public walking leg
            </button>
            {orderedTwoStopItems.length === 2 ? (
              <div className="journey-membership-map-consent" data-testid="bootstrap-two-stop-consent">
                <p>
                  Fresh one-time consent: send only public stop 1 and public stop 2 to the external walking map.
                  Your current location, foreground GPS, member identity, receipt, query center, and private intent stay withheld.
                </p>
                <label>
                  <input
                    type="checkbox"
                    data-testid="bootstrap-two-stop-consent-checkbox"
                    checked={twoStopConsent}
                    onChange={(event) => setTwoStopConsent(event.target.checked)}
                  />
                  I agree to share these two public stop coordinates now.
                </label>
                <div className="v8-actions">
                  <button
                    type="button"
                    data-testid="bootstrap-two-stop-confirm"
                    disabled={!twoStopConsent || twoStopBusy}
                    onClick={() => void confirmTwoStopWalk()}
                  >
                    {twoStopBusy ? "Opening…" : "Open walking leg to stop 2"}
                  </button>
                  <button
                    type="button"
                    data-testid="bootstrap-two-stop-cancel"
                    disabled={twoStopBusy}
                    onClick={() => {
                      setTwoStopConsent(false);
                      setTwoStopNotice(null);
                      setTwoStopFallbackUrl(null);
                    }}
                  >
                    Cancel release
                  </button>
                </div>
                <div data-testid="bootstrap-two-stop-walkability-consent">
                  <p>
                    Separate feasibility check: share only the two public stop coordinates with the configured pedestrian router.
                    Current location, foreground GPS, member identity, receipt, query center, and private intent stay withheld.
                  </p>
                  <label>
                    <input
                      type="checkbox"
                      data-testid="bootstrap-two-stop-walkability-consent-checkbox"
                      checked={twoStopWalkabilityConsent}
                      onChange={(event) => setTwoStopWalkabilityConsent(event.target.checked)}
                    />
                    I agree to check this public-to-public walking leg now.
                  </label>
                  <button
                    type="button"
                    data-testid="bootstrap-two-stop-walkability-check"
                    disabled={!twoStopWalkabilityConsent || twoStopWalkabilityBusy || twoStopBusy}
                    onClick={() => void checkTwoStopWalkability()}
                  >
                    {twoStopWalkabilityBusy ? "Checking…" : "Check walking feasibility"}
                  </button>
                </div>
              </div>
            ) : null}
            {twoStopWalkability ? (
              <div data-testid="bootstrap-two-stop-walkability" role="status">
                {twoStopWalkability.status === "ROUTE_VERIFIED" ? (
                  <>
                    <p data-testid="bootstrap-two-stop-walkability-result">
                      Walking feasibility: {twoStopWalkability.duration_min} min · {((twoStopWalkability.distance_m ?? 0) / 1000).toFixed(2)} km · {twoStopWalkability.provider} · {twoStopWalkability.provenance}.
                    </p>
                    <p>
                      Observed {twoStopWalkability.observed_at}. This is advisory provider evidence; safety, accessibility, opening, price, arrival, and a guaranteed ETA remain UNKNOWN.
                    </p>
                  </>
                ) : (
                  <p data-testid="bootstrap-two-stop-walkability-result">
                    Cannot verify walkability now ({twoStopWalkability.reason_code ?? "ROUTE_UNVERIFIED"}). {twoStopWalkability.reason ?? "No provider-backed walking route is available."} Use the external public walking map below; no duration or distance was invented.
                  </p>
                )}
                <p>Journey remains draft explore-only; checking this route did not start the Journey.</p>
              </div>
            ) : null}
            {twoStopNotice ? <p role="status" data-testid="bootstrap-two-stop-notice">{twoStopNotice}</p> : null}
            {twoStopFallbackUrl ? (
              <p>
                <a href={twoStopFallbackUrl} target="_blank" rel="noopener noreferrer" data-testid="bootstrap-two-stop-fallback">
                  Open authorized two-stop walking leg
                </a>
              </p>
            ) : null}
            {twoStopWalkability?.status === "ROUTE_UNVERIFIED" && twoStopFallbackUrl ? (
              <p>
                <a href={twoStopFallbackUrl} target="_blank" rel="noopener noreferrer" data-testid="bootstrap-two-stop-walkability-fallback">
                  Open external walking directions
                </a>
              </p>
            ) : null}
            {orderedTwoStopItems.length === 2 && adaptiveAlternativeSecond ? (
              <div data-testid="bootstrap-adaptive-short-walk">
                <h4>Find a better second stop for a short walk</h4>
                <p>
                  Compare the current second stop with one other saved public place using only the three public
                  coordinates. This is an advisory draft check; it does not use your origin or GPS and does not
                  change the plan, arrival, opening, safety, price, or booking state.
                </p>
                <label>
                  Maximum walking time for this leg
                  <select
                    data-testid="bootstrap-adaptive-walk-budget"
                    value={adaptiveWalkBudget === null ? "" : String(adaptiveWalkBudget)}
                    onChange={(event) => {
                      const value = event.target.value;
                      setAdaptiveWalkBudget(value ? Number(value) : null);
                      setAdaptiveWalkConsent(false);
                      setAdaptiveWalkComparison(null);
                    }}
                  >
                    <option value="">Choose a maximum</option>
                    {[15, 20, 30, 45].map((minutes) => (
                      <option key={minutes} value={minutes}>{minutes} minutes</option>
                    ))}
                  </select>
                </label>
                <p>
                  Alternative candidate: <strong>{adaptiveAlternativeSecond.name}</strong>. The current second stop is
                  <strong> {orderedTwoStopItems[1].name}</strong>.
                </p>
                <label>
                  <input
                    type="checkbox"
                    data-testid="bootstrap-adaptive-walk-consent-checkbox"
                    checked={adaptiveWalkConsent}
                    onChange={(event) => setAdaptiveWalkConsent(event.target.checked)}
                  />
                  I agree to compare these three public stop coordinates now.
                </label>
                <button
                  type="button"
                  data-testid="bootstrap-adaptive-walk-check"
                  disabled={adaptiveWalkBudget === null || !adaptiveWalkConsent || adaptiveWalkBusy || twoStopBusy}
                  onClick={() => void checkAdaptiveShortWalk()}
                >
                  {adaptiveWalkBusy ? "Comparing…" : "Compare short-walk options"}
                </button>
                {adaptiveWalkComparison ? (
                  <div data-testid="bootstrap-adaptive-walk-result" role="status">
                    {adaptiveWalkComparison.route_state === "COMPARISON_VERIFIED" ? (
                      <>
                        <p>
                          Current second stop: {adaptiveWalkComparison.current_leg.duration_min} min estimated · alternative: {adaptiveWalkComparison.alternative_leg.duration_min} min estimated · {adaptiveWalkComparison.recommendation_state}.
                        </p>
                        <p>
                          Current evidence: {adaptiveWalkComparison.current_leg.provider} · {adaptiveWalkComparison.current_leg.provenance} · observed {adaptiveWalkComparison.current_leg.observed_at}. Alternative evidence: {adaptiveWalkComparison.alternative_leg.provider} · {adaptiveWalkComparison.alternative_leg.provenance} · observed {adaptiveWalkComparison.alternative_leg.observed_at}.
                        </p>
                        <ul>
                          {[...adaptiveWalkComparison.current_leg.route_caveats, ...adaptiveWalkComparison.alternative_leg.route_caveats]
                            .filter((caveat, index, caveats) => caveats.indexOf(caveat) === index)
                            .map((caveat) => <li key={caveat}>{caveat}</li>)}
                        </ul>
                        <p>{adaptiveWalkComparison.recommendation_reason}</p>
                        <p>
                          This provider evidence is advisory. Safety, accessibility, opening, price, arrival, and a guaranteed ETA remain UNKNOWN; the Journey remains a draft and no plan or booking was created.
                        </p>
                        {adaptiveWalkComparison.suggested_second_shortlist_id ? (
                          <button
                            type="button"
                            data-testid="bootstrap-adaptive-choose-alternative"
                            onClick={chooseAdaptiveAlternative}
                          >
                            Choose this better second stop
                          </button>
                        ) : null}
                      </>
                    ) : (
                      <>
                        <p>
                          ROUTE_UNVERIFIED: {adaptiveWalkComparison.current_leg.reason_code ?? "No current-leg route evidence"}; {adaptiveWalkComparison.alternative_leg.reason_code ?? "no alternative-leg route evidence"}. No duration or distance was invented.
                        </p>
                        <p>
                          Current source: {adaptiveWalkComparison.current_leg.provider ?? "none"} · observed {adaptiveWalkComparison.current_leg.observed_at}; alternative source: {adaptiveWalkComparison.alternative_leg.provider ?? "none"} · observed {adaptiveWalkComparison.alternative_leg.observed_at}.
                        </p>
                        <ul>
                          {[...adaptiveWalkComparison.current_leg.route_caveats, ...adaptiveWalkComparison.alternative_leg.route_caveats]
                            .filter((caveat, index, caveats) => caveats.indexOf(caveat) === index)
                            .map((caveat) => <li key={caveat}>{caveat}</li>)}
                        </ul>
                        <p>{adaptiveWalkComparison.recommendation_reason} Use either external public walking map below after a fresh consent.</p>
                        <p>
                          <a href={adaptiveWalkComparison.navigation_url} target="_blank" rel="noopener noreferrer" data-testid="bootstrap-adaptive-current-fallback">
                            Open current public walking map
                          </a>{" "}
                          <a href={adaptiveWalkComparison.alternative_navigation_url} target="_blank" rel="noopener noreferrer" data-testid="bootstrap-adaptive-alternative-fallback">
                            Open alternative public walking map
                          </a>
                        </p>
                      </>
                    )}
                    <p>Comparison is private to this signed member and remains DRAFT_EXPLORE_ONLY.</p>
                  </div>
                ) : null}
              </div>
            ) : null}
          </section>
        </section>
      </section>
    </main>
  );
}
