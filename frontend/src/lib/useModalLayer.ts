/**
 * The layer behaviour every bottom-anchored overlay needs: enter/exit motion, scroll lock, and focus
 * containment.
 *
 * Without this, a sheet is just a positioned div that appears and disappears instantly.  With it the
 * traveller gets a smooth open, a smooth close, Esc dismiss, backdrop click, body scroll lock, and a
 * focus ring that stays inside the dialog.
 *
 * Design rules honoured here:
 *  - Motion: fade + rise (opacity + translateY), matching `cn-modal-in/out` in the stylesheet;
 *  - Scroll: `body { overflow: hidden }` for the duration, so the background cannot scroll behind the dim;
 *  - Focus: trap Tab/Shift+Tab, and on close return focus to the opener;
 *  - Reduced motion: duration collapses to `1ms` (CSS then drops the animation outright).
 */

import { useCallback, useEffect, useRef, useState } from "react";

const FOCUSABLE_SELECTOR =
  'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

const isReducedMotion = () =>
  typeof window === "undefined"
    ? false
    : window.matchMedia("(prefers-reduced-motion: reduce)").matches;

/** Return the element that opened the modal, for focus restoration. */
export function useModalLayer({
  open,
  onClose,
  sheetRef,
}: {
  open: boolean;
  onClose: () => void;
  sheetRef: React.RefObject<HTMLElement | null>;
}) {
  /* The sheet mounts only when `open`, so we always animate *in*; `closing` holds it on screen just
     long enough to animate *out*, then calls `onClose` (which unmounts it). */
  const [closing, setClosing] = useState(false);
  const opener = useRef<Element | null>(null);
  const reduce = useRef(isReducedMotion());
  const exitTimer = useRef<number | null>(null);

  /* ---- remember what opened us ---- */
  useEffect(() => {
    if (!open) {
      setClosing(false);
      return;
    }
    /* The element that had focus when the sheet appeared is where focus goes back afterwards. */
    opener.current = document.activeElement;
  }, [open]);

  /* Clean up the timer on unmount. */
  useEffect(
    () => () => {
      if (exitTimer.current !== null) window.clearTimeout(exitTimer.current);
    },
    [],
  );

  const requestClose = useCallback(() => {
    if (closing) return;
    setClosing(true);
    /* `cn-modal-out` runs for this long; the sheet must stay mounted the whole time or the traveller
       sees it vanish instead of leave. */
    const durMs = reduce.current ? 1 : 280;
    exitTimer.current = window.setTimeout(() => {
      exitTimer.current = null;
      onClose();
      setClosing(false);
    }, durMs);
  }, [closing, onClose]);

  /* ---- scroll lock ---- */
  useEffect(() => {
    if (!open) return;
    const body = document.body;
    const prev = body.style.overflow;
    body.style.overflow = "hidden";
    return () => {
      body.style.overflow = prev;
    };
  }, [open]);

  /* ---- focus containment ---- */
  useEffect(() => {
    if (!open || closing) return;
    const sheet = sheetRef.current;
    if (!sheet) return;

    /* Initial focus: the first focusable inside the sheet, or the close button. */
    const first = sheet.querySelector<HTMLElement>(FOCUSABLE_SELECTOR);
    first?.focus({ preventScroll: true });

    const trap = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.stopPropagation();
        requestClose();
        return;
      }
      if (event.key !== "Tab") return;

      const focusables = [...sheet.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR)].filter(
        (el) => el.offsetWidth > 0 || el.offsetHeight > 0 || el === document.activeElement,
      );
      if (focusables.length === 0) {
        event.preventDefault();
        return;
      }
      const a = focusables[0];
      const z = focusables[focusables.length - 1];
      const cur = document.activeElement;

      if (event.shiftKey) {
        if (cur === a || !sheet.contains(cur)) {
          event.preventDefault();
          z.focus({ preventScroll: true });
        }
      } else if (cur === z || !sheet.contains(cur)) {
        event.preventDefault();
        a.focus({ preventScroll: true });
      }
    };

    document.addEventListener("keydown", trap, true);
    return () => document.removeEventListener("keydown", trap, true);
  }, [open, closing, requestClose]);

  /* ---- focus return ---- */
  useEffect(() => {
    if (!open) return;
    return () => {
      const o = opener.current as HTMLElement | null;
      /* Only focus it if it is still in the DOM and visible. */
      if (o && document.contains(o)) o.focus({ preventScroll: true });
    };
  }, [open]);

  /* ---- backdrop dismiss ---- */
  const onBackdropMouseDown = useCallback(
    (event: React.MouseEvent) => {
      /* The click must land on the dim itself, not on a descendant that bubbles up. */
      if (event.target === event.currentTarget) requestClose();
    },
    [requestClose],
  );

  return { closing: open && closing, requestClose, onBackdropMouseDown };
}
