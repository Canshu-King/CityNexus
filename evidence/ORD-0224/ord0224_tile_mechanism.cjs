/* ORD-0224 mechanism read for the false 「底图未加载」 notice.
 *
 * The notice is React state `tilesUnavailable` (MapPanel.tsx:44 at 0748a1f), and at that sha two
 * doors can set it and neither ever resets it:
 *   :266-268  mapInstance.on("error", e => if (e.sourceId === "open-street-map") setTilesUnavailable(true))
 *   :270-274  on("load", ... loaded = raster?.tiles?.some(bucket => bucket.has && bucket.size !== 0); if (loaded === false) ...)
 *
 * The zero-touch control already showed the notice appears with no gesture at all, ~10s after
 * load, while 9 raster tiles had answered 200. Which door fired is a different question, so this
 * samples the raster source's own per-tile state alongside the notice and the off-origin tally,
 * every 2s, and reports what changed in the interval where the notice appeared.
 *
 * It also checks whether the documented test seam container.citynexusMap is readable directly,
 * which is cheaper than the React-fiber walk my gesture probe had to use.
 */
const PW = process.env.CNX_PW || 'D:/moodle/_qoder_integration_20260919/frontend/node_modules/playwright';
const { chromium } = require(PW);
const fs = require('fs');
const path = require('path');

const BASE = process.env.CNX_BASE || 'http://127.0.0.1:8792';
const RUN = process.env.CNX_RUN || 'tilemech';
const VW = 390, VH = 844;
const sleep = ms => new Promise(r => setTimeout(r, ms));
const localIso = d => { const o = -d.getTimezoneOffset(), s = o >= 0 ? '+' : '-', p = n => String(n).padStart(2, '0'); return new Date(d.getTime() + o * 60000).toISOString().replace('Z', '') + s + p(Math.floor(Math.abs(o) / 60)) + ':' + p(Math.abs(o) % 60); };
const out = { base: BASE, run_label: RUN, pid: process.pid, started_at: localIso(new Date()), samples: [] };

(async () => {
  const browser = await chromium.launch({ headless: true });
  let ctx = null, page = null;
  const offOrigin = [];
  try {
    ctx = await browser.newContext({ viewport: { width: VW, height: VH }, deviceScaleFactor: 2, isMobile: true, hasTouch: true, locale: 'zh-CN', timezoneId: 'Asia/Shanghai' });
    await ctx.addInitScript(([id]) => { try { localStorage.setItem('citynexus.v8.journey_id', id); } catch (e) {} }, [process.env.CNX_JOURNEY || '']);
    page = await ctx.newPage();
    page.on('response', r => { const u = r.url(); if (!u.startsWith(BASE)) offOrigin.push('OK' + r.status() + ' ' + u.slice(0, 90)); });
    page.on('requestfailed', r => { const u = r.url(); if (!u.startsWith(BASE)) offOrigin.push('FAIL ' + (r.failure() && r.failure().errorText) + ' ' + u.slice(0, 90)); });

    await page.goto(BASE + '/v8/hub', { waitUntil: 'load', timeout: 45000 });

    const sample = () => page.evaluate(() => {
      const host = document.querySelector('.v8-map-panel');
      if (!window.__cnxMap2 && host) {
        const key = Object.keys(host).find(k => k.startsWith('__reactFiber$'));
        const isMap = o => o && typeof o.getCenter === 'function' && typeof o.getZoom === 'function';
        const seen = new Set();
        const scan = (obj, d) => {
          if (window.__cnxMap2 || !obj || d > 8 || typeof obj !== 'object' || seen.has(obj)) return;
          seen.add(obj);
          if (isMap(obj)) { window.__cnxMap2 = obj; return; }
          for (const k of ['stateNode', 'memoizedState', 'return', 'child', 'sibling', 'alternate', 'current', 'elementType']) scan(obj[k], d + 1);
          if (!window.__cnxMap2) for (const k of Object.keys(obj)) scan(obj[k], d + 1);
        };
        if (key) scan(host[key], 0);
      }
      const m = window.__cnxMap2 || null;
      let tileStates = null, bucketCount = null, loadedPredicate = null, containerIdent = null, seamOnContainer = null;
      if (m) {
        const raster = m.getSource && m.getSource('open-street-map');
        if (raster && raster.tiles) {
          bucketCount = raster.tiles.length;
          const tiles = [];
          for (const b of raster.tiles) { try { if (b && typeof b.values === 'function') for (const t of b.values()) tiles.push(t); } catch (e) {} }
          const byState = {};
          tiles.forEach(t => { const k = t && t.state ? String(t.state) : 'unknown'; byState[k] = (byState[k] || 0) + 1; });
          tileStates = { total: tiles.length, byState };
          loadedPredicate = raster.tiles.some(b => typeof b?.has === 'function' && b.size !== 0);
        }
        const c = m.getContainer && m.getContainer();
        if (c) {
          const cls = String(c.className || '').trim().split(/\s+/).slice(0, 3).join('.');
          containerIdent = c.tagName.toLowerCase() + (c.id ? '#' + c.id : '') + (cls ? '.' + cls : '');
          seamOnContainer = typeof c.citynexusMap === 'object' && typeof c.citynexusMap.getCenter === 'function';
        }
      }
      const n = [...document.querySelectorAll('*')].find(e => /底图/.test(e.textContent || '') && e.children.length === 0);
      return {
        mapFound: !!m, seamOnPanel: !!(host && host.citynexusMap), containerIdent, seamOnContainer,
        zoom: m ? m.getZoom() : null,
        bucketCount, tileStates, loadedPredicate,
        notice: !!n,
        noticeText: n ? n.textContent.trim().slice(0, 60) : null,
        raster200: 0, rasterFail: 0,
      };
    });

    const t0 = Date.now();
    let prev = null;
    for (let i = 0; i < 12; i++) {
      await sleep(2000);
      const s = await sample();
      s.atMs = Date.now() - t0;
      s.raster200 = offOrigin.filter(u => /^OK200 https:\/\/tile\./.test(u)).length;
      s.rasterFail = offOrigin.filter(u => /^FAIL/.test(u)).length;
      out.samples.push(s);
      if (prev && !prev.notice && s.notice) out.firstAppearance = { atMs: s.atMs, prevSample: prev, thisSample: s };
      prev = s;
    }
    await page.screenshot({ path: path.join(__dirname, 'shots', 'ord0224_' + RUN + '.png') }).catch(() => 0);
    out.offOriginSample = offOrigin.slice(0, 40);
    out.mapAccessAtEnd = out.samples.length ? { mapFound: out.samples[out.samples.length - 1].mapFound, containerIdent: out.samples[out.samples.length - 1].containerIdent, seamOnContainer: out.samples[out.samples.length - 1].seamOnContainer, seamOnPanel: out.samples[out.samples.length - 1].seamOnPanel } : null;
    out.verdict = out.firstAppearance
      ? 'MECHANISM_READ: 提示在 ' + out.firstAppearance.atMs + 'ms 出现，该样本 raster200=' + out.firstAppearance.thisSample.raster200 + ' rasterFail=' + out.firstAppearance.thisSample.rasterFail + ' 瓦片状态=' + JSON.stringify(out.firstAppearance.thisSample.tileStates) + ' loaded谓词=' + out.firstAppearance.thisSample.loadedPredicate
      : 'NO_APPEARANCE_WINDOW: 24s 内提示未出现，需延长观察';
  } catch (e) {
    out.error = String(e && e.message || e).split('\n')[0].slice(0, 200);
    out.verdict = 'ERROR';
  } finally {
    out.ended_at = localIso(new Date());
    fs.writeFileSync(path.join(__dirname, 'ord0224_tilemech_' + RUN + '.json'), JSON.stringify(out, null, 2));
    console.log(JSON.stringify({
      run: RUN, seam: out.samples.map(s => s.atMs + 'ms map=' + (s.mapFound ? 'Y' : 'N') + ' seamPanel=' + (s.seamOnPanel ? 'Y' : 'N') + ' seamCont=' + (s.seamOnContainer ? 'Y' : 'N') + ' ' + (s.containerIdent || '-') + ' zoom=' + (s.zoom && +s.zoom.toFixed(2)) + ' t200=' + s.raster200 + ' fail=' + s.rasterFail + ' tiles=' + JSON.stringify(s.tileStates && s.tileStates.byState) + ' loaded=' + s.loadedPredicate + ' notice=' + (s.notice ? 'YES' : 'no')),
      firstAppearance: out.firstAppearance && { atMs: out.firstAppearance.atMs, thisSample: out.firstAppearance.thisSample },
      verdict: out.verdict, err: out.error || null,
    }, null, 2));
    if (ctx) await ctx.close().catch(() => 0);
    await browser.close().catch(() => 0);
  }
})();
