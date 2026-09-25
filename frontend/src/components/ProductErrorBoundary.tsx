/**
 * Route/product error boundary.
 *
 * A runtime error in any panel must never trap the traveller on a white screen.
 * The boundary always explains what happened, reassures that trip data is safe,
 * and offers retry / back-to-today / reload.
 */

import { Component, type ErrorInfo, type ReactNode } from "react";

import { describeServerReason, reasonFromThrown } from "../lib/serverReason";
import { ServerReasonDetail } from "./ServerReasonDetail";
type Props = { children: ReactNode };
type State = { error: Error | null };

const COPY = {
  en: {
    title: "Something went wrong here",
    body: "Your trip data has not been lost. You can retry this screen or go back to Today.",
    retry: "Try again",
    home: "Back to Today",
    reload: "Reload the app",
    detail: "Technical detail",
  },
  zh: {
    title: "这里出了点问题",
    body: "你的行程数据没有丢失。可以重试当前页面，或回到「今天」。",
    retry: "重试",
    home: "返回今天",
    reload: "重新加载",
    detail: "技术详情",
  },
} as const;

function pick() {
  const lang = (typeof navigator !== "undefined" && navigator.language) || "en";
  return lang.toLowerCase().startsWith("zh") ? COPY.zh : COPY.en;
}

function pickZh() {
  const lang = (typeof navigator !== "undefined" && navigator.language) || "en";
  return lang.toLowerCase().startsWith("zh");
}

export class ProductErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): Partial<State> {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    /* ORD-0326 / Q64=1: a component stack is developer evidence, never traveller-facing text. It used to
       be stored in state and printed in the <pre> below, which is the "异常栈直接进 DOM" the ruling
       forbids; it now stays on the developer channel only. */
    console.error("[ProductErrorBoundary]", error?.message, info?.componentStack);
  }

  private reset = () => this.setState({ error: null });

  private goHome = () => {
    try {
      window.history.pushState({}, "", "/v8/hub");
      window.dispatchEvent(new PopStateEvent("popstate"));
    } catch {
      window.location.assign("/v8/hub");
    }
    this.reset();
  };

  render() {
    const { error } = this.state;
    if (!error) return this.props.children;
    const t = pick();
    const reason = describeServerReason(reasonFromThrown(error));
    return (
      <section
        className="v8-page"
        data-testid="product-error-boundary"
        role="alert"
        aria-live="assertive"
        style={{ padding: "24px 18px", maxWidth: 520, margin: "0 auto" }}
      >
        <h1 style={{ fontSize: 20, marginBottom: 8 }}>{t.title}</h1>
        <p style={{ opacity: 0.8, lineHeight: 1.5 }}>{t.body}</p>
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginTop: 16 }}>
          <button
            type="button"
            data-testid="error-retry"
            className="v8-primary-button"
            onClick={this.reset}
          >
            {t.retry}
          </button>
          <button
            type="button"
            data-testid="error-home"
            className="v8-outline-button"
            onClick={this.goHome}
          >
            {t.home}
          </button>
          <button
            type="button"
            data-testid="error-reload"
            className="v8-outline-button"
            onClick={() => window.location.reload()}
          >
            {t.reload}
          </button>
        </div>
        <details style={{ marginTop: 18, opacity: 0.7, fontSize: 12 }}>
          <summary>{t.detail}</summary>
          <ServerReasonDetail reason={reason} zh={pickZh()} testId="error-detail" />
        </details>
      </section>
    );
  }
}
