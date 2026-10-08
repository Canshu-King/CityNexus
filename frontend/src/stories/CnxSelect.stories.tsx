import type { Meta, StoryObj } from "@storybook/react-vite";
import { useState } from "react";
import { CnxSelect, ENHANCED_MIN_OPTIONS, type CnxSelectOption } from "../components/CnxSelect";

/** The two arms side by side, on the same control contract.
 *
 *  The short arm is what every dropdown on the authoritative line uses today (the
 *  widest one measured five options). The long arm exists for the lists that outgrow
 *  a glance, so this story is where its filter, its window and its sheet get driven
 *  by a real pointer instead of by a claim. */
const meta: Meta<typeof CnxSelect> = {
  title: "Controls/Select",
  component: CnxSelect,
};
export default meta;

type Story = StoryObj<typeof CnxSelect>;

const SHORT: CnxSelectOption[] = [
  { value: "FLIGHT", label: "Flight" },
  { value: "RAIL", label: "Rail" },
  { value: "HOTEL", label: "Hotel" },
  { value: "TICKET", label: "Ticket" },
  { value: "RESERVATION", label: "Reservation" },
];

/** 320 rows: past the threshold on purpose, and with a keyword column so the filter
 *  has something to match that the visible label does not carry. */
const LONG: CnxSelectOption[] = Array.from({ length: 320 }, (_, i) => ({
  value: `opt-${i}`,
  label: `Option ${String(i + 1).padStart(3, "0")} — ${
    ["Harbour", "Market", "Temple", "Station", "Garden", "Museum"][i % 6]
  }`,
  keywords: `CNX-${1000 + i}`,
}));

function Controlled({ options, initial }: { options: CnxSelectOption[]; initial: string }) {
  const [value, setValue] = useState(initial);
  return (
    <div style={{ maxWidth: 420 }}>
      <label style={{ display: "block", marginBottom: 6, fontSize: 12, opacity: 0.8 }}>
        Evidence mode
        <CnxSelect
          data-testid="lab-searchable-select"
          ariaLabel="Evidence mode"
          value={value}
          onChange={setValue}
          options={options}
        />
      </label>
      <p style={{ fontSize: 12, opacity: 0.75 }}>
        value = {value} · options = {options.length} · threshold = {ENHANCED_MIN_OPTIONS}
      </p>
    </div>
  );
}

export const ShortListNativeArm: Story = {
  render: () => <Controlled options={SHORT} initial="RAIL" />,
};

export const LongListSearchableArm: Story = {
  render: () => <Controlled options={LONG} initial="opt-7" />,
};
