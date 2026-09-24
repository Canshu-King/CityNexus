import io

p = 'frontend/src/app/V8Experience.tsx'
t = io.open(p, encoding='utf-8', newline='').read()

anchor = '          {dropped.length > 0 && ('
assert t.count(anchor) == 1, t.count(anchor)

card = '''          {continuation.kind === "pending" && (
            /* ORD-0269 cell 1: an interrupted plan is a durable fact, not a silence.  The marker is
               device-local, so the sentence itself names the boundary ("on this device").  The resume
               gate is MANUAL_RESUME / NOT-EXACTLY-ONCE until ORD-0272 gives the continuation a durable
               server-side identity -- no marker clearing happens before any request is sent. */
            <section className="today-continuation" data-testid="continuation-pending">
              <strong data-testid="continuation-pending-heading">
                {t("hub.continuationPending")}
              </strong>
              <button
                type="button"
                className="v8-primary"
                data-testid="continuation-resume"
                onClick={() => {
                  /* MANUAL_RESUME: the sheet opens on the plan flow; it does NOT auto-send.  The
                     marker deliberately stays until a visible outcome exists (clause 5). */
                  const sheetButton = document.querySelector(
                    '[data-testid="hub-plan-with-ai"]',
                  ) as HTMLButtonElement | null;
                  sheetButton?.click();
                }}
              >
                {t("hub.continuationResume")}
              </button>
            </section>
          )}
          {continuation.kind === "unconfirmable" && (
            /* ORD-0269 cell 3: a marker exists but the feed cannot confirm the mission (read failed
               or the ascending capped page excluded it).  Named state, never silence. */
            <p className="today-continuation-unconfirmable" data-testid="continuation-unconfirmable">
              {t("hub.continuationUnconfirmable")}
            </p>
          )}
'''

t = t.replace(anchor, card + anchor)
io.open(p, 'w', encoding='utf-8', newline='').write(t)
print('cards wired')
