import { Compass, MapPinned, UserRound } from "lucide-react";

export type RevolutionMobileTab = "explore" | "trips" | "me";

type Props = {
  active: RevolutionMobileTab;
  onSelect: (tab: RevolutionMobileTab) => void;
  hasSavedWalk: boolean;
};

const tabs = [
  { key: "explore", label: "探索", icon: Compass },
  { key: "trips", label: "行程", icon: MapPinned },
  { key: "me", label: "我的", icon: UserRound },
] as const;

/**
 * First real mobile information architecture for the isolated Revolution app.
 * Uses already-installed lucide-react; never introduces a dependency to the
 * Qoder mainline or triggers a provider/model request when navigating.
 */
export function RevolutionMobileNav({ active, onSelect, hasSavedWalk }: Props) {
  return (
    <nav className="rev-mobile-bottom-nav" aria-label="底部导航" data-testid="rev-mobile-bottom-nav">
      {tabs.map(({ key, label, icon: Icon }) => (
        <button
          type="button"
          className={"rev-mobile-nav-button" + (active === key ? " is-active" : "")}
          key={key}
          onClick={() => onSelect(key)}
          aria-label={label}
          aria-current={active === key ? "page" : undefined}
          data-testid={"rev-mobile-tab-" + key}
        >
          <span className="rev-mobile-nav-icon">
            <Icon size={22} strokeWidth={active === key ? 2.3 : 1.8} aria-hidden="true" />
            {key === "trips" && hasSavedWalk && <span className="rev-mobile-nav-dot" aria-hidden="true" />}
          </span>
          <span className="rev-mobile-nav-label">{label}</span>
        </button>
      ))}
    </nav>
  );
}
