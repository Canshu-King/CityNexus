import { useCallback, useEffect, useState } from "react";
import { useLocale } from "../../i18n/LocaleContext";
import { CnxMeasuredFacts } from "../../components/CnxMeasuredFacts";
import { classifyReadFailure, copyFor, type Attribution } from "../../lib/failureAttribution";
import type { RawFacts } from "../../lib/rawFacts";
import { formatV8Date } from "../../lib/v8Formatting";
import {
  createShareGrant,
  readActivity,
  readJourneys,
  readMembers,
  readRoleRules,
  readShareGrants,
  readSharingDoors,
  RejectionWithFacts,
  revokeShareGrant,
  SHARING_DOOR_SUFFIXES,
  withdrawMember,
  type ActivityEvent,
  type DoorProbe,
  type JourneyMemberRow,
  type JourneySummary,
  type RoleRule,
  type ShareGrant,
} from "./accessDoors";
import {
  accessCopyFor,
  fillAccess,
  type AccessCopyKey,
} from "./accessCopy";
import {
  actionNamesAMember,
  isScopeKey,
  memberActionKey,
  roleLabelKey,
  ROLE_COLLABORATOR,
  ROLE_OWNER,
  VISIBILITY_LINK_READ,
  VISIBILITY_PRIVATE,
  VISIBILITY_PUBLIC,
  permissionConfirmationKey,
  refusalSentenceKey,
  removalConfirmationKey,
  ROLE_LADDER,
  VISIBILITY_LADDER,
  visibilitySwitchKey,
  invitationQuotaKey,
} from "./accessVocabulary";
import "./access.css";

/**
 * ORD-0436 -- 成员与权限, the screen, on the tree that exists tonight.
 *
 * Mounted through the panel registry (`app/v8PanelRegistry.tsx`, surface "route", key "access"), so
 * this folder and three lines elsewhere are the whole change and the shell stays shut -- the same
 * route ORD-0392/ORD-0402 slice 2 took for `/v8/trash`.
 *
 * Two halves, and they are separated on purpose because the server is not finished:
 *  - read from this server right now: the trip list (`GET /api/v1/journeys`) and what happened to
 *    the chosen trip (`GET /api/v1/journeys/{id}/agent-feed`). Both exist on this tree.
 *  - the sharing state itself -- roles, visibility, invitations -- has no door on this tree yet.
 *    ORD-0434 builds it. This screen therefore shows that half as the *decision table it will use*,
 *    says out loud that the door did not answer, and offers no control that would do nothing
 *    (ORD-0385: copy may not exceed the mechanism). The rows are not buttons and not switches.
 *
 * The one thing that must not happen here is an empty roster read as "nobody shares this trip". That
 * is a different fact from "this server did not answer", and the two get different sentences.
 */

type TripsState =
  | { phase: "loading" }
  | { phase: "ready"; rows: JourneySummary[] }
  | { phase: "failed"; facts: RawFacts | null; attribution: Attribution };

type ActivityState =
  | { phase: "idle" }
  | { phase: "loading" }
  | { phase: "ready"; rows: ActivityEvent[] }
  | { phase: "failed"; facts: RawFacts | null; attribution: Attribution };

type AccessRead =
  | { phase: "loading" }
  | { phase: "absent" }
  | { phase: "partial"; probes: DoorProbe[]; expiries: string[]; rosterSize: number | null }
  | { phase: "present"; probes: DoorProbe[]; expiries: string[]; rosterSize: number | null }
  | { phase: "failed"; facts: RawFacts | null; attribution: Attribution };

const joinPaths = (paths: readonly string[], zh: boolean) => paths.join(zh ? "、" : ", ");

/** The two moves this screen has a gain-or-loss sentence for. Each row is an input to
 *  `visibilitySwitchKey`, so the line below is that function's answer, not a second sentence. */
const SWITCH_CASES: readonly { from: string | null; to: string | null }[] = [
  { from: VISIBILITY_PRIVATE, to: VISIBILITY_PUBLIC },
  { from: VISIBILITY_PUBLIC, to: VISIBILITY_PRIVATE },
];

/** The confirmation table's cases. Each row is an input to `permissionConfirmationKey`, so what a
 *  traveller reads here is that function's answer, not a second copy of the sentence. */
const CONFIRMATION_CASES: readonly {
  whenKey: AccessCopyKey;
  change: Parameters<typeof permissionConfirmationKey>[0];
}[] = [
  {
    whenKey: "access.whenOtherGainsOnly",
    change: { actorRole: ROLE_OWNER, newRole: ROLE_COLLABORATOR, targetsAnotherMember: true },
  },
  {
    whenKey: "access.whenActorLosesStanding",
    change: { actorRole: ROLE_OWNER, newRole: ROLE_OWNER, targetsAnotherMember: true },
  },
  {
    whenKey: "access.whenRoleUnread",
    change: { actorRole: null, newRole: "ADMIN", targetsAnotherMember: true },
  },
];

export function AccessPanel() {
  const { locale, t } = useLocale();
  const zh = locale.startsWith("zh");
  const say = (key: AccessCopyKey, params: Record<string, string | number> = {}) =>
    fillAccess(accessCopyFor(locale, key), params);

  const [trips, setTrips] = useState<TripsState>({ phase: "loading" });
  const [chosen, setChosen] = useState<string | null>(null);
  const [activity, setActivity] = useState<ActivityState>({ phase: "idle" });
  const [access, setAccess] = useState<AccessRead>({ phase: "loading" });
  const [members, setMembers] = useState<JourneyMemberRow[]>([]);
  const [grants, setGrants] = useState<ShareGrant[]>([]);
  const [roleRules, setRoleRules] = useState<RoleRule[] | null>(null);
  const [rosterFailed, setRosterFailed] = useState<Attribution | null>(null);
  const [pending, setPending] = useState<{ kind: "grant" | "member"; id: string } | null>(null);
  const [writeState, setWriteState] = useState<{ busy: boolean; refused: string | null }>({
    busy: false,
    refused: null,
  });
  const [pickVisibility, setPickVisibility] = useState<string>(VISIBILITY_LINK_READ);
  const [pickExpiry, setPickExpiry] = useState<string>("");

  const loadTrips = useCallback(async () => {
    setTrips({ phase: "loading" });
    try {
      setTrips({ phase: "ready", rows: await readJourneys() });
    } catch (cause) {
      setTrips({
        phase: "failed",
        facts: cause instanceof RejectionWithFacts ? cause.facts : null,
        attribution: classifyReadFailure(cause),
      });
    }
  }, []);

  useEffect(() => {
    void loadTrips();
  }, [loadTrips]);

  const loadRoster = useCallback(async (journeyId: string) => {
    setRosterFailed(null);
    try {
      const [memberRows, grantRows, rules] = await Promise.all([
        readMembers(journeyId),
        readShareGrants(journeyId),
        readRoleRules(journeyId),
      ]);
      setMembers(memberRows);
      setGrants(grantRows);
      setRoleRules(rules);
    } catch (cause) {
      setRosterFailed(classifyReadFailure(cause));
    }
  }, []);

  /** Every write path ends by re-reading the doors. The screen never edits its own copy of a row to
   *  look like the write succeeded: what appears after a tap is what the server answered next. */
  const afterWrite = useCallback(
    async (journeyId: string) => {
      setPending(null);
      await Promise.all([loadRoster(journeyId), readActivity(journeyId).then((events) => setActivity({ phase: "ready", rows: events })).catch(() => undefined)]);
    },
    [loadRoster],
  );

  /** The refusal is named by `error.reason_code` in the body, not by the status code and not by a
   *  guess from `details`. The status alone cannot tell "already withdrawn" from "no such row". */
  const refusalKey = (cause: unknown): string => {
    if (!(cause instanceof RejectionWithFacts)) return "other";
    const envelope = cause.envelope as { error?: { reason_code?: unknown } } | undefined;
    const code = envelope?.error?.reason_code;
    return typeof code === "string" && code.length > 0 ? code : `http_${cause.http_status}`;
  };

  const issueInvitation = useCallback(async () => {
    if (chosen === null) return;
    const signer = (trips.phase === "ready" ? trips.rows : []).find((row) => row.id === chosen)?.traveler_id ?? null;
    if (signer === null || signer === undefined) {
      // The list door did not name an owner for this trip, so there is no signature this device is
      // willing to invent for it.
      setWriteState({ busy: false, refused: "nosigner" });
      return;
    }
    setWriteState({ busy: true, refused: null });
    try {
      await createShareGrant(chosen, {
        visibility: pickVisibility,
        created_by: signer,
        expires_at: pickExpiry === "" ? null : new Date(pickExpiry).toISOString(),
      });
      setWriteState({ busy: false, refused: null });
      await afterWrite(chosen);
    } catch (cause) {
      setWriteState({ busy: false, refused: refusalKey(cause) });
    }
  }, [afterWrite, chosen, pickExpiry, pickVisibility, trips]);

  const confirmWithdrawal = useCallback(async () => {
    if (chosen === null || pending === null) return;
    setWriteState({ busy: true, refused: null });
    try {
      if (pending.kind === "grant") await revokeShareGrant(chosen, pending.id);
      else await withdrawMember(chosen, pending.id);
      setWriteState({ busy: false, refused: null });
      await afterWrite(chosen);
    } catch (cause) {
      setWriteState({ busy: false, refused: refusalKey(cause) });
    }
  }, [afterWrite, chosen, pending]);

  const openTrip = useCallback(async (journeyId: string) => {
    setChosen(journeyId);
    setActivity({ phase: "loading" });
    setAccess({ phase: "loading" });
    try {
      setActivity({ phase: "ready", rows: await readActivity(journeyId) });
    } catch (cause) {
      setActivity({
        phase: "failed",
        facts: cause instanceof RejectionWithFacts ? cause.facts : null,
        attribution: classifyReadFailure(cause),
      });
    }
    try {
      const read = await readSharingDoors(journeyId);
      const answered = read.probes.filter((probe) => probe.answered).length;
      const phase = answered === 0 ? "absent" : answered === read.probes.length ? "present" : "partial";
      setAccess({ ...read, phase });
    } catch (cause) {
      setAccess({
        phase: "failed",
        facts: cause instanceof RejectionWithFacts ? cause.facts : null,
        attribution: classifyReadFailure(cause),
      });
    }
    await loadRoster(journeyId);
  }, [loadRoster]);

  const rows = trips.phase === "ready" ? trips.rows : [];
  const chosenTitle =
    trips.phase === "ready" ? rows.find((row) => row.id === chosen)?.title ?? null : null;
  const activities = activity.phase === "ready" ? activity.rows : [];
  const sharing = access.phase === "present" || access.phase === "partial" ? access : null;
  const expiry = sharing && sharing.expiries.length > 0 ? sharing.expiries[0] : null;
  // No door in this product carries a member limit, so `cap` stays null and the quota line says so
  // instead of dividing the roster by a number nobody sent.
  const quotaKey = invitationQuotaKey({ used: sharing?.rosterSize ?? null, cap: null });

  const roleLabel = (role: string): string => {
    const key = roleLabelKey(role);
    return key ? say(key) : say("access.roleUnread", { role });
  };

  /** The ACL row carries a dictionary key, not a sentence (`member.scope.*`, seeded at
   *  `backend/app/db/session.py`). Looking it up here is the whole point: the words live in the one
   *  dictionary the server is allowed to name, and a key it invents is reported as unreadable
   *  rather than answered with a string this file happens to hold. */
  const scopeSentence = (key: string): string => {
    if (!isScopeKey(key)) return say("access.scopeKeyUnread", { key });
    const words = t(key);
    return words === key ? say("access.scopeKeyUnread", { key }) : words;
  };

  /** The scope sentence for a member's role, taken from the ACL rows the same trip just answered.
   *  No row, no sentence -- the screen does not fall back to a role name it read off a member row. */
  const scopeForRole = (role: string): string | null => {
    const rule = (roleRules ?? []).find((row) => row.role === role);
    return rule ? scopeSentence(rule.scope_message_key) : null;
  };

  const grantLabel = (visibility: string): string => {
    const entry = VISIBILITY_LADDER.find((row) => row.level === visibility);
    return entry ? say(entry.labelKey) : visibility;
  };

  /** `member_state` is the server's word for where this row stands. Each one it can send gets its
   *  own sentence; anything else is reported as unreadable rather than dressed up as "active". */
  const memberStateSentence = (member: JourneyMemberRow): string => {
    if (member.removed_at !== null) {
      return say("access.memberStateRemoved", { removed: formatV8Date(member.removed_at, locale) });
    }
    if (member.member_state === "MEMBER_IN_FORCE") return say("access.memberStateActive");
    if (member.member_state === "MEMBER_EXPIRED") return say("access.memberStateExpired");
    if (member.member_state === "MEMBER_WITHDRAWN") {
      return say("access.memberStateRemoved", { removed: formatV8Date(member.removed_at ?? "", locale) });
    }
    return say("access.memberStateUnknown", { state: member.member_state });
  };

  return (
    <section
      className="cn-access"
      data-testid="access-panel"
      {...(chosen ? { "data-journey": chosen } : {})}
      aria-label={say("access.title")}
    >
      <header className="cn-access-head">
        <span className="v8-kicker">{say("access.title")}</span>
        <p className="v8-muted">{say("access.sub")}</p>
      </header>

      {/* ---------------------------------------------------------- read from this server */}
      <div className="cn-access-read" data-testid="access-server-read">
        {trips.phase === "loading" && <p data-testid="access-trips-loading">{say("access.pickLoading")}</p>}
        {trips.phase === "failed" && (
          <div role="alert" data-testid="access-trips-failed">
            <p>{copyFor(trips.attribution, zh).body}</p>
            {trips.facts ? (
              <details className="cn-access-details">
                <summary>{t("agent.advancedDetail")}</summary>
                <CnxMeasuredFacts facts={trips.facts} zh={zh} testId="access-trips" envelope={null} />
              </details>
            ) : null}
          </div>
        )}
        {trips.phase === "ready" && rows.length === 0 && (
          <p data-testid="access-trips-empty">{say("access.pickEmpty")}</p>
        )}
        {trips.phase === "ready" && rows.length > 0 && (
          <label className="cn-access-picker">
            <span className="cn-access-picker-label">{say("access.pickLabel")}</span>
            <select
              data-testid="access-journey-picker"
              value={chosen ?? ""}
              onChange={(event) => {
                if (event.target.value) void openTrip(event.target.value);
              }}
            >
              <option value="">{say("access.pickNone")}</option>
              {rows.map((row) => (
                <option key={row.id} value={row.id}>
                  {row.title || row.id}
                </option>
              ))}
            </select>
          </label>
        )}
        {chosenTitle ? <p data-testid="access-chosen">{say("access.selected", { title: chosenTitle })}</p> : null}
      </div>

      {activity.phase === "loading" && <p data-testid="access-activity-loading">{say("access.activityLoading")}</p>}
      {activity.phase === "failed" && (
        <div role="alert" data-testid="access-activity-failed">
          <p>{copyFor(activity.attribution, zh).body}</p>
          {activity.facts ? (
            <details className="cn-access-details">
              <summary>{t("agent.advancedDetail")}</summary>
              <CnxMeasuredFacts
                facts={activity.facts}
                zh={zh}
                testId="access-activity"
                envelope={null}
              />
            </details>
          ) : null}
        </div>
      )}
      {activity.phase === "ready" && (
        <section className="cn-access-block" aria-label={say("access.activityHeading")}>
          <h3 className="cn-access-h">{say("access.activityHeading")}</h3>
          <p className="cn-access-muted" data-testid="access-activity-caveat">
            {say("access.activityNoSharingWriter")}
          </p>
          {activities.length === 0 ? (
            <p data-testid="access-activity-empty">{say("access.activityEmpty")}</p>
          ) : (
            <ul className="cn-access-activity" data-testid="access-activity-list">
              {activities.map((event) => {
                const key = memberActionKey(event.event_type);
                // `{name}` is only ever filled by a person this door actually named. Today the feed
                // carries `actor_id` (who tapped), not whose row changed, and the two are different
                // people -- guessing the second from the first would put a name on a sentence the
                // server did not say. So an unnamed member reads as unnamed, not as a template.
                const named = event.member_name;
                const params = actionNamesAMember(event.event_type)
                  ? { name: named ? named : say("access.memberUnnamed") }
                  : {};
                return (
                  <li key={event.id} className="cn-access-activity-row" data-event-type={event.event_type}>
                    <span className="cn-access-when">{formatV8Date(event.timestamp, locale)}</span>
                    <span className="cn-access-what">
                      {key ? say(key, params) : say("access.actionUnknown", { token: event.event_type })}
                    </span>
                  </li>
                );
              })}
            </ul>
          )}
        </section>
      )}

      {/* --------------------------------------------- the door ORD-0434 has not built yet */}
      <p className="cn-access-absent" data-testid="access-door-state">
        {access.phase === "loading"
          ? say("access.doorLoading", { paths: joinPaths(SHARING_DOOR_SUFFIXES, zh) })
          : access.phase === "absent"
            ? say("access.doorAbsent", { paths: joinPaths(SHARING_DOOR_SUFFIXES, zh) })
            : access.phase === "failed"
              ? copyFor(access.attribution, zh).body
              : access.phase === "partial"
                ? say("access.doorPartial", {
                    paths: joinPaths(access.probes.filter((p) => !p.answered).map((p) => p.path), zh),
                  })
                : say("access.doorPresent")}
      </p>

      <section className="cn-access-block" aria-label={say("access.roleLadderHeading")}>
        <h3 className="cn-access-h">{say("access.roleLadderHeading")}</h3>
        {roleRules === null ? (
          <p data-testid="access-role-ladder-empty">{say("access.scopeDoorSilent")}</p>
        ) : (
          <ul className="cn-access-ladder" data-testid="access-role-ladder">
            {roleRules.map((rule) => (
              <li className="cn-access-ladder-row" data-role={rule.role} key={rule.role}>
                <span className="cn-access-role">{roleLabel(rule.role)}</span>
                <span className="cn-access-scope" data-testid="access-role-scope">
                  {scopeSentence(rule.scope_message_key)}{" "}
                  {say("access.roleCapabilityCount", { count: rule.capabilities.length })}
                </span>
                <details className="cn-access-details">
                  <summary>{say("access.capabilityTokens")}</summary>
                  <p>{rule.capabilities.join(", ")}</p>
                </details>
              </li>
            ))}
          </ul>
        )}
        <details className="cn-access-details" data-testid="access-role-details">
          <summary>{say("access.roleDetails")}</summary>
          <p>{say("access.roleDetailsBody")}</p>
        </details>
      </section>

      <section className="cn-access-block" aria-label={say("access.visibilityHeading")}>
        <h3 className="cn-access-h">{say("access.visibilityHeading")}</h3>
        <ul className="cn-access-ladder" data-testid="access-visibility-ladder">
          {VISIBILITY_LADDER.map((entry) => (
            <li key={entry.level} className="cn-access-ladder-row" data-level={entry.level}>
              <span className="cn-access-role">{say(entry.labelKey)}</span>
              <span className="cn-access-scope">{say(entry.consequenceKey)}</span>
            </li>
          ))}
        </ul>
      </section>

      <section className="cn-access-block" aria-label={say("access.switchHeading")}>
        <h3 className="cn-access-h">{say("access.switchHeading")}</h3>
        <ul className="cn-access-sentences" data-testid="access-switch-lines">
          {SWITCH_CASES.map((entry) => (
            <li key={`${entry.from}->${entry.to}`} data-switch={`${entry.from}->${entry.to}`}>
              {say(visibilitySwitchKey(entry))}
            </li>
          ))}
        </ul>
      </section>

      <section className="cn-access-block" aria-label={say("access.confirmHeading")}>
        <h3 className="cn-access-h">{say("access.confirmHeading")}</h3>
        <ul className="cn-access-sentences" data-testid="access-confirm-table">
          {CONFIRMATION_CASES.map((entry) => (
            <li key={entry.whenKey} className="cn-access-confirm-row" data-case={entry.whenKey}>
              <span className="cn-access-when">{say(entry.whenKey)}</span>
              <span className="cn-access-scope">
                {say(permissionConfirmationKey(entry.change))}
              </span>
            </li>
          ))}
          <li className="cn-access-confirm-row" data-case="removal">
            <span className="cn-access-when">{say("access.whenMemberRemoved")}</span>
            <span className="cn-access-scope">{say(removalConfirmationKey())}</span>
          </li>
        </ul>
      </section>

      <section className="cn-access-block" aria-label={say("access.inviteHeading")}>
        <h3 className="cn-access-h">{say("access.inviteHeading")}</h3>
        <p className="cn-access-scope" data-testid="access-invite-ttl">
          {expiry
            ? say("access.inviteExpires", { expires: formatV8Date(expiry, locale) })
            : say("access.inviteTtlMissing")}
        </p>
        <p className="cn-access-scope" data-testid="access-invite-quota">
          {quotaKey
            ? say(quotaKey)
            : sharing && sharing.rosterSize !== null
              ? say("access.inviteQuotaNoCap", { used: sharing.rosterSize })
              : say("access.inviteQuotaMissing")}
        </p>
      </section>

      <section className="cn-access-block" aria-label={say("access.inviteFormHeading")}>
        <h3 className="cn-access-h">{say("access.inviteFormHeading")}</h3>
        <label className="cn-access-field">
          <span className="cn-access-picker-label">{say("access.inviteFormPick")}</span>
          <select
            data-testid="access-invite-visibility"
            value={pickVisibility}
            onChange={(event) => setPickVisibility(event.target.value)}
          >
            {VISIBILITY_LADDER.map((entry) => (
              <option key={entry.level} value={entry.level}>
                {say(entry.labelKey)}
              </option>
            ))}
          </select>
        </label>
        <label className="cn-access-field">
          <span className="cn-access-picker-label">{say("access.inviteFormExpiry")}</span>
          <input
            data-testid="access-invite-expiry"
            type="datetime-local"
            value={pickExpiry}
            onChange={(event) => setPickExpiry(event.target.value)}
          />
        </label>
        <p className="cn-access-muted" data-testid="access-invite-signer">
          {say("access.inviteFormSigner")}
        </p>
        <button
          data-testid="access-invite-submit"
          type="button"
          disabled={chosen === null || writeState.busy}
          onClick={() => void issueInvitation()}
        >
          {writeState.busy ? say("access.inviteFormBusy") : say("access.inviteFormSubmit")}
        </button>
        {writeState.refused !== null && writeState.refused !== "nosigner" ? (
          <p className="cn-access-refusal" data-testid="access-write-refused">
            {(() => {
              const key = refusalSentenceKey(writeState.refused);
              return key ? say(key) : say("access.writeRefusedUnknown", { code: writeState.refused });
            })()}
          </p>
        ) : null}
      </section>

      {chosen !== null ? (
        <section className="cn-access-block" aria-label={say("access.grantHeading")}>
          <h3 className="cn-access-h">{say("access.grantHeading")}</h3>
          {grants.length === 0 ? (
            <p data-testid="access-grant-empty">{say("access.grantEmpty")}</p>
          ) : (
            <ul className="cn-access-rows" data-testid="access-grant-list">
              {grants.map((grant) => (
                <li
                  className="cn-access-row"
                  data-revoked={grant.revoked_at !== null}
                  data-testid="access-grant-row"
                  key={grant.id}
                >
                  <span className="cn-access-row-what">
                    {grant.revoked_at !== null
                      ? `${grantLabel(grant.visibility)} · ${say("access.grantRevoked", {
                          revoked: formatV8Date(grant.revoked_at, locale),
                        })}`
                      : grant.expires_at === null
                        ? `${grantLabel(grant.visibility)} · ${say("access.grantNoExpiry")}`
                        : `${grantLabel(grant.visibility)} · ${say("access.grantActive", {
                            expires: formatV8Date(grant.expires_at, locale),
                          })}`}
                  </span>
                  {grant.revoked_at === null ? (
                    <button
                      className="cn-access-row-action"
                      data-testid="access-grant-revoke"
                      type="button"
                      onClick={() => setPending({ kind: "grant", id: grant.id })}
                    >
                      {pending?.kind === "grant" && pending.id === grant.id
                        ? say("access.revokeConfirmButton")
                        : say("access.revokeButton")}
                    </button>
                  ) : null}
                  <details className="cn-access-details">
                    <summary>{say("access.grantTokenSummary")}</summary>
                    <p>{fillAccess(say("access.grantToken"), { token: grant.token })}</p>
                  </details>
                </li>
              ))}
            </ul>
          )}
        </section>
      ) : null}

      {chosen !== null ? (
        <section className="cn-access-block" aria-label={say("access.rosterHeading")}>
          <h3 className="cn-access-h">{say("access.rosterHeading")}</h3>
          {rosterFailed !== null ? (
            <p data-testid="access-roster-failed">{copyFor(rosterFailed, zh).body}</p>
          ) : members.length === 0 ? (
            <p data-testid="access-roster-empty">{say("access.rosterEmpty")}</p>
          ) : (
            <ul className="cn-access-rows" data-testid="access-member-list">
              {members.map((member) => (
                <li className="cn-access-row" data-state={member.member_state} data-testid="access-member-row" key={member.id}>
                  <span className="cn-access-row-what">
                    {fillAccess(say("access.memberRow"), {
                      role: roleLabel(member.role),
                      id: member.traveler_id,
                    })}{" "}
                    · {memberStateSentence(member)}
                    {scopeForRole(member.role) === null ? null : (
                      <>
                        <br />
                        {say("access.memberScopeLine")}
                        {scopeForRole(member.role)}
                      </>
                    )}
                  </span>
                  {/* Two controls whose doors are not on the line yet. They are short-labelled and
                      disabled, and the reason is a sentence beside them -- a button that carries its
                      own paragraph is both unreadable and, at 390 px, what pushed this panel into a
                      horizontal overflow. */}
                  <button
                    className="cn-access-row-action"
                    data-disabled-reason="role-change-door"
                    data-testid="access-member-role-change"
                    disabled
                    type="button"
                  >
                    {say("access.roleChangeButton")}
                  </button>
                  <button
                    className="cn-access-row-action"
                    data-disabled-reason="self-exit-door"
                    data-testid="access-member-self-exit"
                    disabled
                    type="button"
                  >
                    {say("access.selfExitButton")}
                  </button>
                  <p className="cn-access-muted" data-testid="access-disabled-reasons">
                    {say("access.roleChangeDisabled")} {say("access.selfExitDisabled")}
                  </p>
                  {member.removed_at === null ? (
                    <button
                      className="cn-access-row-action"
                      data-testid="access-member-withdraw"
                      type="button"
                      onClick={() => setPending({ kind: "member", id: member.id })}
                    >
                      {pending?.kind === "member" && pending.id === member.id
                        ? say("access.revokeConfirmButton")
                        : say("access.revokeButton")}
                    </button>
                  ) : null}
                </li>
              ))}
            </ul>
          )}
        </section>
      ) : null}

      {pending !== null ? (
        <p className="cn-access-refusal" data-testid="access-confirm-pending">
          {pending.kind === "grant" ? say("access.confirmRevokeGrant") : say("access.confirmRevokeMember")}
          <button data-testid="access-confirm-yes" type="button" onClick={() => void confirmWithdrawal()}>
            {say("access.revokeConfirmButton")}
          </button>
          <button data-testid="access-confirm-no" type="button" onClick={() => setPending(null)}>
            {say("access.revokeButton")}
          </button>
        </p>
      ) : null}
    </section>
  );
}
