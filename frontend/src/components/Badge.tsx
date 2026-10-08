import type { ReactNode } from "react";
import "./badge.css";

/**
 * One badge for every count and status surface, so the colour is the meaning
 * rather than whichever literal hex the nearest panel happened to use.
 */
export type BadgeTone = "error" | "warning" | "success" | "info" | "neutral";

/** `solid` carries a count or an alert; `tinted` labels a state beside other text. */
export type BadgeVariant = "solid" | "tinted";

/**
 * A count above this collapses to `99+`. The pill then has one maximum width, which
 * is what keeps a four-digit backlog from widening the topbar.
 */
export const BADGE_COUNT_MAX = 99;

export function formatBadgeCount(count: number, max: number = BADGE_COUNT_MAX): string {
  return count > max ? `${max}+` : String(count);
}

/**
 * `Event.severity` as the backend publishes it (`schemas/Event` in the OpenAPI
 * document): INFO | MINOR | MAJOR | CRITICAL. An unrecognised or absent severity
 * stays loud, because a signal we cannot classify is not a signal that is safe.
 */
const SEVERITY_TONE: Record<string, BadgeTone> = {
  CRITICAL: "error",
  MAJOR: "error",
  MINOR: "warning",
  INFO: "info",
};

/**
 * Tone for one disruption.
 *
 * An event the traveller has only acknowledged keeps its severity's channel but steps
 * down one level: `disruptionState.ts` is explicit that seeing a change is not
 * resolving it, so it may quiet the colour but must not go neutral.
 */
export function badgeToneForDisruption(
  item: { severity?: string | null; status?: string | null },
  acknowledgedOnly = false,
): BadgeTone {
  const tone = SEVERITY_TONE[String(item.severity ?? "").toUpperCase()] ?? "warning";
  if (!acknowledgedOnly) return tone;
  if (tone === "error") return "warning";
  return tone;
}

/** The loudest tone in a set, used by a badge that counts several of them. */
export function loudestBadgeTone(tones: readonly BadgeTone[]): BadgeTone {
  const order: BadgeTone[] = ["error", "warning", "info", "success", "neutral"];
  for (const tone of order) if (tones.includes(tone)) return tone;
  return "neutral";
}

export type BadgeProps = {
  tone?: BadgeTone;
  variant?: BadgeVariant;
  /** Numeric mode. Rendered truncated past `max`; the true value stays in `aria-label`. */
  count?: number;
  max?: number;
  /** Pin to the top-right of a positioned host (an icon button, a tab label). */
  anchor?: boolean;
  /** Accessible name. Required when a truncated count would hide the true number. */
  label?: string;
  /**
   * True when the host already says the same thing out loud -- an icon button that
   * carries an `aria-label`. Announcing the pill again reads the same number twice.
   */
  decorative?: boolean;
  testId?: string;
  leadingIcon?: ReactNode;
  children?: ReactNode;
};

export function Badge({
  tone = "neutral",
  variant = "solid",
  count,
  max = BADGE_COUNT_MAX,
  anchor = false,
  label,
  decorative = false,
  testId,
  leadingIcon,
  children,
}: BadgeProps) {
  const isCount = typeof count === "number";
  const shown = isCount ? formatBadgeCount(count, max) : null;
  const truncated = isCount && count > max;

  const classes = ["cn-badge", `cn-badge--${tone}`, `cn-badge--${variant}`];
  if (anchor) classes.push("cn-badge--anchor");
  if (isCount) classes.push("cn-badge--count");
  if (leadingIcon) classes.push("cn-badge--with-icon");

  // A truncated number must not be the only place the true count exists.
  const ariaLabel = label ?? (truncated ? String(count) : undefined);

  return (
    <span
      className={classes.join(" ")}
      data-testid={testId}
      aria-label={ariaLabel}
      aria-hidden={decorative || undefined}
      title={ariaLabel}
    >
      {leadingIcon}
      {isCount ? shown : children}
    </span>
  );
}
