import { type FormEvent } from "react";
import "./NamedPlaceSearch.css";

type NamedPlaceSearchProps = {
  value: string;
  onChange: (value: string) => void;
  onSearch: () => void;
  disabled: boolean;
  recipient: string;
};

export function NamedPlaceSearch({
  value,
  onChange,
  onSearch,
  disabled,
  recipient,
}: NamedPlaceSearchProps) {
  const trimmedLength = value.trim().length;
  const canSearch = !disabled && trimmedLength >= 2 && trimmedLength <= 120;

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (canSearch) onSearch();
  };

  return (
    <details className="named-place-search">
      <summary className="named-place-search__summary">已经有想去的地方？</summary>
      <form className="named-place-search__form" onSubmit={submit}>
        <label className="named-place-search__label">
          地点名称
          <input
            className="named-place-search__input"
            type="search"
            value={value}
            onChange={(event) => onChange(event.target.value)}
            placeholder="例如：想去的博物馆或公园"
            maxLength={120}
            disabled={disabled}
          />
        </label>
        <p className="named-place-search__disclosure">
          把地点名和所选公开区域发送至 {recipient}
        </p>
        <button
          className="named-place-search__submit"
          type="submit"
          disabled={!canSearch}
        >
          查找这个地点
        </button>
      </form>
    </details>
  );
}
