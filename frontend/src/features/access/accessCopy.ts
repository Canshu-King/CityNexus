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
    "access.sub":
      "Who can change this trip, what each visibility level means, and which of that this server can answer today.",
    "access.pickLabel": "Choose a trip",
    "access.pickNone": "Pick a trip to look at",
    "access.pickLoading": "Reading your trip list…",
    "access.pickEmpty":
      "This server named no trip for you, so this screen has no subject yet. Nothing about your trips changed.",
    "access.selected": "Looking at: {title}",
    "access.ladderHeading": "Three roles, each with the one sentence that says what it can do",
    "access.roleOwner": "Owner",
    "access.roleAdmin": "Admin",
    "access.roleCollaborator": "Collaborator",
    "access.roleDetails": "Read the full permission rules",
    "access.roleLadderHeading": "What each role may do, read off this server's own ACL rows",
    "access.roleCapabilityCount": "This server grants this role {count} capabilities.",
    "access.capabilityTokens": "The capability codes, as the server names them",
    "access.scopeKeyUnread":
      "This server named a scope key this dictionary has no sentence for: {key}.",
    "access.scopeDoorSilent":
      "The role door answered nothing, so this screen lists no capabilities -- it does not guess them from the role name.",
    "access.roleChangeButton": "Change role",
    "access.selfExitButton": "Leave this trip",
    "access.roleChoicesHeading": "Move this seat to:",
    "access.roleChangePending":
      "This changes what that person may do on this trip. Your own access does not change.",
    "access.confirmSelfExit":
      "This takes you out of this trip. The row stays listed, so anybody reading the roster can see you left.",
    "access.adminCapOpen":
      "This server lets this trip hold {cap} admin seats, and {used} of them are taken right now.",
    "access.adminCapFull":
      "All {cap} admin seats this server allows are taken, so one further promotion is refused.",
    "access.adminCapUnanswered":
      "The seat door did not answer, so this screen says nothing about how many admins this trip may hold.",
    "access.memberScopeLine": "What this role can do: ",
    "access.roleDetailsBody":
      "A role is what this server lets that person do on this trip, not what a screen shows them. Removing the last owner is refused by the server rather than left for a traveller to discover.",
    "access.visibilityHeading": "Each visibility level, with its consequence said in the same breath",
    "access.visPrivate": "Only me",
    "access.visPrivateConsequence": "No one else can open it, not even holding the link.",
    "access.visLinkRead": "Anyone with the link",
    "access.visLinkReadConsequence": "Anyone holding the link can read it without being a member first.",
    "access.visInviteesOnly": "Invited people only",
    "access.visInviteesOnlyConsequence": "Only invitations still in date can open it; an expired one cannot.",
    "access.visPublic": "Public",
    "access.visPublicConsequence": "Visible to everyone on this network.",
    "access.confirmHeading": "What the screen will ask before it changes a permission",
    "access.whenOtherGainsOnly": "Someone else's role changes, yours stays",
    "access.whenActorLosesStanding": "You hand the trip to someone else",
    "access.whenRoleUnread": "This device could not read your own role",
    "access.whenMemberRemoved": "You take someone's access away",
    "access.confirmOtherGains": "That person will get the matching permission.",
    "access.confirmBothChange":
      "That person will get the matching permission, and your own permission changes with it.",
    "access.confirmUnanswered": "This screen will not answer that with a sentence it has to guess at.",
    "access.confirmRemoval": "That person will lose access to this trip.",
    "access.switchHeading": "Private to public, and public to private, each said from the other side",
    "access.switchPrivateToPublic":
      "After this the trip is visible to everyone -- people who could not see it before will be able to.",
    "access.switchPublicToPrivate":
      "After this, the people who followed it lose access -- they will not be able to open it any more.",
    "access.switchUnanswered": "This move has no gain-or-loss sentence on this tree, so none is shown.",
    "access.inviteHeading": "Invitations",
    "access.inviteExpires": "An invitation carries an expiry: {expires}. After that moment it does not open.",
    "access.inviteTtlMissing": "This server gave no expiry for an invitation, so none is claimed here.",
    "access.inviteQuotaNoCap":
      "This server gave a member count ({used}) and no limit, so nothing here says whether the trip is full.",
    "access.inviteQuotaMissing":
      "This server gave no member count or limit for this trip, so nothing is counted here.",
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
    "access.actionUnknown": "This server reported an action this screen has no sentence for: {token}.",
    "access.doorLoading": "Asking this server who else can reach this trip…",
    "access.doorAbsent":
      "This server answered none of {paths}, so nothing on this screen can be changed today. The ladders say what each level will mean once those doors answer -- they are not a claim about this trip.",
    "access.doorPartial":
      "This server answered some but not all of the sharing doors; the ones still silent are {paths}. Read the ladders as what each level will mean, not as this trip's state.",
    "access.doorPresent":
      "This server answered all three sharing doors. The roster and the invitations below are its answers; the ladders and the confirmation lines are still this screen's own words.",
    "access.rosterHeading": "Members of this trip, as the member door answers",
    "access.rosterEmpty": "The member door answered with nobody in the list -- that is its answer, not a load failure.",
    "access.memberRow": "{role} · {name}",
    "access.memberNameUnread":
      "This server named nobody for that member id, so this row shows no name.",
    "access.memberStateActive": "still in force",
    "access.memberStateExpired": "past the expiry this server gave it",
    "access.memberStateRemoved": "withdrawn at {removed}",
    "access.memberStateUnknown": "This server gave a member state this screen has no sentence for: {state}.",
    "access.memberNoEnd": "carries no expiry, so it will not lapse on its own",
    "access.grantHeading": "Invitations issued for this trip",
    "access.grantEmpty": "The invitation door answered with none issued.",
    "access.roleUnread": "This server named a role this screen has no sentence for: {role}.",
    "access.grantTokenSummary": "The token this invitation carries",
    "access.grantActive": "Open until {expires}.",
    "access.grantNoExpiry": "This invitation carries no expiry, so it will not lapse on its own.",
    "access.grantRevoked": "Withdrawn at {revoked}. Whoever held this link can no longer open it.",
    "access.grantToken": "Invitation token, as the server gave it: {token}",
    "access.inviteFormHeading": "Issue an invitation with an expiry",
    "access.inviteFormPick": "Which visibility the invitation carries",
    "access.inviteFormExpiry": "Expiry moment (leaving it empty means the invitation never lapses)",
    "access.inviteFormSigner": "Signed with this trip's own traveler_id. This step is not authenticated: the server records what this device said, it does not check who typed it.",
    "access.inviteFormSubmit": "Issue the invitation",
    "access.inviteFormBusy": "Sending…",
    "access.confirmRevokeGrant": "After this, whoever holds the link can no longer open it. Your own access does not change.",
    "access.confirmRevokeMember": "After this, that person is no longer a member of this trip. Your own access does not change.",
    "access.revokeButton": "Withdraw",
    "access.revokeConfirmButton": "Confirm withdrawal",
    "access.writeRefusedUnknown": "The server refused this write. The code it answered with is: {code}.",
    "access.refuseExpiryInPast": "That expiry moment is already behind us, so the server did not issue the invitation.",
    "access.refuseExpiryNoOffset": "The expiry has to carry its offset from UTC; without one the server will not guess a deadline.",
    "access.refuseExpiryUnreadable": "The server could not read the expiry moment at all.",
    "access.refuseNotLinkReadable": "The server will not issue this level as a link: it says that level is not the link-readable kind.",
    "access.refuseJourneyGone": "This trip is gone from the server, so the invitation had nowhere to attach to.",
    "access.refuseGrantAlreadyRevoked": "This one was already withdrawn; the server did not touch it again.",
    "access.refuseGrantUnknown": "This trip has no such invitation on the server, so nothing was withdrawn.",
    "access.refuseMemberAlreadyWithdrawn": "That member already left; the server did not touch the row again.",
    "access.refuseMemberUnknown": "This trip has no such member on the server, so nothing was withdrawn.",
    "access.refuseRoleUnchanged": "That is already the role this member holds, so the server changed nothing.",
    "access.refuseRoleSelfChange": "The server will not let a person move their own seat; somebody else has to make that change.",
    "access.refuseOwnerRoleImmutable": "The owner seat does not move through this door in either direction, so a role change can never leave this trip unowned.",
    "access.refuseMemberManageNotPermitted": "The role you signed this request with does not hold member management on this trip, so the server refused to move that seat.",
    "access.refuseActorNotInJourney": "The person this request was signed as is not a member of this trip, so the server answered nothing.",
    "access.refuseActorLapsed": "That person's membership on this trip has run out, so it carries no authority to change a role.",
    "access.refuseAdminCapReached": "This trip already holds the number of admin seats the server allows, so the promotion was refused.",
    "access.refuseSelfExitNotAMember": "This server has no membership row for you on this trip, so there was nothing for you to leave.",
    "access.refuseOwnerCannotLeave": "You are this trip's owner, and the server will not let it be left unowned from this screen.",
    "access.activityNoSharingWriter":
      "Member and invitation actions are not written into this trip's activity stream by this server yet, so the list above holds only the trip's own actions.",
  },
  "zh-CN": {
    "access.title": "成员与权限",
    "access.sub": "谁能改这条行程、每个可见档位各意味着什么，以及这些里头哪些是这台服务器现在真能答的。",
    "access.pickLabel": "选一条行程",
    "access.pickNone": "先选一条要看的行程",
    "access.pickLoading": "正在读你的行程列表…",
    "access.pickEmpty": "这台服务器没有报出你的行程，这一屏还没有主语。你的行程没有因此变化。",
    "access.selected": "现在在看：{title}",
    "access.ladderHeading": "三档角色，每档一句它能做什么",
    "access.roleOwner": "所有者",
    "access.roleAdmin": "管理员",
    "access.roleCollaborator": "协作者",
    "access.roleDetails": "查看完整权限规则",
    "access.roleLadderHeading": "每一档能做什么，按这台服务器自己的 ACL 行读出来的",
    "access.roleCapabilityCount": "这台服务器给这一档 {count} 项能力。",
    "access.capabilityTokens": "能力编号（服务器原样叫法）",
    "access.scopeKeyUnread":
      "这台服务器报了一个本字典没有句子的作用域键：{key}。",
    "access.scopeDoorSilent":
      "角色那扇门没答，所以这一屏不列能力——不拿角色名去猜它能做什么。",
    "access.roleChangeButton": "改角色",
    "access.selfExitButton": "我自己退出",
    "access.roleChoicesHeading": "把这枚席位改成：",
    "access.roleChangePending": "这改的是那个人在这条行程里能做的事。你自己的权限不变。",
    "access.confirmSelfExit": "这把你从这条行程里移出去。这一行还留在名单上，别人读得到你走过。",
    "access.adminCapOpen": "这台服务器允许这条行程同时占 {cap} 枚管理员席位，现在占了 {used} 枚。",
    "access.adminCapFull": "这台服务器允许的 {cap} 枚管理员席位已经占满，再多给一枚会被拒。",
    "access.adminCapUnanswered": "席位那扇门没答，所以这一屏不说这条行程能放几枚管理员。",
    "access.memberScopeLine": "这一档能做什么：",
    "access.roleDetailsBody":
      "角色说的是服务器允许这个人在这条行程上做什么，不是屏上显示成什么样。最后一个所有者不能被移除，这条由服务器拒绝，而不是让旅行者自己撞上才知道。",
    "access.visibilityHeading": "可见性每一档，后果就在同一句里",
    "access.visPrivate": "仅个人",
    "access.visPrivateConsequence": "别人打不开，拿到链接也打不开。",
    "access.visLinkRead": "获得链接者可见",
    "access.visLinkReadConsequence": "有链接的人不用先进成员名单就能读。",
    "access.visInviteesOnly": "受邀者可见",
    "access.visInviteesOnlyConsequence": "只有邀请还在有效期内的人打得开，过期就打不开了。",
    "access.visPublic": "公开",
    "access.visPublicConsequence": "全网公开可见。",
    "access.confirmHeading": "改权限之前，屏会先这样问",
    "access.whenOtherGainsOnly": "只动对方的档位，你的不变",
    "access.whenActorLosesStanding": "你把这条行程交到别人手上",
    "access.whenRoleUnread": "这台设备没读到你自己的档位",
    "access.whenMemberRemoved": "你撤销某个人的访问权限",
    "access.confirmOtherGains": "对方将获得对应权限。",
    "access.confirmBothChange": "对方将获得对应权限，你的权限也会随之变化。",
    "access.confirmUnanswered": "这一屏不肯用猜来的句子回答这一步。",
    "access.confirmRemoval": "对方将失去这条行程的权限。",
    "access.switchHeading": "私到公、公到私，各写一句对方会怎样",
    "access.switchPrivateToPublic": "转换后这条行程全网可见——原先看不见的人会开始能看见。",
    "access.switchPublicToPrivate": "转换后，已经在跟踪这条行程的人会失去访问权限。",
    "access.switchUnanswered": "这一步在这棵树上没有谁得失的句子，所以这里也不写一句。",
    "access.inviteHeading": "邀请",
    "access.inviteExpires": "邀请带着一个到期时刻：{expires}。过了那个时间就打不开了。",
    "access.inviteTtlMissing": "这台服务器没有给出邀请的有效期，所以这里不声称有一个。",
    "access.inviteQuotaNoCap":
      "这台服务器给了成员数（{used}），没给上限，所以这里不说这条行程满没满。",
    "access.inviteQuotaMissing": "这台服务器没有给出这条行程的成员数与上限，所以这里不计数。",
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
    "access.actionUnknown": "这台服务器报了一个本屏说不出人话的动作：{token}。",
    "access.doorLoading": "正在问这台服务器还有谁能到达这条行程…",
    "access.doorAbsent":
      "这台服务器 {paths} 一扇都没答，所以这一屏今天没有任何一项能真改。下面写的是那几扇门答话之后每一档意味着什么，不是对这条行程下的结论。",
    "access.doorPartial":
      "这台服务器只答了共享那几扇门里的一部分，还没答的是 {paths}。下面写的是每档将要意味着什么，不是这条行程现在的状态。",
    "access.doorPresent":
      "这台服务器三扇共享门都答了。下面的名单与邀请是这几扇的答案，档位表和确认句仍是这一屏自己的话。",
    "access.rosterHeading": "这条行程的成员，按成员门答的",
    "access.rosterEmpty": "成员门答了，名单是空的——这是它的答案，不是没读到。",
    "access.memberRow": "{role} · {name}",
    "access.memberNameUnread":
      "这台服务器说没人为那个成员编号登记名字，所以这一行不显示名字。",
    "access.memberStateActive": "还在生效",
    "access.memberStateExpired": "已过它自己的到期时刻",
    "access.memberStateRemoved": "已在 {removed} 撤回",
    "access.memberStateUnknown": "这台服务器报了一个本屏说不出人话的成员状态：{state}。",
    "access.memberNoEnd": "没给到期时刻，也就是不会自己失效",
    "access.grantHeading": "这条行程发出去的邀请",
    "access.grantEmpty": "邀请门答了，一条也没发过。",
    "access.roleUnread": "这台服务器报了一个本屏说不出人话的角色：{role}。",
    "access.grantTokenSummary": "这条邀请带的令牌",
    "access.grantActive": "到 {expires} 之前可开。",
    "access.grantNoExpiry": "这条邀请没有到期时刻，不会自己失效。",
    "access.grantRevoked": "已于 {revoked} 撤销。拿这条链接的人再也打不开了。",
    "access.grantToken": "邀请令牌（服务器原样给的）：{token}",
    "access.inviteFormHeading": "发一条带有效期的邀请",
    "access.inviteFormPick": "这条邀请带哪一档可见性",
    "access.inviteFormExpiry": "到期时刻（留空就是这条不会自己失效）",
    "access.inviteFormSigner": "签名用的是这条行程自己的 traveler_id。这一步不鉴权：服务器记下这台设备说了什么，不查是谁在敲。",
    "access.inviteFormSubmit": "发出邀请",
    "access.inviteFormBusy": "正在发…",
    "access.confirmRevokeGrant": "撤销后，拿这条链接的人就打不开了。你自己的权限不变。",
    "access.confirmRevokeMember": "撤回后，这个人不再是这条行程的成员。你自己的权限不变。",
    "access.revokeButton": "撤销",
    "access.revokeConfirmButton": "确认撤销",
    "access.writeRefusedUnknown": "这台服务器拒绝了这一笔，它给的编号是：{code}。",
    "access.refuseExpiryInPast": "那个到期时刻已经过去了，服务器没有发出这条邀请。",
    "access.refuseExpiryNoOffset": "到期时刻要带上与 UTC 的偏移，不带的话服务器不替你猜一个期限。",
    "access.refuseExpiryUnreadable": "服务器完全读不出这个到期时刻。",
    "access.refuseNotLinkReadable": "这一档不能当链接发出去：服务器说它不是可凭链接读的那一档。",
    "access.refuseJourneyGone": "这条行程已经不在服务器上了，邀请没地方挂。",
    "access.refuseGrantAlreadyRevoked": "这一条早就撤销了，服务器没有再动它。",
    "access.refuseGrantUnknown": "这条行程在服务器上没有这条邀请，所以什么都没撤销。",
    "access.refuseMemberAlreadyWithdrawn": "这一位早就退出了，服务器没有再动这一行。",
    "access.refuseMemberUnknown": "这条行程在服务器上没有这一位成员，所以什么都没撤回。",
    "access.refuseRoleUnchanged": "那本来就是这一位在服务器上的角色，所以服务器什么都没改。",
    "access.refuseRoleSelfChange": "服务器不许一个人自己挪自己的席位，这一改得由别人来按。",
    "access.refuseOwnerRoleImmutable": "主人席位不从这扇门两头挪，所以改角色不会让这条行程没有主人。",
    "access.refuseMemberManageNotPermitted": "你签名用的那个角色在这条行程上没有成员管理权，所以服务器没让你挪这一席。",
    "access.refuseActorNotInJourney": "这笔请求签名的人在服务器上不属这条行程的成员，所以服务器什么都没答。",
    "access.refuseActorLapsed": "那个人在这条行程上的成员期限已过，所以他没有改别人角色的权。",
    "access.refuseAdminCapReached": "这条行程的管理员席位已经占满服务器允许的数量，所以这一枚提升被拒。",
    "access.refuseSelfExitNotAMember": "服务器在这条行程上没有你的成员行，所以也没有可退的位置。",
    "access.refuseOwnerCannotLeave": "你是这条行程的主人，服务器不许从这一屏把它变成没有主人。",
    "access.activityNoSharingWriter":
      "成员与邀请这类动作，这台服务器还没往活动流里写，所以上面只有这条行程自己的动作。",
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
