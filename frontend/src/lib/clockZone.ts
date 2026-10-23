/**
 * The execution clock on screen: which zone a moment is in, and whether the journey got the zone
 * it asked for.
 *
 * The server's execution clock answers three questions in one payload: `now` is the instant,
 * `timezone` is the zone the journey asked for, and `used_timezone` says the zone that instant
 * is actually in, with `timezone_honoured` saying whether the two are the same.  A screen that
 * renders `now` in `timezone` and prints `timezone` underneath therefore shows two facts that can
 * disagree: the number in one zone, the label naming another.  On a traveller whose device is not
 * on the journey's zone that is not a rounding difference -- it is an hour or a day.
 *
 * So the panel must render the moment in the zone the server says it used, and when the journey's
 * zone was not honoured it must say so instead of printing the requested zone as if it had been
 * granted.  The server's answer is authoritative: this module never decides on its own which zone
 * a moment is in.
 *
 * The zone string is checked with `Intl` because the contract types it as a bare string with no
 * enum -- an unusable name is contract-legal, and `Intl` throws on it.  A name this runtime cannot
 * format is not silently dropped: it is reported as unusable, and the words under the clock say
 * so.
 */

import { dictionaryCopy } from "../i18n/LocaleContext";
import { clockZoneLabel } from "./displayVocabulary";

export type ClockZoneFacts = {
  timezone?: string | null;
  used_timezone?: string | null;
  timezone_honoured?: boolean;
};

export type ClockZoneRead = {
  /** The zone the moment is rendered in, or undefined when the runtime cannot format it. */
  zone: string | undefined;
  /**
   * Whether the journey got the zone it asked for.
   *
   * `null` means the payload does not say -- an older server that predates the two fields.  That
   * is not the same as "not honoured", and a caller must not print either word on a guess.
   */
  honoured: boolean | null;
  /** The zone the journey asked for, as the server sent it. */
  requested: string | null;
  /** The zone the moment is actually in, as the server sent it. */
  used: string | null;
};

/** A zone name this runtime can actually format in, or undefined when it cannot. */
export function renderableZone(value: unknown): string | undefined {
  if (typeof value !== "string") return undefined;
  const name = value.trim();
  if (!name) return undefined;
  try {
    new Intl.DateTimeFormat("en-GB", { timeZone: name });
    return name;
  } catch {
    return undefined;
  }
}

/**
 * What the screen may say about the zone of a clock reading.
 *
 * The server's `used_timezone` is the authority: it is the zone the instant is in.  `timezone` is
 * what the journey asked for, and the two differ exactly when the request could not be granted.
 * When the payload carries no `used_timezone` at all (an older server), the request is used -- and
 * `honoured` is then unknown rather than claimed, so a caller cannot print "granted" on a guess.
 */
export function readClockZone(facts: ClockZoneFacts | undefined | null): ClockZoneRead {
  const requested = typeof facts?.timezone === "string" ? facts.timezone : null;
  const used = typeof facts?.used_timezone === "string" ? facts.used_timezone : null;
  const honoured =
    typeof facts?.timezone_honoured === "boolean" ? facts.timezone_honoured : null;

  if (used) {
    return {
      zone: renderableZone(used),
      honoured: honoured === null ? used === requested : honoured,
      requested,
      used,
    };
  }
  if (requested) {
    return {
      zone: renderableZone(requested),
      honoured,
      requested,
      used: null,
    };
  }
  return { zone: undefined, honoured, requested: null, used: null };
}

/**
 * The words under the clock.
 *
 * The zone the moment is in is the server's answer, and when the journey's zone was not the one
 * used the traveller has to be told that -- the number alone would be a moment they cannot place.
 * The sentence lives in the dictionary, like every other phrase a traveller reads, and the zone
 * name is rendered by the same table the rest of the family uses.
 */
export function clockZoneCaption(
  facts: ClockZoneFacts | undefined | null,
  zh: boolean,
): { label: string; honoured: boolean | null; zone: string | undefined } {
  const read = readClockZone(facts);
  if (read.honoured === false) {
    /* The refused zone is the one the traveller asked for, so it is the one to name: "your trip
       said Shanghai, Shanghai could not be used, so this reading is in UTC".  Naming the zone the
       moment landed in instead would leave the traveller unable to tell what was refused. */
    const refused = read.requested ? clockZoneLabel(read.requested, zh) : null;
    const sentence = dictionaryCopy(zh ? "zh-CN" : "en", "exec.zoneNotHonoured");
    return {
      label: refused ? `${refused} · ${sentence}` : sentence,
      honoured: false,
      zone: read.zone,
    };
  }
  const name = read.used ?? read.requested;
  const zone = name ? clockZoneLabel(name, zh) : null;
  return {
    label: zone ?? dictionaryCopy(zh ? "zh-CN" : "en", "exec.execClock"),
    honoured: read.honoured,
    zone: read.zone,
  };
}
