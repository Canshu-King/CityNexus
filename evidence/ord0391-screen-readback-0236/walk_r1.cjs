/* ORD-0391 screen read-back - walk the failure states the reworded sentences live in.
 *
 * The 23 lines ORD-0391 reworded are copy on the failure view, so a reading means reaching each
 * classified state on a real screen. The states are produced from outside the product: this lane's own
 * stub (:7042) answers the journey read with the scenario's status/body, and the app classifies it with
 * its own code. Each state is proven to have landed by echoing the status the page actually received.
 *
 * Two axes that the copy itself depends on are driven here:
 *   cached  - whether the device holds an offline copy (the copy has a different sentence for it);
 *   locale  - zh-CN / en-US, because every one of these lines is one arm of a ternary.
 */
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const HERE = __dirname;
const BASE = 'http://localhost:4541';
const STUB = 'http://127.0.0.1:7042';
const JOURNEY_ID = '22222222-2222-4222-8222-222222222222';
const ROUTE = '/v8/hub';
const VIEWPORT = { width: 390, height: 844 };

function setScenario(name) {
  return fetch(STUB + '/__scenario', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name }),
  }).then((r) => r.json());
}

/* The offline copy the app reads through Dexie; only its presence is folded into the classification,
   so the snapshot stays minimal but real-shaped. */
function offlineRow() {
  return {
    journey_id: JOURNEY_ID,
    sequence: 1,
    valid_until: new Date(Date.now() + 3600_000).toISOString(),
    snapshot: {
      active_plan_version_id: null,
      current_activity_id: null,
      next_24h: [],
      legs: [],
      hotel: null,
      reservations: [],
      read_only: true,
      financial_actions_allowed: false,
    },
    provider_freshness: { latest_provider_capture_at: null, transit_realtime: 'stale' },
    updated_at: new Date().toISOString(),
  };
}

async function crawlOne(browser, spec) {
  const scenario = await setScenario(spec.scenario);
  const ctx = await browser.newContext({
    viewport: VIEWPORT, locale: spec.locale === 'zh' ? 'zh-CN' : 'en-US', deviceScaleFactor: 1,
  });
  const seen = [];
  ctx.on('response', (res) => {
    const u = res.url();
    if (u.includes('/api/v1/journeys')) {
      seen.push({ url: u.replace(BASE, '').replace(STUB, ''), status: res.status(),
        ct: res.headers()['content-type'] || null });
    }
  });
  const pageErrors = [];
  ctx.on('page', (p) => p.on('pageerror', (e) => pageErrors.push(String(e.message).slice(0, 160))));
  const page = await ctx.newPage();
  await page.addInitScript((seed) => {
    localStorage.setItem('citynexus.locale', seed.locale);
    localStorage.setItem('citynexus.v8.journey_id', seed.journeyId);
    if (seed.seedOffline) {
      const req = indexedDB.open('citynexus-offline', 1);
      req.onupgradeneeded = () => {
        const db = req.result;
        if (!db.objectStoreNames.contains('journeys')) {
          db.createObjectStore('journeys', { keyPath: 'journey_id' });
        }
      };
      req.onsuccess = () => {
        try {
          const db = req.result;
          if (db.objectStoreNames.contains('journeys')) {
            const tx = db.transaction('journeys', 'readwrite');
            tx.objectStore('journeys').put(seed.row);
          }
        } catch (e) { /* the app's own read decides the flag; a failed seed shows up as cached=false */ }
      };
    }
  }, {
    locale: spec.locale === 'zh' ? 'zh-CN' : 'en-US',
    journeyId: spec.journeyId || JOURNEY_ID,
    seedOffline: Boolean(spec.cached),
    row: offlineRow(),
  });
  const shot = path.join(HERE, 'shots', spec.name + '.png');
  fs.mkdirSync(path.dirname(shot), { recursive: true });
  await page.goto(BASE + ROUTE, { waitUntil: 'domcontentloaded', timeout: 60_000 });
  let failureView = false;
  try {
    await page.waitForSelector('[data-testid="failure-view"]', { timeout: 12_000 });
    failureView = true;
  } catch (e) { /* not every state is a failure state - recorded, not assumed */ }
  await page.waitForTimeout(1500);
  const read = await page.evaluate(() => {
    const txt = (sel) => {
      const el = document.querySelector(sel);
      return el ? (el.textContent || '').trim() : null;
    };
    const nodes = [];
    const walk = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    for (let n = walk.nextNode(); n; n = walk.nextNode()) {
      const t = (n.nodeValue || '').trim();
      if (t.length > 0) nodes.push(t);
    }
    return {
      title: txt('title'),
      h1: txt('h1'),
      kicker: txt('[data-testid="failure-view"] h2, [data-testid="failure-view"] .v8-kicker'),
      reason: txt('[data-testid="failure-reason"]'),
      telemetry: txt('[data-testid="failure-attribution-line"]'),
      recovery: txt('[data-testid="failure-view"] button'),
      bodyChars: (document.body.innerText || '').length,
      bodyText: (document.body.innerText || ''),
      textNodes: nodes,
      attrCount: document.querySelectorAll('[data-cnx-field]').length,
    };
  });
  await page.screenshot({ path: shot, fullPage: false });
  const url = page.url();
  await ctx.close();
  return {
    name: spec.name, scenario: spec.scenario, locale: spec.locale, cached: Boolean(spec.cached),
    journey_id_used: spec.journeyId || JOURNEY_ID,
    route: ROUTE, url, failure_view: failureView,
    scenario_confirmed_in: (scenario.spec.rules || []).length,
    journey_responses: seen, page_errors: pageErrors, shot: path.basename(shot),
    read,
  };
}

(async () => {
  const specs = [];
  const LOCALES = ['zh', 'en'];
  for (const locale of LOCALES) {
    for (const scenario of ['off', 'not_found', 'server_error', 'unauthorized', 'forbidden',
      'html_200', 'empty_200']) {
      for (const cached of [false, true]) {
        if (!['server_error', 'html_200', 'empty_200', 'off'].includes(scenario) && cached) continue;
        specs.push({
          name: 's_' + scenario + '_c' + (cached ? 1 : 0) + '_' + locale,
          scenario, locale, cached,
        });
      }
    }
  }
  /* The "device remembers a trip this server does not have" arm uses an id the store does not hold,
     and it has to be a *well-formed* uuid or the shell treats it as no reference at all. */
  specs.push({ name: 's_off_missingid_c0_zh', scenario: 'off', locale: 'zh', cached: false,
    journeyId: '33333333-3333-4333-8333-333333333333' });
  specs.push({ name: 's_off_missingid_c0_en', scenario: 'off', locale: 'en', cached: false,
    journeyId: '33333333-3333-4333-8333-333333333333' });

  const browser = await chromium.launch({ timeout: 120_000 });
  const states = [];
  for (const spec of specs) {
    try {
      states.push(await crawlOne(browser, spec));
    } catch (err) {
      states.push({ name: spec.name, scenario: spec.scenario, error: String(err.message).slice(0, 300) });
    }
    process.stdout.write('.');
  }
  await browser.close();
  await setScenario('off');
  const tally = {};
  for (const s of states) {
    const k = s.failure_view === true ? 'failure_view' : (s.error ? 'walk_error' : 'no_failure_view');
    tally[k] = (tally[k] || 0) + 1;
  }
  fs.writeFileSync(path.join(HERE, 'walk_r1.json'), JSON.stringify({
    base: BASE, stub: STUB, route: ROUTE, viewport: VIEWPORT, states_walked: states.length,
    tally, states,
  }, null, 1));
  console.log('\n' + JSON.stringify({ states: states.length, tally }));
})();
