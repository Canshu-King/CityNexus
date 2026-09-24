import io

p = 'frontend/src/features/setup/JourneyTrialSetup.tsx'
t = io.open(p, encoding='utf-8', newline='').read()

# 1. prop type
type_anchor = '  sealedDemoUnavailable?: string | null;'
type_add = type_anchor + '\n  /** ORD-0273: technical facts (raw message, error name) for data-* only -- never user copy. */\n  sealedDemoDetail?: { message: string; name: string } | null;'
assert t.count(type_anchor) == 1
t = t.replace(type_anchor, type_add)

# 2. destructure
de_anchor = '  sealedDemoUnavailable,'
de_add = '  sealedDemoDetail,'
assert t.count(de_anchor) == 1
t = t.replace(de_anchor, de_add)

# 3. the alert element: i18n key text, technical detail in data-*, and an executable next step
render_old = '''      {/* Secondary, de-emphasised: the sealed demo is not the golden path. */}
      {sealedDemoUnavailable && (
        /* ORD-0209 5: fail-closed with the reason, never a silent creation fallback. */
        <p
          className="trial-city-warning"
          data-testid="trial-sealed-unavailable"
          role="alert"
        >
          {sealedDemoUnavailable}
        </p>
      )}'''
render_new = '''      {/* Secondary, de-emphasised: the sealed demo is not the golden path. */}
      {sealedDemoUnavailable && (
        /* ORD-0209 5: fail-closed with the reason, never a silent creation fallback.
           ORD-0273-TEXT: the sentence is an i18n key; the raw error facts ride in data-*.
           ORD-0273-ACTION: an executable next step travels with the failure -- retry the same
           read here; creating one's own trip stays available below regardless. */
        <div
          className="trial-city-warning"
          data-testid="trial-sealed-unavailable"
          role="alert"
          data-error-name={sealedDemoDetail?.name ?? ""}
          data-error-message={sealedDemoDetail?.message ?? ""}
        >
          <p>{sealedDemoUnavailable}</p>
          <button
            type="button"
            className="trial-back-link"
            data-testid="trial-sealed-retry"
            disabled={busy}
            onClick={() => void onUseSealedDemo()}
          >
            {zh ? "重试" : "Retry"}
          </button>
        </div>
      )}'''
assert t.count(render_old) == 1
t = t.replace(render_old, render_new)

io.open(p, 'w', encoding='utf-8', newline='').write(t)
print('ACTION half wired (retry CTA + data-* detail)')
