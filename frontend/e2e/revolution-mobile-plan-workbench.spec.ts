import { expect, test } from "@playwright/test";

const journeyId = "00000000-0000-4000-8000-000000000331";
const planId = "00000000-0000-4000-8000-000000000332";

for (const width of [390, 430]) {
test(`TEST_FIXTURE saved server brief and two-place multiday preview ${width}`, async ({page}, testInfo) => {
  await page.setViewportSize({width,height:844});
  const ids = ["00000000-0000-4000-8000-000000000341", "00000000-0000-4000-8000-000000000342"];
  let goal="三天、美食、少走路";
  let ready=false;
  let generated=false;
  const writes:string[]=[];
  await page.addInitScript((id) => {
    sessionStorage.setItem("citynexus.traveler.bearer","TEST_FIXTURE_BRIEF_OWNER");
    sessionStorage.setItem("citynexus.traveler.session-id","TEST_FIXTURE_BRIEF_TRAVELER");
    localStorage.setItem("citynexus.revolution.firstlook.journey",JSON.stringify({id,cityCode:"TEST_FIXTURE",cityName:"测试地区",status:"DRAFT",ownerTravelerId:"TEST_FIXTURE_BRIEF_TRAVELER"}));
  },journeyId);
  await page.route("**/api/v1/**",async route => {
    const req=route.request(); const path=new URL(req.url()).pathname;
    const respond=(data:unknown,status=200)=>route.fulfill({status,contentType:"application/json",body:JSON.stringify(data)});
    if(req.method()==="POST"||req.method()==="PUT") writes.push(path);
    if(path.endsWith("/travelers/session")) return respond({traveler_id:"TEST_FIXTURE_BRIEF_TRAVELER"});
    if(path.endsWith("/agent/runtime-status")) return respond({ai_state:"DISABLED",runtime_identity:"UNAVAILABLE"});
    if(path===`/api/v1/journeys/${journeyId}`) return respond({id:journeyId,title:"TEST_FIXTURE",city_code:"TEST_FIXTURE",timezone:"Asia/Shanghai",status:"DRAFT",start_at:"2026-11-01T09:00:00+08:00",end_at:"2026-11-03T20:00:00+08:00"});
    if(path.endsWith("/planning-intent")) {
      expect(req.headers().authorization).toBe("Bearer TEST_FIXTURE_BRIEF_OWNER");
      if(req.method()==="PUT") goal=req.postDataJSON().goal;
      return respond({journey_id:journeyId,intent:{id:"TEST_FIXTURE_INTENT",goal,interests:["cafe"],energy:"easy",updated_at:goal,source:"USER_TRAVEL_BRIEF",free_text_status:"PRESERVED_NOT_FULLY_COMPILED",mapped_preferences:[{input:"美食",preference:"food"}]},
        trip:{dates:["2026-11-01","2026-11-02","2026-11-03"],party_size:2,budget:{amount_minor:200000,currency:"CNY"},planning_mode:"balanced"},
        preview_kind:"UNVERIFIED_SUGGESTION_DRAFT",transport_status:"UNKNOWN",plan_version_id:null,
        candidates:ids.map((id,index)=>({candidate_id:id,name:`TEST_FIXTURE 地点${index+1}`,provider_key:"photon",receipt_id:"TEST_FIXTURE_RECEIPT",source_url:`https://www.openstreetmap.org/way/${991230+index}`,provider_provenance:"TEST_PROVIDER",public_access_state:"PUBLIC_ACCESS_UNVERIFIED",selection_state:ready?"READY_FOR_NATIVE_PLAN":"OPENING_UNVERIFIED",selection_blockers:ready?[]:["OPENING_UNVERIFIED","COST_UNKNOWN"],opening_hours:ready?{status:"NORMALIZED_VALID",open:"09:00",close:"18:00"}:{status:"UNKNOWN"},cost_evidence:ready?{status:"KNOWN",amount_minor:0,evidence_basis:"OSM_FEE_NO"}:{status:"UNKNOWN"}}))});
    }
    if(path.endsWith("/plans/generate")) {
      expect(req.postDataJSON()).toEqual({candidate_count:1,bootstrap_candidate_ids:ids});
      expect(req.headers()["idempotency-key"]).toBeTruthy(); generated=true; return respond([],201);
    }
    if(path.endsWith("/plans")) return respond(generated?[{id:planId,journey_id:journeyId,version_no:1,status:"CANDIDATE",is_current:false,selectable:true,stale:false,lifecycle:"ACTIVE",activities:ids.map((id,i)=>({id,place_id:id,sequence_no:i+1,title:`TEST_FIXTURE 正式安排${i+1}`,start_at:`2026-11-0${i+1}T12:00:00+08:00`,end_at:`2026-11-0${i+1}T13:00:00+08:00`,travel_from_prev_min:0,cost_status:"KNOWN_FREE"}))}]:[]);
    if(path.endsWith("/bootstrap-shortlist"))return respond({journey_id:journeyId,items:[],resume:null,pocket_walk:null});
    return respond({detail:"TEST_FIXTURE_NOT_SEEDED"},404);
  });
  await page.goto("/revolution");
  await page.getByTestId("rev-mobile-tab-trips").click();
  const input=page.getByTestId("rev-travel-input");
  await expect(input).toContainText("3 天 · 2 人");
  await input.getByRole("checkbox",{name:"TEST_FIXTURE 地点1",exact:true}).check();
  await input.getByRole("checkbox",{name:"TEST_FIXTURE 地点2",exact:true}).check();
  await expect(input).toContainText("这一天还没有选地点");
  await expect(input).toContainText("营业时间：未知");
  await expect(page.getByTestId("rev-plan-generate")).toBeDisabled();
  expect(writes).toEqual([]);
  await input.getByText("修改旅行需求",{exact:true}).click();
  await input.getByRole("textbox",{name:"想做什么"}).fill("睡到中午，下午看博物馆");
  await input.getByRole("button",{name:"保存旅行需求",exact:true}).click();
  await expect(input.locator("p").filter({hasText:"睡到中午，下午看博物馆"})).toBeVisible();
  await page.getByTestId("rev-mobile-tab-explore").click();
  await expect(page.locator("#rev-mission-chat-input")).toHaveValue(/睡到中午，下午看博物馆/);
  await page.getByTestId("rev-mobile-tab-trips").click();
  await page.reload(); await page.getByTestId("rev-mobile-tab-trips").click();
  await expect(input).toContainText("睡到中午，下午看博物馆");
  ready=true;
  await page.getByRole("button",{name:"刷新方案",exact:true}).click();
  await input.getByRole("checkbox",{name:"TEST_FIXTURE 地点1",exact:true}).check();
  await input.getByRole("checkbox",{name:"TEST_FIXTURE 地点2",exact:true}).check();
  await expect(input).toContainText("营业时间：09:00–18:00 · 免费");
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  await page.evaluate(()=>window.scrollTo({top:0,behavior:"instant"}));
  await page.screenshot({path:testInfo.outputPath(`server-brief-multiplace-${width}-TEST_FIXTURE.png`),fullPage:true});
  await page.getByTestId("rev-plan-generate").click();
  await expect(page.getByTestId("rev-plan-workbench")).toContainText("TEST_FIXTURE 正式安排2");
  expect(writes).toEqual([`/api/v1/journeys/${journeyId}/planning-intent`,`/api/v1/journeys/${journeyId}/plans/generate`]);
});
}

for (const viewport of [{ width: 390, height: 844 }, { width: 430, height: 932 }]) {
test(`TEST_FIXTURE mobile plan review requires separate select and start, and survives refresh ${viewport.width}`, async ({ page }, testInfo) => {
  await page.setViewportSize(viewport);
  const writes: string[] = [];
  let selected = false;
  let active = false;
  await page.addInitScript(({ journeyId }) => {
    sessionStorage.setItem("citynexus.traveler.bearer", "TEST_FIXTURE_PLAN_OWNER");
    sessionStorage.setItem("citynexus.traveler.session-id", "TEST_FIXTURE_PLAN_TRAVELER");
    localStorage.setItem("citynexus.revolution.firstlook.journey", JSON.stringify({
      id: journeyId, cityCode: "TEST_FIXTURE", cityName: "测试地区", status: "DRAFT", ownerTravelerId: "TEST_FIXTURE_PLAN_TRAVELER",
    }));
  }, { journeyId });
  await page.route("**/api/v1/**", async (route) => {
    const req = route.request();
    const path = new URL(req.url()).pathname;
    const respond = (data: unknown, status = 200) => route.fulfill({ status, contentType: "application/json", body: JSON.stringify(data) });
    if (req.method() === "POST") writes.push(path);
    if (path.endsWith("/travelers/session")) return respond({ traveler_id: "TEST_FIXTURE_PLAN_TRAVELER" });
    if (path.endsWith("/agent/runtime-status")) return respond({ ai_state: "DISABLED", runtime_identity: "UNAVAILABLE" });
    if (path.endsWith("/members/me")) { if(req.headers().authorization !== "Bearer TEST_FIXTURE_PLAN_OWNER") return respond({detail:"TEST_FIXTURE_OTHER_MEMBER"},403); expect(req.headers().authorization).toBe("Bearer TEST_FIXTURE_PLAN_OWNER"); return respond({journey_id:journeyId,traveler_id:"TEST_FIXTURE_PLAN_TRAVELER",may_confirm_departure:true,seat:{in_force:true,role:"OWNER"}}); }
    if (path.endsWith("/departure")) { if(req.headers().authorization !== "Bearer TEST_FIXTURE_PLAN_OWNER") return respond({detail:"TEST_FIXTURE_OTHER_MEMBER"},403); expect(req.headers().authorization).toBe("Bearer TEST_FIXTURE_PLAN_OWNER"); return respond({journey_id:journeyId,gate:active?"ALREADY_RUNNING":selected?"READY_TO_DEPART":"NO_PLAN_SELECTED",observed_at:"2026-10-20T00:00:00Z",reason_detail:null,selected_plan:selected?{plan_version_id:planId,activities_count:1}:null,candidates:[]}); }
    if (path === `/api/v1/journeys/${journeyId}`) return respond({
      id: journeyId, city_code: "TEST_FIXTURE", title: "TEST_FIXTURE 3天旅行", timezone: "Asia/Shanghai",
      status: active ? "ACTIVE" : selected ? "PLANNED" : "DRAFT",
      start_at: "2026-11-01T09:00:00+08:00", end_at: "2026-11-03T18:00:00+08:00",
    });
    if (path.endsWith("/plans") && req.method() === "GET") {
      if (req.headers().authorization !== "Bearer TEST_FIXTURE_PLAN_OWNER") return respond({ detail: "TEST_FIXTURE_OTHER_MEMBER" }, 403);
      expect(req.headers().authorization).toBe("Bearer TEST_FIXTURE_PLAN_OWNER");
      return respond([{
        id: planId, journey_id: journeyId, version_no: 1, status: active ? "ACTIVE" : selected ? "SELECTED" : "CANDIDATE",
        is_current: selected, selectable: true, stale: false, lifecycle: "ACTIVE", planning_mode: "balanced", source: "INITIAL",
        total_cost: { amount_minor: 0, currency: "CNY" }, total_cost_status: "PARTIAL_UNKNOWN",
        activities: [{
          id: "TEST_FIXTURE_ACTIVITY", sequence_no: 1, title: "TEST_FIXTURE · 城市公园", activity_type: "VISIT",
          start_at: "2026-11-01T10:00:00+08:00", end_at: "2026-11-01T11:00:00+08:00",
          travel_from_prev_min: 15, estimated_cost: { amount_minor: 0, currency: "CNY" }, cost_status: "UNKNOWN",
          metadata: { opening_hours: { source_urls: ["https://example.org/TEST_FIXTURE/place", "javascript:alert(1)"] } },
        }],
      }]);
    }
    if (path.endsWith("/departure/commit") && req.method() === "POST") {
      // 选用这份方案 now presses the commit door.  The key is the point of the press, so the
      // spec fails if the client ever sends this without one: a tap and a half would become two
      // decisions (`backend/app/departure_commit.py:156`).
      expect(req.headers().authorization).toBe("Bearer TEST_FIXTURE_PLAN_OWNER");
      const sent = req.postDataJSON() as { plan_version_id?: string };
      expect(sent.plan_version_id).toBe(planId);
      const key = req.headers()["idempotency-key"];
      expect(typeof key).toBe("string");
      expect(String(key).length).toBeGreaterThan(8);
      selected = true;
      return respond({ journey_id: journeyId, plan_version_id: planId,
        committed_by: "TEST_FIXTURE_PLAN_TRAVELER",
        seat: { traveler_id: "TEST_FIXTURE_PLAN_TRAVELER", seat_kind: "OWNER", role: "OWNER",
          member_id: null, member_state: "MEMBER_IN_FORCE", expires_at: null, in_force: true },
        idempotency_key: String(key), decision_action: "plan.committed_by_traveler",
        committed_at: "2026-10-22T04:00:00Z",
        journey: { id: journeyId, status: "PLANNED", active_plan_version_id: planId } });
    }
    // The bare select route stays stubbed because it is still the transition the commit door
    // calls server-side (`backend/app/main.py:18029`); the browser no longer presses it.
    if (path.endsWith(`/plans/${planId}/select`) && req.method() === "POST") {
      expect(req.headers().authorization).toBe("Bearer TEST_FIXTURE_PLAN_OWNER");
      selected = true;
      return respond({ status: "PLANNED" });
    }
    if (path.endsWith("/start") && req.method() === "POST") {
      expect(selected).toBe(true);
      active = true;
      return respond({ journey_id: journeyId, active_plan_version_id: planId, context: { journey_status: "ACTIVE" } });
    }
    if (path.endsWith("/bootstrap-shortlist")) return respond({ journey_id: journeyId, items: [], resume: null, pocket_walk: null });
    return respond({ detail: "TEST_FIXTURE_NOT_SEEDED" }, 404);
  });

  await page.goto("/revolution");
  await page.getByTestId("rev-mobile-tab-trips").click();
  const workbench = page.getByTestId("rev-plan-workbench");
  await expect(workbench).toContainText("TEST_FIXTURE · 城市公园");
  await expect(workbench).toContainText("10:00—11:00");
  await expect(workbench).toContainText("费用待确认");
  await expect(workbench.getByTestId("rev-plan-day-gap")).toHaveText("还有 2 天未安排，可返回探索补充地点。");
  await expect(workbench.locator('a[href^="javascript:"]')).toHaveCount(0);
  expect(writes).toEqual([]);
  await expect(page.getByTestId("rev-plan-start")).toHaveCount(0);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  const selectBounds = await page.getByTestId("rev-plan-select").boundingBox();
  expect(selectBounds?.height ?? 0).toBeGreaterThanOrEqual(44);
  await page.screenshot({ path: testInfo.outputPath(`plan-review-${viewport.width}x${viewport.height}-TEST_FIXTURE.png`) });
  await page.getByTestId("rev-plan-select").click();
  await expect(workbench).toContainText("已选用");
  await expect(page.getByTestId("rev-v3-server-departure")).toContainText("可以确认出发");
  expect(writes).toEqual([`/api/v1/journeys/${journeyId}/departure/commit`]);
  await page.reload();
  await page.getByTestId("rev-mobile-tab-trips").click();
  await expect(workbench).toContainText("已选用");
  await expect(page.getByTestId("rev-plan-start")).toBeVisible();
  await page.getByTestId("rev-plan-start").click();
  await expect(workbench).toContainText("正在使用");
  expect(writes).toEqual([`/api/v1/journeys/${journeyId}/departure/commit`, `/api/v1/journeys/${journeyId}/start`]);
  await page.evaluate(() => {
    sessionStorage.setItem("citynexus.traveler.bearer", "TEST_FIXTURE_OTHER_MEMBER");
    window.dispatchEvent(new CustomEvent("citynexus.traveler.bearer.changed"));
  });
  await expect(workbench).not.toContainText("TEST_FIXTURE · 城市公园");
  await expect(workbench).toContainText("当前账号无法读取这份行程");
});
}
