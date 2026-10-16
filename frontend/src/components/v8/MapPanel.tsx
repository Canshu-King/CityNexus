import { useEffect, useMemo, useRef, useState } from "react";
import "maplibre-gl/dist/maplibre-gl.css";
import type { FeatureCollection } from "geojson";
import type { ActivityCoordinate, V8Data } from "../../app/v8Types";
import { useT, useLocale } from "../../i18n/LocaleContext";
import { mapCopy } from "../../i18n/mapPanelCopy";
import { MapViewportControls, type ViewportState } from "./MapViewportControls";
import { formatStampDay, stampForActivity, type FootprintState } from "../../features/checkin/footprintRead";
import { placeLabels, stopLabel, type LabelBox } from "../../lib/mapStopLabels";
import "../../map-attribution.css";
import "../../map-selection.css";
import "../../map-stop-labels.css";

/* WP-D: the basemap's address, written once. Two surfaces need it now -- the style document that asks
   for tiles, and the retry that asks the same server again -- and two literals would be two chances to
   name a host this panel never actually called. */
const BASEMAP_TILE_URL = "https://tile.openstreetmap.org/{z}/{x}/{y}.png";
/* Named twice on purpose -- the URL above and this host -- and tied to each other by measurement rather
   than by a parse the reader has to trust: `e2e/qoder-butugong-wpd-basemap-degraded.spec.ts` compares
   this attribute against the host of every tile request the arm actually made. If the two literals ever
   disagree, that arm goes red; a `slice()` of the URL would only agree with itself. */
const BASEMAP_HOST = "tile.openstreetmap.org";

/**
 * WP-D: the one rule for "the word this stop may be called by on the glass", shared by the pin and by
 * the degraded stop list.
 *
 * ORD-0512 chose the field and ORD-0415 decided what of it may be painted; that rule already lived here
 * as three lines inside the build effect. It is lifted into a function because the list has to say the
 * SAME word as the pin it stands for -- a second copy is how a pin and its own row can end up
 * disagreeing about one stop, and the gates that judge forbidden words off the glass read both.
 */
export function stopGlassWord(
  point: { title?: string; place_name?: string | null },
  index: number,
): string {
  const label = stopLabel(point);
  if (label) return label.text;
  const hadAName = `${point.place_name ?? ""}${point.title ?? ""}`.trim().length > 0;
  return hadAName ? String(index + 1) : (point.title ?? "");
}

/**
 * ORD-0394: the one rule for "does this activity have a place on the map".
 *
 * It reads `location`, which the server joins off the place row the activity names, and it returns
 * the system the number is written in alongside it.  Six call sites used to test
 * `metadata.longitude/latitude` -- a pair the backend has never once sent (0 of 140 activity rows),
 * so every one of those branches had only ever taken the "no coordinate" path on real data.  One
 * exported predicate instead, because a rule with six copies is six chances to drift.
 */
export function activityCoordinate(item: {
  location?: ActivityCoordinate | null;
}): { latitude: number; longitude: number; coordinate_system: string | null } | null {
  const location = item.location;
  if (!location || location.latitude == null || location.longitude == null) return null;
  // A number past the WGS84 range is not a place: it drops a pin in nowhere and the map paints that
  // as fact. The server already refuses these on the way in (backend/app/schemas.py, `GeoPoint`);
  // the render path refuses them too, so "this activity has a coordinate" means the same thing
  // wherever it is asked.
  if (
    location.latitude < -90 || location.latitude > 90 ||
    location.longitude < -180 || location.longitude > 180
  ) {
    return null;
  }
  return {
    latitude: location.latitude,
    longitude: location.longitude,
    coordinate_system: location.coordinate_system,
  };
}

/**
 * ORD-0465: the map's own input, named instead of borrowing all of `V8Data`.
 *
 * This is a widening, not a change of behaviour: every field below is one of the six the component
 * actually reads (`active_plan.activities/legs/disruptions/current_activity_id/user_location`, `offers`,
 * `mobility_facts`, `provider_mesh.mobility`), every existing call site still passes a full `V8Data`,
 * and a `V8Data` satisfies this type unchanged.
 *
 * It exists because the share-receiving screen has stops and coordinates and none of the rest.  Under
 * the old prop it had to either take `V8Data` whole -- which means inventing a party size and two
 * owner-only flags for a trip this device does not own -- or cast.  `locked` and `protected` are the
 * owner's editing facts and the share door deliberately does not send them
 * (`backend/app/schemas.py`, `SharedStop`), so the honest rendering is a marker with no commitment
 * ring, not a ring drawn from a `false` nobody was told.
 */
export type MapPlottableActivity = {
  id: string;
  title: string;
  /**
   * ORD-0512: the place row's own name, when the door this surface reads happens to send it.
   * `backend/app/schemas.py` (`SharedStop`) sends it and states the screen rule — place name first,
   * the plan's `title` only when there is no name — so the map asks for it and paints accordingly.
   * The owner's v8 read sends none of it (measured: `Activity` in `backend/app/schemas.py` has no such
   * field), and an absent field is the plan's own word being used, not a missing fact papered over.
   */
  place_name?: string | null;
  metadata?: { latitude?: number; longitude?: number; crs?: string; role?: string } | null;
  location?: ActivityCoordinate | null;
  protected?: boolean;
};

export type MapPanelInput = {
  active_plan: {
    current_activity_id?: string | null;
    activities: MapPlottableActivity[];
    legs?: Array<{ mode: string; geometry: V8Data["mobility_facts"][number]["geometry"] }>;
    disruptions?: Array<{ affected_activity_id: string | null }>;
    user_location?: {
      latitude: number;
      longitude: number;
      accuracy_m: number;
      captured_at: string;
      source: string;
    } | null;
  } | null;
  offers?: Array<{
    property_name: string;
    location: { latitude: number | null; longitude: number | null };
  }>;
  mobility_facts?: V8Data["mobility_facts"];
  provider_mesh?: Record<string, any>;
};

/**
 * ORD-0082 ④: the map's own "there is nothing to centre this on" condition, as a pure function of
 * the same fields the point list reads.  Exported because one viewport used to hold two
 * contradictory answers -- the map panel saying this trip has no trustworthy coordinates while the
 * attention band beside it said "一切正常".  One screen, one rule.
 */
export function tripHasNoCoordinates(data: MapPanelInput | null): boolean {
  if (!data) return true;
  const locatedActivity = (data.active_plan?.activities ?? []).some(
    (item) => activityCoordinate(item) != null,
  );
  if (locatedActivity) return false;
  return (data.offers ?? []).some(
    (offer) => offer.location.longitude != null && offer.location.latitude != null,
  ) === false;
}

export function MapPanel({
  data,
  option,
  onNoLocationChange = null,
  selectedActivityId = null,
  onSelectActivity = null,
  footprints = null,
  onlyStamped = false,
}: {
  data: MapPanelInput | null;
  option: V8Data["options"][number] | null;
  /** ORD-0082 ④: only the map knows whether it found *something to centre on* -- route geometry
      counts, and a trip with no located activity can still have a route.  Attention needs that
      same answer or one screen can say "没有可信的坐标" and "一切正常" at once. */
  onNoLocationChange?: ((value: boolean) => void) | null;
  /** ORD-0390: the map does not own a selection.  This is the same `detailActivityId` the trips
      list and `ActivityDetail` already read, so one stop can be selected in exactly one place. */
  selectedActivityId?: string | null;
  /** ORD-0390: called with the activity id a marker stands for, or null to clear.  A stay offer
      that has no plan activity reports null rather than inventing an id. */
  onSelectActivity?: ((id: string | null) => void) | null;
  /**
   * ORD-0497: the footprint *read*, held by the surface that asked and passed down -- the map keeps
   * no footprint of its own.  `null` means this surface never asked (the hub, Live, the share
   * screen), and the map then paints exactly what it painted before this prop existed: no hollow
   * pins, no dates, no claim.  Only the `read` arm is allowed to distinguish solid from hollow;
   * `refused` / `unreachable` / `not_asked` fall to the same silence, because a pin that went hollow
   * on a failed read would be the map answering for a server that never answered.
   */
  footprints?: FootprintState | null;
  /**
   * ORD-0497: 「只看打过」. Lives with the surface that owns the read, not in a library and not in a
   * database -- the order rules that the switch state is never written down, and this prop is the
   * whole of its travel.  On, it hides the pins the read returned no stamp for; it never hides a pin
   * the read did not answer about (`footprints` not on its `read` arm ⇒ the switch is not offered at
   * all, see the row in V8Experience).  Hiding is `visibility`, never removal:
   * `e2e/qoder-map-ord0390-selection-both-ways.spec.ts` and
   * `e2e/qoder-ord0394-map-coordinates.spec.ts` count pins and rows as the proof that every
   * located stop can still be picked, and ORD-0453 already settled that a filter is a clip, not a
   * deletion.
   */
  onlyStamped?: boolean;
}) {
  const host = useRef<HTMLDivElement | null>(null);
  /* ORD-0390: the marker elements and the map instance are kept in refs so a selection change can
     restyle a marker and move the camera without tearing the map down and rebuilding it — the
     rebuild path is `useEffect([data, points, route])` below, and panning through it would reset
     the zoom the traveller just chose. */
  const mapRef = useRef<import("maplibre-gl").Map | null>(null);
  const markerEls = useRef<{ el: HTMLElement; id: string | null; at: [number, number] | null }[]>([]);
  /* ORD-0497: the date badges are maplibre markers of their own, appended and removed by
     `applyFootprints` -- never children of a pin, because
     `e2e/qoder-map-ord0403-named-control-and-labels.spec.ts` asserts a pin paints nothing but
     its stop number. Kept in a ref so a footprint read that lands after the map was built can restyle
     the pins without tearing the map down (the camera-reset lesson of ORD-0390 right above). */
  const stampBadges = useRef<import("maplibre-gl").Marker[]>([]);
  /* ORD-0512: the stop's word beside the pin. Its own markers for the reason the badges have their own
     (a pin paints only its number), and its own refs for the reason the pins have theirs: fitting the
     words to the glass is a placement pass over the current camera, so it restyles elements rather than
     rebuilding the map — rebuilding to re-fit text would reset the zoom the traveller just chose. */
  const labelNodes = useRef<
    {
      el: HTMLElement;
      marker: import("maplibre-gl").Marker;
      key: string;
      at: [number, number];
      priority: number;
      order: number;
    }[]
  >([]);
  const labelMarkers = useRef<import("maplibre-gl").Marker[]>([]);
  const applyLabelsRef = useRef<() => void>(() => {});
  /* maplibre is loaded by dynamic import inside the build effect, so the only handle on its
     `Marker` class is the one that effect can hand out.  The badges need it, and nothing else does. */
  const maplibreRef = useRef<{ Marker: typeof import("maplibre-gl").Marker } | null>(null);
  /* The read and the filter are both re-applied, never rebuilt: refs so the map-building effect can
     call the current version of `applyFootprints` without making either one of them a dependency of
     the camera. */
  const footprintsRef = useRef<FootprintState | null>(footprints);
  const filterRef = useRef<boolean>(onlyStamped);
  const applyFootprintsRef = useRef<() => void>(() => {});
  footprintsRef.current = footprints;
  filterRef.current = onlyStamped;
  /* The click handlers are attached inside the map-building effect, which deliberately does not
     depend on `onSelectActivity` (rebuilding the map to rebind a callback would reset the camera).
     A ref keeps the handler current without making the camera its hostage. */
  const selectRef = useRef(onSelectActivity);
  selectRef.current = onSelectActivity;
  /* The same hostage problem one line above, on the other side of the marker: the build effect reads
     `selectedActivityId` when it paints `aria-pressed`, and markers are created after the map reports
     itself ready — seconds after the render that scheduled the build.  A selection that already exists
     by then (a pick restored on boot) was therefore painted from the older render's value, so the glass
     named the stop while every pin answered `aria-pressed=false`, and nothing re-painted it until the
     traveller clicked.  Measured: restored pick → pins all false at 0/1.5/3/6 s; one click → correct.
     A ref keeps the pressed state current without making the camera hostage to it. */
  const selectedRef = useRef(selectedActivityId);
  selectedRef.current = selectedActivityId;
  // Map truth: never centre on a hardcoded city.  If the Journey has no
  // trustworthy coordinates we say so explicitly instead of silently showing
  // an unrelated city (design corrections §10).
  const [noLocation, setNoLocation] = useState(false);
  /* A blocked or offline raster tile server used to degrade silently to the flat
     canvas underneath, which is exactly what reads as "the map is just a picture".
     The fallback stays, but it is now named. */
  const [tilesUnavailable, setTilesUnavailable] = useState(false);
  /* WP-D: two facts the degradation surface speaks that the flag alone cannot carry.
     `basemapRetries` is what the traveller has already asked for, so a second and third failed attempt
     reads as "still no answer" rather than as a screen that never moved; it is cleared by the same arm
     that clears the flag, because a count of a basemap that has since drawn is a claim about a failure
     that no longer exists.
     `degradedStopsOpen` is the tile-independent view, and it is off by default: the plate's height comes
     straight out of the glass the pins and their names are placed on (`.v8-map-degraded` is reserved
     ground in `applyLabels`), so an always-open list would push names off the map for a traveller who
     never asked for a list. */
  const [basemapRetries, setBasemapRetries] = useState(0);
  const [degradedStopsOpen, setDegradedStopsOpen] = useState(false);
  /* ORD-0403: one control, and the control carries its own state. `targetRef` is the point the
     camera was last asked to frame — the whole journey, or a single selected stop — and
     `viewportState` says whether the camera is still on it. It is recomputed from the camera on
     every move/zoom end, so what changes the label is the map actually moving, not a flag set at
     click time that could drift away from what is on screen. */
  const [viewportState, setViewportState] = useState<ViewportState>("on-target");
  const targetRef = useRef<{ lng: number; lat: number } | null>(null);
  const refitRef = useRef<(() => void) | null>(null);
  const t = useT();
  const { locale } = useLocale();
  const route = useMemo(() => {
    /* Stamp the travel mode and the leg order onto the feature so the line layer has
       something to group by.  Measured: the provider's geometry already carries
       `properties.mode` ({"crs":"WGS84","mode":"AUTO",...}), so for today's data this
       re-states what is already there.  It stays because the grouping is what stops
       "一根大线": a provider that omits the key would otherwise collapse every leg onto
       the fallback colour and nothing on screen would say the style had degraded. */
    const tag = (
      feature: { type: "Feature"; properties?: Record<string, unknown>; geometry: { type: "LineString"; coordinates: number[][] } },
      mode: string,
      index: number,
    ) => ({
      ...feature,
      properties: { ...(feature.properties ?? {}), mode, leg_index: index },
    });
    if (data?.active_plan?.legs?.length)
      return data.active_plan.legs.map((leg, index) => tag(leg.geometry, leg.mode, index));
    if (!data || !option) return [];
    return option.leg_mode_map.flatMap((leg, index) => {
      const fact = (data.mobility_facts ?? []).find(
        (item) =>
          item.from_key === leg.from_key &&
          item.to_key === leg.to_key &&
          item.mode === leg.mode,
      );
      return fact?.geometry ? [tag(fact.geometry, leg.mode, index)] : [];
    });
  }, [data, option]);
  /* ORD-0418: which sentence the caption is allowed to speak. `route.length` is the same predicate the
     line layer above already uses, so the words and the drawn geometry cannot disagree -- a second
     condition would be a second truth. The provider status is read from the payload's own
     `provider_mesh.mobility`, and only from the two entries that can actually produce a leg geometry
     (valhalla and amap): the mesh also carries transit_realtime and ride_hail, whose statuses are
     UNKNOWN_REALTIME / UNKNOWN_COST on this deployment and say nothing about routing. Treating every
     mobility entry as a routing provider would have kept the sharper sentence permanently unreachable
     -- measured, not assumed. */
  const noRoutingProvider = (() => {
    const mobility = data?.provider_mesh?.mobility;
    if (!mobility || typeof mobility !== "object") return false;
    const routers = ["valhalla", "amap"]
      .map((key) => (mobility as Record<string, { status?: unknown }>)[key])
      .filter((entry) => entry);
    return routers.length > 0 && routers.every((entry) => entry.status === "NOT_CONFIGURED");
  })();
  const routeModes = useMemo(
    () =>
      Array.from(
        new Set(route.map((feature) => String(feature.properties?.mode ?? "")).filter(Boolean)),
      ),
    [route],
  );
  const points = useMemo(() => {
    const active =
      data?.active_plan?.activities.flatMap((item) => {
        const at = activityCoordinate(item);
        return at
          ? [
              {
                id: item.id as string | null,
                title: item.title,
                place_name: item.place_name ?? null,
                longitude: at.longitude,
                latitude: at.latitude,
                role: item.metadata?.role,
                protected: item.protected === true,
                current: item.id === data?.active_plan?.current_activity_id,
                disrupted:
                  (data?.active_plan?.disruptions ?? []).some(
                    (event) => event.affected_activity_id === item.id,
                  ) ?? false,
              },
            ]
          : [];
      }) ?? [];
    if (active.length) return active;
    if (!data) return [];
    return (data.offers ?? []).slice(0, 1).map((offer) => ({
      // A stay offer is not a plan activity, so it has no id to select.  Inventing one would let a
      // marker claim a selection the trips list cannot show.
      id: null as string | null,
      title: offer.property_name,
      // A stay offer carries the property's own name, which is exactly what `title` holds here; there
      // is no separate place row behind it, so the name source stays the plan's word.
      place_name: null,
      longitude: offer.location.longitude,
      latitude: offer.location.latitude,
      role: "STAY",
      protected: false,
      current: false,
      disrupted: false,
    }));
  }, [data]);

  /* ORD-0417: the stop the shared selection currently names, so the glass can say which one a finger
     just landed on.  Read off the same two values the selection effect below reads (`points` and
     `selectedActivityId`), because the map does not own a selection -- ORD-0390.  A stay offer has no
     activity id, so it selects nothing and this stays null rather than inventing a name to paint. */
  const selectedPoint = useMemo(
    () => points.find((point) => point.id && point.id === selectedActivityId) ?? null,
    [points, selectedActivityId],
  );

  useEffect(() => {
    let disposed = false;
    let map: import("maplibre-gl").Map | null = null;
    let resizeObserver: ResizeObserver | null = null;
    void import("maplibre-gl").then(({ default: maplibregl }) => {
      if (disposed || !host.current) return;
      maplibreRef.current = maplibregl;
      const coordinates = route
        .flatMap((feature) => feature.geometry.coordinates)
        .filter((value) => value.length >= 2);
      const center: [number, number] | null =
        (coordinates[Math.floor(coordinates.length / 2)] as [number, number] | undefined) ??
        (points[0] ? [points[0].longitude, points[0].latitude] : null);
      if (!center) {
        // No route geometry and no located activity: an honest empty state is
        // the correct answer, not another city's map.
        setNoLocation(true);
        onNoLocationChange?.(true);
        return;
      }
      setNoLocation(false);
      onNoLocationChange?.(false);
      /* Read the app's own palette out of the document rather than inventing a
         second set of literals inside the map style: the route lines then follow
         the light/dark binding the rest of the product already uses. */
      const css = getComputedStyle(document.documentElement);
      const token = (name: string, fallback: string) =>
        css.getPropertyValue(name).trim() || fallback;
      const routePalette: Record<string, string> = {
        WALK: token("--cn-accent", "#0a66ff"),
        TRANSIT: token("--cn-success", "#248a3d"),
        AUTO: token("--cn-warning", "#b06000"),
        TRAIN: token("--v8-violet", "#8063d7"),
      };
      const routeFallbackColour = token("--cn-accent-text", "#0a5cd6");
      const casingColour = token("--v8-panel", "#ffffff");
      const modesPresent = Array.from(new Set(route.map((feature) => String(feature.properties?.mode ?? ""))));
      const lineCases: unknown[] = ["case"];
      for (const mode of modesPresent) {
        lineCases.push(["==", ["get", "mode"], mode], routePalette[mode] ?? routeFallbackColour);
      }
      lineCases.push(routeFallbackColour);
      const lineColour = lineCases.length > 2 ? lineCases : routeFallbackColour;
      const mapInstance = new maplibregl.Map({
        /* Never leave the traveller staring at an empty box when the tile
           server is unreachable (common on restricted networks). The Apple
           branch's GeoJSON typing fix dropped this line along with the comment
           that explained it; maplibre's own default happens to be false, but an
           accessibility-relevant intent belongs in the source, not in an
           implicit library default. maplibre's shipped MapOptions type omits
           this documented constructor flag, hence the narrow cast at the end of
           the options object. */
        failIfMajorPerformanceCaveat: false,
        container: host.current,
      style: {
        version: 8,
        sources: {
          "open-street-map": {
            type: "raster",
            tiles: [BASEMAP_TILE_URL],
            tileSize: 256,
            attribution: t("mapComp.attribution"),
          },
          // A flat canvas behind the raster tiles means a blocked or offline
          // tile server degrades to a readable route view instead of a blank
          // white rectangle.
          "base-canvas": {
            type: "geojson",
            data: { type: "FeatureCollection", features: [] },
          },
          "journey-provider-route": {
            type: "geojson",
            data: {
              type: "FeatureCollection",
              features: route,
            } as FeatureCollection,
          },
        },
        layers: [
          {
            id: "canvas",
            type: "background",
            paint: { "background-color": "#dfeae8" },
          },
          {
            id: "open-street-map",
            type: "raster",
            source: "open-street-map",
            paint: { "raster-opacity": 0.82 },
          },
          {
            /* A casing underneath so the line stays readable on a pale raster the
               same way a road label keeps its outline. */
            id: "journey-provider-route-casing",
            type: "line",
            source: "journey-provider-route",
            paint: {
              "line-color": casingColour,
              "line-width": [
                "interpolate", ["exponential", 1.3], ["zoom"],
                8, 3,
                12, 6,
                16, 11,
              ],
              "line-opacity": 0.95,
            },
          },
          {
            /* Was a single #4658d9 stroke at a fixed 4px for every leg, which is
               what read as "one big line". Colour now follows the travel mode and
               width follows the zoom level. */
            id: "journey-provider-route",
            type: "line",
            source: "journey-provider-route",
            paint: {
              "line-color": lineColour as unknown as string,
              "line-width": [
                "interpolate", ["exponential", 1.3], ["zoom"],
                8, 1.5,
                12, 3.5,
                16, 7,
              ],
              "line-opacity": 0.9,
            },
          },
        ],
      },
      center: center as [number, number],
      zoom: 11,
      attributionControl: false,
      /* `interactive: false` here switched off drag, zoom, rotate and pitch at once,
         which is why the panel behaved like a static image.  Rotation and pitch stay off
         because a tilted, spun city view is not readable on a phone and nothing in this
         product depends on it.

         ORD-0134 ②: `cooperativeGestures: true` is what made the panel dead under a finger.
         It asks for two fingers to pan, and on the phones we tested one finger then does
         neither thing -- the map refuses the drag and the page above it does not take it
         either (measured: twelve of twelve one-finger swipes starting on the canvas moved
         the page 0px, and the camera with it).  A traveller's words were "滑不动，用力滑就滑到
         旁边的面板".  Single-finger drag therefore belongs to the map again, and the page is
         scrolled from the page -- which is the ownership rule the new gate measures both ways. */
      interactive: true,
      dragRotate: false,
      pitchWithRotate: false,
      touchPitch: false,
      maxPitch: 0,
      } as maplibregl.MapOptions & { failIfMajorPerformanceCaveat?: boolean });
      /* The flat canvas behind the raster tiles is the right degradation, but it
         must not be a *silent* one: with every tile blocked the panel looked like a picture of a map
         rather than a map that failed to load its basemap.
         r2 (屏读工-0415) — the sentence was raised by a predicate that cannot answer the question. It
         read `raster.tiles` as a tile cache, but for a raster source that array holds the tile URL
         templates (`typeof tiles[0] === "string"`, measured), so `some(bucket => typeof bucket.has ===
         "function" …)` is false whether the basemap draws or not, and 「底图未加载」 was painted on every
         load — measured over a drawn basemap with 6 of 22 tile requests answered 200. `tileload` is not
         a way out: it fires zero times on both arms of the control (6/6 tiles drawn, and 6/6 aborted),
         while `error` fires exactly on the aborted arm. So the claim is now carried by the one signal
         that separates the arms — did any basemap tile come back — and it can go both ways. */
      const basemapTileDrawn = () =>
        performance.getEntriesByType("resource").some((entry) => {
          const e = entry as PerformanceResourceTiming;
          return /tile\.openstreetmap\.org/.test(e.name) && e.responseStatus >= 200 && e.responseStatus < 400;
        });
      mapInstance.on("error", (event) => {
        const source = (event as { sourceId?: string }).sourceId;
        if (source === "open-street-map" && !basemapTileDrawn()) setTilesUnavailable(true);
      });
      mapInstance.on("idle", () => {
        if (basemapTileDrawn()) {
          setTilesUnavailable(false);
          setBasemapRetries(0);
        }
      });
      map = mapInstance;
      mapRef.current = mapInstance;
      /* Test seam.  maplibre keeps its instance off the DOM, but the acceptance
         gate has to read the camera to prove a gesture actually moved it — a
         rendered-frame diff alone cannot say *why* nothing changed.  Exposing the
         instance on the container is the smallest surface that does it, and nothing
         in the app reads it back. */
      (host.current as (HTMLElement & { citynexusMap?: unknown })).citynexusMap = mapInstance;
      resizeObserver = new ResizeObserver(() => map?.resize());
      resizeObserver.observe(host.current);
    /* A rebuild replaces the map instance, so every element that was added to the old one goes with it;
       `marker.remove()` on nodes of a removed map is a no-op at best, and these arrays are the only
       handles the panel keeps on them. */
    for (const marker of labelMarkers.current) marker.remove();
    labelMarkers.current = [];
    labelNodes.current = [];
    markerEls.current = [];
    points.forEach((point, index) => {
      /* ORD-0512 chose the field; ORD-0415 decides what of that field may reach the glass, and the
         accepted map gates read a marker's `aria-label` as part of the judged corpus
         (`qoder-map-ord0403-*.spec.ts`, `qoder-map-ord0412-*.spec.ts`). The rule itself is in
         `stopGlassWord` above, because the degraded stop list has to name a stop exactly as its pin
         does -- two copies of this sentence is how the two would drift apart. */
      const label = stopLabel(point);
      const marker = document.createElement("div");
      marker.className = `v9-map-marker ${point.role === "STAY" ? "stay" : ""} ${point.protected ? "protected" : ""} ${point.current ? "current" : ""} ${point.disrupted ? "disrupted" : ""}`;
      marker.textContent = String(index + 1);
      marker.setAttribute("aria-label", stopGlassWord(point, index));
      /* ORD-0390: a marker used to be a painted dot — `aria-label` for a screen reader and nothing
         else.  It is now a real button that selects the stop it stands for, and `aria-pressed`
         carries the shared selection so the state is readable without a class-name convention.
         Keyboard is wired alongside pointer because a map-only affordance is unreachable on a
         keyboard; the hit area is the marker box itself, which the narrow-width gate measures. */
      marker.setAttribute("role", "button");
      marker.tabIndex = 0;
      marker.setAttribute("aria-pressed", String(!!point.id && point.id === selectedRef.current));
      /* The class is the painted half of the same state (`map-selection.css`), and the build path
         set only the attribute, so a selection that existed before the markers were created announced
         itself to a screen reader and not to the eye. */
      if (point.id && point.id === selectedRef.current) marker.classList.add("selected");
      const choose = () => selectRef.current?.(point.id ?? null);
      marker.addEventListener("click", choose);
      marker.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          choose();
        }
      });
      markerEls.current.push({ el: marker, id: point.id, at: [point.longitude, point.latitude] });
        new maplibregl.Marker({ element: marker })
        .setLngLat([point.longitude, point.latitude])
        .addTo(mapInstance);
      /* ORD-0512: the name itself, on the glass. `aria-hidden` is not a loss of information — the pin
         beside it is a button whose accessible name is already this stop's word, so announcing the chip
         as well would read every stop twice. What the chip adds is what an eye can use and a screen
         reader never needed: which number is which place, without tapping.
         ORD-0415: a stop whose word is entirely forbidden gets no chip at all rather than a word the
         rule rejects -- the pin, its hit target and its node stay, which is what the accepted map gates
         count as the proof a located stop is still pickable. */
      if (label) {
        const chip = document.createElement("div");
        chip.className = "v8-map-stop-label";
        chip.setAttribute("data-testid", "v8-map-stop-label");
        chip.setAttribute("data-stop-ordinal", String(index + 1));
        chip.setAttribute("data-name-source", label.from);
        /* Which classes were taken out of this word, in an attribute and not on the glass: a machine
           word belongs in an attribute (the same convention `data-placement` follows), and it is the
           only reading that tells a gate the rule fired rather than the data happening to be clean. */
        chip.setAttribute("data-forbidden-removed", label.removed.join(",") || "nothing");
        chip.setAttribute("aria-hidden", "true");
        chip.textContent = label.text;
        const at: [number, number] = [point.longitude, point.latitude];
        const chipMarker = new maplibregl.Marker({ element: chip })
          .setLngLat(at)
          .addTo(mapInstance);
        labelMarkers.current.push(chipMarker);
        labelNodes.current.push({
          el: chip,
          marker: chipMarker,
          key: point.id ?? `stay-${index}`,
          at,
          priority: point.id && point.id === selectedRef.current ? 3 : point.current ? 2 : 1,
          order: index,
        });
      }
    });
    if (data?.active_plan?.user_location) {
      const user = document.createElement("div");
      user.className = "v9-map-marker user";
      user.textContent = "●";
      user.setAttribute(
        "aria-label",
        t("mapComp.yourLocation", { n: Math.round(data.active_plan.user_location.accuracy_m) }),
      );
      new maplibregl.Marker({ element: user })
        .setLngLat([
          data.active_plan.user_location.longitude,
          data.active_plan.user_location.latitude,
        ])
        .addTo(mapInstance);
    }
    /* ORD-0497: a map that has just been built is a set of brand-new pin elements, which carry no
       footprint class until somebody paints them.  This is that somebody, and it is called here as
       well as from the effect below because the read usually lands while the map already exists --
       but on a first mount the two arrive in the other order, and a screen that showed hollow pins
       only after the traveller panned would be a second, timing-dependent truth. */
    applyFootprintsRef.current();
    /* ORD-0410: what the journey's view is framed on — the route geometry when there is any, and
       otherwise the stops this panel just painted markers for.  Gating this on route coordinates
       alone made the whole block conditional on a journey having leg geometry, so a journey with
       located stops and no legs never got a `refitRef.current` at all: the named control rendered,
       took the press, called `refitRef.current?.()` into a null, and did nothing without an
       exception.  The fallback is the same set of positions the traveller can see, which keeps the
       one-definition rule below intact instead of inventing a second "journey's view" for the
       button. */
    const framePositions: number[][] =
      coordinates.length > 1
        ? coordinates
        : points.map((point) => [point.longitude, point.latitude]);
    if (framePositions.length > 0) {
      const bounds = framePositions
        .slice(1)
        .reduce(
          (value, coordinate) => value.extend(coordinate as [number, number]),
          new maplibregl.LngLatBounds(
            framePositions[0] as [number, number],
            framePositions[0] as [number, number],
          ),
        );
      const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      /* The route-context caption floats over the bottom of the canvas, so a
         uniform 42px padding let the last marker sit underneath it (pass-9
         blocker #1). The fix tells the camera how much of its own viewport the
         overlay occupies, rather than raising the marker's z-index so the two
         elements take turns bullying each other.
         ORD-A: that overlay is now the whole stack (bubble + caption + notice), so the camera is
         told about all of it — measuring only the caption would re-open the hole the comment above
         describes, one element at a time. */
      const overlay = host.current?.parentElement?.querySelector(
        ".v8-map-overlay-stack, .v8-map-caption",
      ) as HTMLElement | null;
      const overlayHeight = overlay?.getBoundingClientRect().height ?? 0;
      const side = 42;
      const safetyGap = 16;
      /* The same call the reset button re-runs, kept as a closure so "back to the journey's view"
         reframes exactly what the first fit framed — same padding, same maxZoom — instead of
         inventing a second definition of the journey's view somewhere else.
         WP-D: the TOP edge is measured when the call runs rather than captured here, because the bottom
         band is already painted when the map is built and the degraded plate is not — it arrives with
         a tile error, after the first fit. A height frozen at build time let the plate stand on every
         stop name: measured on this lane's own run, names shown on the glass fell from five to zero the
         moment the plate appeared. Reading it at call time means the same closure frames the journey
         into whatever ground the panel has actually left free. */
      const fitToJourney = () => {
        const plate = host.current?.parentElement?.querySelector(
          ".v8-map-degraded",
        ) as HTMLElement | null;
        const plateHeight = plate?.getBoundingClientRect().height ?? 0;
        /* The plate is only paid for when the camera can still be given glass to frame into. This panel
           reserves 42 px on the sides, 42 + the bottom band + 16 at the foot, so once the plate is taller
           than what is left there is no honest answer to give — maplibre crams the journey in anyway and
           the pins end up under the plate (measured: 8 of 9 under a 180 px plate). Ignoring a plate that
           does not fit keeps the framing the traveller was promised; the plate's own height budget is
           enforced in `cn-pulse-map.css` so this arm is the backstop and not the plan. */
        const canvasHeight = host.current?.getBoundingClientRect().height ?? 0;
        const roomForPlate =
          plateHeight > 0 &&
          canvasHeight -
            (side + plateHeight + safetyGap) -
            (side + overlayHeight + safetyGap) >=
          40;
        return mapInstance.fitBounds(bounds, {
          padding: {
            /* Exactly `side` when there is no plate. Writing `side + 0 + safetyGap` for the empty case
               looked harmless and moved the untouched tip's camera from zoom 9.446 to 9.277 -- the
               two-arm table caught it as a change on a screen where nothing was supposed to change. */
            top: roomForPlate ? side + plateHeight + safetyGap : side,
            right: side,
            bottom: side + overlayHeight + safetyGap,
            left: side,
          },
          maxZoom: 13,
          duration: reducedMotion ? 0 : 650,
        });
      };
      refitRef.current = () => {
        refitPending = true;
        fitToJourney();
      };
      /* The initial framing is this same call — it was lost once when the direct `fitBounds` was
         turned into a closure, which is how a map can come up centred on a midpoint nobody asked
         for. Calling it here also seeds the target below on its first moveend. */
      fitToJourney();
    }
    /* Distance is measured in projected pixels, not degrees, so the tolerance means the same
       physical thing at every zoom level and every latitude. */
    /* Declared out here because both the framing block above and this listener need it: a fit we
       asked for is what redefines the target, and the flag has to survive the block that ran it. */
    let refitPending = true;
    const TOLERANCE_PX = 24;
    const syncViewportState = () => {
      /* A fit we asked for defines what "on target" means, so the target is recorded from the
         camera once that fit settles. `bounds.getCenter()` would be wrong here: the fit is given
         extra bottom padding for the overlay stack, so the camera deliberately settles north of
         the geometric centre, and a correctly framed journey would have been reported as lost. */
      if (refitPending) {
        refitPending = false;
        const settled = mapInstance.getCenter();
        targetRef.current = { lng: settled.lng, lat: settled.lat };
        setViewportState("on-target");
        return;
      }
      const target = targetRef.current;
      if (!target) return;
      const want = mapInstance.project([target.lng, target.lat]);
      const have = mapInstance.project([mapInstance.getCenter().lng, mapInstance.getCenter().lat]);
      const next: ViewportState =
        Math.hypot(want.x - have.x, want.y - have.y) > TOLERANCE_PX ? "off-target" : "on-target";
      setViewportState((prev) => (prev === next ? prev : next));
    };
    mapInstance.on("moveend", syncViewportState);
    mapInstance.on("zoomend", syncViewportState);
    /* Fitting the names is a job the camera owns: the boxes that collide are screen boxes, so they
       change on every pan and zoom. Scheduled through one animation frame because `move`/`zoom` fire
       per frame and measuring a dozen chips per frame is layout thrash the traveller would feel.
       The first fit goes through the same schedule rather than running here: a marker that maplibre
       has not yet transformed has a rect of its own choosing, and reading it this early would hide
       every name behind whatever box the unpositioned nodes happened to share. */
    let labelFrame = 0;
    const scheduleLabelFit = () => {
      if (labelFrame) return;
      labelFrame = window.requestAnimationFrame(() => {
        labelFrame = 0;
        if (disposed) return;
        applyLabelsRef.current();
      });
    };
    mapInstance.on("move", scheduleLabelFit);
    mapInstance.on("zoom", scheduleLabelFit);
    scheduleLabelFit();
    /* The pass that follows maplibre's first render, when every marker has a transform on it — the one
       frame where this panel can tell a name that does not fit from a name it has not placed yet. */
    mapInstance.once("render", scheduleLabelFit);
    });
    return () => {
      disposed = true;
      resizeObserver?.disconnect();
      /* ORD-0497: the badges are markers on this map instance, so they go with it -- while it is
         still there to take them. Doing it after `map.remove()` would be removing nodes from a map
         that no longer has a container to remove them from. */
      for (const badge of stampBadges.current) badge.remove();
      stampBadges.current = [];
      for (const marker of labelMarkers.current) marker.remove();
      labelMarkers.current = [];
      labelNodes.current = [];
      map?.remove();
      mapRef.current = null;
      maplibreRef.current = null;
      markerEls.current = [];
    };
  }, [data, points, route]);

  /* ORD-0497 -- paint the footprint read onto the pins that already exist.
   *
   * Three rules this function is the only place for:
   *   1. only a `read` arm paints. A `refused` / `unreachable` / `not_asked` read, or no read at all
   *      (the hub, Live, the share screen), leaves every pin exactly as it was drawn -- the map does
   *      not answer for a server that did not;
   *   2. a stamp is matched by the server's own `target_key` (`stampForActivity`), never by a title
   *      or an index, so a renamed stop cannot move a stamp onto a neighbour;
   *   3. 「只看打过」 only ever removes pins the read answered "no stamp" about. Stamped pins, stay
   *      offers and the traveller's own dot are never filtered, and filtering hides by visibility:
   *      the node stays in the document, because the accepted map gates count pins and rows as the
   *      proof that a located stop is still pickable.
   */
  const applyFootprints = () => {
    const read = footprintsRef.current?.kind === "read" ? footprintsRef.current : null;
    const only = filterRef.current;
    const map = mapRef.current;
    const maplibre = maplibreRef.current;
    for (const badge of stampBadges.current) badge.remove();
    stampBadges.current = [];
    for (const entry of markerEls.current) {
      entry.el.classList.remove("stamped", "un-stamped", "filtered-out");
      if (!read || !entry.id) continue;
      const stamp = stampForActivity(read, entry.id);
      if (!stamp) {
        entry.el.classList.add("un-stamped");
        if (only) entry.el.classList.add("filtered-out");
        continue;
      }
      entry.el.classList.add("stamped");
      if (!map || !maplibre || !entry.at) continue;
      /* The day goes beside the pin, not inside it: `e2e/qoder-map-ord0403-named-control-and-labels
         .spec.ts` asserts a pin paints nothing but its stop number, and a child node would
         break that with the text it adds. Date only, never a clock -- `formatStampDay` names the
         glass rule that forbids one. */
      const badge = document.createElement("div");
      badge.className = "v8-map-stamp-date";
      badge.setAttribute("data-testid", `map-stamp-date-${entry.id}`);
      const day = formatStampDay(locale, stamp.stamped_at);
      badge.textContent = day;
      badge.setAttribute("aria-label", mapCopy(locale, "footprintBadgeAria").replace("%s", day));
      stampBadges.current.push(
        new maplibre.Marker({ element: badge, anchor: "top", offset: [0, 15] })
          .setLngLat(entry.at)
          .addTo(map),
      );
    }
  };
  applyFootprintsRef.current = applyFootprints;
  /* ORD-0512 — fit the names to the glass this camera is showing, and say why each one is not shown.
   *
   * The blockers are measured, never assumed: the map surface is the frame, and whatever the panel has
   * already painted on top of the map (the basemap attribution the ORD-A obligation requires, the
   * caption/notice stack, the named control, the gesture bubble) is reserved ground. A name underneath
   * one of those is not on the glass, and a name that eats the attribution takes away the traveller's
   * only route to the tile licence.
   */
  /* The chip clears its pin's own 28 px box by a few pixels, and the same number is used on every side
     so a name flipped left or dropped below does not sit closer than one that stayed right. */
  const LABEL_GAP_PX = 18;
  /* The order the ruling gave this family: right of the pin, then left, then under it. A third side is
     the cheapest extra word there is -- it costs no truncation and no wrapped line -- so it is tried
     before a name is hidden at all. */
  const LABEL_SIDES = ["right", "left", "under"] as const;
  const applyLabels = () => {
    const canvas = host.current;
    const panel = canvas?.closest(".v8-map-panel") ?? null;
    const map = mapRef.current;
    if (!canvas || !panel || !map) return;
    const at = canvas.getBoundingClientRect();
    const frame: LabelBox = { x: at.x, y: at.y, w: at.width, h: at.height };
    const reserved: LabelBox[] = Array.from(
      panel.querySelectorAll<HTMLElement>(
        [
          "[data-testid='v8-map-attribution']",
          ".v8-map-overlay-stack",
          ".v8-map-caption",
          ".v8-map-tile-notice",
          /* WP-D: the degraded plate is the widest thing this panel has ever painted over the glass, so
             it is reserved ground the same way the notice it contains is. Left out of this list a stop
             name would legally land under 「底图没能加载」, and no gate would notice. */
          ".v8-map-degraded",
          "[data-testid='v8-map-gesture-hint']",
          "[data-testid='map-viewport-reset']",
        ].join(", "),
      ),
    )
      .map((el) => el.getBoundingClientRect())
      .filter((box) => box.width > 0 && box.height > 0)
      .map((box) => ({ x: box.x, y: box.y, w: box.width, h: box.height }));
    /* All three sides are built from the pin's anchor point rather than measured off the element, because
       the element sits wherever the *previous* fit put it -- its width is stable, its position is not. */
    const candidates = labelNodes.current.map((node) => {
      const size = node.el.getBoundingClientRect();
      const pin = map.project(node.at);
      const cx = frame.x + pin.x;
      const cy = frame.y + pin.y;
      return {
        id: node.key,
        sides: [
          { x: cx + LABEL_GAP_PX, y: cy - size.height / 2, w: size.width, h: size.height },
          { x: cx - LABEL_GAP_PX - size.width, y: cy - size.height / 2, w: size.width, h: size.height },
          { x: cx - size.width / 2, y: cy + LABEL_GAP_PX, w: size.width, h: size.height },
        ],
        priority: node.priority,
        order: node.order,
      };
    });
    const verdicts = placeLabels(candidates, frame, reserved);
    for (const node of labelNodes.current) {
      /* `data-placement` carries the reason and `data-side` the branch that was used: both are facts
         about this camera, not about the stop, and a machine word belongs in an attribute -- which is
         where this family already puts them. */
      const verdict = verdicts.get(node.key)
        ?? { placement: "no_box" as const, side: 0, fits: [], blocked_by: null };
      const size = node.el.getBoundingClientRect();
      const pin = map.project(node.at);
      const reach = LABEL_GAP_PX + size.width / 2;
      const drop = LABEL_GAP_PX + size.height / 2;
      const side = LABEL_SIDES[verdict.side] ?? LABEL_SIDES[0];
      node.marker.setOffset(side === "under" ? [0, drop] : side === "left" ? [-reach, 0] : [reach, 0]);
      node.el.setAttribute("data-placement", verdict.placement);
      node.el.setAttribute("data-side", side);
      /* which side would have held the word, and what was standing there instead -- said per side so
         "no room on this map" and "a neighbour took the room" are two different readings on the glass,
         not one attribute that covers both. */
      node.el.setAttribute("data-fits-right", String(verdict.fits[0] === true));
      node.el.setAttribute("data-fits-left", String(verdict.fits[1] === true));
      node.el.setAttribute("data-fits-under", String(verdict.fits[2] === true));
      node.el.setAttribute("data-blocked-by", verdict.blocked_by ?? "nothing");
      node.el.classList.toggle("label-hidden", verdict.placement !== "shown");
    }
  };
  applyLabelsRef.current = applyLabels;
  /* Re-fit, never rebuild. A pick changes which name outranks the others, a language change makes
     every word longer or shorter, and a footprint read can add a date badge the labels have to live
     with — none of those is a reason to move the camera.
     WP-D adds the two states that change the glass without changing the data: the plate arriving, and
     the stop list opening inside it. Both are ground the placement pass has to be told about, and a
     stale pass is how a name ends up painted underneath a surface that is standing on it. */
  useEffect(() => {
    applyLabelsRef.current();
  }, [selectedActivityId, points, locale, footprints, onlyStamped, tilesUnavailable, degradedStopsOpen]);
  /* Re-paint, never rebuild: the read can arrive after the map, the switch can flip at any moment,
     and a language change changes the badge's words. None of those is a reason to reset the camera,
     which is why this is a separate effect on the same refs ORD-0390 established. */
  useEffect(() => {
    applyFootprintsRef.current();
  }, [footprints, onlyStamped, points, locale]);

  /* ORD-0390, the reverse half of the link: a selection made anywhere else (the trips card's
     「在地图上显示」, or a sibling stop in the detail sheet) has to move this camera.  It is a
     separate effect on purpose — the map-building effect above keys on data/points/route, and
     rebuilding to pan would throw away the zoom the traveller just set.  `easeTo` rather than
     `fitBounds` because the question is "where is this stop", not "reframe the whole plan". */
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    const chosen = points.find((point) => point.id && point.id === selectedActivityId) ?? null;
    for (const marker of markerEls.current) {
      const on = !!chosen && marker.id === chosen.id;
      marker.el.classList.toggle("selected", on);
      marker.el.setAttribute("aria-pressed", String(on));
    }
    if (!chosen) return;
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    targetRef.current = { lng: chosen.longitude, lat: chosen.latitude };
    map.easeTo({
      center: [chosen.longitude, chosen.latitude],
      duration: reducedMotion ? 0 : 450,
    });
  }, [selectedActivityId, points]);
  /* WP-D: when the plate arrives, the journey is reframed into the ground that is left.
   *
   * Reframing on ARRIVAL only. When the tiles come back the plate leaves the map more glass than it had,
   * so nothing is occluded and the camera stays wherever the traveller put it — moving it to reclaim
   * space nobody asked about would be the panel spending the user's view on its own cleanup.
   * `refitRef` is the same closure the named control presses, so this is the journey's view by one
   * definition rather than a second one invented for the failure path. */
  useEffect(() => {
    if (tilesUnavailable) refitRef.current?.();
  }, [tilesUnavailable]);

  /* WP-D: what 「再取底图」 does, and what it deliberately does not do.
   *
   * maplibre's `Source.setTiles` runs `setSourceProperty`, which re-creates the tile set and reloads the
   * source (`load(true)` in `maplibre-gl` 5.24) — the public way to ask the same server again without
   * tearing the map down, and therefore without throwing away the camera the traveller just panned or
   * zoomed. Rebuilding instead would also work, and would cost the traveller their view for a retry they
   * asked to be about the basemap only.
   *
   * The URL is passed UNCHANGED on purpose. A cache-busting query would make every retry miss the browser
   * cache and re-hit a shared public tile server for bytes it may already hold; the retry is meant to
   * re-open the network path, not to multiply traffic.
   *
   * The count only moves when a reload was actually issued. Counting a press that found no source would
   * put 「已经再取过 N 次」 on the glass for an attempt that never left the page. */
  const retryBasemap = () => {
    const source = mapRef.current?.getSource("open-street-map") as
      | { setTiles?: (tiles: string[]) => void }
      | undefined;
    if (!source?.setTiles) return;
    setBasemapRetries((n) => n + 1);
    source.setTiles([BASEMAP_TILE_URL]);
  };

  if (noLocation) {
    return (
      <div
        className="v8-map-panel v8-map-empty"
        data-testid="v8-map-empty"
        /* ORD-0407 ①: the tier this cell is in, named the way ORD-0359 names a tier -- the sentence
           carries the words, the attribute carries the code. NOT_AVAILABLE is measured, not asserted:
           see the note on `noLocationBody` in i18n/mapPanelCopy.ts. */
        data-cnx-activity-entry="NOT_AVAILABLE"
        role="status"
        aria-live="polite"
      >
        <div className="v8-map-empty-body">
          <b>{mapCopy(locale, "noLocationTitle")}</b>
          <p>{mapCopy(locale, "noLocationBody")}</p>
        </div>
      </div>
    );
  }

  return (
    <div
      className="v8-map-panel"
      data-testid="v8-maplibre-panel"
      data-route-legs={route.length}
      data-route-modes={routeModes.join(" ")}
      aria-label={t("mapComp.journeyMap")}
    >
      <div ref={host} className="v8-maplibre-canvas" data-testid="v8-maplibre-canvas" />
      <MapViewportControls
        state={viewportState}
        onResetView={() => refitRef.current?.()}
        labels={{
          resetToJourney: mapCopy(locale, "viewportResetToJourney"),
          onTarget: mapCopy(locale, "viewportOnTarget"),
          offTarget: mapCopy(locale, "viewportOffTarget"),
        }}
      />
      {tilesUnavailable && (
        /* WP-D. Requirement 3 of ORD-0037 named the defect this block still answers: the flat canvas
           behind the raster tiles is the right degradation, but saying nothing is what made the panel
           read as a picture someone had drawn. The one-line notice did say that much, and it is kept
           byte-for-byte (`tileNotice`, and its class and test identity, which
           `e2e/qoder-map-ord0403-*.spec.ts:213` measures and `e2e/qoder-0512-*.spec.ts:711` borrows) —
           what it could not do is answer the three questions a traveller actually has standing in front
           of a blank map: WHAT refused, WHETHER the trip survived, and WHAT to do now.
           So this is a surface, not a toast: the cause names the class that failed (network or tile
           source) and the tile host rides in `data-cnx-basemap-host` beside the permanent ORD-A
           attribution line that already names it on the glass; the evidence quotes the panel's own
           `points.length` (the same array that painted the pins, so the sentence cannot be true while
           the stops it counts are missing); and the two exits are a retry that asks that host again and
           a stop list that needs no tiles at all.
           No placeholder tile is painted anywhere — a local stand-in would be the map claiming to have
           loaded a basemap it never got, which is the defect this order exists to remove.
           `NOT_AVAILABLE` is the tier word `data-cnx-activity-entry` already uses on this component's
           empty state, not a new vocabulary; the human sentence above carries the specifics. */
        <div
          className="v8-map-degraded"
          data-testid="v8-map-degraded"
          data-cnx-basemap="NOT_AVAILABLE"
          data-cnx-basemap-host={BASEMAP_HOST}
          data-cnx-basemap-retries={basemapRetries}
          data-cnx-basemap-stops={points.length}
        >
          {/* The shipped ORD-0037 sentence stays in the document, keeps its class, its test identity and
              its `role="status"`, and is no longer painted. That is a real decision and it is worth the
              words: this panel leaves the camera 153 px of glass (pins measured at relative 59..187 of a
              392 px panel, the bottom 139 px already the caption band, the top 61 px the named control),
              and with both sentences drawn the plate measured 113 px tall and stood on seven of the nine
              pins. The headline below says what this line says -- the basemap is not there, the journey
              still is -- and this line still answers a screen reader, so no traveller is left without the
              sentence; the ones who read it get it in a plate that does not eat the map. */}
          <p className="v8-map-tile-notice" data-testid="v8-map-tile-notice" role="status">
            {mapCopy(locale, "tileNotice")}
          </p>
          <b className="v8-map-degraded-headline">
            {points.length > 0
              ? mapCopy(locale, "degradedHeadline").replace("%s", String(points.length))
              : mapCopy(locale, "degradedHeadlineNoStops")}
          </b>
          {/* One row for the two exits, sharing the headline's line where the width allows. Their bottom
              edge has to stay above the canvas's vertical centre, where four accepted map gates put a
              finger (`qoder-map-gesture-ownership`, `qoder-map-interaction`, `qoder-map-ord0403`,
              `qoder-0512` all drag there). */}
          <div className="v8-map-degraded-actions">
            <button
              type="button"
              className="v8-map-degraded-btn"
              data-testid="v8-map-degraded-retry"
              data-contrast-role="control"
              onClick={retryBasemap}
            >
              {mapCopy(locale, "degradedRetry")}
            </button>
            {points.length > 0 && (
              <button
                type="button"
                className="v8-map-degraded-btn v8-map-degraded-btn--quiet"
                data-testid="v8-map-degraded-stops-toggle"
                data-contrast-role="control"
                aria-expanded={degradedStopsOpen}
                onClick={() => setDegradedStopsOpen((open) => !open)}
              >
                {mapCopy(locale, degradedStopsOpen ? "degradedStopsClose" : "degradedStopsOpen")}
              </button>
            )}
          </div>
          {basemapRetries > 0 && (
            <p className="v8-map-degraded-retried">
              {mapCopy(locale, "degradedRetried").replace("%s", String(basemapRetries))}
            </p>
          )}
          {/* The tile-independent view. It is a press away rather than permanent because its height comes
              straight out of the same 153 px: a list always open would bury the journey the plate is
              standing in front of, and the traveller who opens it has chosen the text for a moment.
              The rows ARE the pins, in the same order under the same numbers -- `stopGlassWord` is the
              shared rule, so a row cannot name a stop its own pin is not allowed to name. They read and
              do not navigate: this panel's pins are already the pickable surface, and a second set of
              pickable rows would be a second selection owner on one screen (ORD-0390: a stop is picked
              in exactly one place). */}
          {degradedStopsOpen && (
            <div className="v8-map-degraded-stops-wrap">
              <ol className="v8-map-degraded-stops">
                {points.map((point, index) => (
                  <li
                    key={point.id ?? `stay-${index}`}
                    className="v8-map-degraded-stop"
                    data-current={String(point.current)}
                  >
                    <span className="v8-map-degraded-ordinal">{index + 1}</span>
                    <span className="v8-map-degraded-stop-word">{stopGlassWord(point, index)}</span>
                  </li>
                ))}
              </ol>
            </div>
          )}
        </div>
      )}
      {/* ORD-A: the caption and the gesture bubble used to be positioned independently
          (`.v8-map-caption` bottom:12px, `.v8-map-gesture-hint` bottom:calc(40px + safe-area)), which
          was fine while the caption was one line. Adding the basemap notice made it two, and the
          bubble then painted over the notice at every width from 320 to 414 — measured, not guessed
          (2,513–3,316 px² of overlap). One bottom-anchored stack removes the whole class of bug
          instead of nudging one offset. */}
      <div className="v8-map-overlay-stack">
        <p className="v8-map-gesture-hint" data-testid="v8-map-gesture-hint">
          {mapCopy(locale, "gestureHint")}
        </p>
        <div className="v8-map-caption">
          {/* ORD-0417: the answer to a tap on a pin, painted on the glass the tap happened on.  The
              name used to live only in the pin's `aria-label`, so a traveller whose eyes work got a
              number and no name; the card that does name the stop is below the panel, and reaching it
              means the page scrolling away from the surface the finger is on.
              It goes inside the caption rather than as another block in the stack, and that placement
              is the load-bearing part of this change.  The stack is the box `fitBounds` measures its
              bottom padding against -- once, with nothing selected, paying `side + overlayHeight +
              safetyGap`.  A line added to the stack, or permanently reserved there, raises the band's
              top edge into ground the framing was promised: this lane's gate measured both, a
              conditional stack line covering three pins at 139->184 px and a reserved one still
              covering a pin at 390x844 that the untouched tip leaves clear.  Text laid out in the line
              box the caption already owns is the form that costs no band height; the `geometry-*` arms
              of `e2e/qoder-ord0417-tap-names-the-stop.spec.ts` measure it rather than assume it. */}
          {selectedPoint && (
            <span className="v8-map-selected-stop" data-testid="v8-map-selected-stop">
              {t("mapComp.selectedStopOnMap", { name: selectedPoint.title })}
            </span>
          )}
          <span className="status-dot" />
          {t("mapComp.routeContext")} <b>{t("mapComp.legs", { n: route.length })}</b>
          {/* ORD-0418: "供应商支持的路线" is a claim about where the geometry came from, so it may
              only be spoken -- and read aloud, this span is `v8-sr-only` -- when there is geometry
              at all. With zero legs the server holds no route, and saying "provider-backed" anyway
              handed the traveller a promise no request had earned. */}
          {route.length > 0 ? (
            <span className="v8-sr-only">{t("mapComp.providerRoute")}</span>
          ) : noRoutingProvider ? (
            <span className="v8-sr-only">{t("mapComp.noRouteNoProvider")}</span>
          ) : (
            <span className="v8-sr-only">{t("mapComp.noRouteNotRouted")}</span>
          )}
          {/* ORD-A: the basemap is fetched from tile.openstreetmap.org, so the notice belongs on the
              glass. `attributionControl:false` above means maplibre will not draw it, and the
              source's own `attribution` field only reaches the style document — invisible to a
              traveller. It inherits the caption's colour, so light/dark needs no rule here. */}
          <span className="v8-map-attribution" data-testid="v8-map-attribution">
            {mapCopy(locale, "attributionRaster")}
          </span>
        </div>
      </div>
    </div>
  );
}
