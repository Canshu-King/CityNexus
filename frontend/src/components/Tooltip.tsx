import {
  useCallback,
  useEffect,
  useId,
  useLayoutEffect,
  useRef,
  useState,
  type PointerEvent as ReactPointerEvent,
  type ReactNode,
} from "react";
import { createPortal } from "react-dom";

/* One bubble face for the whole frontend.  Before this file the tree had no tooltip at all:
   seven CSS rules ellipsised text with `text-overflow: ellipsis` and nothing ever gave the
   clipped half back.  A bubble that only exists where a designer happened to write a `<span>`
   would re-open the same split, so timing, placement and wrapping live here and callers only
   supply the words.
   The bubble is portalled to `<body>` and fixed-positioned.  ORD-0510 measured the alternative
   in this codebase: a popover that escapes its card is cut by the card's own `overflow`, and a
   cut control reads as a control that does nothing.  A tooltip that is itself clipped is the
   same bug wearing a smaller hat. */

const SHOW_MS = 120;
const HIDE_MS = 80;
const GAP = 8;
const EDGE = 10;

type Position = { left: number; top: number; place: "top" | "bottom" };

function isClipped(el: HTMLElement): boolean {
  return el.scrollWidth - el.clientWidth > 1 || el.scrollHeight - el.clientHeight > 1;
}

function hasHover(): boolean {
  return window.matchMedia("(hover: hover)").matches;
}

export function useCnTooltip(content: ReactNode) {
  const anchorRef = useRef<HTMLElement | null>(null);
  const bubbleRef = useRef<HTMLDivElement | null>(null);
  const timerRef = useRef<number | null>(null);
  const tipId = useId();
  const [open, setOpen] = useState(false);
  const [pinned, setPinned] = useState(false);
  const [pos, setPos] = useState<Position | null>(null);

  const cancelTimer = useCallback(() => {
    if (timerRef.current !== null) {
      window.clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  const hide = useCallback(() => {
    cancelTimer();
    setPinned(false);
    setOpen(false);
    setPos(null);
  }, [cancelTimer]);

  /* A sweep of the pointer across a row must not flash every label open, so hover waits; a
     keyboard focus is a deliberate act, so it answers at once. */
  const show = useCallback(
    (delay: number) => {
      const el = anchorRef.current;
      if (!el) return;
      if (!isClipped(el)) return;
      cancelTimer();
      setPos(null);
      timerRef.current = window.setTimeout(() => setOpen(true), delay);
    },
    [cancelTimer],
  );

  const hideLater = useCallback(() => {
    if (pinned) return;
    cancelTimer();
    timerRef.current = window.setTimeout(hide, HIDE_MS);
  }, [cancelTimer, hide, pinned]);

  const togglePinned = useCallback(() => {
    if (pinned) {
      hide();
      return;
    }
    setPinned(true);
    show(0);
  }, [hide, pinned, show]);

  const measure = useCallback(() => {
    const el = anchorRef.current;
    const bubble = bubbleRef.current;
    if (!el || !bubble) return;
    const anchor = el.getBoundingClientRect();
    const width = bubble.offsetWidth;
    const height = bubble.offsetHeight;
    const vw = window.innerWidth;
    const vh = window.innerHeight;
    let place: Position["place"] = "bottom";
    let top = anchor.bottom + GAP;
    if (top + height > vh - EDGE) {
      const above = anchor.top - GAP - height;
      if (above >= EDGE) {
        place = "top";
        top = above;
      } else {
        top = Math.max(EDGE, Math.min(vh - EDGE - height, top));
      }
    }
    let left = anchor.left;
    if (left + width > vw - EDGE) left = Math.max(EDGE, vw - EDGE - width);
    setPos({ left, top, place });
  }, []);

  useLayoutEffect(() => {
    if (open) measure();
  }, [open, content, measure]);

  useEffect(() => {
    if (!open) return;
    const onMove = () => measure();
    /* Escape is listened for on the document because the anchor is a label, not a control: it
       never holds focus, so a key handler on it would be a handler that cannot fire. */
    const onKey = (event: globalThis.KeyboardEvent) => {
      if (event.key === "Escape") hide();
    };
    window.addEventListener("scroll", onMove, true);
    window.addEventListener("resize", onMove);
    document.addEventListener("keydown", onKey);
    return () => {
      window.removeEventListener("scroll", onMove, true);
      window.removeEventListener("resize", onMove);
      document.removeEventListener("keydown", onKey);
    };
  }, [open, measure, hide]);

  useEffect(() => {
    if (!pinned) return;
    const onDocPointerDown = (event: PointerEvent) => {
      const target = event.target as Node | null;
      if (!target) return;
      if (bubbleRef.current?.contains(target)) return;
      if (anchorRef.current?.contains(target)) return;
      hide();
    };
    document.addEventListener("pointerdown", onDocPointerDown, true);
    return () => document.removeEventListener("pointerdown", onDocPointerDown, true);
  }, [pinned, hide]);

  useEffect(() => cancelTimer, [cancelTimer]);

  const bind = {
    onPointerEnter: (event: ReactPointerEvent<HTMLElement>) => {
      if (event.pointerType === "mouse") show(SHOW_MS);
    },
    onPointerLeave: (event: ReactPointerEvent<HTMLElement>) => {
      if (event.pointerType === "mouse") hideLater();
    },
    onClick: () => {
      /* A pointer that can hover already got its answer, so a mouse click must not fight the
         text selection a user drags across the same label.  A finger has no hover, so the tap is
         the only door and it pins the bubble open. */
      if (!hasHover()) togglePinned();
    },
    "aria-describedby": open ? tipId : undefined,
  };

  const bubble = open
    ? createPortal(
        <div
          ref={bubbleRef}
          id={tipId}
          role="tooltip"
          className="cn-tip"
          onPointerEnter={cancelTimer}
          onPointerLeave={() => hideLater()}
          data-place={pos ? pos.place : "bottom"}
          data-measured={pos ? "true" : "false"}
          data-pinned={pinned ? "true" : "false"}
          style={pos ? { left: `${pos.left}px`, top: `${pos.top}px` } : undefined}
        >
          {content}
        </div>,
        document.body,
      )
    : null;

  return { anchorRef, bind, bubble, open };
}

/* The shape a screen actually calls with: the words, and the class that already ellipsises them.
   The span this renders is the span that was in the markup before, so a file adopting it moves no
   DOM, no `data-testid` and no hit-box — which is the only reason the seven existing ellipsis sites
   can be converted one at a time instead of all at once. */
export function CnTipText({ className, text }: { className: string; text: string }) {
  const tip = useCnTooltip(text);
  return (
    <>
      <span
        className={className}
        ref={(node) => {
          tip.anchorRef.current = node;
        }}
        {...tip.bind}
      >
        {text}
      </span>
      {tip.bubble}
    </>
  );
}
