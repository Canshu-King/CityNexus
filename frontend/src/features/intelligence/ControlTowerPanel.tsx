import { Icon } from "../../components/v8/Icon";
import type { AgentRuntimeStatus } from "../../api/citynexus";
import { useLocale, useT } from "../../i18n/LocaleContext";
import { policyModeLabel, runtimeIdentityLabel } from "../../lib/displayVocabulary";

type Policy = { mode: "ADVISORY" | "ASSISTED" | "AUTONOMOUS"; version: number } | null;

export function ControlTowerPanel({
  policy,
  runtimeStatus,
  onActivate,
}: {
  policy: Policy;
  runtimeStatus: AgentRuntimeStatus | null;
  onActivate: () => Promise<void>;
}) {
  const t = useT();
  const { locale } = useLocale();
  /* 链路只在真读到 runtime_identity 时才画。原先的 else 支把「根本没读过」与
     HERMES_COMPAT_ENDPOINT / NOT_CONFIGURED 一并写成 "Deterministic fallback"，等于替服务器
     编了一条它没说过的链路；`lib/displayVocabulary.ts:22` 那张表本来就给这四枚值各备了说法，
     所以读得到的未知身份改走同一张表，读不到就明说读不到。 */
  const runtimeChain = !runtimeStatus
    ? [t("intel.runtimeUnknown")]
    : runtimeStatus.runtime_identity === "HERMES_NATIVE_MCP"
      ? [t("intel.deepseek"), t("intel.hermes"), "MCP", t("intel.gateway"), t("intel.domain")]
      : runtimeStatus.runtime_identity === "NATIVE_DEEPSEEK_TOOL_LOOP"
        ? [t("intel.deepseek"), "CityNexus Direct", t("intel.gateway"), t("intel.domain")]
        : [runtimeIdentityLabel(runtimeStatus.runtime_identity, locale)];
  return (
    <section className="v8-page">
      <div className="v8-page-intro compact">
        <div>
          <p className="v8-kicker">{t("intel.kicker")}</p>
          <h1>{t("intel.title")}</h1>
          <p className="v8-lede">{t("intel.lede")}</p>
        </div>
        <button className="v8-primary" onClick={() => void onActivate()}>
          {policy?.mode === "AUTONOMOUS" ? t("intel.autonomyActive") : t("intel.enableRecovery")}
        </button>
      </div>
      <div className="v8-intelligence-grid">
        <article className="v8-intel-hero">
          {/* 「就绪」以前与任何读数无关都点亮，现在至少要有一条控制面读数；本屏没有 guardian
              读数，所以一条 policy 读数是否足以支撑「就绪」这个词已上账待裁。 */}
          <span className={policy ? "v8-status-pill violet" : "v8-status-pill"}>
            <Icon name="spark" />
            {policy ? t("intel.guardianReady") : t("intel.guardianUnknown")}
          </span>
          <h2>{t("intel.recoveryTitle")}</h2>
          <p>{t("intel.recoverySub")}</p>
          <div className="v8-chain">
            {runtimeChain.map((item, index) => (
              <span key={`${item}-${index}`}>{item}{index < runtimeChain.length - 1 && <b className="v8-chain-arrow">→</b>}</span>
            ))}
          </div>
          <div className="v8-runtime-card" data-testid="v17-runtime-status">
            <span>{t("intel.runtimeSource")}</span>
            <b>{runtimeStatus ? runtimeIdentityLabel(runtimeStatus.runtime_identity, locale) : t("intel.runtimeUnknown")}</b>
            <small>
              {/* 两臂三元把「没读过」答成了一句确定的否定（没问过却说「未宣称」）。
                  补上第三态：证明状态没读到就是没读到。 */}
              {!runtimeStatus
                ? t("intel.proofUnknown")
                : runtimeStatus.native_mcp_proven
                  ? t("intel.nativeMcpProven")
                  : t("intel.nativeMcpNotProven")}
            </small>
          </div>
        </article>
        <div className="v8-intel-facts">
          <div>
            <span>{t("intel.policy")}</span>
            {/* 空读过去显示 intel.advisory，与建议态逐字相同，屏上分不出「没读到」与「真是建议」；
                同屏 :51 的运行时那一格已经示范了正确写法（走 intel.runtimeUnknown）。 */}
            <b>{policy ? policyModeLabel(policy.mode, locale) : t("intel.policyUnknown")}</b>
            <small>{t("intel.versionPrefix")} {policy?.version ?? "—"} {t("intel.versionSuffix")}</small>
          </div>
          <div>
            <span>{t("intel.postActionGate")}</span>
            <b>{t("intel.feasible")}</b>
            <small>{t("intel.gateSub")}</small>
          </div>
          <div>
            <span>{t("intel.commitment")}</span>
            <b>{t("intel.protected")}</b>
            <small>{t("intel.commitmentSub")}</small>
          </div>
        </div>
      </div>
    </section>
  );
}
