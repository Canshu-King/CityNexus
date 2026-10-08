/**
 * The rendered height of the fixed bottom bar, published as a CSS custom property.
 *
 * `--cn-nav-h` in `design-tokens.css` is a *declared* number: item floor + nav padding. It is the
 * right default for the first paint, and it is also how the bar's own height is audited, so it stays.
 * But it is a floor, not a measurement -- `min-height` on the row buttons does not cap them, and the
 * row's real height is whatever icon + label + gap + line box come to. At 390x844 that renders 76px
 * against a declared 80px, which is the correct direction (bar shorter than reserved), and it is the
 * direction that hides defects: any surface whose own bottom offset is measured from the declared
 * number rather than the rendered one silently drifts.
 *
 * So the bar measures itself. A `ResizeObserver` on `.v8-mobile-nav` writes the rendered height to
 * `--cn-nav-h-measured` on `:root`, and `--cn-nav-clearance` prefers it and falls back to the
 * declared value before the first observation lands. Every bottom-anchored surface that already says
 * `calc(var(--cn-nav-clearance) + env(safe-area-inset-bottom, 0px))` then tracks the real bar without
 * anyone restating its height, and the safe-area inset stays additive rather than folded into a
 * literal -- the phone's home indicator and the app's own chrome are two different bands and adding
 * them together is the only order that cannot double-count or drop one.
 */

const VAR = "--cn-nav-h-measured";
const SELECTOR = ".v8-mobile-nav";

/** Rounding to whole pixels keeps the value stable across subpixel layout jitter. */
function publish(target: HTMLElement, height: number) {
  target.style.setProperty(VAR, `${Math.round(height)}px`);
}

export function installNavHeightVar(): () => void {
  if (typeof window === "undefined" || typeof document === "undefined") return () => undefined;

  const root = document.documentElement;
  let observer: ResizeObserver | null = null;
  let bar: Element | null = null;
  let frame = 0;
  let cancelled = false;

  const measure = () => {
    if (!bar) return;
    publish(root, bar.getBoundingClientRect().height);
  };

  const attach = (next: Element) => {
    bar = next;
    measure();
    observer = new ResizeObserver(measure);
    observer.observe(next);
    /* The bar's own box does not resize when the font it renders with loads late, so a
       ResizeObserver alone can report a height that was correct for the fallback face. Re-reading on
       the next frame and once more after load catches that without polling. */
    frame = requestAnimationFrame(measure);
  };

  /* The shell mounts asynchronously: a journey-addressed boot renders the setup screen first and the
     bottom bar only once the journey is in hand, so looking for the bar once at install time finds
     nothing and the measurement never lands. Watch for it instead of guessing a delay -- and stop
     watching as soon as it appears, so the observer count does not grow with the app's lifetime. */
  const existing = document.querySelector(SELECTOR);
  if (existing) {
    attach(existing);
  } else {
    const watcher = new MutationObserver(() => {
      const found = document.querySelector(SELECTOR);
      if (found && !cancelled) {
        watcher.disconnect();
        attach(found);
      }
    });
    watcher.observe(document.documentElement, { childList: true, subtree: true });
    observer = { disconnect: () => watcher.disconnect() } as ResizeObserver;
  }

  const remeasure = () => measure();
  window.addEventListener("load", remeasure);

  return () => {
    cancelled = true;
    cancelAnimationFrame(frame);
    window.removeEventListener("load", remeasure);
    observer?.disconnect();
    root.style.removeProperty(VAR);
  };
}