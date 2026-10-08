/**
 * The band the fixed bottom bar actually occupies, published as a CSS custom property.
 *
 * `--cn-nav-h` in `design-tokens.css` is a *declared* number: item floor + nav padding, taken at
 * inset zero. It is the right default for the first paint, but it is a floor and a snapshot, not a
 * measurement -- `min-height` on the row buttons does not cap them, so the row's real height is
 * whatever icon + label + gap + line box come to. At 390x844 that renders 76px against a declared
 * 80px, and any surface whose bottom offset is measured from the declared number rather than the
 * rendered one silently drifts the moment the bar's content changes.
 *
 * So the bar measures itself: the rendered height is published to `--cn-nav-band-measured` on
 * `:root`, and `--cn-nav-clearance` prefers that and falls back to
 * `calc(var(--cn-nav-h) + env(safe-area-inset-bottom, 0px))` before the first reading lands.
 *
 * The published value is the WHOLE band and must not have the inset added to it again. The bar's own
 * `padding-bottom` is `calc(var(--cn-nav-pad-bottom) + env(safe-area-inset-bottom, 0px))`, so the
 * height read off the element already contains the home indicator. Adding `env()` a second time
 * reserves the indicator twice and floats every overlay off the bar by exactly the inset -- a 34px
 * iPhone would push the Copilot dock 34px above the bar it is supposed to sit a gap over.
 *
 * A desktop viewport cannot demonstrate that failure, because there the inset resolves to zero and
 * the wrong formula and the right one agree. So the rule is enforced structurally by
 * `probe/audit_bottom_anchored_r1.py`, which treats `--cn-nav-band-measured` and
 * `--cn-nav-clearance` as inset-bearing and rejects any declaration that adds
 * `env(safe-area-inset-bottom)` on top of either. That gate is checked against the pre-fix form as a
 * negative control, because a gate that catches nothing proves nothing.
 *
 * The bar is looked up by selector on every reading rather than bound once. React replaces the
 * `<nav>` node when the shell remounts, and an observer holding the old node keeps watching a
 * detached element: the published value then freezes at whatever the first bar measured, which is
 * worse than not measuring at all because it looks live.
 */

const VAR = "--cn-nav-band-measured";
const SELECTOR = ".v8-mobile-nav";

export function installNavHeightVar(): () => void {
  if (typeof window === "undefined" || typeof document === "undefined") return () => undefined;

  const root = document.documentElement;
  let tracked: Element | null = null;
  let observer: ResizeObserver | null = null;
  let cancelled = false;

  const publish = (height: number) => {
    /* Rounding to whole pixels keeps the value stable across subpixel layout jitter. */
    root.style.setProperty(VAR, `${Math.round(height)}px`);
  };

  const measure = () => {
    if (cancelled) return;
    const bar = document.querySelector(SELECTOR);
    if (!bar) return;
    const height = bar.getBoundingClientRect().height;
    /* A detached node measures zero. Writing that would tell every bottom-anchored surface that the
       whole band is free, which is the one failure mode worse than a stale number. */
    if (height <= 0) return;
    publish(height);
  };

  const bind = (bar: Element) => {
    if (bar === tracked) return;
    tracked = bar;
    observer?.disconnect();
    observer = new ResizeObserver(measure);
    /* border-box, not the content-box default. The band this publishes is padding + the home
       indicator, and a `min-height` row whose content is unchanged keeps its content box the same
       size when the padding grows -- so observing the default box means the one change that matters
       (the inset appearing on a real phone) never fires a callback at all. Measured: growing the
       bar's padding-bottom by 34px moved getBoundingClientRect().height from 76 to 110 and produced
       zero ResizeObserver deliveries, leaving the published value frozen at the first reading. */
    observer.observe(bar, { box: "border-box" });
    measure();
  };

  /* Two things can change here: the bar may not exist yet (a journey-addressed boot renders the
     setup screen first), and it may be replaced later by a remount. One MutationObserver covers
     both -- it re-resolves the selector and rebinds only when the node identity actually changes. */
  const sync = () => {
    if (cancelled) return;
    const bar = document.querySelector(SELECTOR);
    if (bar) bind(bar);
  };

  const watcher = new MutationObserver(sync);
  watcher.observe(document.documentElement, { childList: true, subtree: true });
  sync();

  /* The bar's box does not resize when a webfont finishes loading, so a ResizeObserver alone can
     leave a height that was correct for the fallback face. One re-read after load catches that. */
  window.addEventListener("load", measure);

  return () => {
    cancelled = true;
    window.removeEventListener("load", measure);
    watcher.disconnect();
    observer?.disconnect();
    tracked = null;
    root.style.removeProperty(VAR);
  };
}