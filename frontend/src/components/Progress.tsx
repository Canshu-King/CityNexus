import { useId } from "react";

/* A single, shared progress surface.  Two rules hold everywhere it is used:
   1. The bar is the same height and the same accent colour in every screen, so a
      traveller learns one shape for "CityNexus is working".
   2. A number appears only when *this component* was handed a real, whole
      denominator.  An indeterminate bar never guesses -- the codebase is explicit
      that an invented percentage is worse than none, so the sweep carries no digits. */

export type ProgressProps = {
  /** Fraction already done, 0..1.  Omit it (or pass null) for an indeterminate bar. */
  value?: number | null;
  /** The total the value is measured against, when this screen actually knows one. */
  total?: number | null;
  /** How many of `total` are complete.  Preferred over `value` when counts are known. */
  complete?: number | null;
  /** Human caption shown beside the bar; the percentage is appended only when it is real. */
  label?: string;
  className?: string;
  /** Stable id for the caption, so the bar can name it instead of the aria value. */
  valueText?: string;
};

const clamp = (n: number) => Math.max(0, Math.min(1, n));

export function Progress({
  value,
  total,
  complete,
  label,
  className,
  valueText,
}: ProgressProps) {
  const captionId = useId();

  /* Prefer an explicit, whole count (complete / total) over a bare fraction: the count
     is what a traveller can check by eye, and a fraction from an unknown denominator is
     refused. */
  let fraction: number | null = null;
  let shownPercent: number | null = null;
  if (typeof complete === "number" && typeof total === "number" && total > 0) {
    fraction = clamp(complete / total);
    shownPercent = Math.round(fraction * 100);
  } else if (typeof value === "number" && Number.isFinite(value)) {
    fraction = clamp(value);
    shownPercent = Math.round(fraction * 100);
  }

  const indeterminate = fraction === null;
  const percentText = shownPercent == null ? null : `${shownPercent}%`;

  const classes = ["cn-progress", indeterminate ? "cn-progress--indeterminate" : "cn-progress--determinate", className]
    .filter(Boolean)
    .join(" ");

  const progressbarProps = indeterminate
    ? { "aria-valuenow": undefined, "aria-valuetext": valueText ?? label }
    : { "aria-valuenow": shownPercent ?? 0, "aria-valuetext": valueText ?? percentText ?? undefined };

  return (
    <div className={classes}>
      <div
        className="cn-progress__track"
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-busy={indeterminate || undefined}
        aria-valuenow={progressbarProps["aria-valuenow"]}
        aria-valuetext={progressbarProps["aria-valuetext"]}
        aria-labelledby={label ? captionId : undefined}
      >
        <span
          className="cn-progress__fill"
          style={indeterminate ? undefined : { width: `${(fraction as number) * 100}%` }}
        />
      </div>
      {(label || percentText) && (
        <div className="cn-progress__meta">
          {label && (
            <span className="cn-progress__caption" id={captionId}>
              {label}
            </span>
          )}
          {percentText && <span className="cn-progress__percent">{percentText}</span>}
        </div>
      )}
    </div>
  );
}
