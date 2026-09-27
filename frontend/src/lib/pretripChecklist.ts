/**
 * ORD-0384 -- the pre-trip checklist, derived only from what the server already answers.
 *
 * Scope of the first version, deliberately: this file stores nothing and writes nothing. Every item is
 * a read over a payload the app already fetches, and each one carries the endpoint and field that make
 * it true right now, so a traveller (and the next gate) can ask "why is this on my list?" and get a
 * field name rather than a guess. Completion is not a checkbox: when the underlying truth changes the
 * item goes away by itself, which is the only reason there is no "mark done" control here.
 *
 * Copy lives in this module on purpose -- `LocaleContext.tsx` is being edited by two other lanes, and a
 * checklist that cannot state its own wording is not shippable.
 */

export type ChecklistBasis = {
  /** The endpoint whose response carries the field. `{journeyId}` is the placeholder the app fills. */
  endpoint: string;
  /** Dotted path inside that response. */
  field: string;
};

export type ChecklistItem = {
  key: string;
  title: { zh: string; en: string };
  /** Why this is listed, phrased as the fact the server stated -- not an instruction invented here. */
  why: { zh: string; en: string };
  basis: ChecklistBasis;
  /** An existing screen that can act on it. This order adds no screen of its own. */
  target: { route: string; label: { zh: string; en: string } };
};

export type PretripSources = {
  experience: unknown;
  wallet: unknown;
};

const EXPERIENCE = "/api/v1/journeys/{journeyId}/experience";
const WALLET = "/api/v1/journeys/{journeyId}/wallet";

type Bag = Record<string, any>;

const bag = (v: unknown): Bag | null => (v && typeof v === "object" ? (v as Bag) : null);
const isAbsent = (v: unknown) => v === null || v === undefined || v === "";

/**
 * The rules, in the order a traveller would meet them. Each returns an item only when the field it
 * names is actually in that state in the payload it was handed; an unread source yields no items,
 * because "we could not look" must never be rendered as "nothing is missing" or as an invented gap.
 */
export function derivePretripChecklist(sources: PretripSources): ChecklistItem[] {
  const exp = bag(sources.experience);
  const wallet = bag(sources.wallet);
  if (!exp) return [];

  const items: ChecklistItem[] = [];
  const trip = bag(exp.trip) ?? {};
  const flags = bag(exp.experience_flags) ?? {};
  const stayBudget = bag(trip.stay_budget);
  const reservations = Array.isArray(wallet?.reservations) ? wallet.reservations : null;
  const commitments = Array.isArray(wallet?.commitments) ? wallet.commitments : null;

  if (stayBudget && stayBudget.declared === null) {
    items.push({
      key: "stay_budget_undeclared",
      title: { zh: "住宿预算还没声明", en: "Stay budget not declared" },
      why: {
        zh: "服务端把住宿预算标为未声明（`declared` 为空），所以任何“超出预算”的判断都还没有依据。",
        en: "The server marks the stay budget as undeclared (`declared` is null), so no over-budget judgement has a basis yet.",
      },
      basis: { endpoint: EXPERIENCE, field: "trip.stay_budget.declared" },
      target: { route: "studio", label: { zh: "去设定预算", en: "Set the budget" } },
    });
  }

  const failures = Array.isArray(flags.feasibility_failures) ? flags.feasibility_failures : [];
  if (failures.length > 0) {
    items.push({
      key: "plan_feasibility_open",
      title: { zh: "方案有未处理的可行性失败", en: "The plan has open feasibility failures" },
      why: {
        /* The server's own strings, counted and quoted, never rewritten into a cause we did not measure. */
        zh: `服务端在这一代方案上列出了 ${failures.length} 条可行性失败，最新一条是「${String(failures[failures.length - 1])}」。`,
        en: `The server lists ${failures.length} feasibility failure(s) on this plan generation; the latest reads "${String(failures[failures.length - 1])}".`,
      },
      basis: { endpoint: EXPERIENCE, field: "experience_flags.feasibility_failures" },
      target: { route: "studio", label: { zh: "去看方案", en: "Review the plan" } },
    });
  }

  if (!isAbsent(exp.selected_option_id) && reservations?.length === 0 && commitments?.length === 0) {
    items.push({
      key: "stay_chosen_but_unconfirmed",
      title: { zh: "住宿已选定，但还没有确认的预订", en: "A stay is chosen but nothing is confirmed" },
      why: {
        zh: "这一趟已选定住宿，而服务端的预订与承诺两条列表都是空的，所以选定还没有变成一项确认。",
        en: "A stay option is selected for this journey, while the server's reservation and commitment lists are both empty, so the choice has not become a confirmation.",
      },
      basis: { endpoint: WALLET, field: "reservations / commitments" },
      target: { route: "bookings", label: { zh: "去处理预订", en: "Handle the booking" } },
    });
  }

  if (isAbsent(exp.selected_option_id)) {
    items.push({
      key: "stay_not_chosen",
      title: { zh: "还没有选定住宿", en: "No stay has been chosen" },
      why: {
        zh: "服务端说这一趟还没有选定项（`selected_option_id` 为空）。",
        en: "The server reports no selected option for this journey (`selected_option_id` is empty).",
      },
      basis: { endpoint: EXPERIENCE, field: "selected_option_id" },
      target: { route: "stay", label: { zh: "去选住宿", en: "Choose a stay" } },
    });
  }

  if (bag(exp.active_plan) === null) {
    items.push({
      key: "no_active_plan",
      title: { zh: "还没有可执行的方案", en: "There is no active plan yet" },
      why: {
        zh: "服务端这一趟的 `active_plan` 为空，行前安排还没有落成一版。",
        en: "The server's `active_plan` for this journey is null, so no plan version exists to travel against.",
      },
      basis: { endpoint: EXPERIENCE, field: "active_plan" },
      target: { route: "studio", label: { zh: "去生成方案", en: "Build the plan" } },
    });
  }

  const recovery = bag(exp.recovery);
  if (recovery?.requires_user_decision === true) {
    items.push({
      key: "recovery_needs_decision",
      title: { zh: "恢复方案等你决定", en: "A recovery is waiting on your decision" },
      why: {
        zh: "服务端把这一趟标为需要用户决定（`requires_user_decision` 为真），在你决定之前方案不会自己改。",
        en: "The server flags this journey as needing a user decision (`requires_user_decision`), and the plan will not change itself before you choose.",
      },
      basis: { endpoint: EXPERIENCE, field: "recovery.requires_user_decision" },
      target: { route: "live", label: { zh: "去看恢复选项", en: "See the recovery options" } },
    });
  }

  for (const [field, anchor] of [
    ["trip.arrival_anchor.at", "到达"],
    ["trip.departure_anchor.at", "离开"],
  ] as const) {
    const which = field.split(".")[1];
    if (isAbsent(bag(trip[which])?.at)) {
      items.push({
        key: `${which}_anchor_missing`,
        title: { zh: `${anchor}时间还没有确定`, en: `The ${which} time is not fixed` },
        why: {
          zh: `服务端的 \`${field}\` 是空的，所以按${anchor}排的这一段还没有依据。`,
          en: `The server's \`${field}\` is empty, so anything scheduled against this ${which} has no basis.`,
        },
        basis: { endpoint: EXPERIENCE, field },
        target: { route: "studio", label: { zh: "去补行程边界", en: "Set the trip bounds" } },
      });
    }
  }

  if (wallet && wallet.offline_ready === false) {
    items.push({
      key: "offline_pack_not_ready",
      title: { zh: "离线包还没就绪", en: "The offline pack is not ready" },
      why: {
        zh: "服务端的 `offline_ready` 为假，出了信号范围时这一屏可能拿不到内容。",
        en: "The server's `offline_ready` is false, so this screen may have nothing to show outside coverage.",
      },
      basis: { endpoint: WALLET, field: "offline_ready" },
      target: { route: "me", label: { zh: "去准备离线内容", en: "Prepare offline content" } },
    });
  }

  return items;
}

/**
 * What the panel says when the derivation returns nothing. It names the sources it actually read, so
 * an empty list is never mistaken for "everything was checked and passed".
 */
export function emptyStateCopy(zh: boolean, read: { experience: boolean; wallet: boolean }) {
  if (!read.experience) {
    return zh
      ? "还没有读到服务端的这一趟数据，所以这里什么都不说。"
      : "The journey has not been read from the server yet, so this list says nothing.";
  }
  return zh
    ? "服务端此刻没有列出待办项。这里只列服务端说出来的事，没有跑过的检查不会被打勾。"
    : "The server lists nothing outstanding right now. This panel only shows what the server states; a check that was not run is never ticked.";
}
