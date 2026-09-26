"""ORD-0323 甲 follow-on (CMDR 04:53): the four forms in JourneyInboxWorkbench.tsx.

Each fix is counted-exact, and each one moves a decision onto the channel this product already has
(`lib/failureAttribution.ts`, whose blob is byte-identical between the ordered base and this branch, so
"no second helper" is a measurement rather than a claim):

  F1  `await response.json()` was unguarded: an HTML error page or an empty body raised the *engine's*
      sentence, which quoted the beginning of the body, and the catch sites printed that. The body is now
      read once as text and classified as this device's own observation (`OriginResponseUnusableError`,
      which `classifyReadFailure` already decides first).
  F2  `result.reason ?? …` handed the reply's sentence straight into the status line. The line is now this
      device's copy plus the reply's own machine enum.
  F3/F4  `<p>{reasoning_summary}</p>` rendered the model's sentence as the panel's own. Replaced with a
      held/not-shown fact in the same machine-token style as the existing fields line.
"""
from __future__ import annotations

import pathlib
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
FILE = pathlib.Path(r"D:\moodle\_qoder_b_lane_20260923\frontend\src\features\inbox\JourneyInboxWorkbench.tsx")
t = FILE.read_text(encoding="utf-8")


def rep(old: str, new: str, want: int = 1) -> None:
    global t
    n = t.count(old)
    if n != want:
        raise SystemExit(f"expected {want}, found {n} for:\n{old[:260]}")
    t = t.replace(old, new)


# --- F1: guarded body read, classified as the device's own observation -------------------------------
rep(
    """async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, init);
  const payload = (await response.json()) as T;
  if (!response.ok) {
    throw new InboxRequestRejected(response.status, response.headers.get("content-type") ?? "");
  }
  return payload;
}""",
    """async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, init);
  /* ORD-0323 form F1 (CMDR 04:53).  The body used to be parsed straight away, so a reply that was not
     JSON at all raised the engine's own sentence -- a string that quotes the beginning of whatever came
     back -- and that is what the catch sites printed.  The body is read once as text here, and an
     unusable one is reported as what this device observed: which status answered, with which media type,
     and in what shape the body arrived. */
  const contentType = response.headers.get("content-type") ?? "";
  const raw = await response.text().catch(() => null);
  if (!response.ok) {
    throw new InboxRequestRejected(response.status, contentType);
  }
  if (raw === null || raw.trim() === "") {
    throw new OriginResponseUnusableError(response.status, contentType || null, "empty");
  }
  try {
    return JSON.parse(raw) as T;
  } catch {
    const looksHtml = /^\\s*<(?:!doctype|html|[a-z][a-z0-9-]*[\\s>])/i.test(raw);
    throw new OriginResponseUnusableError(response.status, contentType || null, looksHtml ? "html" : "not_json");
  }
}""",
)
rep('import {\n  classifyReadFailure,\n  copyFor,\n} from "../../lib/failureAttribution";',
    'import {\n  classifyReadFailure,\n  copyFor,\n  OriginResponseUnusableError,\n} from "../../lib/failureAttribution";')

# the machine line has to name the media type for this class of answer too, not only for a rejected one
rep(
    """    const ct = error instanceof InboxRequestRejected ? error.content_type : "";""",
    """    const ct = error instanceof InboxRequestRejected
      ? error.content_type
      : error instanceof OriginResponseUnusableError
        ? error.content_type ?? ""
        : "";""",
)

# --- F2: the reply's sentence stops being the status line --------------------------------------------
rep(
    """          : result.reason ?? `${t("inbox.extractionStatus")} ${result.status}`,""",
    """          /* ORD-0323 form F2 (CMDR 04:53): `result.reason` is the reply's own sentence, and it was being
             used as this screen's status line.  What the traveller reads now is this device's copy plus the
             reply's machine status; the sentence is not re-labelled as our explanation of it. */
          : `${t("inbox.extractionStatus")} ${result.status}`,""",
)

# --- F3 / F4: the model's summary is a held fact, not the panel's own words --------------------------
rep(
    """                {item.reasoning_summary && <p>{item.reasoning_summary}</p>}""",
    """                {/* ORD-0323 forms F3/F4 (CMDR 04:53): the summary is the upstream's sentence, and printed
                    here it read as this panel's own claim.  The row keeps stating what it measured. */}
                {item.reasoning_summary ? <small data-testid="v13-2-memory-summary-held">reasoning_summary=held 原文不在这一屏</small> : null}""",
)
rep(
    """            {draft.interpretation?.reasoning_summary && <p>{draft.interpretation.reasoning_summary}</p>}""",
    """            {draft.interpretation?.reasoning_summary
              ? <small data-testid="v13-2-draft-summary-held">reasoning_summary=held 原文不在这一屏</small>
              : null}""",
)

if "reasoning_summary}</p>" in t:
    raise SystemExit("a raw reasoning_summary render survived the patch")
FILE.write_text(t, encoding="utf-8", newline="\n")
print("four forms patched in", FILE.name)
