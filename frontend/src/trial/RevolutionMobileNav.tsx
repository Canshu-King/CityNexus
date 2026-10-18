import { useState } from "react";
import { Bot, Compass, Map, MapPinned, UserRound } from "lucide-react";
import { WorkspaceActions, type WorkspacePanel } from "./mobile/WorkspaceActions";

export type RevolutionMobileTab = "explore" | "trips" | "me";
type Props = { active: RevolutionMobileTab; onSelect: (tab: RevolutionMobileTab) => void; hasSavedWalk: boolean };
const tabs = [
  { key: "explore", label: "探索", icon: Compass },
  { key: "trips", label: "行程", icon: MapPinned },
  { key: "assistant", label: "AI助手", icon: Bot },
  { key: "map", label: "地图", icon: Map },
  { key: "me", label: "我的", icon: UserRound },
] as const;

// The existing three routes keep their state; map and assistant are available from every route.
export function RevolutionMobileNav({ active, onSelect, hasSavedWalk }: Props) {
  const [panel, setPanel] = useState<WorkspacePanel>(null);
  return <>
    <nav className="rev-mobile-bottom-nav rev-workspace-nav" aria-label="底部导航" data-testid="rev-mobile-bottom-nav">
      {tabs.map(({ key, label, icon: Icon }) => {
        const selected = panel ? panel === key : active === key;
        return <button type="button" className={"rev-mobile-nav-button" + (selected ? " is-active" : "")} key={key}
          onClick={() => { if (key === "map" || key === "assistant") setPanel(key); else { setPanel(null); onSelect(key); } }}
          aria-label={label} aria-current={selected ? "page" : undefined} data-testid={"rev-mobile-tab-" + key}>
          <span className="rev-mobile-nav-icon"><Icon size={22} strokeWidth={selected ? 2.3 : 1.8} aria-hidden="true" />
            {key === "trips" && hasSavedWalk && <span className="rev-mobile-nav-dot" aria-hidden="true" />}</span>
          <span className="rev-mobile-nav-label">{label}</span>
        </button>;
      })}
    </nav>
    <WorkspaceActions panel={panel} onClose={() => setPanel(null)} />
  </>;
}
