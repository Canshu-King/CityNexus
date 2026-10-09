/* Verification face for the tooltip — not a product route and not linked from the app.
   It exists because the two product faces this order wires both need server rows to appear, and a
   claim about *when a bubble opens* cannot be measured through a data supply that is not there.
   Everything rendered here is the real component, real CSS and real strings; only the mounting is
   ours.  Serve with:
     node node_modules/vite/bin/vite.js dev -c vite.harness.config.ts
   then open /harness/tooltip-harness.html. */
import { createRoot } from "react-dom/client";
import { LocaleProvider } from "../src/i18n/LocaleContext";
import { ActivityCard } from "../src/features/execution/V12StatePrimitives";
import { CnTipText } from "../src/components/Tooltip";
import "../src/styles.css";
import "../src/design-tokens.css";
/* The note's own sheet: without it `.cn-collections__item-note` renders unstyled and never
   clips, so the arm that is supposed to prove long-text recovery would silently prove nothing. */
import "../src/features/collections/collections.css";

const LONG_STATION =
  "天津西站 · 南站房第三候车厅 Tianjin West Station — south concourse, waiting hall three, gate D";

const LONG_NOTE =
  "青岛站 · 鱼山路入口 Qingdao Station — Yushan Road entrance：出站后右手边第三个路口左转；" +
  "雨天请走地下通道 instead of the surface crossing，因为台阶会积水，而导航仍然把它当成首选路线。" +
  "这一段故意写到超过气泡的框，为的就是看它到底是换行、滚动，还是把后半句又吞掉。";

const SHELL = {
  padding: 40,
  display: "grid",
  gap: 26,
  alignItems: "start",
  fontFamily:
    "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif",
} as const;

const CARD = {
  width: 240,
  padding: 12,
  border: "1px solid #dfe4ed",
  borderRadius: 12,
  /* The point of this arm: the card clips its own contents.  A bubble placed inside it would be
     cut here, which is the ORD-0510 failure this design has to clear. */
  overflow: "hidden",
  background: "#fff",
} as const;

function Face() {
  return (
    <div style={SHELL}>
      <div id="arm-a" style={CARD} data-testid="clipping-card">
        <ActivityCard title={LONG_STATION} state="IN_PROGRESS" />
      </div>

      <div id="arm-b" style={{ width: 260, padding: 12, border: "1px solid #dfe4ed", borderRadius: 12, background: "#fff" }}>
        <ul className="cn-collections__items">
          <li data-testid="collection-item">
            <span className="cn-collections__item-name">栈桥回澜阁</span>
            <CnTipText className="cn-collections__item-note" text={LONG_NOTE} />
          </li>
        </ul>
      </div>

      <div id="arm-c" style={{ ...CARD, width: 430 }}>
        <ActivityCard title="厦门站 Xiamen Station" state="COMPLETED" />
      </div>
    </div>
  );
}

createRoot(document.getElementById("root")!).render(
  <LocaleProvider>
    <Face />
  </LocaleProvider>,
);
