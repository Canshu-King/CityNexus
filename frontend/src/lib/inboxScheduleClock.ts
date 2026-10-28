/* Conversion between the stored schedule instants and what a datetime-local input shows.

   Policy (ORD-0553-r2): the stored schedule keeps whichever offset the server stamped on
   it ("Z" or "+hh:mm"; a bare wall is treated as "+08:00", matching what the save path has
   always written back).  The input speaks the traveller device's local wall clock.  Both
   directions convert through the instant, so a device inside the stored offset sees the
   same digits it always saw, and any other device sees its own wall clock for the same
   moment instead of a foreign clock silently relabelled as local.

   deviceOffsetMinutes defaults to the runtime zone so callers need not know it; the arm
   passes explicit values to read other devices' screens without moving the machine clock. */

const pad2 = (n: number): string => String(n).padStart(2, "0");

const defaultDeviceOffsetMinutes = (): number => -new Date().getTimezoneOffset();

export function zoneSuffixOf(value: string): string {
  const m = value.match(/(Z|([+-])(\d{2}):?(\d{2}))$/);
  if (!m) return "+08:00";
  return m[1] === "Z" ? "Z" : `${m[2]}${m[3]}:${m[4]}`;
}

/** Stored instant -> device-local wall "YYYY-MM-DDTHH:mm" for the input's value. */
export function storedToLocalWall(value: string, deviceOffsetMinutes?: number): string {
  if (!value) return "";
  const off = deviceOffsetMinutes ?? defaultDeviceOffsetMinutes();
  const anchored = /(Z|[+-]\d{2}:?\d{2})$/.test(value) ? value : `${value}:00+08:00`;
  const instant = Date.parse(anchored);
  if (Number.isNaN(instant)) return value.replace(/Z$/, "").slice(0, 16);
  const d = new Date(instant + off * 60000);
  return `${d.getUTCFullYear()}-${pad2(d.getUTCMonth() + 1)}-${pad2(d.getUTCDate())}T${pad2(d.getUTCHours())}:${pad2(d.getUTCMinutes())}`;
}

/** Device-local wall from the input -> the stored shape, rewritten in the stored zone. */
export function localWallToStored(wall: string, zone: string, deviceOffsetMinutes?: number): string {
  const m = wall.match(/^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})/);
  if (!m) return wall;
  const off = deviceOffsetMinutes ?? defaultDeviceOffsetMinutes();
  const om = zone === "Z" ? null : zone.match(/^([+-])(\d{2}):(\d{2})$/);
  if (zone !== "Z" && !om) return `${wall}:00+08:00`;
  const [, y, mo, da, hh, mi] = m;
  const instant = Date.UTC(Number(y), Number(mo) - 1, Number(da), Number(hh), Number(mi)) - off * 60000;
  const minutes = om ? (om[1] === "-" ? -1 : 1) * (Number(om[2]) * 60 + Number(om[3])) : 0;
  const shifted = new Date(instant + minutes * 60000);
  const stamp = `${shifted.getUTCFullYear()}-${pad2(shifted.getUTCMonth() + 1)}-${pad2(shifted.getUTCDate())}T${pad2(shifted.getUTCHours())}:${pad2(shifted.getUTCMinutes())}:00`;
  return zone === "Z" ? `${stamp}Z` : `${stamp}${zone}`;
}
