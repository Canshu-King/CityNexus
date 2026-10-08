import { useEffect, useId, useMemo, useRef, useState } from "react";
import "./cnx-select.css";

export type CnxSelectOption = {
  value: string;
  label: string;
  /** Words the label alone doesn't carry (a code, an alias). The search box matches
   *  these too, because a traveller types the word they can see and the word the
   *  server sent are frequently not the same word. */
  keywords?: string;
  disabled?: boolean;
};

/** Below this many options the operating system's own picker is the better control:
 *  it paints natively, it is already the platform's scroll, and a search field over
 *  four rows is noise. The enhanced arm exists for the lists that outgrow a glance. */
export const ENHANCED_MIN_OPTIONS = 12;

/** Rows the panel paints before it asks for more. This is the whole reason the panel
 *  can hold a long list: the DOM never carries more than a slice of it. */
const PAGE_ROWS = 30;

type Props = {
  value: string;
  options: CnxSelectOption[];
  onChange: (value: string) => void;
  "data-testid"?: string;
  id?: string;
  /** For a control the host doesn't wrap in a <label>. */
  ariaLabel?: string;
  disabled?: boolean;
  /** Set it to force the enhanced arm on a short list, or raise it to keep a long
   *  list native. Defaults to ENHANCED_MIN_OPTIONS. */
  searchThreshold?: number;
  className?: string;
};

/** The arms take the flattened name: `data-testid` is the host's spelling, `testId` is
 *  what the component threads through its own markup. */
type ArmProps = {
  value: string;
  options: CnxSelectOption[];
  onChange: (value: string) => void;
  disabled?: boolean;
  ariaLabel?: string;
  id?: string;
  testId?: string;
  className?: string;
};

function matches(option: CnxSelectOption, needle: string): boolean {
  if (!needle) return true;
  const hay = `${option.label} ${option.keywords ?? ""}`.toLowerCase();
  return hay.includes(needle);
}

export function CnxSelect(props: Props) {
  const {
    value,
    options,
    onChange,
    disabled,
    ariaLabel,
    id,
    searchThreshold = ENHANCED_MIN_OPTIONS,
    className,
  } = props;
  const testId = props["data-testid"];
  const enhanced = options.length >= searchThreshold;
  return enhanced ? (
    <CnxSelectListbox
      value={value}
      options={options}
      onChange={onChange}
      disabled={disabled}
      ariaLabel={ariaLabel}
      id={id}
      testId={testId}
      className={className}
    />
  ) : (
    <CnxSelectNative
      value={value}
      options={options}
      onChange={onChange}
      disabled={disabled}
      ariaLabel={ariaLabel}
      id={id}
      testId={testId}
      className={className}
    />
  );
}

/** The short arm. A real <select>, because that is what a short list needs, and
 *  because the product's own E2E arms drive these controls with selectOption(). */
function CnxSelectNative({
  value,
  options,
  onChange,
  disabled,
  ariaLabel,
  id,
  testId,
  className,
}: ArmProps) {
  return (
    <select
      id={id}
      className={["cnx-select", className].filter(Boolean).join(" ")}
      data-testid={testId}
      aria-label={ariaLabel}
      value={value}
      disabled={disabled}
      onChange={(event) => onChange(event.target.value)}
    >
      {options.map((option) => (
        <option key={option.value} value={option.value} disabled={option.disabled}>
          {option.label}
        </option>
      ))}
    </select>
  );
}

/** The long arm: a combobox over a windowed listbox, with a live filter. */
function CnxSelectListbox({
  value,
  options,
  onChange,
  disabled,
  ariaLabel,
  id,
  testId,
  className,
}: ArmProps) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [limit, setLimit] = useState(PAGE_ROWS);
  const [active, setActive] = useState(0);
  const rootRef = useRef<HTMLDivElement | null>(null);
  const searchRef = useRef<HTMLInputElement | null>(null);
  const sentinelRef = useRef<HTMLDivElement | null>(null);
  const listId = useId();
  /** Ids are numbered by the position in the *painted* slice: a filtered list is a
   *  different list, and an id taken from the unfiltered index would point the keyboard
   *  cursor at somebody else's row. */
  const optionId = (index: number) => `${listId}-o${index}`;

  const selectedIndex = Math.max(
    0,
    options.findIndex((option) => option.value === value),
  );
  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return options.filter((option) => matches(option, needle));
  }, [options, query]);
  const shown = filtered.slice(0, limit);
  const chosen = options[selectedIndex];

  // Opening seats the cursor on what is already chosen; typing must not fight it, which
  // is why the filtered length is deliberately not a dependency here.
  useEffect(() => {
    if (!open) {
      setQuery("");
      setLimit(PAGE_ROWS);
      return;
    }
    setActive(Math.min(selectedIndex, Math.max(filtered.length - 1, 0)));
    searchRef.current?.focus();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const onDocumentDown = (event: MouseEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onDocumentDown);
    return () => document.removeEventListener("mousedown", onDocumentDown);
  }, [open]);

  // The window opens as the traveller reaches the bottom of what is painted. Scrolling
  // never hands the browser the whole list, which is the point of this arm.
  useEffect(() => {
    if (!open) return;
    const sentinel = sentinelRef.current;
    if (!sentinel) return;
    const scroller = sentinel.parentElement;
    if (!scroller) return;
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) {
          setLimit((current) => Math.min(current + PAGE_ROWS, filtered.length));
        }
      },
      { root: scroller, rootMargin: "120px" },
    );
    observer.observe(sentinel);
    return () => observer.disconnect();
  }, [open, filtered.length]);

  const pick = (option: CnxSelectOption) => {
    if (option.disabled) return;
    onChange(option.value);
    setOpen(false);
  };

  const onKeyDown = (event: React.KeyboardEvent) => {
    if (event.key === "Escape") {
      setOpen(false);
      return;
    }
    if (!open && (event.key === "ArrowDown" || event.key === "Enter" || event.key === " ")) {
      if (disabled) return;
      event.preventDefault();
      setOpen(true);
      return;
    }
    if (!open) return;
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      setActive((current) => {
        const next = current + (event.key === "ArrowDown" ? 1 : -1);
        return Math.min(Math.max(next, 0), Math.min(shown.length, limit) - 1);
      });
      return;
    }
    if (event.key === "Home") {
      event.preventDefault();
      setActive(0);
      return;
    }
    if (event.key === "End") {
      event.preventDefault();
      setActive(Math.min(shown.length, limit) - 1);
      return;
    }
    if (event.key === "Enter") {
      event.preventDefault();
      const option = shown[active];
      if (option) pick(option);
    }
  };

  return (
    <div
      ref={rootRef}
      className={["cnx-select", "cnx-select--listbox", className].filter(Boolean).join(" ")}
      data-open={open ? "true" : "false"}
      data-disabled={disabled ? "true" : "false"}
      onKeyDown={onKeyDown}
    >
      <button
        type="button"
        id={id}
        className="cnx-select__trigger"
        data-testid={testId}
        aria-label={ariaLabel}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-controls={open ? `${listId}-panel` : undefined}
        disabled={disabled}
        onClick={() => setOpen((current) => !current)}
      >
        <span className="cnx-select__value">{chosen ? chosen.label : ""}</span>
        <span className="cnx-select__caret" aria-hidden="true">
          ▾
        </span>
      </button>

      {open ? (
        <div
          className="cnx-select__panel"
          id={`${listId}-panel`}
          data-testid={testId ? `${testId}-panel` : undefined}
          role="dialog"
          aria-label={ariaLabel}
        >
          <input
            ref={searchRef}
            className="cnx-select__search"
            data-testid={testId ? `${testId}-search` : undefined}
            type="search"
            inputMode="search"
            autoComplete="off"
            aria-label={ariaLabel}
            value={query}
            onChange={(event) => {
              setQuery(event.target.value);
              setLimit(PAGE_ROWS);
              setActive(0);
            }}
          />
          <div
            className="cnx-select__list"
            data-testid={testId ? `${testId}-list` : undefined}
            data-empty={filtered.length === 0 ? "true" : "false"}
            role="listbox"
            aria-activedescendant={shown[active] ? optionId(active) : undefined}
          >
            {shown.map((option, index) => (
                <button
                  key={option.value}
                  type="button"
                  role="option"
                  id={optionId(index)}
                  className="cnx-select__option"
                  data-testid={testId ? `${testId}-option` : undefined}
                  aria-selected={option.value === value}
                  data-active={index === active ? "true" : "false"}
                  disabled={option.disabled}
                  onMouseEnter={() => setActive(index)}
                  onClick={() => pick(option)}
                >
                  <span className="cnx-select__option-label">{option.label}</span>
                  {option.keywords ? (
                    <span className="cnx-select__option-keywords">{option.keywords}</span>
                  ) : null}
                </button>
            ))}
            {shown.length < filtered.length ? (
              <div ref={sentinelRef} className="cnx-select__sentinel" aria-hidden="true" />
            ) : null}
          </div>
          {/* Digits and a slash, no sentence: this arm must not put copy the dictionary
              has no key for onto a traveller's screen. role=status carries "nothing
              matched" to a screen reader as the count dropping to zero. */}
          <p
            className="cnx-select__count"
            data-testid={testId ? `${testId}-count` : undefined}
            role="status"
          >
            {filtered.length} / {options.length}
          </p>
        </div>
      ) : null}
    </div>
  );
}
