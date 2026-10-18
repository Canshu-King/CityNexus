import { useEffect, useState } from "react";
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
  const [goalRequest, setGoalRequest] = useState<{ journeyId: string; goal: string } | null>(null);
  const openCanvas = (kind: "assistant" | "map", request?: { journeyId: string; goal: string }) => {
    onSelect("explore"); setPanel(null);
    window.requestAnimationFrame(() => {
      const canvas = document.querySelector<HTMLElement>(".cn-mission-os");
      if (!canvas) { if (request) setGoalRequest(request); setPanel(kind); return; }
      if (kind === "assistant") window.dispatchEvent(new CustomEvent("citynexus:mission-command", { detail: request }));
      canvas.querySelector<HTMLElement>(kind === "map" ? ".cn-mission-map-pane" : ".cn-mission-agent-pane")?.scrollIntoView({ block: "nearest", inline: "start", behavior: "smooth" });
    });
  };
  useEffect(() => {
    const open = (event: Event) => {
      const value = (event as CustomEvent).detail;
      if (!value || typeof value.journeyId !== "string" || typeof value.goal !== "string") return;
      openCanvas("assistant", { journeyId: value.journeyId, goal: value.goal.slice(0, 2000) });
    };
    window.addEventListener("citynexus:open-goal-task", open);
    return () => window.removeEventListener("citynexus:open-goal-task", open);
  }, [onSelect]);
  // Mission canvas can expand the real, authenticated map without adding a sixth tab.
  useEffect(() => {
    const openMap = () => openCanvas("map");
    window.addEventListener("citynexus:open-map-workspace", openMap);
    return () => window.removeEventListener("citynexus:open-map-workspace", openMap);
  }, [onSelect]);
  return <>
    <nav className="rev-mobile-bottom-nav rev-workspace-nav" aria-label="底部导航" data-testid="rev-mobile-bottom-nav">
      {tabs.map(({ key, label, icon: Icon }) => {
        const selected = panel ? panel === key : active === key;
        return <button type="button" className={"rev-mobile-nav-button" + (selected ? " is-active" : "")} key={key}
          onClick={() => { if (key === "map" || key === "assistant") openCanvas(key); else { setPanel(null); onSelect(key); } }}
          aria-label={label} aria-current={selected ? "page" : undefined} data-testid={"rev-mobile-tab-" + key}>
          <span className="rev-mobile-nav-icon"><Icon size={22} strokeWidth={selected ? 2.3 : 1.8} aria-hidden="true" />
            {key === "trips" && hasSavedWalk && <span className="rev-mobile-nav-dot" aria-hidden="true" />}</span>
          <span className="rev-mobile-nav-label">{label}</span>
        </button>;
      })}
    </nav>
    <WorkspaceActions panel={panel} goalRequest={goalRequest} onClose={() => { setPanel(null); setGoalRequest(null); window.dispatchEvent(new Event("citynexus:mission-refresh")); }} />
  </>;
}
