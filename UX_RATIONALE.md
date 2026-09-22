# UX rationale

## Setup: put the answer beside the action

The user reaches `Next` after completing a form, so a disabled-looking primary action without its reason in the same visual band creates a search problem: the user must scan upward, interpret broken link rows, and then return to the action. The existing field-jump behavior is useful, so it remains a real keyboard-reachable button; only its presentation is corrected to inline text links.

The hint remains the same accessible description used by `aria-describedby`, which keeps the sighted and assistive paths on one source of truth. The mobile sticky band is pinned to the viewport edge after the hint became taller; otherwise the band’s old simulation-ball clearance covered the arrival/departure controls.

## Wallet: semantic surfaces must follow the theme

Wallet contains commitment evidence and an inbox for importing confirmation text. Those surfaces are high-attention, trust-sensitive content. A white card on a black page is not just a cosmetic mismatch: it creates glare, breaks hierarchy, and can make low-contrast copy disappear. The fix maps the legacy Wallet surfaces to the existing semantic tokens and preserves state distinctions through border/accent treatments as well as color.

## What was intentionally not changed

No planner, API, map behavior, backend truth, or Hermes authority was altered. Today and Live already passed the existing overflow gate, so the sprint adds coverage at 390 px and Wallet rather than spending a third defect slot on a green path.
