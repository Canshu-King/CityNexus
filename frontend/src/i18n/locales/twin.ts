// ORD-0572: this domain's slice of ../LocaleContext.tsx, moved verbatim -- no value was reworded.

export const twin = {
  en: {

  // ── Traveler Twin ──
  "twin.kicker": "Traveler Twin · soft context",
  "twin.title": "Personalization with a boundary.",
  "twin.lede": "Explicit intent wins. Learned evidence helps rank a plan, but never expands budget, payment, commitment, or autonomy authority.",
  "twin.explicit": "Explicit",
  "twin.explicitFrom": "From this Journey request",
  "twin.explicitSub": "Applied directly to the current plan objective.",
  "twin.learned": "Learned soft signal",
  "twin.learnedFrom": "From completed Journey outcomes",
  "twin.learnedSub": "Ranking input only · expires with evidence freshness.",
  "twin.authorityBoundary": "Authority boundary",
  "twin.boundarySub": "Your preferences can improve a route or hotel ranking. They cannot create a booking, spend money, or weaken a confirmed reservation.",
  "twin.provenance": "Inspectable provenance available",

  /* ORD-0422 -- the traveler-facing sentences these three panels used to hardcode in English:
     features/traveler-twin/TwinPanel.tsx, features/recovery/V14RecoveryTruthPanel.tsx,
     features/discovery/RealCityDiscoveryPanel.tsx. One contiguous block per locale on purpose
     (ORD-0420 appends to this file too; scattered insertions are what let two lanes take each
     other's value). The `twin.cap.*`, `twin.sev.*`, `twin.dim.*` and `v14.mode.*` keys are the
     server's closed vocabularies -- backend/app/capabilities.py, backend/app/schemas.py,
     backend/app/schemas.py -- and the data/mock/traveler_demo.json preference keys, which are
     open (backend/app/execution/traveler_twin.py takes them from preference rows), so every
     group has an *Unknown frame that quotes the token instead of rendering a bare enum. */
  "twin.capabilityNeeds": "Capability needs",
  "twin.learnedCapabilityState": "Learned capability state",
  "twin.noCapabilityFacts": "No explicit capability facts recorded.",
  "twin.noExplicitPrefs": "No explicit preferences",
  "twin.noLearnedSignals": "No learned signals",
  "twin.confirmedByTraveler": "Confirmed by traveler",
  "twin.statedNeedsConfirm": "Stated; confirmation needed",
  "twin.hardNeedsRemain": "{n} hard {plural:need}, explicit and never learned.",
  "twin.hardNeverInferred": "Hard accessibility needs are never inferred from behavior.",
  "twin.unknownEvidenceNote": "Unknown accessibility evidence is not accessible.",
  "twin.capUnknown": "unregistered capability code: {code}",
  "twin.sevUnknown": "unregistered severity: {code}",
  "twin.dimUnknown": "unregistered preference dimension: {code}",
  "twin.sev.HARD": "Hard need",
  "twin.sev.STRONG": "Strong preference",
  "twin.sev.SOFT": "Soft preference",
  "twin.dim.culture": "culture",
  "twin.dim.local_food": "local food",
  "twin.dim.waterfront": "waterfront",
  "twin.dim.relaxed": "relaxed pace",
  "twin.dim.walking_minutes_max": "walking minutes cap",
  "twin.cap.STEP_FREE_REQUIRED": "Step-free required",
  "twin.cap.AVOID_STAIRS": "Avoid stairs",
  "twin.cap.MAX_WALKING_PER_LEG_M": "Max walking per leg (m)",
  "twin.cap.MAX_CONTINUOUS_WALKING_MIN": "Max continuous walking (min)",
  "twin.cap.MAX_DAILY_WALKING_M": "Max daily walking (m)",
  "twin.cap.MIDDAY_REST_WINDOW": "Midday rest window",
  "twin.cap.REST_EVERY_MIN": "Rest every (min)",
  "twin.cap.INFANT_NAP_WINDOW": "Infant nap window",
  "twin.cap.TOILET_BREAK_EVERY_MIN": "Toilet break every (min)",
  "twin.cap.STROLLER": "Stroller",
  "twin.cap.LARGE_LUGGAGE": "Large luggage",
  "twin.cap.SLOW_PACE": "Slow pace",
  "twin.cap.QUIET_ENVIRONMENT": "Quiet environment",
  "twin.cap.INDOOR_PREFERRED": "Indoor preferred",
  "twin.cap.SENSORY_LOW_STIMULATION": "Low sensory stimulation",
  },
  zh: {

  // ── 旅行者画像 ──
  "twin.kicker": "旅行者画像 · 软上下文",
  "twin.title": "有边界的个性化。",
  "twin.lede": "显式意图优先。学习到的证据帮助排序方案，但永远不会扩展预算、支付、承诺或自主权限。",
  "twin.explicit": "显式",
  "twin.explicitFrom": "来自此次行程请求",
  "twin.explicitSub": "直接应用于当前方案目标。",
  "twin.learned": "学习到的软信号",
  "twin.learnedFrom": "来自已完成的行程结果",
  "twin.learnedSub": "仅用于排序 · 随证据新鲜度过期。",
  "twin.authorityBoundary": "权限边界",
  "twin.boundarySub": "你的偏好可改善路线或酒店排名，但不会创建预订、花费金钱或削弱已确认的预订。",
  "twin.provenance": "可检查的溯源可用",

  /* ORD-0422 -- the traveler-facing sentences these three panels used to hardcode in English:
     features/traveler-twin/TwinPanel.tsx, features/recovery/V14RecoveryTruthPanel.tsx,
     features/discovery/RealCityDiscoveryPanel.tsx. One contiguous block per locale on purpose
     (ORD-0420 appends to this file too; scattered insertions are what let two lanes take each
     other's value). The `twin.cap.*`, `twin.sev.*`, `twin.dim.*` and `v14.mode.*` keys are the
     server's closed vocabularies -- backend/app/capabilities.py, backend/app/schemas.py,
     backend/app/schemas.py -- and the data/mock/traveler_demo.json preference keys, which are
     open (backend/app/execution/traveler_twin.py takes them from preference rows), so every
     group has an *Unknown frame that quotes the token instead of rendering a bare enum. */
  "twin.capabilityNeeds": "能力需求",
  "twin.learnedCapabilityState": "习得的能力状态",
  "twin.noCapabilityFacts": "没有记录到明确的能力事实。",
  "twin.noExplicitPrefs": "没有明确偏好",
  "twin.noLearnedSignals": "没有习得信号",
  "twin.confirmedByTraveler": "已由旅行者确认",
  "twin.statedNeedsConfirm": "已声明，尚待确认",
  "twin.hardNeedsRemain": "{n} 项硬性需求仍按明确声明保留，不会被习得。",
  "twin.hardNeverInferred": "无障碍硬性需求不会从行为里推断出来。",
  "twin.unknownEvidenceNote": "来源不明的无障碍证据，不作为无障碍依据。",
  "twin.capUnknown": "未登记的能力代码：{code}",
  "twin.sevUnknown": "未登记的强度：{code}",
  "twin.dimUnknown": "未登记的偏好维度：{code}",
  "twin.sev.HARD": "硬性需求",
  "twin.sev.STRONG": "较强偏好",
  "twin.sev.SOFT": "一般偏好",
  "twin.dim.culture": "文化",
  "twin.dim.local_food": "当地饮食",
  "twin.dim.waterfront": "滨水",
  "twin.dim.relaxed": "放松节奏",
  "twin.dim.walking_minutes_max": "步行时长上限",
  "twin.cap.STEP_FREE_REQUIRED": "全程免台阶",
  "twin.cap.AVOID_STAIRS": "避开楼梯",
  "twin.cap.MAX_WALKING_PER_LEG_M": "每段步行上限（米）",
  "twin.cap.MAX_CONTINUOUS_WALKING_MIN": "连续步行上限（分钟）",
  "twin.cap.MAX_DAILY_WALKING_M": "每日步行上限（米）",
  "twin.cap.MIDDAY_REST_WINDOW": "午间休息时段",
  "twin.cap.REST_EVERY_MIN": "定时休息（分钟）",
  "twin.cap.INFANT_NAP_WINDOW": "婴儿午睡时段",
  "twin.cap.TOILET_BREAK_EVERY_MIN": "定时如厕（分钟）",
  "twin.cap.STROLLER": "需要婴儿车",
  "twin.cap.LARGE_LUGGAGE": "大件行李",
  "twin.cap.SLOW_PACE": "慢节奏",
  "twin.cap.QUIET_ENVIRONMENT": "安静环境",
  "twin.cap.INDOOR_PREFERRED": "偏好室内",
  "twin.cap.SENSORY_LOW_STIMULATION": "低感官刺激",
  },
};
