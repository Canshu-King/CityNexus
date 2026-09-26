/**
 * ORD-0361: which stop the traveller last picked on the map, kept per journey.
 *
 * The map used to be a picture: tapping a marker produced no observable consequence, so nothing
 * remembered a choice. This is the smallest thing that makes the pick survive a reload -- a
 * journey-scoped entry in the same `citynexus.v8.*` family the shell already uses for
 * `journey_id` and `continuation`. It is deliberately *not* a server field: no endpoint was ordered,
 * and inventing a write for a view preference would put an unowned claim on the journey.
 *
 * The value is only ever an activity id this journey's plan contains. A stored id that is no longer
 * in the plan is dropped on read rather than honoured -- keeping it alive is how a stale focus comes
 * back to haunt a trip that has moved on.
 */

const PREFIX = "citynexus.v8.map_focus.";

export function mapFocusKey(journeyId: string): string {
  return PREFIX + journeyId;
}

export function readMapFocus(journeyId: string | null | undefined, validIds: string[]): string | null {
  if (!journeyId) return null;
  try {
    const raw = localStorage.getItem(mapFocusKey(journeyId));
    if (!raw) return null;
    const parsed = JSON.parse(raw) as { activity_id?: unknown };
    const id = typeof parsed.activity_id === "string" ? parsed.activity_id : null;
    if (!id || validIds.length === 0) return null;
    if (!validIds.includes(id)) {
      // Stale by measurement, not by guess: the plan this journey has now does not contain it.
      localStorage.removeItem(mapFocusKey(journeyId));
      return null;
    }
    return id;
  } catch {
    // Blocked or private storage: the map still works, it just will not remember across a reload.
    return null;
  }
}

export function writeMapFocus(journeyId: string | null | undefined, activityId: string): void {
  if (!journeyId) return;
  try {
    localStorage.setItem(mapFocusKey(journeyId), JSON.stringify({ activity_id: activityId }));
  } catch {
    /* Nothing to do. */
  }
}

/**
 * Why a marker cannot be picked. Named, because the defect being fixed is silence: a traveller
 * pressed something and the screen said nothing back. `role` is the contract field the marker
 * carries (Q70 anchors it by name on screen), so the sentence quotes a value rather than guessing.
 */
export type UnpickableReason = "not-a-catalogued-stop";

export function unpickableReason(hasActivityId: boolean): UnpickableReason | null {
  return hasActivityId ? null : "not-a-catalogued-stop";
}

export function unpickableCopy(role: string, zh: boolean): string {
  return zh
    ? `这个点不在这一趟的地点目录里（它的角色是 ${role}），所以没有卡片可以跳过去。`
    : `This marker is not a catalogued stop on this trip (its role is ${role}), so there is no card to jump to.`;
}
