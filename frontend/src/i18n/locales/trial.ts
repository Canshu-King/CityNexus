// ORD-0572: this domain's slice of ../LocaleContext.tsx, moved verbatim -- no value was reworded.

export const trial = {
  en: {
  "trial.kicker": "Try CityNexus with your own city",
  "trial.title": "Start a real journey, not only the sealed demo.",
  "trial.lede": "Choose your destination and travel anchors. Cities with no sealed replay use live city providers when enabled; CityNexus will not quietly substitute another city's replay data for the one you asked for.",
  "trial.liveTitle": "Generic-city trial",
  "trial.liveNote": "For cities without a sealed replay, use live providers. If providers are unavailable, CityNexus will tell you instead of inventing facts about the city.",
  /* ORD-0216 ④: no city name here, on purpose.  `GET /api/v1/demo/scene` picks the sealed journey
     from server data -- the one an ACTIVE plan points at, else the most recently seeded one
     (backend/app/main.py) -- so the entry cannot know which city it hands over until the
     server has answered.  HJ-P1 read 「使用封存的天津演示」 on a stage whose sealed journey is
     Guangzhou (`review/evidence/ui-overnight/ord0216-scene-city.json` reproduces the selection
     rule).  Naming *any* city here is the `HUMAN_MISLEADING` defect; so would be "Guangzhou". */
  "trial.tianjinDemo": "Use the sealed demo trip",
  /* ORD-0273: the sealed-demo read failure is a named product state, not a raw error passthrough.
     The technical facts ride in data-* of the element (see V8Experience), never in this sentence.
     This is the `en` copy: the same key in `zhCN` below carries the Chinese sentence, and neither
     dictionary may hold the other's language -- an English screen speaking Chinese is the ORD-0240
     defect wearing the other coat. */
  "trial.sealedUnreadable": "Couldn't read the sealed demo: the server answered just now, but what it answered isn't something we can use. Nothing you filled in caused this.",
  /* ORD-0349 (HJ-P3): this leg never got an answer, so it may not borrow the sentence that says the
     server answered.  The wording covers both ways an answer can fail to arrive -- the connection
     never came up, or this read reached its own deadline -- because the screen is not allowed to
     name a cause it did not observe. */
  "trial.sealedNoAnswer": "Couldn't read the sealed demo: this device got no answer from the server -- the connection did not come up, or this read ended without a reply. Nothing you filled in caused this.",

  "trial.city": "Destination city",
  "trial.country": "Country/region code",
  "trial.timezone": "Time zone",
  "trial.start": "Journey start",
  "trial.end": "Journey end",
  "trial.arrival": "Arrival location",
  "trial.departure": "Departure location",
  "trial.budget": "Trip budget",
  "trial.stayBudget": "Stay budget",
  "trial.currency": "Currency",
  "trial.party": "Travelers",
  "trial.rooms": "Rooms (suggested)",
  /* ORD-0557: the tail the entry form invents when it has to say, on its own, whether a field blocks
     the review step and what an open-ended lower bound means. `lib/entryLimits.ts` carried this pair
     inline; the copy here is the words that were already on the glass, unchanged. */
  "trial.fieldRequired": "required",
  "trial.fieldOptional": "optional",
  "trial.rangeFrom": "from {min} {unit}",
  "trial.create": "Create journey",
  "trial.creating": "Creating…",
  "trial.cancel": "Back to current journey",
  "trial.newJourney": "Try another city",
  "trial.createdLiveHint": "Journey created. Open City Discovery to use live providers for this city.",
  "trial.autoSetPrefix": "Auto-set: ",
  "trial.changeThisAria": "Change ",
  "trial.departureField": "Departure",
  "trial.destination": "Destination",
  "trial.navArrival": "where you arrive",
  "trial.navDeparture": "where you leave",
  "trial.navDestination": "the destination",
  "trial.next": "Next",
  "trial.notFilledRequired": " not filled in · required",
  "trial.retry": "Retry",
  "trial.toConfirm": "to confirm",
  },
  zh: {
  "trial.kicker": "用你自己的城市试用 CityNexus",
  "trial.title": "创建真实行程，不只局限于封存演示。",
  "trial.lede": "选择目的地和出发/返程锚点。没有封存回放的城市在启用时使用实时城市数据源；CityNexus 不会悄悄拿别的城市的封存数据冒充你要去的地方。",
  "trial.liveTitle": "通用城市试用",
  "trial.liveNote": "没有封存回放的城市应使用实时数据源。若数据源不可用，系统会明确告诉你，而不是编造这座城市的资料。",
  /* ORD-0216 ④：这里刻意不写城市名。封存演示是哪一趟由服务器的 /api/v1/demo/scene 决定（有 ACTIVE
     方案的那趟，否则最近 seed 的那趟，backend/app/main.py），入口在服务器回答之前无从知道
     城市。HJ-P1 在封存那趟为广州的舞台上读到「使用封存的天津演示」（`ord0216-scene-city.json` 复现了
     这条选择规则）。写任何城市名都是 `HUMAN_MISLEADING`；改成"广州"同样只是把不一致挪个地方。 */
  "trial.tianjinDemo": "使用封存的演示行程",
  "trial.sealedUnreadable": "没读到封存演示的信息：服务器刚才答了，但答的内容我们用不了。这不是你填错了什么。",
  /* ORD-0349：这一腿根本没拿到回答，所以不许借用"服务器答了"那一句。措辞覆盖拿不到回答的两种走法
     —— 连接没成，或这一趟到时限也没回话 —— 因为屏幕不许点名一个它没观察到的原因。 */
  "trial.sealedNoAnswer": "没读到封存演示的信息：这台设备没有拿到服务器的回答——连接没成，或者这一趟到时限也没有回话。这不是你填错了什么。",

  "trial.city": "目的城市",
  "trial.country": "国家/地区代码",
  "trial.timezone": "时区",
  "trial.start": "行程开始",
  "trial.end": "行程结束",
  "trial.arrival": "抵达地点",
  "trial.departure": "离开地点",
  "trial.budget": "行程预算",
  "trial.stayBudget": "住宿预算",
  "trial.currency": "货币",
  "trial.party": "出行人数",
  "trial.rooms": "房间数（建议值，可调整）",
  /* ORD-0557：入口表自己补的那截尾巴——这一格挡不挡审核、只有下限的区间怎么说。
     原先写死在 `lib/entryLimits.ts`，这里的中文就是屏上原本那几个字。 */
  "trial.fieldRequired": "必填",
  "trial.fieldOptional": "选填",
  "trial.rangeFrom": "{min} {unit}起",
  "trial.create": "创建行程",
  "trial.creating": "正在创建…",
  "trial.cancel": "返回当前行程",
  "trial.newJourney": "试用其他城市",
  "trial.createdLiveHint": "行程已创建。进入“城市探索”后可使用该城市的实时数据源。",
  "trial.autoSetPrefix": "已自动设置：",
  "trial.changeThisAria": "改这一项：",
  "trial.departureField": "离开",
  "trial.destination": "目的地",
  "trial.navArrival": "抵达地点",
  "trial.navDeparture": "离开地点",
  "trial.navDestination": "目的地",
  "trial.next": "下一步",
  "trial.notFilledRequired": " 未填写 · 必填",
  "trial.retry": "重试",
  "trial.toConfirm": "待确认",
  },
};
