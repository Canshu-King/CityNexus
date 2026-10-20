/**
 * Is this element actually painted, the way a person would see it?
 *
 * Why this exists: the screen sweep reported `中止这趟行程@200,388 96x44 被 h1…` and that reading
 * reached the arbiter as a defect to fix. Measured on the same build, the trip page's abort row is
 * a closed `<details>`: its submit button still has a 96x44 *layout* box, but nothing is painted at
 * that place -- the screenshot shows the card one line high and the heading where the box says a
 * button sits. A ruler that measures layout boxes and calls them "a button a person cannot press"
 * manufactures defects, and this one did.
 *
 * `getBoundingClientRect()` cannot answer this, and neither can `visibility`/`opacity` on the
 * element itself: Chrome hides closed `<details>` content by not painting the subtree, while the
 * children keep their boxes. So the rule is written where it is true -- the ancestor chain -- and
 * shared, because two arms have to agree on what "on screen" means.
 *
 * Shipped as source text: `page.evaluate` runs in the browser, where this module's exports do not
 * exist, so both arms inject the same function body rather than each keeping its own copy.
 */

export const PAINTED_PROBE_SOURCE = `(el) => {
  if (!(el instanceof HTMLElement)) return false;
  /* 只判那一件真的事：折叠的 <details> 只画它自己的 <summary>，里面的东西有布局盒、没有像素。
     不去重演一遍 CSS 的可见性——祖先链上的 opacity/visibility 一加进来，这把尺就会把画得清清楚楚的
     那颗 summary 判成"没画"（第一版就是这么错的），而一把会漏报真控件的尺比会误报的尺更坏。 */
  if (el.closest("details:not([open])") && !el.closest("summary")) return false;
  const style = getComputedStyle(el);
  if (style.display === "none" || style.visibility === "hidden") return false;
  const box = el.getBoundingClientRect();
  return box.width > 6 && box.height > 6;
}`;

/** Evaluate the probe against one element and return the element's own verdict. */
export async function isPainted(page: import("@playwright/test").Page, selector: string): Promise<boolean> {
  return page.evaluate(
    `(${PAINTED_PROBE_SOURCE})(document.querySelector(${JSON.stringify(selector)}))`,
  ) as Promise<boolean>;
}
