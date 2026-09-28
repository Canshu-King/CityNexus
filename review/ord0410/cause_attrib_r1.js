/* ORD-0410 lane cause-attribution instrument.
 *
 * The commander's hypothesis was "the closure holds a dead map instance".  That is one of several
 * shapes that all look identical from the outside (markers do not move, no exception), so this reads
 * the discriminating values instead:
 *   legs        — `data-route-legs` is `route.length` painted by the panel, i.e. the very condition
 *                 the `coordinates.length > 1` block is gated on.
 *   liveMap     — the instance the canvas seam exposes, plus whether maplibre says it is removed and
 *                 whether its canvas is still attached.
 *   fitBoundsCallCount — a wrapper installed on the LIVE instance before the click.  A click that
 *                 never reaches this counter means the action was never dispatched to the on-screen
 *                 map at all (null or stale ref), which is a different fix from "dispatched and lost".
 *   controlManualFit — then the same fitBounds is called by hand on the live instance.  If the
 *                 markers come back for that, the live map is capable and the fault is upstream.
 * Usage: node _cause_attrib_r1.js <base> <out-dir>
 */
const { chromium } = require("D:/moodle/CityNexus/frontend/node_modules/playwright");
const fs = require("fs");
const BASE = process.argv[2];
const OUT = process.argv[3];
fs.mkdirSync(OUT, { recursive: true });

const readings = (p) => p.evaluate(() => {
  const panel = document.querySelector(".v8-map-panel");
  const host = document.querySelector(".v8-maplibre-canvas");
  const m = host && host.citynexusMap;
  const btn = document.querySelector("[data-testid='map-viewport-reset']");
  return {
    legs: panel ? panel.getAttribute("data-route-legs") : null,
    routeModes: panel ? panel.getAttribute("data-route-modes") : null,
    controlState: btn ? btn.getAttribute("data-viewport-state") : null,
    markers: Array.from(document.querySelectorAll(".v8-map-panel .v9-map-marker")).map((e) => {
      const b = e.getBoundingClientRect();
      return [Math.round(b.x), Math.round(b.y)];
    }),
    hasLiveMap: !!m,
    liveMapRemoved: m ? !!m._removed : null,
    liveCanvasAttached: m ? !!(m.getCanvas && m.getCanvas() && m.getCanvas().isConnected) : null,
    canvasCount: document.querySelectorAll(".maplibregl-canvas").length,
    camera: m ? (() => { const c = m.getCenter(); return { lng: +c.lng.toFixed(5), lat: +c.lat.toFixed(5), zoom: +m.getZoom().toFixed(3) }; })() : null,
    fitCalls: window.__fitCalls,
    moveends: window.__moveends,
    // true while the canvas still exposes the very object the counters were installed on, i.e. no
    // map rebuild happened underneath the measurement.
    sameInstanceAsInstalled: !!m && m === window.__installedMap,
  };
});

(async () => {
  const br = await chromium.launch({ channel: "chrome", headless: true });
  const p = await br.newPage({ viewport: { width: 390, height: 844 } });
  const errs = [];
  p.on("pageerror", (e) => errs.push(String(e).slice(0, 200)));
  await p.goto(BASE, { waitUntil: "networkidle", timeout: 60000 });
  const seal = p.getByText("使用封存的演示行程", { exact: false }).first();
  if (await seal.count()) { await seal.click(); await p.waitForTimeout(5000); }
  await p.goto(BASE.replace(/\/$/, "") + "/v8/map", { waitUntil: "networkidle", timeout: 60000 });
  await p.waitForTimeout(5000);

  // Install the counters on whatever instance is live right now.
  const installed = await p.evaluate(() => {
    const host = document.querySelector(".v8-maplibre-canvas");
    const m = host && host.citynexusMap;
    if (!m) return false;
    window.__fitCalls = 0;
    window.__moveends = 0;
    window.__installedMap = m;
    const orig = m.fitBounds.bind(m);
    m.fitBounds = (...a) => { window.__fitCalls += 1; return orig(...a); };
    m.on("moveend", () => { window.__moveends += 1; });
    return true;
  });

  const atRest = await readings(p);
  const box = await p.locator(".v8-maplibre-canvas").boundingBox();
  await p.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
  await p.mouse.down();
  await p.mouse.move(box.x + box.width / 2 - 130, box.y + box.height / 2 - 90, { steps: 12 });
  await p.mouse.up();
  await p.waitForTimeout(2500);
  const afterDrag = await readings(p);

  await p.getByTestId("map-viewport-reset").click();
  await p.waitForTimeout(3500);
  const afterClick = await readings(p);

  // Control: the same kind of call, made by hand on the live instance, over the markers' own bbox
  // (read back by un-projecting where each marker currently paints).  If this moves the markers,
  // the on-screen map is capable and the fault is in the button's action path, not in maplibre.
  let manualFit = null;
  if (afterClick.hasLiveMap) {
    manualFit = await p.evaluate(() => {
      const host = document.querySelector(".v8-maplibre-canvas");
      const m = host.citynexusMap;
      const els = Array.from(document.querySelectorAll(".v8-map-panel .v9-map-marker"));
      const ll = els.map((el) => {
        const b = el.getBoundingClientRect();
        const c = m.unproject([b.x + b.width / 2, b.y + b.height / 2]);
        return [c.lng, c.lat];
      });
      const lngs = ll.map((x) => x[0]), lats = ll.map((x) => x[1]);
      const bbox = [[Math.min(...lngs), Math.min(...lats)], [Math.max(...lngs), Math.max(...lats)]];
      m.fitBounds(bbox, { padding: 42, maxZoom: 13, duration: 0 });
      return { markerCount: ll.length };
    });
    await p.waitForTimeout(2500);
  }
  const afterManual = await readings(p);
  const rec = { at: new Date().toISOString(), base: BASE, countersInstalled: installed,
    atRest, afterDrag, afterClick, afterManual,
    clickMovedMarkers: JSON.stringify(afterDrag.markers) !== JSON.stringify(afterClick.markers),
    clickReachedLiveFitBounds: (afterClick.fitCalls || 0) > (afterDrag.fitCalls || 0),
    moveendsDeltaDuringClick: (afterClick.moveends || 0) - (afterDrag.moveends || 0),
    manualFitMovedMarkers: JSON.stringify(afterClick.markers) !== JSON.stringify(afterManual.markers),
    manualFit, pageerrors: errs };
  fs.writeFileSync(OUT + "attribution.json", JSON.stringify(rec, null, 1), "utf-8");
  console.log(JSON.stringify(rec, null, 1));
  await br.close();
})().catch((e) => { console.log("FATAL", String(e).slice(0, 300)); process.exit(9); });
