import os
import unittest

os.environ["STUDIO_TEST_MODE"] = "true"

from fastapi.testclient import TestClient

from backend.app import app, store


def auth(actor: str, role: str) -> dict[str, str]:
    return {"Authorization": f"Bearer test:{actor}:{role}"}


class StudioLifecycleTests(unittest.TestCase):
    def setUp(self) -> None:
        store.reset()
        self.client = TestClient(app)
        self.admin = auth("admin-1", "admin")
        self.reviewer = auth("reviewer-1", "reviewer")
        self.professional = auth("professional-1", "professional")
        self.client_user = auth("client-1", "client")

    def post(self, path: str, payload: dict, headers: dict[str, str]) -> dict:
        response = self.client.post(path, json=payload, headers=headers)
        self.assertLess(response.status_code, 300, response.text)
        return response.json()

    def test_complete_synthetic_managed_delivery_lifecycle(self) -> None:
        organization = self.post("/api/organizations", {"name": "Synthetic Retail Co"}, self.admin)
        org_id = organization["id"]
        for actor_id, role in (("reviewer-1", "reviewer"), ("professional-1", "professional"), ("client-1", "client")):
            self.post(f"/api/organizations/{org_id}/members", {"actor_id": actor_id, "role": role}, self.admin)
        self.post("/api/professionals/professional-1/approve", {}, self.admin)

        engagement = self.post("/api/engagements", {"organization_id": org_id, "name": "Inventory modernization", "objective": "Reduce stockout investigation time"}, self.admin)
        project = self.post("/api/projects", {"engagement_id": engagement["id"], "name": "Synthetic delivery"}, self.admin)
        package = self.post("/api/work-packages", {"project_id": project["id"], "title": "Prepare diagnostic plan", "acceptance_criteria": ["Plan is reviewed", "Steps are bounded"]}, self.admin)
        assignment = self.post(f"/api/work-packages/{package['id']}/assignments", {"professional_id": "professional-1"}, self.admin)
        self.assertEqual(assignment["status"], "invited")
        assignments = self.client.get("/api/professionals/professional-1/assignments", headers=self.professional)
        self.assertEqual(assignments.status_code, 200)
        self.assertEqual(assignments.json()[0]["status"], "invited")
        unauthorized_accept = self.client.post(f"/api/assignments/{assignment['id']}/accept", headers=self.reviewer)
        self.assertEqual(unauthorized_accept.status_code, 403)
        accepted_assignment = self.post(f"/api/assignments/{assignment['id']}/accept", {}, self.professional)
        self.assertEqual(accepted_assignment["status"], "accepted")
        self.assertEqual(self.client.get(f"/api/engagements/{engagement['id']}/projects", headers=self.professional).status_code, 200)

        run = self.post("/api/ai-runs", {"work_package_id": package["id"], "specification": "Create a bounded implementation work breakdown for the approved inventory problem."}, self.admin)
        self.assertEqual(run["agent"], "synthetic-planner-v1")
        rejected_self = self.client.post(f"/api/ai-runs/{run['id']}/decision", json={"decision": "approved"}, headers=self.admin)
        self.assertEqual(rejected_self.status_code, 409)
        artifact = self.post(f"/api/ai-runs/{run['id']}/decision", {"decision": "approved", "comment": "Bounded plan is suitable for review."}, self.reviewer)
        self.assertEqual(artifact["status"], "approved")

        deliverable = self.post("/api/deliverables", {"work_package_id": package["id"], "title": "Reviewed plan", "content": "Synthetic plan content"}, self.professional)
        review = self.post(f"/api/deliverables/{deliverable['id']}/review", {"decision": "approved", "comment": "Evidence and acceptance criteria checked."}, self.reviewer)
        self.assertEqual(review["deliverable"]["status"], "approved")
        accepted = self.post(f"/api/deliverables/{deliverable['id']}/accept", {}, self.client_user)
        self.assertEqual(accepted["status"], "accepted")
        self.assertEqual(self.client.get(f"/api/engagements/{engagement['id']}/projects", headers=self.client_user).status_code, 200)
        self.assertEqual(len(self.client.get(f"/api/work-packages/{package['id']}/deliverables", headers=self.client_user).json()), 1)
        completed = self.post(f"/api/projects/{project['id']}/complete", {}, self.admin)
        self.assertEqual(completed["status"], "completed")

        events = self.client.get("/api/audit", headers=self.admin).json()
        actions = {event["action"] for event in events}
        self.assertIn("ai_run.completed", actions)
        self.assertIn("deliverable.client_accepted", actions)
        self.assertIn("project.completed", actions)

    def test_unapproved_professional_and_cross_organization_access_are_denied(self) -> None:
        first = self.post("/api/organizations", {"name": "First synthetic org"}, self.admin)
        second = self.post("/api/organizations", {"name": "Second synthetic org"}, self.admin)
        self.post(f"/api/organizations/{first['id']}/members", {"actor_id": "client-1", "role": "client"}, self.admin)
        self.post(f"/api/organizations/{second['id']}/members", {"actor_id": "client-2", "role": "client"}, self.admin)
        engagement = self.post("/api/engagements", {"organization_id": first["id"], "name": "Private engagement", "objective": "No cross-org access"}, self.admin)
        project = self.post("/api/projects", {"engagement_id": engagement["id"], "name": "Private project"}, self.admin)
        package = self.post("/api/work-packages", {"project_id": project["id"], "title": "Private package", "acceptance_criteria": ["review"]}, self.admin)
        unapproved = self.client.post(f"/api/work-packages/{package['id']}/assignments", json={"professional_id": "professional-2"}, headers=self.admin)
        self.assertEqual(unapproved.status_code, 409)

        hidden = self.client.get("/api/engagements", headers=auth("client-2", "client"))
        self.assertEqual(hidden.status_code, 200)
        self.assertEqual(hidden.json(), [])
        self.assertEqual(self.client.get(f"/api/engagements/{engagement['id']}/projects", headers=auth("client-2", "client")).status_code, 403)

    def test_professional_cannot_self_approve(self) -> None:
        response = self.client.post(
            "/api/professionals/professional-1/approve",
            headers=self.professional,
        )
        self.assertEqual(response.status_code, 403)
        application = self.client.post(
            "/api/professionals/professional-1/application",
            headers=self.professional,
        )
        self.assertEqual(application.status_code, 201)
        decision = self.client.post(
            "/api/professionals/professional-1/decision",
            headers=self.admin,
            json={"decision": "approved"},
        )
        self.assertEqual(decision.status_code, 200)

    def test_membership_revocation_removes_access_and_preserves_an_owner(self) -> None:
        organization = self.post("/api/organizations", {"name": "Revocation test"}, self.admin)
        org_id = organization["id"]
        self.post(f"/api/organizations/{org_id}/members", {"actor_id": "analyst-1", "role": "reviewer"}, self.admin)
        visible = self.client.get("/api/engagements", headers=auth("analyst-1", "reviewer"))
        self.assertEqual(visible.status_code, 200)

        revoked = self.client.delete(f"/api/organizations/{org_id}/members/analyst-1/reviewer", headers=self.admin)
        self.assertEqual(revoked.status_code, 200)
        self.assertEqual(self.client.get("/api/engagements", headers=auth("analyst-1", "reviewer")).json(), [])
        final_owner = self.client.delete(f"/api/organizations/{org_id}/members/admin-1/owner", headers=self.admin)
        self.assertEqual(final_owner.status_code, 409)
        actions = {event["action"] for event in self.client.get("/api/audit", headers=self.admin).json()}
        self.assertIn("membership.revoked", actions)

    def test_reviewer_audit_history_is_organization_scoped(self) -> None:
        first = self.post("/api/organizations", {"name": "Visible org"}, self.admin)
        second = self.post("/api/organizations", {"name": "Hidden org"}, self.admin)
        self.post(f"/api/organizations/{first['id']}/members", {"actor_id": "reviewer-1", "role": "reviewer"}, self.admin)
        self.post("/api/engagements", {"organization_id": first["id"], "name": "Visible engagement", "objective": "Visible audit"}, self.admin)
        self.post("/api/engagements", {"organization_id": second["id"], "name": "Hidden engagement", "objective": "Hidden audit"}, self.admin)
        reviewer_events = self.client.get("/api/audit", headers=self.reviewer)
        self.assertEqual(reviewer_events.status_code, 200)
        self.assertTrue(reviewer_events.json())
        self.assertTrue(all(event["organization_id"] == first["id"] for event in reviewer_events.json()))

    def test_real_authentication_is_required_when_test_mode_is_disabled(self) -> None:
        os.environ["STUDIO_TEST_MODE"] = "false"
        try:
            response = self.client.get("/api/me", headers=self.admin)
            self.assertEqual(response.status_code, 503)
        finally:
            os.environ["STUDIO_TEST_MODE"] = "true"


if __name__ == "__main__":
    unittest.main()
