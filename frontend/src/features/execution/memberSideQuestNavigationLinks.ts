import type { MemberSideQuestNavigationTarget } from "../../api/citynexus";

function exactWgs84Coordinates(target: MemberSideQuestNavigationTarget): [number, number] {
  const { latitude, longitude } = target;
  if (
    target.coordinate_system.trim().toUpperCase() !== "WGS84"
    || typeof latitude !== "number"
    || typeof longitude !== "number"
    || !Number.isFinite(latitude)
    || !Number.isFinite(longitude)
    || latitude < -90
    || latitude > 90
    || longitude < -180
    || longitude > 180
  ) {
    throw new Error("An exact WGS84 map pin is unavailable.");
  }
  return [latitude, longitude];
}

export function buildGoogleWalkingDirectionsUrl(target: MemberSideQuestNavigationTarget): string {
  const [latitude, longitude] = exactWgs84Coordinates(target);
  const url = new URL("https://www.google.com/maps/dir/");
  url.searchParams.set("api", "1");
  // Google Maps accepts a destination label or a comma-separated coordinate
  // pair. Use coordinates as the actual route target; keep the authorized
  // place label separate so it cannot change geocoding of the exact pin.
  url.searchParams.set("destination", `${latitude},${longitude}`);
  url.searchParams.set("destination_label", target.name);
  url.searchParams.set("travelmode", "walking");
  return url.toString();
}

export function buildOpenStreetMapPinUrl(target: MemberSideQuestNavigationTarget): string {
  const [latitude, longitude] = exactWgs84Coordinates(target);
  const zoom = 18;
  const url = new URL("https://www.openstreetmap.org/");
  url.searchParams.set("mlat", String(latitude));
  url.searchParams.set("mlon", String(longitude));
  url.searchParams.set("zoom", String(zoom));
  url.hash = `map=${zoom}/${latitude}/${longitude}`;
  return url.toString();
}
