// Run the building's acceptance ruler end to end: read the screen, judge it, print the verdict.
//
// Why this file exists.  The ruler in `building_screen_ruler_r1.py` owns the JUDGEMENT (three questions per
// cause) and takes its screen readings on stdin, because the project venv has no python playwright -- a
// ruler whose judgement changes with its environment is not a ruler, so the split is deliberate.  But it
// left the caller hand-assembling JSON, which is exactly the work that makes "just re-run it after the fix"
// never happen.  This file is the missing leg: the repo's own frontend dev dependency already ships
// playwright, so the reading runs where playwright actually exists, and hands its output to the ruler.
//
// It adds no judgement of its own.  Delete this file and the ruler still runs; edit the ruler and this
// file's verdict moves with it.
//
// Before scoring anything it checks the server actually answered each cause's own code, so a screen that
// never settled cannot be scored as an honest screen.
//
// Run:  node building_acceptance_r2.mjs <frontendBase> <backendBase>

import { chromium } from 'playwright';
import { readFileSync, writeFileSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const RULER = path.join(HERE, 'building_screen_ruler_r1.py');

const SCENARIOS = [
  { cause: 'no_canonical_identity', query: '贡山独龙族怒族自治县', expect: 'NO_CANONICAL_IDENTITY' },
  { cause: 'catalog_empty', query: '北京', expect: 'COVERAGE_INCOMPLETE' },
];

const NOTICES = ['trial-city-warning', 'trial-inferred', 'trial-alert'];

async function serverAnswer(backend, query) {
  const url = `${backend}/api/v1/destinations/capability?query=${encodeURIComponent(query)}`;
  const r = await fetch(url);
  if (!r.ok) throw new Error(`server answered HTTP ${r.status} for ${query}`);
  return r.json();
}

async function readOne(page, frontend, query) {
  await page.goto(`${frontend}/v8/discover`);
  await page.waitForSelector("[data-testid='trial-city']", { timeout: 25000 });
  await page.getByTestId('trial-city').fill(query);
  await page.waitForTimeout(2500);
  for (const tid of NOTICES) {
    const loc = page.getByTestId(tid);
    if (await loc.count()) return (await loc.first().innerText()).trim();
  }
  return (await page.locator('body').first().innerText()).trim();
}

async function main() {
  const [frontend, backend] = process.argv.slice(2).map((s) => s.replace(/\/$/, ''));
  if (!frontend || !backend) {
    console.error('usage: node building_acceptance_r2.mjs <frontendBase> <backendBase>');
    process.exit(2);
  }

  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  const payload = [];
  const refusals = [];
  for (const sc of SCENARIOS) {
    const api = await serverAnswer(backend, sc.query);
    const body = await readOne(page, frontend, sc.query);
    const got = api.reason_code ?? null;
    if (got !== sc.expect) refusals.push(`${sc.cause}: server answered ${got}, expected ${sc.expect}`);
    payload.push({
      scenario: sc.cause,
      server_code: got,
      server_missing: (api.missing_categories ?? []).length,
      body,
    });
    console.log(`[read] ${sc.cause}: server=${got} screen=${JSON.stringify(body.slice(0, 90))}`);
  }
  await browser.close();

  if (refusals.length) {
    for (const r of refusals) console.error(`REFUSE: ${r} -- a screen that never settled must not be scored`);
    process.exit(9);
  }

  const input = path.join(HERE, 'ruler_input_acceptance_r2.json');
  writeFileSync(input, JSON.stringify(payload), 'utf8');
  console.log(`\nwrote ${path.basename(input)}`);

  // the ruler must be the one next to this script, not one resolved against the caller's cwd
const proc = spawnSync(process.env.PYTHON_BIN ?? 'python', ['-X', 'utf8', RULER], {
    input: readFileSync(input, 'utf8'),
    encoding: 'utf8',
  });
  process.stdout.write(proc.stdout ?? '');
  process.stderr.write(proc.stderr ?? '');
  process.exit(proc.status ?? 1);
}

main();