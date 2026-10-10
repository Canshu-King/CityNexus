/* ORD-0553 timezone-follow-up (lane 抬秤工) — a mount point for the real V10 execution panel.

   The quantity this order judges is whether one screen's two halves of one fact agree: the clock
   number and the label under it. Reaching that cell through the shell needs a staged journey and a
   live execution clock, which is a different order's problem. So the harness mounts the product
   component with the props the registry passes it (`V8Experience`/`v8PanelRegistry` hand it
   `journey?.id` and `active_plan ?? null`) and the component's own read is answered by the test's
   route stub, with the real hook, the real react-query client and the real `Intl` call.

   Nothing about the server is claimed here. `plan` is null on purpose: that is the shape
   `liveActivityWindow` documents for "no active plan" (lib/executionWindow.ts), and the clock cell
   does not read it.
 */
import React from "react";
import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { LocaleProvider } from "../../src/i18n/LocaleContext";
import { V10LiveExecutionPanel } from "../../src/features/execution/V10LiveExecutionPanel";

declare global {
  interface Window {
    __tcTzHarness?: { mounted: boolean; journeyId: string };
  }
}

const host = document.createElement("div");
host.id = "tc-tz-host";
document.body.appendChild(host);

/* retry 0, so a missing stub shows up as this run's own red instead of a thirty-second wait. */
const queryClient = new QueryClient({ defaultOptions: { queries: { retry: 0 } } });

createRoot(host).render(
  React.createElement(
    QueryClientProvider,
    { client: queryClient },
    React.createElement(
      LocaleProvider,
      null,
      React.createElement(V10LiveExecutionPanel, { journeyId: "tc0553tz-journey", plan: null }),
    ),
  ),
);

window.__tcTzHarness = { mounted: true, journeyId: "tc0553tz-journey" };
