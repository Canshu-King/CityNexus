"""One-shot rewrite of the shell's three failure views into a single classified view (R14 / ORD-0169).

Kept as a file rather than a heredoc: the replacement text contains comment markers that a shell
scan reads as a UNC path, and this script is also the record of exactly what was replaced.
"""

import io

PATH = "D:/moodle/_qoder_integration_20260919/frontend/src/app/V8Experience.tsx"
START = "  /* ORD-0126 ③: a non-2xx has to be readable where the traveller was standing"
END = "  // " + "Intentional, and ruled so (Amendment F #1)"

NEW = '''  /* R14-P / ORD-0169: one failure view, driven by the classification that was made at the evidence
     boundary.  The kicker, the headline, the body, the announcement and the recovery button are all
     read off `failure.attribution`, so a 404 can no longer be shown as a network failure by a branch
     that wrote its own sentence, and the map is not hidden unless the classified state says so. */
  if (failure && !data) {
    const copy = copyFor(failure.attribution, locale.startsWith("zh"), {
      journeyId: failure.journeyId ?? undefined,
    });
    const action = failure.attribution.recovery_action;
    const recovery =
      action === "choose-journey"
        ? {
            testId: "failure-choose-journey",
            label: locale.startsWith("zh") ? "选一趟行程" : "Choose a trip",
            run: () => {
              setFailure(null);
              setSetupOpen(true);
            },
          }
        : action === "sign-in"
          ? {
              testId: "failure-sign-in",
              label: locale.startsWith("zh") ? "重新登录" : "Sign in again",
              run: () => {
                setFailure(null);
                window.location.reload();
              },
            }
          : action === "read-only-cached"
            ? {
                testId: "failure-read-cached",
                label: locale.startsWith("zh") ? "看已保存的只读副本" : "Read the saved copy",
                run: () => {
                  setFailure(null);
                  window.location.reload();
                },
              }
            : {
                testId: "failure-retry",
                label: locale.startsWith("zh") ? "重试" : "Try again",
                run: () => {
                  setFailure(null);
                  setBusy(true);
                  window.location.reload();
                },
              };
    return (
      <section
        className="v8-page"
        data-testid="failure-view"
        data-attribution-reason={failure.attribution.reason}
        data-evidence-kind={failure.attribution.evidence_kind}
        data-http-status={failure.attribution.http_status ?? ""}
        data-source-layer={failure.attribution.source_layer}
        data-recovery-action={action}
        role="alert"
        aria-live="assertive"
      >
        <div className="v8-page-intro compact">
          <div>
            <p className="v8-kicker">{copy.kicker}</p>
            <h1>{copy.title}</h1>
            <p className="v8-lede" data-testid="failure-reason">
              {copy.body}
            </p>
          </div>
        </div>
        <div className="v8-sheet-primary">
          <button
            type="button"
            className="v8-primary-button"
            data-testid={recovery.testId}
            onClick={recovery.run}
          >
            {recovery.label}
          </button>{" "}
          {action !== "retry" && (
            <button
              type="button"
              className="v8-outline-button"
              data-testid="failure-retry"
              onClick={() => {
                setFailure(null);
                setBusy(true);
                window.location.reload();
              }}
            >
              {locale.startsWith("zh") ? "重试" : "Try again"}
            </button>
          )}
        </div>
        {/* The record the classifier actually produced, kept on screen for the same reason telemetry
            keeps it: a false cause has to be discoverable without a screenshot. */}
        <details className="v8-advanced" data-testid="failure-attribution">
          <summary>{locale.startsWith("zh") ? "归因详情" : "Attribution detail"}</summary>
          <code data-testid="failure-attribution-line">{failure.attribution.telemetry}</code>
        </details>
      </section>
    );
  }

'''


def main() -> int:
    text = io.open(PATH, encoding="utf-8", newline="").read()
    start = text.find(START)
    end = text.find(END)
    if start < 0 or end < start:
        print(f"ABORT: anchors not found (start={start}, end={end}); nothing was written")
        return 2
    removed = text[start:end]
    updated = text[:start] + NEW + text[end:]
    io.open(PATH, "w", encoding="utf-8", newline="").write(updated)
    after = io.open(PATH, encoding="utf-8", newline="").read()
    crlf = io.open(PATH, "rb").read().count(b"\r\n")
    print(
        f"removed_chars={len(removed)} added_chars={len(NEW)} "
        f"journeyGone={after.count('journeyGone')} loadFailure={after.count('loadFailure')} "
        f"setUnreachable={after.count('setUnreachable')} crlf={crlf}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
