# CityNexus Revolution Lab — first HUMAN trial (2026-10-14)

**This is not the fusion product.** This branch comes straight from Revolution `a5a2f1096e0fbd806acd8be134fe8fb6095ad1a9`. The only additions are an isolated first-look launcher, a labelled local provider emulator, and this guide. It does not modify Qoder, Commander, the fusion work, or any deployed site.

## What is actually built

- The modern React/Vite UI boots through `frontend/src/main.tsx -> app/V8Experience.tsx`. Direct page: `/v8/hub`; the old `/legacy` page is not the normal entry.
- Revolution capabilities have user interfaces inside the existing V8 shell, not a wholly redesigned Revolution home. The most direct unique experience is a **zero-catalogue DRAFT Journey** -> `BootstrapDiscoveryPanel` -> R107 private two-stop Pocket Walk -> R108 GO MODE with stop navigation, self-reported progress, pause/resume/undo and reload.
- `frontend/src/features/execution/LiveRecovery.tsx` contains Journey Operator controls for ACTIVE Journey workflows.
- R107/R108 reported signed 390x844 Chromium runs and `npm run build` / typecheck passing on Codex's environment. GPT-only R108 reviewer fixes at Revolution HEAD were **not yet rerun** on that same environment. None of these reports establishes present-day device behavior.
- The UI reuses much of the earlier V8 shell. There are many English strings in the Revolution-specific surfaces. This is a usable developer preview candidate, **not proof of finished visual polish or a real-phone release**.
- A plain static HTML export is insufficient: backend API, signed identity, database and live server are needed.

## Windows quick start — isolated local developer preview

Prerequisites: Git, Python 3.12+ (3.13 recommended and used by prior Codex tests), Node.js 22 LTS + npm. Network may be needed on first run to install Python/npm dependencies.

From your already-cloned repository on Windows PowerShell (replace path if yours differs):

```powershell
cd D:\moodle\CityNexus
git fetch origin
git worktree add --detach D:\moodle\CityNexus-Revolution-Trial origin/trial/revolution-first-look-20261014
cd D:\moodle\CityNexus-Revolution-Trial
py -3.13 trial\try_revolution.py
```

The launcher:
1. Creates its OWN `trial/.runtime/python-venv`; installs the dependencies declared in `backend/pyproject.toml` on first setup; installs `frontend/node_modules` via `npm ci` if absent;
2. Starts an explicitly **CONTROLLED TEST_PROVIDER** city service and Overpass-shaped provider, both on `127.0.0.1`; never calls the public geocoder or Overpass for its demo discovery;
3. Starts a separate local backend with `backend/_revolution_hands_on.db`, distinct random persisted signing secret, `CITYNEXUS_AI_ENABLED=false`, mock booking/payment, and no Guardian autorun;
4. Starts the actual Vite frontend with a same-origin API proxy, then opens **http://127.0.0.1:14173/v8/hub**;
5. Leaves everything running until you press Enter in the launcher console. Services bind localhost only. Logs are in `trial/.runtime/*.log`.

This uses the real Revolution React frontend and application API, not a screenshot or synthetic UI. **The external city/OSM results are controlled fake samples, clearly labelled TEST_PROVIDER**. Do not walk to, share as factual, or rely on their returned coordinates/POI identities.

If you prefer a fresh database for a later trial without deleting an old one:

```powershell
py -3.13 trial\try_revolution.py --fresh
```

The browser's old localStorage may still point to a different previous Journey. Use a fresh Chrome profile/browser session or remove the old trial site's local data when starting `--fresh`; do not clear Qoder's existing site data.

## Existing frontend lock mismatch (known and safely handled)

The source Revolution `frontend/package.json` has `@types/react` and `@types/react-dom` but its `package-lock.json` root does not list them, and the lock omits these packages plus `csstype`. Plain `npm ci` exits with `EUSAGE`. As of the trial launcher fix, `try_revolution.py` detects **that precise** mismatch, and runs `npm install --no-audit --no-fund` only inside this isolated trial checkout. This updates only its local frontend lockfile, not the Revolution/Qoder remote source. Other npm failures are **not** silently ignored.

If using a previously fetched, older launcher, the immediate workaround is:

```powershell
cd D:\moodle\CityNexus-Revolution-Trial\frontend
npm install --no-audit --no-fund
cd ..
py -3.13 trial\try_revolution.py
```

To bring only the fixed launcher into an existing detached worktree, without discarding a locally repaired package-lock or changing the worktree branch:

```powershell
cd D:\moodle\CityNexus-Revolution-Trial
git fetch origin
git restore --source origin/trial/revolution-first-look-20261014 -- trial/try_revolution.py
py -3.13 trial\try_revolution.py
```

The pip upgrade notice is unrelated to the npm EUSAGE problem.

## First-time hands-on user journey (recommended)

1. Open the URL above. The app should show an onboarding wizard if this origin has no saved Journey. Create a **new Journey** for **Shanghai / 上海**, choose a future date range and reasonable budget. The launcher creates signed traveler identity through the **real product wizard**, not a console-injected token.
2. If that city has no native catalogue places, the shell enters **first-place discovery** (`BootstrapDiscoveryPanel`). This is intentional. **Do not select or start a formal PlanVersion yet:** Pocket Walk is deliberately DRAFT-only.
3. Choose the **manual/public city center** source. Search `Shanghai` after reading its distinct city-search consent. The local test provider returns `Shanghai, China (CONTROLLED TEST RESPONSE)`.
4. Paste the safe test public map-center URL `https://www.openstreetmap.org/#map=13/31.2304/121.4737`; apply/confirm the map center and city label. This URL encodes a PUBLIC map position, not a private home/GPS reading.
5. Choose **Art and history** and give its separate provider consent. Press **Search public places** once. The local emulator should return at least two `SAMPLE ONLY - Revolution ...` named records with `TEST_PROVIDER` grade. Opening/price/ETA should remain UNKNOWN. If none appear, see logs; do not invent actual OSM identity.
6. Pick two of the current results as first and second stop, set order/budget if offered, confirm the private save. Your **Pocket Walk** card should appear.
7. Use **GO MODE**: start -> optionally ask for destination navigation with its **separate consent** -> return -> **self-report first stop** -> head to second -> pause/resume -> self-report done -> reload to see persisted state. A map launch is NOT physical arrival proof.
8. The ordinary `/v8` shell's **Live Journey / Recovery** routes are also worth inspecting once you have an ACTIVE Journey, but AI is deliberately OFF here. Do not mistake a truthful `EXTERNAL_AGENT_BLOCKED`/unavailable state for an autonomous AI success.

**Product limitation:** This is based on previously reported automated E2E paths, not a live hands-on validation of the new launcher on your Windows machine. If the normal wizard cannot create a Shanghai Journey or the discovery panel remains inaccessible, that is a genuine first-user blocker. Capture the exact screen and logs; do not solve it by faking browser sessionStorage without explicit disclosure. Codex should fix the user entry on this trial branch first.

## Real Android phone without public deployment

An Android phone with Chrome, USB debugging and Android SDK platform-tools can use the SAME LOCAL PREVIEW via ADB reverse (no Cloudflare tunnel or public credentials required). Keep the trial launcher running on the PC:

```powershell
adb devices
adb reverse tcp:14173 tcp:14173
```

On the Android phone open **http://localhost:14173/v8/hub** in Chrome. The browser sees its own localhost as a potentially trustworthy origin. The phone uses the Vite proxy for backend APIs; the backend remains on the PC localhost. The localhost fixture stays TEST_PROVIDER. This is a suggested physical-device route, not a verified phone run.

For iPhone or a non-USB full PWA trial, ask Codex to set up a **separate access-controlled HTTPS staging origin** that proxies the exact same-origin frontend and API, with no production database or leaked credentials. Do not publish port 18201 or both test provider ports. Never put private traveler tokens into links or chat.

## Quick health check / troubleshooting

- Frontend via proxy: `http://127.0.0.1:14173/api/v1/health` should return HTTP 200 with JSON.
- Direct backend: `http://127.0.0.1:18201/api/v1/health` should answer.
- Test city provider: `http://127.0.0.1:18202/status` says `TEST_PROVIDER`.
- Test Overpass provider: `http://127.0.0.1:18203/status` says `TEST_PROVIDER`.
- Port already in use: stop conflicting process, do not borrow an existing Qoder backend. The trial refuses to reuse any of its four ports.
- Dependencies fail to install: inspect terminal output, or have Codex run setup in its known Python 3.13 worktree.
- Backend/frontend fails to start: inspect `trial/.runtime/backend.err.log`, `frontend.err.log`, `fixtures.err.log`.
- Existing Journey reopens incorrectly after `--fresh`: new Chrome profile/site storage, since `localStorage` may hold an old Journey id. Do not reset a genuine production Journey.
- Some map tiles and link previews may require internet even though this **controlled discovery service** does not query real public providers.

## What to tell Codex, only if first launch fails

"Check `trial/revolution-first-look-20261014`, run `py -3.13 trial/try_revolution.py` on Windows, visit the actual V8 onboarding UI as a human without injecting auth manually, complete a fresh Shanghai DRAFT -> controlled TEST_PROVIDER -> two-stop Pocket Walk -> R108 GO/refresh, fix ONLY the concrete first-user blockers on this trial branch, and give me the actual usable URL/device steps and screenshots. No new R110 work and no fusion or broad verifier campaign."

### Strict evidence language
`RUNBOOK/LAUNCHER PREPARED` does not equal `LOCAL_RUN_PASS`. `LOCAL_RUN_PASS` does not equal `REAL_PHONE_PASS`. `TEST_PROVIDER` does not equal `LIVE_PROVIDER`. `USER_REPORTED_PROGRESS` does not equal `PHYSICAL_ARRIVAL_PROVEN`.
