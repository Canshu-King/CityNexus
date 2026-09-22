import { useEffect, useMemo, useRef, useState } from "react";
import "maplibre-gl/dist/maplibre-gl.css";
import type { FeatureCollection } from "geojson";
import type { V8Data } from "../../app/v8Types";
import { useT, useLocale } from "../../i18n/LocaleContext";

/**
 * ORD-0082 ④: the map's own "there is nothing to centre this on" condition, as a pure function of
 * the same fields the point list reads.  Exported because one viewport used to hold two
 * contradictory answers -- the map panel saying this trip has no trustworthy coordinates while the
 * attention band beside it said "一切正常".  One screen, one rule.
 */
export function tripHasNoCoordinates(data: V8Data | null): boolean {
  if (!data) return true;
  const locatedActivity = (data.active_plan?.activities ?? []).some(
    (item) => item.metadata.longitude != null && item.metadata.latitude != null,
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
}: {
  data: V8Data | null;
  option: V8Data["options"][number] | null;
  /** ORD-0082 ④: only the map knows whether it found *something to centre on* -- route geometry
      counts, and a trip with no located activity can still have a route.  Attention needs that
      same answer or one screen can say "没有可信的坐标" and "一切正常" at once. */
  onNoLocationChange?: ((value: boolean) => void) | null;
}) {
  const host = useRef<HTMLDivElement | null>(null);
  // Map truth: never centre on a hardcoded city.  If the Journey has no
  // trustworthy coordinates we say so explicitly instead of silently showing
  // an unrelated city (design corrections §10).
  const [noLocation, setNoLocation] = useState(false);
  /* A blocked or offline raster tile server used to degrade silently to the flat
     canvas underneath, which is exactly what reads as "the map is just a picture".
     The fallback stays, but it is now named. */
  const [tilesUnavailable, setTilesUnavailable] = useState(false);
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
    if (data?.active_plan?.legs.length)
      return data.active_plan.legs.map((leg, index) => tag(leg.geometry, leg.mode, index));
    if (!data || !option) return [];
    return option.leg_mode_map.flatMap((leg, index) => {
      const fact = data.mobility_facts.find(
        (item) =>
          item.from_key === leg.from_key &&
          item.to_key === leg.to_key &&
          item.mode === leg.mode,
      );
      return fact?.geometry ? [tag(fact.geometry, leg.mode, index)] : [];
    });
  }, [data, option]);
  const routeModes = useMemo(
    () =>
      Array.from(
        new Set(route.map((feature) => String(feature.properties?.mode ?? "")).filter(Boolean)),
      ),
    [route],
  );
  const points = useMemo(() => {
    const active =
      data?.active_plan?.activities.flatMap((item) =>
        item.metadata.longitude != null && item.metadata.latitude != null
          ? [
              {
                title: item.title,
                longitude: item.metadata.longitude,
                latitude: item.metadata.latitude,
                role: item.metadata.role,
                protected: item.protected,
                current: item.id === data?.active_plan?.current_activity_id,
                disrupted:
                  data?.active_plan?.disruptions.some(
                    (event) => event.affected_activity_id === item.id,
                  ) ?? false,
              },
            ]
          : [],
      ) ?? [];
    if (active.length) return active;
    if (!data) return [];
    return data.offers.slice(0, 1).map((offer) => ({
      title: offer.property_name,
      longitude: offer.location.longitude,
      latitude: offer.location.latitude,
      role: "STAY",
      protected: false,
      current: false,
      disrupted: false,
    }));
  }, [data]);

  useEffect(() => {
    let disposed = false;
    let map: import("maplibre-gl").Map | null = null;
    let resizeObserver: ResizeObserver | null = null;
    void import("maplibre-gl").then(({ default: maplibregl }) => {
      if (disposed || !host.current) return;
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
            tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
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
         must not be a *silent* one: with every tile blocked the panel looked like a
         picture of a map rather than a map that failed to load its basemap. */
      mapInstance.on("error", (event) => {
        const source = (event as { sourceId?: string }).sourceId;
        if (source === "open-street-map") setTilesUnavailable(true);
      });
      mapInstance.on("load", () => {
        const raster = mapInstance.getSource("open-street-map") as
          | { tiles?: { has: (v: unknown) => boolean; size?: number }[]; cache?: { has: (v: unknown) => boolean } }
          | undefined;
        const loaded = raster?.tiles?.some((bucket) => typeof bucket?.has === "function" && bucket.size !== 0);
        if (loaded === false) setTilesUnavailable(true);
      });
      map = mapInstance;
      /* Test seam.  maplibre keeps its instance off the DOM, but the acceptance
         gate has to read the camera to prove a gesture actually moved it — a
         rendered-frame diff alone cannot say *why* nothing changed.  Exposing the
         instance on the container is the smallest surface that does it, and nothing
         in the app reads it back. */
      (host.current as (HTMLElement & { citynexusMap?: unknown })).citynexusMap = mapInstance;
      resizeObserver = new ResizeObserver(() => map?.resize());
      resizeObserver.observe(host.current);
    points.forEach((point, index) => {
      const marker = document.createElement("div");
      marker.className = `v9-map-marker ${point.role === "STAY" ? "stay" : ""} ${point.protected ? "protected" : ""} ${point.current ? "current" : ""} ${point.disrupted ? "disrupted" : ""}`;
      marker.textContent = String(index + 1);
      marker.setAttribute("aria-label", point.title);
        new maplibregl.Marker({ element: marker })
        .setLngLat([point.longitude, point.latitude])
        .addTo(mapInstance);
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
    if (coordinates.length > 1) {
      const bounds = coordinates
        .slice(1)
        .reduce(
          (value, coordinate) => value.extend(coordinate as [number, number]),
          new maplibregl.LngLatBounds(
            coordinates[0] as [number, number],
            coordinates[0] as [number, number],
          ),
        );
      const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      /* The route-context caption floats over the bottom of the canvas, so a
         uniform 42px padding let the last marker sit underneath it (pass-9
         blocker #1). The fix tells the camera how much of its own viewport the
         overlay occupies, rather than raising the marker's z-index so the two
         elements take turns bullying each other. */
      const caption = host.current?.parentElement?.querySelector(
        ".v8-map-caption",
      ) as HTMLElement | null;
      const captionHeight = caption?.getBoundingClientRect().height ?? 0;
      const side = 42;
      const safetyGap = 16;
      mapInstance.fitBounds(bounds, {
        padding: {
          top: side,
          right: side,
          bottom: side + captionHeight + safetyGap,
          left: side,
        },
        maxZoom: 13,
        duration: reducedMotion ? 0 : 650,
      });
    }
    });
    return () => {
      disposed = true;
      resizeObserver?.disconnect();
      map?.remove();
    };
  }, [data, points, route]);
  if (noLocation) {
    return (
      <div
        className="v8-map-panel v8-map-empty"
        data-testid="v8-map-empty"
        role="status"
        aria-live="polite"
      >
        <div className="v8-map-empty-body">
          <b>{locale.startsWith("zh") ? "尚未获取地图位置" : "No map location yet"}</b>
          <p>
            {locale.startsWith("zh")
              ? "这个行程还没有可信的坐标。添加活动地点或开启定位后，地图会显示正确的城市。"
              : "This trip has no trustworthy coordinates yet. Add located activities or enable location, and the map will show the right city."}
          </p>
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
      {tilesUnavailable && (
        /* Requirement 3 of ORD-0037: the flat canvas behind the raster tiles is the
           right degradation, but saying nothing is what made the panel read as a
           picture someone had drawn rather than a map that failed to fetch one. */
          <p className="v8-map-tile-notice" data-testid="v8-map-tile-notice" role="status">
            {locale.startsWith("zh")
              ? "底图未加载，显示的是路线示意。"
              : "Basemap did not load — showing the route diagram only."}
          </p>
        )}
      <div className="v8-map-caption">
        <span className="status-dot" />
        {t("mapComp.routeContext")} <b>{t("mapComp.legs", { n: route.length })}</b>
        <span className="v8-sr-only">{t("mapComp.providerRoute")}</span>
      </div>
      <p className="v8-map-gesture-hint" data-testid="v8-map-gesture-hint">
        {locale.startsWith("zh")
          ? "单指拖动地图 · 双指缩放 · 想翻这一页就拖地图以外的地方"
          : "One finger drags the map · two fingers zoom · to move the page, drag outside the map"}
      </p>
    </div>
  );
}
