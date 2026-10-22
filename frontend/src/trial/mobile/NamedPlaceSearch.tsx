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
    <section className="named-place-search" aria-label="按关键词查找公开地点">
      <h3 className="named-place-search__summary">直接搜索想去的地方</h3>
      <p className="named-place-search__help">不限于下方四种快捷分类。可以尝试古城、土楼、夜市、当地小吃或具体地点名称；公开数据不一定完整。</p>
      <form className="named-place-search__form" onSubmit={submit}>
        <label className="named-place-search__label">
          地点名称或关键词
          <input
            className="named-place-search__input"
            type="search"
            value={value}
            onChange={(event) => onChange(event.target.value)}
            placeholder="例如：客家土楼、古城、牛肉馆"
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
          搜索真实地点 →
        </button>
      </form>
    </section>
  );
}
