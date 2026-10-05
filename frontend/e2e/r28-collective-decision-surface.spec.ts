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
});
