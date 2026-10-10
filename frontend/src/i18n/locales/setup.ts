// ORD-0572: this domain's slice of ../LocaleContext.tsx, moved verbatim -- no value was reworded.

export const setup = {
  en: {

  // ── Trip-creation wizard: spoken labels, buttons and status lines ──
  /* ORD-0555 (lane 起手工): the wizard held these strings in `zh ? "..." : "..."` arms, so
     neither half was reachable by a key lookup. Both halves move here, in the file's line order.
     Values are byte-for-byte the strings the screen already showed -- this is a move, not a rewrite.
     Readings: _qoder_shouqigong_0555/readings/. */
  "setup.change2": "Change",
  "setup.weFilledThisInForYou": "we filled this in for you",
  "setup.createATrip": "Create a trip",
  "setup.eGTianjinTokyoSingapore": "e.g. Tianjin, Tokyo, Singapore",
  "setup.seeSupportedDestinations": "See supported destinations",
  "setup.noNameLandedInThisGroupThisRound": "No name landed in this group this round.",
  "setup.arrivalTime": "Arrival time",
  "setup.departureTime": "Departure time",
  "setup.advancedSettings": "Advanced settings",
  "setup.pace": "Pace",
  "setup.interests": "Interests",
  "setup.specialRequirements": "Special requirements",
  "setup.notFilledInRequired": "not filled in · required",
  "setup.travellersRooms": "Travellers / rooms",
  "setup.totalStayBudget": "Total / stay budget",
  "setup.pace2": "Pace",
  "setup.autoSet2": "Auto-set",
  "setup.stoppedWaiting": "Stopped waiting",
  "setup.back": "Back",
  "setup.createTrip": "Create trip",
  "setup.identityNotReadYet": "identity not read yet",
  "setup.theServerNamedIt": "the server named it",
  "setup.noIdentityYet": "no identity yet",
  "setup.thisName": "this name",
  "setup.theServerCannotNameThisPlace": "The server cannot name this place",
  "setup.thePlacesAreHereButNoneHasACoordinate": "The places are here, but none has a coordinate",
  "setup.thisDestinationHasNotBeenPrepared": "This destination has not been prepared",
  "setup.noPlacesAreRegisteredForThisDestination": "No places are registered for this destination",
  "setup.theServerSaysThisDestinationCanBePlannedNow": "the server says this destination can be planned now",
  "setup.itWasAskedAndNothingAnsweredThisRound": "it was asked, and nothing answered this round",
  "setup.theServerGaveSomeOtherVerdict": "the server gave some other verdict",
  },
  zh: {

  // ── 行程创建向导：口语标签、按钮与状态行 ──
  /* ORD-0555（车道 起手工）：向导里这些串写在 `zh ? "..." : "..."` 的分支上，两边都查不到键。
     两端都搬进字典，按该文件的行序排。值是这些屏本来就在显示的那串，逐字节相同——这是搬运，不是改写。
     读数：_qoder_shouqigong_0555/readings/。 */
  "setup.change2": "改这一项",
  "setup.weFilledThisInForYou": "我们替你填的",
  "setup.createATrip": "新建行程",
  "setup.eGTianjinTokyoSingapore": "例如：天津、东京、新加坡",
  "setup.seeSupportedDestinations": "看支持的目的地",
  "setup.noNameLandedInThisGroupThisRound": "这一轮没有名字落在这一组。",
  "setup.arrivalTime": "抵达时间",
  "setup.departureTime": "离开时间",
  "setup.advancedSettings": "高级设置",
  "setup.pace": "旅行节奏",
  "setup.interests": "兴趣",
  "setup.specialRequirements": "特殊要求",
  "setup.notFilledInRequired": "未填写 · 必填",
  "setup.travellersRooms": "人数 / 房间",
  "setup.totalStayBudget": "总预算 / 住宿",
  "setup.pace2": "节奏",
  "setup.autoSet2": "自动设置",
  "setup.stoppedWaiting": "已停止等待",
  "setup.back": "返回",
  "setup.createTrip": "确认创建",
  "setup.identityNotReadYet": "身份还没读到",
  "setup.theServerNamedIt": "服务器给了身份",
  "setup.noIdentityYet": "还没有身份",
  "setup.thisName": "这个名字",
  "setup.theServerCannotNameThisPlace": "服务器认不出这个名字",
  "setup.thePlacesAreHereButNoneHasACoordinate": "这里有地点，但它们没有坐标",
  "setup.thisDestinationHasNotBeenPrepared": "这座城还没准备过",
  "setup.noPlacesAreRegisteredForThisDestination": "这座城还没登记任何地点",
  "setup.theServerSaysThisDestinationCanBePlannedNow": "服务器说这座城现在就能规划",
  "setup.itWasAskedAndNothingAnsweredThisRound": "问了，这一轮没人回答",
  "setup.theServerGaveSomeOtherVerdict": "服务器给了别的判定",
  },
};
