// ORD-0271-B: one self-contained browser pass, byte-constant across every round and every shape.
//
// The pass opens its OWN page in the shared browser context - another lane or the user may be holding the tab
// this session started with, and during this order one of them navigated that tab to a router admin page - so no
// reading depends on someone else's tab and nothing here signals a page I do not own.
//
// It then clears the origin's service worker and precaches, because a generation switch leaves the page one load
// behind on the previous bundle: the first control reading of this order measured exactly that (the face already
// served the control bytes while the page still executed the mutant bundle), and the Q8(b) fingerprints caught it.
// After the clear it loads the face twice, runs the Q8(b) readout body verbatim from `q8b_readout.js`, posts the
// payload to my collector on :4499 so the screen text reaches disk without passing through my fingers, screenshots
// the screen, and closes its page.
//
// Per-pass parameters live in `params.js` as `window.__Q8B_PARAMS__ = {label, asset, sha256, url}`, rewritten from
// the shell before each call. The driver itself never changes, so no round can be quietly measured differently.
async (page) => {
  const p = await page.context().newPage();
  await p.setViewportSize({ width: 620, height: 900 });
  await p.goto("about:blank");
  await p.addScriptTag({ path: 'C:/Users/仓鼠王/cnx0271b/params.js' });
  const P = await p.evaluate(() => window.__Q8B_PARAMS__);
  await p.goto(P.url);
  const cleared = await p.evaluate(async () => {
    const regs = await navigator.serviceWorker.getRegistrations();
    const un = [];
    for (const r of regs) { un.push(r.scope); await r.unregister(); }
    const del = [];
    for (const k of await caches.keys()) { del.push(k); await caches.delete(k); }
    return JSON.stringify({ unregistered: un, caches_deleted: del,
                            idb: (await indexedDB.databases()).map(x => x.name) });
  });
  await p.goto(P.url);
  await p.waitForTimeout(1200);
  await p.goto(P.url);
  await p.waitForTimeout(3500);
  await p.addScriptTag({ path: 'C:/Users/仓鼠王/cnx0271b/q8b_readout.js' });
  await p.evaluate(e => { window.__Q8B_EXPECTED__ = e; }, { asset: P.asset, sha256: P.sha256, pass: P.label });
  const raw = await p.evaluate(async (lab) => {
    const wrapped = JSON.parse(await window.__Q8B_READOUT__());
    const r = await fetch('http://127.0.0.1:4499/collect?pass=' + lab, { method: 'POST', body: wrapped.payload });
    const ack = JSON.parse(await r.text());
    return JSON.stringify({ wrapped, ack });
  }, P.label);
  const { wrapped, ack } = JSON.parse(raw);
  const o = JSON.parse(wrapped.payload);
  const f = o.q8b_fingerprints;
  await p.screenshot({ path: 'C:/Users/仓鼠王/.playwright-mcp/shot_' + P.label + '.png', fullPage: true, type: 'png' });
  const url = p.url();
  await p.close();
  return JSON.stringify({
    label: P.label, url, cleared: JSON.parse(cleared),
    sha_agrees: ack.sha256_of_bytes_written === wrapped.payload_sha256,
    sha12: wrapped.payload_sha256.slice(0, 12), chars: wrapped.payload_chars,
    attribution_line: o.attribution_line, headline: o.headline, body: o.body,
    network_words: o.network_words, snapshot_words: o.snapshot_words, buttons: o.doors,
    snapshot_rows: o.snapshot_rows, skeleton: o.skeleton,
    executed: f.executed_bundle_rehashed_from_its_own_url.map(e =>
      (e.url || '').split('/').pop() + ':' + String(e.sha256).slice(0, 10)),
    q8b: [f.asset_matches_expected, f.sha_matches_local_build, f.sw_controls_page,
          f.shell_same_generation, f.cached_shell_same_generation],
    exp_reads: o.api_reads.filter(r => /experience/.test(r.url)).map(r => r.duration_ms + 'ms/' + r.status)
  });
}
