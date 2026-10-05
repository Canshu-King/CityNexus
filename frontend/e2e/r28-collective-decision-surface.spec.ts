import { expect, test } from "@playwright/test";
import { ensureDemoJourney, openScreen } from "./_qoderShellSeed";

const TOKEN = "r28-ui-signed-bearer";
const mission = {
  id: "r28-ui-mission",
  journey_id: "journey-from-route",
  trigger_event_id: null,
  user_text: "Resolve the shared trade-off.",
  status: "WAITING_FOR_MEMBERS",
  parent_mission_id: null,
  clarification: {
    kind: "COLLECTIVE_TRADEOFF",
    clarification_id: "r28-ui-clarification",
    status: "WAITING_FOR_MEMBERS",
  },
};

test.describe("R28 collective decision surface", () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript((token) => {
      window.sessionStorage.setItem("citynexus.traveler.bearer", token);
    }, TOKEN);
    await ensureDemoJourney(page);
    await openScreen(page, "/v8/hub", ["today-heading"]);
  });

  test("shows member progress and sends the signed traveler bearer when answering", async ({ page }) => {
    let answerAuthorization = "";
    await page.route("**/api/v1/journeys/*/missions/pending", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          journey_id: "journey-from-route",
          viewer: {
            traveler_id: "traveler-owner",
            member_id: "member-owner",
            role: "OWNER",
            auth_method: "SIGNED_HMAC_BEARER",
          },
          items: [{
            mission,
            run: null,
            continuation: null,
            collective: {
              status: "WAITING_FOR_MEMBERS",
              policy: "MATERIAL_TRADEOFF_REQUIRES_ALL_RELEVANT_MEMBER_RESPONSES",
              required_count: 2,
              response_count: 1,
              viewer_member_id: "member-owner",
              viewer_has_responded: false,
              selected_proposal_id: null,
              required_members: [
                {
                  member_id: "member-owner",
                  traveler_id: "traveler-owner",
                  role: "OWNER",
                  display_name: "Owner",
                  responded: false,
                  is_viewer: true,
                },
                {
                  member_id: "member-admin",
                  traveler_id: "traveler-admin",
                  role: "ADMIN",
                  display_name: "Admin",
                  responded: true,
                  is_viewer: false,
                },
              ],
              candidate_options: [
                {
                  proposal_id: "11111111-1111-1111-1111-111111111111",
                  status: "GROUNDED_FEASIBLE",
                  display_places: [{ place_id: "garden", name: "Garden", category: "garden" }],
                  fit_subject_tags: ["garden", "quiet"],
                  fairness: { unacceptable_member_ids: ["member-admin"] },
                },
                {
                  proposal_id: "22222222-2222-2222-2222-222222222222",
                  status: "GROUNDED_FEASIBLE",
                  display_places: [{ place_id: "museum", name: "Museum", category: "museum" }],
                  fit_subject_tags: ["museum", "craft"],
                  fairness: { unacceptable_member_ids: ["member-owner"] },
                },
              ],
            },
          }],
        }),
      });
    });

    await page.route("**/api/v1/journeys/*/missions/*/collective-clarification/member-owner", async (route) => {
      answerAuthorization = route.request().headers()["authorization"] ?? "";
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          journey_id: "journey-from-route",
          mission_id: mission.id,
          clarification_id: "r28-ui-clarification",
          status: "WAITING_FOR_MEMBERS",
          responses: {
            "member-owner": {
              member_id: "member-owner",
              proposal_id: "11111111-1111-1111-1111-111111111111",
            },
          },
          baseline_preferences_unchanged: true,
          traveler_twin_unchanged: true,
          child_mission: null,
        }),
      });
    });

    await page.getByTestId("v18-copilot-dock").locator(".cn-copilot-edge").click();
    await expect(page.getByTestId("collective-decision")).toBeVisible();
    await expect(page.getByTestId("collective-progress")).toHaveText("1/2");
    await expect(page.getByTestId("collective-member")).toHaveCount(2);
    await expect(page.getByTestId("collective-option")).toHaveCount(2);

    await page.getByTestId("collective-option").first().getByRole("button").click();
    await expect.poll(() => answerAuthorization).toBe(`Bearer ${TOKEN}`);
    await expect(page.locator(".cn-collective-notice")).toContainText(/saved|等待/i);
  });

  test("shows durable approval and sends the same signed identity when approving", async ({ page }) => {
    let approvalAuthorization = "";
    await page.route("**/api/v1/journeys/*/missions/pending", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          journey_id: "journey-from-route",
          viewer: {
            traveler_id: "traveler-owner",
            member_id: "member-owner",
            role: "OWNER",
            auth_method: "SIGNED_HMAC_BEARER",
          },
          items: [{
            mission: {
              ...mission,
              id: "r28-approval-mission",
              status: "WAITING_FOR_APPROVAL",
              clarification: {},
            },
            run: {
              run_id: "r28-run",
              mission_id: "r28-approval-mission",
              provider_key: "hermes",
              model_key: "test",
              status: "WAITING_FOR_APPROVAL",
              outcome: "waiting",
              failure_reason: null,
              tool_steps: [],
              completion_contract: { kind: "APPROVAL_PENDING" },
            },
            collective: null,
            continuation: {
              pending_action_id: "pending-1",
              pending_status: "PENDING",
              tool_name: "accept_replan",
              approval_id: "approval-1",
              approval_status: "PENDING",
              required_decision: "REQUIRE_CONFIRMATION",
              approved_by: null,
              viewer_can_approve: true,
            },
          }],
        }),
      });
    });

    await page.route("**/api/v1/journeys/*/agent/approvals/approval-1/approve", async (route) => {
      approvalAuthorization = route.request().headers()["authorization"] ?? "";
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          approval_id: "approval-1",
          journey_id: "journey-from-route",
          action: "ACCEPT_REPLAN",
          target_type: "ReplanProposal",
          target_id: "proposal-1",
          status: "CONSUMED",
          approval_method: "USER_CONFIRMATION",
          approved_by: "traveler-owner",
          created_at: new Date().toISOString(),
          expires_at: new Date(Date.now() + 60_000).toISOString(),
          approved_at: new Date().toISOString(),
          consumed_at: new Date().toISOString(),
          continuation: {
            status: "RESUMED",
            pending_action_id: "pending-1",
            run_id: "r28-run",
            mission_id: "r28-approval-mission",
            replayed: false,
          },
        }),
      });
    });

    await page.getByTestId("v18-copilot-dock").locator(".cn-copilot-edge").click();
    await expect(page.getByTestId("collective-approval")).toBeVisible();
    await page.getByTestId("collective-approve").click();
    await expect.poll(() => approvalAuthorization).toBe(`Bearer ${TOKEN}`);
    await expect(page.locator(".cn-collective-notice")).toContainText(/resumed|继续|完成/i);
  });

  test("shows disagreement, grounded mediation progress, renewed round, and approval", async ({ page }) => {
    let stage = 0;
    let mediatorResumeCount = 0;
    const ownerProposal = "11111111-1111-1111-1111-111111111111";
    const adminProposal = "22222222-2222-2222-2222-222222222222";
    const compromiseProposal = "33333333-3333-3333-3333-333333333333";

    const collective = (options: Array<Record<string, unknown>>, responseCount = 0) => ({
      status: "WAITING_FOR_MEMBERS",
      policy: "POST_DISAGREEMENT_REQUIRES_RENEWED_MEMBER_CONSENT",
      required_count: 2,
      response_count: responseCount,
      viewer_member_id: "member-owner",
      viewer_has_responded: false,
      selected_proposal_id: null,
      required_members: [
        { member_id: "member-owner", traveler_id: "traveler-owner", role: "OWNER", display_name: "Owner", responded: responseCount > 0, is_viewer: true },
        { member_id: "member-admin", traveler_id: "traveler-admin", role: "ADMIN", display_name: "Admin", responded: responseCount > 0, is_viewer: false },
      ],
      candidate_options: options,
    });
    const oldOptions = [
      { proposal_id: ownerProposal, status: "GROUNDED_FEASIBLE", display_places: [{ place_id: "garden", name: "Garden", category: "garden" }], fit_subject_tags: ["garden"], fairness: { unacceptable_member_ids: ["member-admin"] } },
      { proposal_id: adminProposal, status: "GROUNDED_FEASIBLE", display_places: [{ place_id: "museum", name: "Museum", category: "museum" }], fit_subject_tags: ["museum"], fairness: { unacceptable_member_ids: ["member-owner"] } },
    ];
    const newOptions = [
      { proposal_id: compromiseProposal, status: "GROUNDED_FEASIBLE", display_places: [{ place_id: "craft-garden", name: "Craft Garden", category: "craft" }], fit_subject_tags: ["craft", "garden"], fairness: { minimum_member_fit: 0.7, maximum_regret: 0.2, unacceptable_member_ids: [] } },
    ];

    await page.route("**/api/v1/journeys/*/missions/pending", async (route) => {
      const states = [
        {
          mission: { ...mission, id: "r29-round-1", status: "WAITING_FOR_MEMBERS", clarification: { ...mission.clarification, clarification_id: "r29-round-1" } },
          collective: collective(oldOptions, 1),
        },
        {
          mission: { ...mission, id: "r29-mediator", status: "CREATED", parent_mission_id: "r29-round-1", clarification: {}, resolved_intent: { collective_mediation: { kind: "DISAGREEMENT_MEDIATION", round: 1 } } },
          collective: null,
        },
        {
          mission: { ...mission, id: "r29-round-2", status: "WAITING_FOR_MEMBERS", clarification: { ...mission.clarification, clarification_id: "r29-round-2" } },
          collective: collective(newOptions, 0),
        },
        {
          mission: { ...mission, id: "r29-approval", status: "WAITING_FOR_APPROVAL", clarification: {} },
          run: { run_id: "r29-run", mission_id: "r29-approval", provider_key: "hermes", model_key: "test", status: "WAITING_FOR_APPROVAL", outcome: "waiting", failure_reason: null, tool_steps: [], completion_contract: { kind: "APPROVAL_PENDING" } },
          collective: null,
          continuation: { pending_action_id: "r29-pending", pending_status: "PENDING", tool_name: "accept_replan", approval_id: "r29-approval", approval_status: "PENDING", required_decision: "REQUIRE_CONFIRMATION", approved_by: null, viewer_can_approve: true },
        },
      ];
      const state = states[Math.min(stage, states.length - 1)];
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          journey_id: "journey-from-route",
          viewer: { traveler_id: "traveler-owner", member_id: "member-owner", role: "OWNER", auth_method: "SIGNED_HMAC_BEARER" },
          items: [{ mission: state.mission, run: state.run ?? null, continuation: state.continuation ?? null, collective: state.collective }],
        }),
      });
    });

    await page.route("**/api/v1/journeys/*/missions/*/collective-clarification/member-owner", async (route) => {
      if (stage === 0) {
        stage = 1;
        await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ status: "MEDIATION_REQUIRED", child_mission: { id: "r29-mediator" } }) });
      } else {
        stage = 3;
        await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ status: "WAITING_FOR_MEMBERS", child_mission: { id: "r29-round-2" } }) });
      }
    });
    await page.route("**/api/v1/journeys/*/missions/r29-mediator/resume", async (route) => {
      mediatorResumeCount += 1;
      if (mediatorResumeCount > 1) stage = 2;
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ run: { status: "WAITING_FOR_MEMBERS" } }) });
    });
    await page.route("**/api/v1/journeys/*/missions/r29-round-2/resume", async (route) => {
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ run: { status: "WAITING_FOR_APPROVAL" } }) });
    });

    await page.getByTestId("v18-copilot-dock").locator(".cn-copilot-edge").click();
    await expect(page.getByTestId("collective-decision")).toBeVisible();
    await page.getByTestId("collective-option").first().getByRole("button").click();
    await expect(page.getByTestId("collective-mediation")).toBeVisible();
    await expect(page.getByTestId("collective-mediation")).toContainText(/mediating|调解/i);
    await expect(page.getByTestId("collective-mediation").getByText(/winner|获胜者/i)).toHaveCount(0);

    await page.getByTestId("collective-mediation").getByRole("button").click();
    await expect(page.getByTestId("collective-decision")).toBeVisible();
    await expect(page.getByText("Craft Garden")).toBeVisible();
    await expect(page.getByTestId("collective-option")).toHaveCount(1);
    await page.getByTestId("collective-option").getByRole("button").click();
    await expect(page.getByTestId("collective-approval")).toBeVisible();
    await expect(page.getByTestId("collective-approval")).toContainText(/waiting for approval|等批准/i);
  });
});
