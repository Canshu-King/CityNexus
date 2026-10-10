// ORD-0572: this domain's slice of ../LocaleContext.tsx, moved verbatim -- no value was reworded.

export const v8panelregistry = {
  en: {

  /* ORD-0555: words that belong to the panel table. A `render` in `app/v8PanelRegistry.tsx` is a
     plain function rather than a component, so a mount site that needs a label reads it through a
     small component that takes the dictionary itself -- the literal pair never lives in the table. */
  "v8panelregistry.advancedDeveloper": "Advanced / developer",
  },
  zh: {

  /* ORD-0555：面板登记表自己的文案。`app/v8PanelRegistry.tsx` 里的 `render` 是普通函数而非组件，
     所以挂载位要一个标签时，由一个自己取词的小组件去读字典，而不是把中英二选一的写死串留在表里。 */
  "v8panelregistry.advancedDeveloper": "高级 / 开发者",
  },
};
