// Q8(b) readout, one body used verbatim for the control pass and for every mutant pass.
//
// It returns, in one shot: the rendered sentence with the product's own attribution line (the columns the
// fifth arm reads), the snapshot fact measured from IndexedDB, and the three fingerprints the arbiter's
// Q8(b) requires of any runtime mutant reading:
//
//   1. the script URLs the page actually executed            (proof the running code is the build I mean)
//   2. SHA-256 of the bytes fetched back from that very URL   (proof those bytes are my local build)
//   3. if a service worker controls the page, the shell it serves is the same generation as the mutant
//      (the hashed JS may carry `revision:null`, so nothing here demands `__WB_REVISION__`)
//
// Everything is read from the live page: no field below is typed in by me afterwards.
//
// Delivery, because the Playwright sandbox exposes neither `require` nor dynamic `import`: this file is
// injected into the page with `page.addScriptTag({path})` from the MCP-allowed directory, and the expectation
// (asset name + sha256 of the build that must be running) is injected separately as `window.__Q8B_EXPECTED__`.
// One body, per-pass expectation, and the driver reports the sha256 of the bytes it injected, so the pass names
// a single instrument rather than a copy retyped per pass.
window.__Q8B_READOUT__ = async () => {
  const EXPECTED = window.__Q8B_EXPECTED__ || {};
  const EXPECTED_ASSET = EXPECTED.asset || "";
  const EXPECTED_SHA = EXPECTED.sha256 || "";
  const SHA = async (buf) => [...new Uint8Array(await crypto.subtle.digest("SHA-256", buf))]
    .map(b => b.toString(16).padStart(2, "0")).join("");

  for (const d of document.querySelectorAll("details")) d.open = true;
  await new Promise(r => setTimeout(r, 400));

  const t = document.body.innerText || "";
  const lines = t.split("\n").map(s => s.trim()).filter(Boolean);
  const attribution = (t.match(/attribution_reason=.*$/m) || [""])[0];
  const resources = performance.getEntriesByType("resource");
  const jsExecuted = resources.filter(r => /\.js(\?|$)/.test(r.name)).map(r => r.name);
  const apiReads = resources.filter(r => /\/api\/v1\//.test(r.name))
    .map(r => ({ url: r.name, duration_ms: Math.round(r.duration), status: r.responseStatus }));

  // fingerprint 2: re-fetch the executed bundle by its own URL and hash the bytes that come back
  const executed = [];
  for (const url of jsExecuted) {
    try {
      const res = await fetch(url, { cache: "no-store" });
      const buf = await res.arrayBuffer();
      executed.push({ url, bytes: buf.byteLength, sha256: await SHA(buf), status: res.status });
    } catch (e) { executed.push({ url, error: String(e) }); }
  }

  // fingerprint 3: under SW control, ask whether the shell the network serves names the same asset
  const swControlled = !!(navigator.serviceWorker && navigator.serviceWorker.controller);
  let shell = { checked: false };
  try {
    const res = await fetch("/v8/hub", { cache: "no-store" });
    const txt = await res.text();
    const m = txt.match(/assets\/index-[A-Za-z0-9_-]+\.js/);
    const cacheKeys = (await caches.keys()).filter(k => /workbox-precache/.test(k));
    let cachedShell = null;
    for (const k of cacheKeys) {
      const c = await caches.open(k);
      const hit = (await c.keys()).find(r => /index\.html/.test(r.url));
      if (hit) {
        const resp = await c.match(hit);
        const txt2 = resp ? await resp.text() : "";
        const mm = txt2.match(/assets\/index-[A-Za-z0-9_-]+\.js/);
        cachedShell = { cache: k, key: hit.url, names_asset: mm ? mm[0] : null };
      }
    }
    shell = { checked: true, status: res.status, asset_named_by_shell: m ? m[0] : null,
              workbox_precaches_present: cacheKeys, cached_shell: cachedShell };
  } catch (e) { shell = { checked: true, error: String(e) }; }

  const snapshotRows = await new Promise(res => {
    const rq = indexedDB.open("citynexus-offline");
    rq.onsuccess = () => { const db = rq.result; const names = [...db.objectStoreNames];
      if (!names.includes("journeys")) { db.close(); res(0); return; }
      const c = db.transaction("journeys", "readonly").objectStore("journeys").count();
      c.onsuccess = () => { db.close(); res(c.result); }; c.onerror = () => { db.close(); res("err"); }; };
    rq.onerror = () => res("open-err");
  });

  const payload = JSON.stringify({
    read_at_ms: Math.round(performance.now()),
    headline: lines.slice(0, 2).join(" | "),
    body: lines.slice(2, 3).join(" "),
    attribution_line: attribution,
    full_text_chars: t.length,
    skeleton: t.includes("正在准备城市周末行程"),
    network_words: [...new Set(t.match(/网络不可用|网络问题|没能出去|没有收到任何回答|离线|连不上/g) || [])],
    snapshot_words: [...new Set(t.match(/已保存|只读副本|本地快照|快照/g) || [])],
    doors: [...document.querySelectorAll("button")].map(b => (b.innerText || "").trim())
      .filter(Boolean).slice(0, 6),
    snapshot_rows: snapshotRows,
    journey_id_in_localStorage: localStorage.getItem("citynexus.v8.journey_id"),
    onLine: navigator.onLine,
    api_reads: apiReads,
    q8b_fingerprints: {
      expected_asset: EXPECTED_ASSET, expected_sha256: EXPECTED_SHA,
      script_urls_executed: jsExecuted,
      executed_bundle_rehashed_from_its_own_url: executed,
      asset_matches_expected: executed.some(e => (e.url || "").endsWith(EXPECTED_ASSET)),
      sha_matches_local_build: executed.some(e => e.sha256 === EXPECTED_SHA),
      sw_controls_page: swControlled,
      shell: shell,
      shell_same_generation: shell.asset_named_by_shell === null ? null
        : String(shell.asset_named_by_shell).endsWith(EXPECTED_ASSET.replace("assets/", "")),
      cached_shell_same_generation: !shell.cached_shell ? null
        : String(shell.cached_shell.names_asset || "").endsWith(EXPECTED_ASSET.replace("assets/", ""))
    }
  });
  const payload_sha256 = await SHA(new TextEncoder().encode(payload).buffer);
  return JSON.stringify({ payload, payload_sha256, payload_chars: payload.length });
};
