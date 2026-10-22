/**
 * ORD-0436 -- the sentences the 成员与权限 screen says, in one file, both languages.
 *
 * Deliberately NOT in `i18n/LocaleContext.tsx`: that dictionary is the shared serialisation point
 * other lanes edit the same night -- the same reason `features/trash/journeyTrashCopy.ts` and
 * `features/studio/planVersionHistoryCopy.ts` give. Only `nav.access` went into the shared
 * dictionary, because the nav strip builds its labels as `t("nav." + key)` and has no fallback hook.
 *
 * Shape source: `D:/moodle/_apk_analysis_pi_travel/RELATION/relation_and_copy_findings.md` 1.4. What
 * is taken is the inventory -- which state gets a sentence, and which person that sentence names.
 * Every Chinese line here was rewritten for this product: it has trips, not 收藏夹.
 *
 * Three rules, all of them pinned elsewhere already:
 *  - a trip coming out of the bin is 找回. 恢复 and `recover*` are autonomous recovery here, and
 *    还原 is the plan-version screen's word (`planVersionHistoryCopy.ts:10`, restated by the 找回
 *    door in `backend/app/main.py`), so sharing does not take 还原 either: taking a person's access
 *    away is 撤销.
 *  - a sentence names whose situation changed. "对方将获得对应权限" and "你的权限也会随之变化"
 *    are two sentences because two people lose different things; which one applies is decided in
 *    `accessVocabulary.ts`, never by a string picked at the point of use.
 *  - nothing here offers what the server cannot do. There is no member table, no visibility column
 *    and no invitation door on this tree (ORD-0434 builds them), so the ladders say what each level
 *    will mean, `access.doorAbsent` says so on the same screen, and no ladder row is a control
 *    (ORD-0385: copy may not exceed the mechanism).
 */
export const accessCopy = {
  en: {
    "access.title": "Members and access",
    "access.sub": "Manage trip roles, visibility and invitations.",
    "access.pickLabel": "Choose a trip",
    "access.pickNone": "Pick a trip to look at",
    "access.pickLoading": "Reading your trip list…",
    "access.pickEmpty": "No trip is available to manage.",
    "access.selected": "Looking at: {title}",
    "access.ladderHeading": "Trip roles",
    "access.roleOwner": "Owner",
    "access.roleOwnerScope": "Everything: change visibility, invite people, remove members, delete the trip.",
    "access.roleAdmin": "Admin",
    "access.roleAdminScope": "Manage collaborators and edit places.",
    "access.roleCollaborator": "Collaborator",
    "access.roleCollaboratorScope": "Edit places.",
    "access.roleDetails": "Read the full permission rules",
    "access.roleDetailsBody": "Roles set what each member can do. A trip must keep one owner.",
    "access.visibilityHeading": "Trip visibility",
    "access.visPrivate": "Only me",
    "access.visPrivateConsequence": "No one else can open it, not even holding the link.",
    "access.visLinkRead": "Anyone with the link",
    "access.visLinkReadConsequence": "Anyone holding the link can read it without being a member first.",
    "access.visInviteesOnly": "Invited people only",
    "access.visInviteesOnlyConsequence": "Current invitees can open it until expiry.",
    "access.visPublic": "Public",
    "access.visPublicConsequence": "Visible to everyone on this network.",
    "access.confirmHeading": "Permission changes that need your confirmation",
    "access.whenOtherGainsOnly": "Someone else's role changes, yours stays",
    "access.whenActorLosesStanding": "You hand the trip to someone else",
    "access.whenRoleUnread": "Your role could not be loaded.",
    "access.whenMemberRemoved": "You take someone's access away",
    "access.confirmOtherGains": "That person will get the matching permission.",
    "access.confirmBothChange":
      "That person will get the matching permission, and your own permission changes with it.",
    "access.confirmUnanswered": "Permission change details are unavailable.",
    "access.confirmRemoval": "That person will lose access to this trip.",
    "access.switchHeading": "Change trip visibility",
    "access.switchPrivateToPublic":
      "After this the trip is visible to everyone -- people who could not see it before will be able to.",
    "access.switchPublicToPrivate":
      "After this, the people who followed it lose access -- they will not be able to open it any more.",
    "access.switchUnanswered": "Visibility change details are unavailable.",
    "access.inviteHeading": "Invitations",
    "access.inviteExpires": "Invitation expires at {expires}.",
    "access.inviteTtlMissing": "Invitation expiry unavailable.",
    "access.inviteQuotaNoCap": "Members: {used}. Limit unavailable.",
    "access.inviteQuotaMissing": "Member count and limit unavailable.",
    "access.inviteLimitReached": "This trip has reached its member limit, so a new invitation cannot be sent.",
    "access.activityHeading": "What has happened on this trip",
    "access.activityLoading": "Reading what happened…",
    "access.activityEmpty": "This trip has no recorded action yet.",
    "access.action.journey.created": "created this trip",
    "access.action.journey.deleted": "put this trip in the recycle bin",
    "access.action.journey.undeleted": "brought this trip back from the recycle bin",
    "access.action.journey.memberAdded": "added {name} to this trip",
    "access.action.journey.memberRoleChanged": "changed {name}'s permission",
    "access.action.journey.memberRemoved": "took {name}'s access away",
    "access.memberUnnamed": "a member this server did not name",
    "access.action.journey.visibilityChanged": "changed who can see this trip",
    "access.action.journey.invitationSent": "sent an invitation to this trip",
    "access.action.journey.invitationRevoked": "cancelled an invitation to this trip",
    "access.actionUnknown": "Unknown action: {token}.",
    "access.doorLoading": "Loading trip access settings…",
    "access.doorAbsent": "Access settings are unavailable ({paths}).",
    "access.doorPartial": "Some access settings are unavailable ({paths}).",
    "access.doorPresent": "Access settings are loaded. The member list is unavailable.",
  },
  "zh-CN": {
    "access.title": "成员与权限",
    "access.sub": "管理成员权限、行程可见范围和邀请。",
    "access.pickLabel": "选一条行程",
    "access.pickNone": "先选一条要看的行程",
    "access.pickLoading": "正在读你的行程列表…",
    "access.pickEmpty": "服务器暂未返回行程列表。",
    "access.selected": "现在在看：{title}",
    "access.ladderHeading": "成员角色权限",
    "access.roleOwner": "所有者",
    "access.roleOwnerScope": "全部权限：改可见性、请人、移除成员、删除行程。",
    "access.roleAdmin": "管理员",
    "access.roleAdminScope": "管理协作者、编辑地点。",
    "access.roleCollaborator": "协作者",
    "access.roleCollaboratorScope": "编辑地点。",
    "access.roleDetails": "查看完整权限规则",
    "access.roleDetailsBody": "角色决定成员可在这条行程中执行的操作。最后一位所有者不能被移除。",
    "access.visibilityHeading": "行程可见范围",
    "access.visPrivate": "仅个人",
    "access.visPrivateConsequence": "别人打不开，拿到链接也打不开。",
    "access.visLinkRead": "获得链接者可见",
    "access.visLinkReadConsequence": "有链接的人不用先进成员名单就能读。",
    "access.visInviteesOnly": "受邀者可见",
    "access.visInviteesOnlyConsequence": "只有邀请还在有效期内的人打得开，过期就打不开了。",
    "access.visPublic": "公开",
    "access.visPublicConsequence": "全网公开可见。",
    "access.confirmHeading": "需要你确认的权限变更",
    "access.whenOtherGainsOnly": "只动对方的档位，你的不变",
    "access.whenActorLosesStanding": "你把这条行程交到别人手上",
    "access.whenRoleUnread": "这台设备没读到你自己的档位",
    "access.whenMemberRemoved": "你撤销某个人的访问权限",
    "access.confirmOtherGains": "对方将获得对应权限。",
    "access.confirmBothChange": "对方将获得对应权限，你的权限也会随之变化。",
    "access.confirmUnanswered": "暂时无法读取权限变化。",
    "access.confirmRemoval": "对方将失去这条行程的权限。",
    "access.switchHeading": "更改行程可见范围",
    "access.switchPrivateToPublic": "转换后这条行程全网可见——原先看不见的人会开始能看见。",
    "access.switchPublicToPrivate": "转换后，已经在跟踪这条行程的人会失去访问权限。",
    "access.switchUnanswered": "暂时无法读取可见性变化。",
    "access.inviteHeading": "邀请",
    "access.inviteExpires": "邀请带着一个到期时刻：{expires}。过了那个时间就打不开了。",
    "access.inviteTtlMissing": "邀请有效期暂不可用。",
    "access.inviteQuotaNoCap": "当前成员数：{used}。上限暂不可用。",
    "access.inviteQuotaMissing": "成员数和上限暂不可用。",
    "access.inviteLimitReached": "这条行程的成员已到上限，发不出新邀请。",
    "access.activityHeading": "这条行程上发生过什么",
    "access.activityLoading": "正在读发生过什么…",
    "access.activityEmpty": "这条行程还没有记下任何动作。",
    "access.action.journey.created": "新建了这条行程",
    "access.action.journey.deleted": "把这条行程丢进了回收站",
    "access.action.journey.undeleted": "把这条行程从回收站找回",
    "access.action.journey.memberAdded": "把{name}加进了这条行程",
    "access.action.journey.memberRoleChanged": "改了{name}的权限",
    "access.action.journey.memberRemoved": "撤销了{name}的访问权限",
    "access.memberUnnamed": "这台服务器没有点名的人",
    "access.action.journey.visibilityChanged": "改了这条行程能被谁看见",
    "access.action.journey.invitationSent": "向这条行程发出一个邀请",
    "access.action.journey.invitationRevoked": "撤销了这条行程的一个邀请",
    "access.actionUnknown": "未知操作：{token}。",
    "access.doorLoading": "正在读取行程权限…",
    "access.doorAbsent": "权限设置暂不可用（{paths}）。",
    "access.doorPartial": "部分权限设置暂不可用（{paths}）。",
    "access.doorPresent": "权限设置已加载，成员名单暂不可用。",
  },
} as const;

export type AccessCopyKey = keyof (typeof accessCopy)["zh-CN"];

/** A key missing in one language must never reach a traveller as a raw key (the rule every lane copy
 *  module in this tree follows). */
export function accessCopyFor(locale: string, key: AccessCopyKey): string {
  const table = accessCopy[locale.startsWith("zh") ? "zh-CN" : "en"];
  return table[key] ?? accessCopy.en[key] ?? key;
}

/** `{name}`, `{ttl}`, `{used}`, `{cap}`, `{token}` and `{path}` come from a read or from the door
 *  this screen asked -- never from a number this file knows. A placeholder with no value stays
 *  visible as the placeholder, so a field the server did not send reads as missing instead of
 *  arriving as a finished sentence. */
export function fillAccess(template: string, params: Record<string, string | number>): string {
  return template.replace(/\{(\w+)\}/g, (_, name: string) => String(params[name] ?? `{${name}}`));
}
