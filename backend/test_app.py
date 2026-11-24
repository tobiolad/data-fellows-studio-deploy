import os
import unittest
from unittest.mock import patch

os.environ["STUDIO_TEST_MODE"] = "true"

from fastapi.testclient import TestClient

import backend.app as app_module
from backend.review_fixture import assert_review_workflow
from backend.admission_fixture import admit_professional, assert_admission_gates
from backend.app import app, store
from backend.auth import Principal, TokenValidationError


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

    def test_deployed_environment_refuses_test_identity_on_api_routes(self):
        for environment in ("staging", "production"):
            with patch.dict(os.environ, {"STUDIO_ENV": environment, "STUDIO_TEST_MODE": "true"}):
                self.assertEqual(self.client.get("/api/me", headers=self.admin).status_code, 503)

    def test_scoped_review_queue_and_single_decision(self):
        assert_review_workflow(self)

    def test_resubmission_and_decision_provenance(self):
        path = "/api/professionals/release-candidate"
        owner = auth("release-candidate", "professional")
        admit_professional(self.client, "release-candidate", self.admin)
        before = self.client.get(path + "/application", headers=owner).json()
        self.assertEqual(self.client.post(path + "/application", headers=owner).status_code, 409)
        self.assertEqual(self.client.get(path + "/application", headers=owner).json(), before)
        self.assertEqual(self.client.get(path + "/admission-history", headers=owner).status_code, 403)
        history = self.client.get(path + "/admission-history", headers=self.admin).json()
        self.assertEqual(history[0]["previous_status"], "under_review")
        self.assertEqual(history[0]["policy_version"], "studio-admission-v2")
        self.assertEqual(len(history[0]["verified_evidence"]), 1)
        profile = self.client.get(path + "/profile", headers=owner).json()
        self.assertEqual(profile["evidence_references"][0]["status"], "reviewer verified")
        self.client.put(path + "/profile", headers=owner, json=profile).raise_for_status()
        self.assertEqual(self.client.get(path + "/profile", headers=owner).json()["evidence_references"][0]["status"], "unverified")
        self.assertEqual(history[0]["reviewed_profile_version"], 1)
        self.assertEqual(history[0]["reviewer"], before["decided_by"])

    def test_admission_policy_denials(self):
        assert_admission_gates(self, "synthetic-policy-applicant")

    def test_complete_synthetic_managed_delivery_lifecycle(self) -> None:
        organization = self.post("/api/organizations", {"name": "Synthetic Retail Co"}, self.admin)
        org_id = organization["id"]
        self.assertEqual(self.client.get("/api/organizations", headers=self.admin).status_code, 200)
        for actor_id, role in (("reviewer-1", "reviewer"), ("professional-1", "professional"), ("client-1", "client")):
            self.post(f"/api/organizations/{org_id}/members", {"actor_id": actor_id, "role": role}, self.admin)
        roster = self.client.get(f"/api/organizations/{org_id}/members", headers=self.admin)
        self.assertEqual(roster.status_code, 200)
        self.assertTrue(any(item["actor_id"] == "client-1" and item["role"] == "client" for item in roster.json()))
        admit_professional(self.client, "professional-1", self.admin)

        engagement = self.post("/api/engagements", {"organization_id": org_id, "name": "Inventory modernization", "objective": "Reduce stockout investigation time"}, self.admin)
        project = self.post("/api/projects", {"engagement_id": engagement["id"], "name": "Synthetic delivery"}, self.admin)
        package = self.post("/api/work-packages", {"project_id": project["id"], "title": "Prepare diagnostic plan", "acceptance_criteria": ["Plan is reviewed", "Steps are bounded"]}, self.admin)
        dependent = self.post("/api/work-packages", {"project_id": project["id"], "title": "Validate delivery", "acceptance_criteria": ["Validation complete"], "depends_on": [package["id"]]}, self.admin)
        self.assertEqual(dependent["depends_on"], [package["id"]])
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
        packages = self.client.get(f"/api/projects/{project['id']}/work-packages", headers=self.professional)
        self.assertEqual(packages.status_code, 200)
        self.assertEqual([p["id"] for p in packages.json()], [package["id"]])

        run = self.post("/api/ai-runs", {"work_package_id": package["id"], "specification": "Create a bounded implementation work breakdown for the approved inventory problem."}, self.admin)
        self.assertEqual(run["agent"], "synthetic-planner-v1")
        visible_run = self.client.get(f"/api/ai-runs/{run['id']}", headers=self.reviewer)
        self.assertEqual(visible_run.status_code, 200)
        self.assertEqual(visible_run.json()["artifact"]["status"], "pending_review")
        hidden_run = self.client.get(f"/api/ai-runs/{run['id']}", headers=self.client_user)
        self.assertEqual(hidden_run.status_code, 403)
        rejected_self = self.client.post(f"/api/ai-runs/{run['id']}/decision", json={"decision": "approved"}, headers=self.admin)
        self.assertEqual(rejected_self.status_code, 409)
        artifact = self.post(f"/api/ai-runs/{run['id']}/decision", {"decision": "approved", "comment": "Bounded plan is suitable for review."}, self.reviewer)
        self.assertEqual(artifact["status"], "approved")

        deliverable = self.post("/api/deliverables", {"work_package_id": package["id"], "title": "Reviewed plan", "content": "Synthetic plan content"}, self.professional)
        review = self.post(f"/api/deliverables/{deliverable['id']}/review", {"decision": "approved", "comment": "Evidence and acceptance criteria checked."}, self.reviewer)
        self.assertEqual(review["deliverable"]["status"], "approved")
        unauthorized_accept = self.client.post(f"/api/deliverables/{deliverable['id']}/accept", headers=self.admin)
        self.assertEqual(unauthorized_accept.status_code, 403)
        accepted = self.post(f"/api/deliverables/{deliverable['id']}/accept", {}, self.client_user)
        self.assertEqual(accepted["status"], "accepted")
        self.assertEqual(self.client.get(f"/api/engagements/{engagement['id']}/projects", headers=self.client_user).status_code, 200)
        self.assertEqual(len(self.client.get(f"/api/work-packages/{package['id']}/deliverables", headers=self.client_user).json()), 1)
        completed = self.post(f"/api/projects/{project['id']}/complete", {}, self.admin)
        self.assertEqual(completed["status"], "completed")
        path = f"/api/projects/{project['id']}"
        client_headers = self.client_user
        record = self.client.get(path + "/coordination", headers=client_headers).json()
        self.assertTrue(record["handover"]["versions"])
        self.assertTrue(all(row["version"] > 0 for row in record["handover"]["versions"]))
        response = self.client.post(path + "/requests", headers=client_headers, json={"subject": "Confirm reporting frequency"})
        self.assertEqual(response.status_code, 201)
        decision_path = path + "/requests/" + response.json()["id"] + "/decision"
        decision = {"decision": "approved", "rationale": "Included in the approved scope"}
        self.assertEqual(self.client.post(decision_path, headers=client_headers, json=decision).status_code, 403)
        self.assertEqual(self.client.post(decision_path, headers=self.admin, json=decision).status_code, 200)
        self.assertEqual(self.client.post(decision_path, headers=self.admin, json=decision).status_code, 409)
        updated = self.client.get(path + "/coordination", headers=client_headers).json()
        self.assertEqual(updated["requests"][0]["rationale"], decision["rationale"])
        self.assertEqual(updated["handover"], record["handover"])


        events = self.client.get("/api/audit", headers=self.admin).json()
        actions = {event["action"] for event in events}
        self.assertIn("ai_run.completed", actions)
        self.assertIn("deliverable.client_accepted", actions)
        self.assertIn("project.completed", actions)

    def test_admin_overview_is_role_scoped_and_uses_real_counts(self) -> None:
        organization = self.post("/api/organizations", {"name": "Mission Control client"}, self.admin)
        engagement = self.post("/api/engagements", {"organization_id": organization["id"], "name": "Mission Control engagement", "objective": "Validate operational reporting"}, self.admin)
        project = self.post("/api/projects", {"engagement_id": engagement["id"], "name": "Mission Control project"}, self.admin)
        self.post("/api/work-packages", {"project_id": project["id"], "title": "Bounded review package", "acceptance_criteria": ["Review complete"]}, self.admin)
        overview = self.client.get("/api/admin/overview", headers=self.admin)
        self.assertEqual(overview.status_code, 200)
        self.assertEqual(overview.json()["metrics"]["active_engagements"], 1)
        self.assertEqual(overview.json()["projects"][0]["organization_name"], "Mission Control client")
        self.assertEqual(self.client.get("/api/admin/overview", headers=self.professional).status_code, 403)

    def test_client_overview_is_safe_and_client_decisions_are_audited(self) -> None:
        organization = self.post("/api/organizations", {"name": "Client portal org"}, self.admin)
        org_id = organization["id"]
        self.post(f"/api/organizations/{org_id}/members", {"actor_id": "client-1", "role": "client"}, self.admin)
        self.post(f"/api/organizations/{org_id}/members", {"actor_id": "reviewer-1", "role": "reviewer"}, self.admin)
        self.post(f"/api/organizations/{org_id}/members", {"actor_id": "professional-1", "role": "professional"}, self.admin)
        admit_professional(self.client, "professional-1", self.admin)
        engagement = self.post("/api/engagements", {"organization_id": org_id, "name": "Client delivery", "objective": "Publish a reviewed outcome"}, self.admin)
        project = self.post("/api/projects", {"engagement_id": engagement["id"], "name": "Client portal project"}, self.admin)
        package = self.post("/api/work-packages", {"project_id": project["id"], "title": "Reviewed handoff", "acceptance_criteria": ["Client can verify the outcome"]}, self.admin)
        invite = self.post(f"/api/work-packages/{package['id']}/assignments", {"professional_id": "professional-1"}, self.admin)
        self.post(f"/api/assignments/{invite['id']}/accept", {}, self.professional)
        deliverable = self.post("/api/deliverables", {"work_package_id": package["id"], "title": "Outcome summary", "content": "Synthetic verified outcome"}, self.professional)
        self.post(f"/api/deliverables/{deliverable['id']}/review", {"decision": "approved", "comment": "Independent review complete"}, self.reviewer)
        overview = self.client.get("/api/client/overview", headers=self.client_user)
        self.assertEqual(overview.status_code, 200)
        payload = overview.json()
        self.assertEqual(payload["projects"][0]["name"], "Client portal project")
        self.assertEqual(payload["metrics"]["deliverables_for_review"], 1)
        self.assertNotIn("submitted_by", payload["deliverables"][0])
        revision = self.client.post(f"/api/deliverables/{deliverable['id']}/client-revision", json={"comment": "Please clarify the measurement period."}, headers=self.client_user)
        self.assertEqual(revision.status_code, 200)
        self.assertEqual(revision.json()["deliverable"]["status"], "revision_requested")
        self.assertEqual(self.client.get("/api/client/overview", headers=auth("client-2", "client")).status_code, 403)
        actions = {event["action"] for event in self.client.get("/api/audit", headers=self.admin).json()}
        self.assertIn("deliverable.client_revision_requested", actions)

    def test_project_operations_are_scoped_and_audited(self) -> None:
        organization = self.post("/api/organizations", {"name": "Operations workspace"}, self.admin)
        org_id = organization["id"]
        for actor_id, role in (("client-1", "client"), ("professional-1", "professional"), ("reviewer-1", "reviewer")):
            self.post(f"/api/organizations/{org_id}/members", {"actor_id": actor_id, "role": role}, self.admin)
        admit_professional(self.client, "professional-1", self.admin)
        engagement = self.post("/api/engagements", {"organization_id": org_id, "name": "Operations engagement", "objective": "Test scoped collaboration"}, self.admin)
        project = self.post("/api/projects", {"engagement_id": engagement["id"], "name": "Operations project"}, self.admin)
        package = self.post("/api/work-packages", {"project_id": project["id"], "title": "Operations package", "acceptance_criteria": ["Messages are scoped"]}, self.admin)
        invitation = self.post(f"/api/work-packages/{package['id']}/assignments", {"professional_id": "professional-1"}, self.admin)
        self.post(f"/api/assignments/{invitation['id']}/accept", {}, self.professional)

        document = self.post(
            f"/api/projects/{project['id']}/documents",
            {"name": "Approved brief", "description": "Synthetic project brief", "classification": "project", "storage_reference": "blob://private/project/brief-v1"},
            self.admin,
        )
        self.assertNotIn("storage_reference", self.client.get(f"/api/projects/{project['id']}/documents", headers=self.client_user).json()[0])
        self.assertEqual(document["classification"], "project")
        sent = self.post(f"/api/projects/{project['id']}/messages", {"body": "Please confirm the delivery window.", "recipient_group": "internal"}, self.client_user)
        self.assertEqual(sent["sender_id"], "client-1")
        reply = self.post(f"/api/projects/{project['id']}/messages", {"body": "The synthetic window is confirmed.", "recipient_group": "client"}, self.admin)
        self.assertEqual(reply["recipient_group"], "client")
        self.assertEqual(len(self.client.get(f"/api/projects/{project['id']}/messages", headers=self.client_user).json()), 2)
        self.assertEqual(self.client.post(f"/api/projects/{project['id']}/messages", json={"body": "Cannot contact a professional directly.", "recipient_group": "professional"}, headers=self.client_user).status_code, 403)
        self.assertTrue(self.client.get("/api/notifications", headers=self.client_user).json())
        activity = self.client.get(f"/api/projects/{project['id']}/activity", headers=self.client_user)
        self.assertEqual(activity.status_code, 200)
        self.assertEqual([event["action"] for event in activity.json()], ["project.created"])
        self.assertEqual(set(activity.json()[0]), {"action", "created_at"})

        other = self.post("/api/organizations", {"name": "Other operations workspace"}, self.admin)
        self.post(f"/api/organizations/{other['id']}/members", {"actor_id": "client-2", "role": "client"}, self.admin)
        self.assertEqual(self.client.get(f"/api/projects/{project['id']}/messages", headers=auth("client-2", "client")).status_code, 403)
        self.assertEqual(self.client.get(f"/api/projects/{project['id']}/documents", headers=auth("client-2", "client")).status_code, 403)

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
        visible_orgs = self.client.get("/api/organizations", headers=auth("client-1", "client"))
        self.assertEqual(visible_orgs.status_code, 200)
        self.assertEqual([item["id"] for item in visible_orgs.json()], [first["id"]])
        self.assertEqual(self.client.get(f"/api/organizations/{first['id']}/members", headers=auth("client-1", "client")).status_code, 403)
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
        self.assertEqual(decision.status_code, 410)

    def test_admission_queue_is_admin_and_reviewer_only_and_tracks_decisions(self) -> None:
        submitted = self.client.post("/api/professionals/professional-1/application", headers=self.professional)
        self.assertEqual(submitted.status_code, 201)
        pending = self.client.get("/api/professionals/admissions?status_filter=submitted", headers=self.admin)
        self.assertEqual(pending.status_code, 200)
        self.assertEqual(pending.json()[0]["professional_id"], "professional-1")
        reviewer_view = self.client.get("/api/professionals/admissions?status_filter=submitted", headers=self.reviewer)
        self.assertEqual(reviewer_view.status_code, 200)
        self.assertEqual(reviewer_view.json()[0]["professional_id"], "professional-1")
        reviewer_application = self.client.get("/api/professionals/professional-1/application", headers=self.reviewer)
        self.assertEqual(reviewer_application.status_code, 200)
        self.assertEqual(reviewer_application.json()["professional_id"], "professional-1")
        self.assertEqual(self.client.get("/api/professionals/professional-1/application", headers=self.client_user).status_code, 403)
        self.assertEqual(self.client.get("/api/professionals/admissions", headers=self.professional).status_code, 403)
        self.assertEqual(self.client.get("/api/professionals/admissions", headers=self.client_user).status_code, 403)
        admit_professional(self.client, "professional-1", self.admin)
        approved = self.client.get("/api/professionals/admissions?status_filter=approved", headers=self.admin)
        self.assertEqual(approved.status_code, 200)
        self.assertEqual(approved.json()[0]["status"], "approved")

    def test_professional_profile_is_editable_without_granting_admission(self) -> None:
        submitted = self.client.post("/api/professionals/professional-1/application", headers=self.professional)
        self.assertEqual(submitted.status_code, 201)
        profile = {
            "display_name": "Alex Johnson",
            "headline": "Operations automation specialist",
            "bio": "I help teams turn reliable process evidence into maintainable automation.",
            "skills": ["Python", "Data quality"],
            "specializations": ["Operations analytics"],
            "education": [{"school": "Synthetic University", "degree": "BSc", "field": "Systems"}],
            "experience": [{"title": "Automation lead", "company": "Synthetic Co", "start": "2022", "end": "Present"}],
            "portfolio": [{"title": "Inventory workflow", "url": "https://example.test/portfolio/inventory"}],
            "availability": "Available for scoped work",
        }
        saved = self.client.put("/api/professionals/professional-1/profile", headers=self.professional, json=profile)
        self.assertEqual(saved.status_code, 200, saved.text)
        self.assertEqual(saved.json()["version"], 1)
        self.assertEqual(saved.json()["application_status"], "submitted")
        loaded = self.client.get("/api/professionals/professional-1/profile", headers=self.professional)
        self.assertEqual(loaded.status_code, 200)
        self.assertEqual(loaded.json()["skills"], ["Python", "Data quality"])
        self.assertEqual(self.client.get("/api/professionals/professional-1/profile", headers=self.client_user).status_code, 403)
        stale = self.client.put("/api/professionals/professional-1/profile", headers=self.professional, json={**profile, "expected_version": 99})
        self.assertEqual(stale.status_code, 409)
        self.assertEqual(self.client.get("/api/professionals/admissions?status_filter=submitted", headers=self.admin).json()[0]["status"], "submitted")
        self.assertIn("professional_profile.updated", {event["action"] for event in self.client.get("/api/audit", headers=self.admin).json()})
        admit_professional(self.client, "professional-1", self.admin)
        self.assertEqual(self.client.get("/api/professionals/professional-1/profile", headers=self.professional).json()["application_status"], "approved")

    def test_admission_review_is_independent_from_profile_completeness_and_audited(self) -> None:
        self.client.post("/api/professionals/professional-1/application", headers=self.professional)
        profile = {"display_name": "Alex Johnson", "headline": "Automation specialist", "bio": "Synthetic biography", "skills": ["Python"], "specializations": ["Operations"], "education": [], "experience": [], "portfolio": [], "availability": "Available"}
        self.assertEqual(self.client.put("/api/professionals/professional-1/profile", headers=self.professional, json=profile).status_code, 200)
        review = self.client.post("/api/professionals/professional-1/review", headers=self.admin, json={"status": "under_review", "next_action": "Provide one assessment example"})
        self.assertEqual(review.status_code, 200)
        self.assertEqual(review.json()["status"], "under_review")
        assessment = self.client.post("/api/professionals/professional-1/review", headers=auth("reviewer-1", "reviewer"), json={"status": "assessment", "assessment_requests": [{"title": "Synthetic assessment", "description": "Submit a short example"}], "next_action": "Complete assessment"})
        self.assertEqual(assessment.status_code, 200)
        approved = self.client.post("/api/professionals/professional-1/review", headers=auth("reviewer-1", "reviewer"), json={"status": "approved", "reason": "Evidence reviewed by an independent reviewer"})
        self.assertEqual(approved.status_code, 409)
        approved = admit_professional(self.client, "professional-1", self.reviewer)
        self.assertEqual(approved.json()["status"], "approved")
        self.assertIn("professional.admission_approved", {event["action"] for event in self.client.get("/api/audit", headers=self.admin).json()})

    def test_public_evidence_references_are_rejected(self) -> None:
        self.client.post("/api/professionals/professional-1/application", headers=self.professional)
        payload = {"display_name": "Alex Johnson", "headline": "Automation specialist", "bio": "Synthetic biography", "evidence_references": [{"label": "CV", "reference": "https://example.test/cv.pdf"}]}
        response = self.client.put("/api/professionals/professional-1/profile", headers=self.professional, json=payload)
        self.assertEqual(response.status_code, 422)
        payload["evidence_references"][0]["reference"] = "quarantine://synthetic/profile/cv.pdf"
        self.assertEqual(self.client.put("/api/professionals/professional-1/profile", headers=self.professional, json=payload).status_code, 200)

    def test_opportunity_board_requires_approval_and_preserves_interest_review(self) -> None:
        blocked = self.client.get("/api/opportunities", headers=self.professional)
        self.assertEqual(blocked.status_code, 403)
        published = self.post(
            "/api/opportunities",
            {
                "title": "Synthetic reporting opportunity",
                "summary": "Build a bounded reporting workflow.",
                "specialization": "Data & automation",
                "skills": ["Python", "Quality review"],
                "compensation": None,
                "deadline": None,
            },
            self.admin,
        )
        self.post("/api/professionals/professional-1/application", {}, self.professional)
        admit_professional(self.client, "professional-1", self.admin)
        visible = self.client.get("/api/opportunities", headers=self.professional)
        self.assertEqual(visible.status_code, 200)
        self.assertEqual(visible.json()[0]["id"], published["id"])
        interest = self.post(
            f"/api/opportunities/{published['id']}/interests",
            {"approach": "Synthetic delivery experience and independent QA."},
            self.professional,
        )
        self.assertEqual(interest["status"], "interested")
        self.assertEqual(self.client.get("/api/opportunities/interests", headers=self.professional).status_code, 403)
        reviewed = self.post(f"/api/opportunity-interests/{interest['id']}/selected", {}, self.admin)
        self.assertEqual(reviewed["status"], "selected")
        self.assertEqual(self.client.get("/api/opportunities", headers=self.client_user).status_code, 403)

    def test_revision_requested_creates_immutable_successor(self) -> None:
        organization = self.post("/api/organizations", {"name": "Revision test org"}, self.admin)
        org_id = organization["id"]
        for actor_id, role in (("reviewer-1", "reviewer"), ("professional-1", "professional")):
            self.post(f"/api/organizations/{org_id}/members", {"actor_id": actor_id, "role": role}, self.admin)
        admit_professional(self.client, "professional-1", self.admin)
        engagement = self.post("/api/engagements", {"organization_id": org_id, "name": "Revision engagement", "objective": "Verify successors"}, self.admin)
        project = self.post("/api/projects", {"engagement_id": engagement["id"], "name": "Revision project"}, self.admin)
        package = self.post("/api/work-packages", {"project_id": project["id"], "title": "Revision package", "acceptance_criteria": ["review"]}, self.admin)
        invitation = self.post(f"/api/work-packages/{package['id']}/assignments", {"professional_id": "professional-1"}, self.admin)
        self.post(f"/api/assignments/{invitation['id']}/accept", {}, self.professional)
        first = self.post("/api/deliverables", {"work_package_id": package["id"], "title": "First version", "content": "Initial synthetic content"}, self.professional)
        revised = self.client.post(f"/api/deliverables/{first['id']}/review", headers=self.reviewer, json={"decision": "revision_requested", "comment": "Add validation notes"})
        self.assertEqual(revised.status_code, 200)
        second = self.post("/api/deliverables", {"work_package_id": package["id"], "title": "Second version", "content": "Revised synthetic content"}, self.professional)
        self.assertEqual(second["version"], 2)
        blocked = self.client.post("/api/deliverables", headers=self.professional, json={"work_package_id": package["id"], "title": "Third version", "content": "Should be blocked while under review"})
        self.assertEqual(blocked.status_code, 409)

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

    def test_readiness_allows_local_synthetic_development(self) -> None:
        with patch.dict(os.environ, {"STUDIO_ENV": "development", "STUDIO_TEST_MODE": "true", "STUDIO_PERSISTENCE": "memory"}):
            response = self.client.get("/ready")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ready")

    def test_readiness_rejects_synthetic_identity_in_staging(self) -> None:
        with patch.dict(os.environ, {"STUDIO_ENV": "staging", "STUDIO_TEST_MODE": "true", "STUDIO_PERSISTENCE": "postgres"}, clear=False):
            response = self.client.get("/ready")
        self.assertEqual(response.status_code, 503)
        self.assertFalse(response.json()["detail"]["checks"]["test_identity_disabled_for_staging"])

    def test_readiness_accepts_configured_staging_boundaries(self) -> None:
        with patch.dict(
            os.environ,
            {
                "STUDIO_ENV": "staging",
                "STUDIO_TEST_MODE": "false",
                "STUDIO_ENTRA_ENABLED": "true",
                "STUDIO_ENTRA_TENANT_ID": "synthetic-tenant",
                "STUDIO_ENTRA_AUDIENCE": "api://studio",
                "STUDIO_ENTRA_WEB_CLIENT_ID": "synthetic-web",
                "STUDIO_PERSISTENCE": "postgres",
                "STUDIO_DATABASE_URL": "postgresql://placeholder",
            },
            clear=False,
        ), patch.object(app_module, "postgres_repository") as repository:
            repository.return_value.schema_current.return_value = True
            response = self.client.get("/ready")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["persistence"], "postgres")

    def test_localhost_and_loopback_frontend_origins_support_preflight(self) -> None:
        response = self.client.options(
            "/api/organizations",
            headers={"Origin": "http://127.0.0.1:5173", "Access-Control-Request-Method": "POST"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("access-control-allow-origin"), "http://127.0.0.1:5173")

    def test_extra_allowed_origins_are_additive_to_the_fixed_local_defaults(self) -> None:
        with patch.dict(os.environ, {"STUDIO_EXTRA_ALLOWED_ORIGINS": "https://studio.datafellowsai.com, https://preview.vercel.app"}):
            origins = app_module._allowed_frontend_origins()
        self.assertIn("http://localhost:5173", origins)
        self.assertIn("https://studio.datafellowsai.com", origins)
        self.assertIn("https://preview.vercel.app", origins)

    def test_extra_allowed_origins_defaults_to_just_the_fixed_local_origins(self) -> None:
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("STUDIO_EXTRA_ALLOWED_ORIGINS", None)
            origins = app_module._allowed_frontend_origins()
        self.assertEqual(origins, ["http://localhost:5173", "http://localhost:8100", "http://127.0.0.1:5173", "http://127.0.0.1:8100"])

    def test_platform_session_writes_require_the_exact_origin(self):
        from unittest.mock import Mock
        validator = Mock()
        validator.validate.return_value = Principal("staff", "test", frozenset({"admin"}), {})
        settings = {"STUDIO_TEST_MODE": "false", "STUDIO_ENTRA_ENABLED": "true", "STUDIO_PLATFORM_AUTH": "easy-auth",
                    "STUDIO_PUBLIC_ORIGIN": "https://studio.example"}
        headers = {"x-ms-token-aad-access-token": "local-fixture"}
        with patch.dict(os.environ, settings), patch.object(app_module, "entra_validator", return_value=validator):
            for origin in ("", "https://other.example"):
                response = self.client.post("/api/organizations", headers={**headers, "origin": origin}, json={"name": "Sample"})
                self.assertEqual(response.status_code, 403)
            response = self.client.post("/api/organizations", headers={**headers, "origin": settings["STUDIO_PUBLIC_ORIGIN"]}, json={"name": "Sample"})
            self.assertEqual(response.status_code, 201)
            validator.validate.assert_called_once()

    def test_entra_enabled_requests_use_validator_boundary(self) -> None:
        class FakeValidator:
            def validate(self, token: str) -> Principal:
                if token != "synthetic-signed-token":
                    raise TokenValidationError("invalid token")
                return Principal("entra-staff-1", "synthetic-tenant", frozenset({"admin"}), {})

        os.environ["STUDIO_TEST_MODE"] = "false"
        os.environ["STUDIO_ENTRA_ENABLED"] = "true"
        try:
            with patch.object(app_module, "entra_validator", return_value=FakeValidator()):
                valid = self.client.get("/api/me", headers={"Authorization": "Bearer synthetic-signed-token"})
                invalid = self.client.get("/api/me", headers={"Authorization": "Bearer invalid"})
            self.assertEqual(valid.status_code, 200)
            self.assertEqual(valid.json()["id"], "entra-staff-1")
            self.assertEqual(invalid.status_code, 401)
        finally:
            os.environ["STUDIO_TEST_MODE"] = "true"
            os.environ.pop("STUDIO_ENTRA_ENABLED", None)


if __name__ == "__main__":
    unittest.main()
