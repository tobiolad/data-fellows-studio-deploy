import os
import unittest

from backend.review_fixture import assert_review_workflow
from backend.admission_fixture import admit_professional, assert_admission_gates

from fastapi.testclient import TestClient

import backend.app as app_module
from backend.app import app, store


def auth(actor: str, role: str) -> dict[str, str]:
    return {"Authorization": f"Bearer test:{actor}:{role}"}


@unittest.skipUnless(os.getenv("STUDIO_TEST_DATABASE_URL"), "Set STUDIO_TEST_DATABASE_URL for PostgreSQL API tests")
class PostgresApiIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        store.reset()
        os.environ["STUDIO_TEST_MODE"] = "true"
        os.environ["STUDIO_PERSISTENCE"] = "postgres"
        os.environ["STUDIO_DATABASE_URL"] = os.environ["STUDIO_TEST_DATABASE_URL"]
        app_module.postgres_repository.cache_clear()
        app_module.postgres_repository().migrate()
        self.client = TestClient(app)
        self.admin = auth("postgres-admin", "admin")

    def tearDown(self) -> None:
        os.environ.pop("STUDIO_PERSISTENCE", None)
        os.environ.pop("STUDIO_DATABASE_URL", None)
        app_module.postgres_repository.cache_clear()

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

    def test_core_organization_and_engagement_routes_use_postgres(self) -> None:
        organization = self.client.post("/api/organizations", headers=self.admin, json={"name": "Persistent synthetic org"})
        self.assertEqual(organization.status_code, 201)
        organization_id = organization.json()["id"]
        self.assertEqual(self.client.get("/api/organizations", headers=self.admin).status_code, 200)
        membership = self.client.post(
            f"/api/organizations/{organization_id}/members",
            headers=self.admin,
            json={"actor_id": "postgres-client", "role": "client"},
        )
        self.assertEqual(membership.status_code, 201)
        roster = self.client.get(f"/api/organizations/{organization_id}/members", headers=self.admin)
        self.assertEqual(roster.status_code, 200)
        self.assertTrue(any(item["actor_id"] == "postgres-client" for item in roster.json()))
        engagement = self.client.post(
            "/api/engagements",
            headers=self.admin,
            json={"organization_id": organization_id, "name": "Persistent engagement", "objective": "Verify database routing"},
        )
        self.assertEqual(engagement.status_code, 201)
        listed = self.client.get("/api/engagements", headers=auth("postgres-client", "client"))
        self.assertEqual(listed.status_code, 200)
        self.assertIn(engagement.json()["id"], {item["id"] for item in listed.json()})
        project = self.client.post("/api/projects", headers=self.admin, json={"engagement_id": engagement.json()["id"], "name": "Persistent project"})
        self.assertEqual(project.status_code, 201)
        self.assertEqual(self.client.get(f"/api/engagements/{engagement.json()['id']}/projects", headers=self.admin).status_code, 200)
        package = self.client.post(
            "/api/work-packages",
            headers=self.admin,
            json={"project_id": project.json()["id"], "title": "Persistent package", "acceptance_criteria": ["reviewed"]},
        )
        self.assertEqual(package.status_code, 201)
        dependent_package = self.client.post(
            "/api/work-packages",
            headers=self.admin,
            json={"project_id": project.json()["id"], "title": "Persistent dependent package", "acceptance_criteria": ["reviewed"], "depends_on": [package.json()["id"]]},
        )
        self.assertEqual(dependent_package.status_code, 201)
        self.assertEqual(self.client.get(f"/api/projects/{project.json()['id']}/work-packages", headers=self.admin).status_code, 200)
        professional = self.client.post(
            f"/api/organizations/{organization_id}/members",
            headers=self.admin,
            json={"actor_id": "postgres-professional", "role": "professional"},
        )
        self.assertEqual(professional.status_code, 201)
        reviewer = self.client.post(
            f"/api/organizations/{organization_id}/members",
            headers=self.admin,
            json={"actor_id": "postgres-reviewer", "role": "reviewer"},
        )
        self.assertEqual(reviewer.status_code, 201)
        client = self.client.post(
            f"/api/organizations/{organization_id}/members",
            headers=self.admin,
            json={"actor_id": "postgres-client-user", "role": "client"},
        )
        self.assertEqual(client.status_code, 201)
        approval = admit_professional(self.client, "postgres-professional", self.admin)
        self.assertEqual(approval.status_code, 200)
        admissions = self.client.get("/api/professionals/admissions?status_filter=approved", headers=self.admin)
        self.assertEqual(admissions.status_code, 200)
        self.assertTrue(any(item["professional_id"] == "postgres-professional" for item in admissions.json()))
        roster_entry = next(item for item in admissions.json() if item["professional_id"] == "postgres-professional")
        self.assertEqual(roster_entry["display_name"], "Synthetic applicant")
        reviewer_admissions = self.client.get("/api/professionals/admissions?status_filter=approved", headers=auth("postgres-reviewer", "reviewer"))
        self.assertEqual(reviewer_admissions.status_code, 200)
        self.assertTrue(any(item["professional_id"] == "postgres-professional" for item in reviewer_admissions.json()))
        self.assertEqual(
            self.client.post(
                "/api/professionals/postgres-professional/approve",
                headers=auth("postgres-professional", "professional"),
            ).status_code,
            403,
        )
        invitation = self.client.post(
            f"/api/work-packages/{package.json()['id']}/assignments",
            headers=self.admin,
            json={"professional_id": "postgres-professional"},
        )
        self.assertEqual(invitation.status_code, 201)
        accepted = self.client.post(
            f"/api/assignments/{invitation.json()['id']}/accept",
            headers=auth("postgres-professional", "professional"),
        )
        self.assertEqual(accepted.status_code, 200)
        listed_assignments = self.client.get(
            "/api/professionals/postgres-professional/assignments",
            headers=auth("postgres-professional", "professional"),
        )
        self.assertEqual(listed_assignments.status_code, 200)
        self.assertEqual(listed_assignments.json()[0]["status"], "accepted")
        run = self.client.post(
            "/api/ai-runs",
            headers=self.admin,
            json={"work_package_id": package.json()["id"], "specification": "Prepare a bounded synthetic plan for the approved work package."},
        )
        self.assertEqual(run.status_code, 201)
        visible_run = self.client.get(f"/api/ai-runs/{run.json()['id']}", headers=auth("postgres-reviewer", "reviewer"))
        self.assertEqual(visible_run.status_code, 200)
        self.assertEqual(visible_run.json()["artifact"]["status"], "pending_review")
        hidden_run = self.client.get(f"/api/ai-runs/{run.json()['id']}", headers=auth("postgres-client-user", "client"))
        self.assertEqual(hidden_run.status_code, 403)
        self.assertEqual(self.client.post(f"/api/ai-runs/{run.json()['id']}/decision", headers=self.admin, json={"decision": "approved"}).status_code, 409)
        decision = self.client.post(
            f"/api/ai-runs/{run.json()['id']}/decision",
            headers=auth("postgres-reviewer", "reviewer"),
            json={"decision": "approved", "comment": "Synthetic review complete"},
        )
        self.assertEqual(decision.status_code, 200)
        terminal_cancel = self.client.post(f"/api/ai-runs/{run.json()['id']}/cancel", headers=self.admin)
        self.assertEqual(terminal_cancel.status_code, 409)
        deliverable = self.client.post(
            "/api/deliverables",
            headers=auth("postgres-professional", "professional"),
            json={"work_package_id": package.json()["id"], "title": "Persistent deliverable", "content": "Synthetic deliverable content"},
        )
        self.assertEqual(deliverable.status_code, 201)
        review = self.client.post(
            f"/api/deliverables/{deliverable.json()['id']}/review",
            headers=auth("postgres-reviewer", "reviewer"),
            json={"decision": "approved", "comment": "Reviewed synthetic deliverable"},
        )
        self.assertEqual(review.status_code, 200)
        blocked_revision = self.client.post(
            "/api/deliverables",
            headers=auth("postgres-professional", "professional"),
            json={"work_package_id": package.json()["id"], "title": "Duplicate pending version", "content": "Should be blocked"},
        )
        self.assertEqual(blocked_revision.status_code, 409)
        accepted_deliverable = self.client.post(
            f"/api/deliverables/{deliverable.json()['id']}/accept",
            headers=auth("postgres-client-user", "client"),
        )
        self.assertEqual(accepted_deliverable.status_code, 200)
        visible_deliverables = self.client.get(
            f"/api/work-packages/{package.json()['id']}/deliverables",
            headers=auth("postgres-client-user", "client"),
        )
        self.assertEqual(visible_deliverables.status_code, 200)
        self.assertEqual(len(visible_deliverables.json()), 1)
        document = self.client.post(
            f"/api/projects/{project.json()['id']}/documents",
            headers=self.admin,
            json={"name": "Persistent brief", "description": "Synthetic project document", "classification": "project", "storage_reference": "blob://private/persistent/brief"},
        )
        self.assertEqual(document.status_code, 201)
        client_documents = self.client.get(f"/api/projects/{project.json()['id']}/documents", headers=auth("postgres-client-user", "client"))
        self.assertEqual(client_documents.status_code, 200)
        self.assertNotIn("storage_reference", client_documents.json()[0])
        client_message = self.client.post(
            f"/api/projects/{project.json()['id']}/messages",
            headers=auth("postgres-client-user", "client"),
            json={"body": "Please confirm the synthetic delivery window.", "recipient_group": "internal"},
        )
        self.assertEqual(client_message.status_code, 201)
        internal_message = self.client.post(
            f"/api/projects/{project.json()['id']}/messages",
            headers=self.admin,
            json={"body": "The synthetic delivery window is confirmed.", "recipient_group": "client"},
        )
        self.assertEqual(internal_message.status_code, 201)
        self.assertEqual(len(self.client.get(f"/api/projects/{project.json()['id']}/messages", headers=auth("postgres-client-user", "client")).json()), 2)
        self.assertTrue(self.client.get(f"/api/projects/{project.json()['id']}/activity", headers=auth("postgres-client-user", "client")).json())
        self.assertTrue(self.client.get("/api/notifications", headers=auth("postgres-client-user", "client")).json())
        completed = self.client.post(f"/api/projects/{project.json()['id']}/complete", headers=self.admin)
        self.assertEqual(completed.status_code, 200)
        path = f"/api/projects/{project.json()['id']}"
        client_headers = auth("postgres-client-user", "client")
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


    def test_professional_profile_persists_and_is_version_checked(self) -> None:
        application = self.client.post("/api/professionals/postgres-profile/application", headers=auth("postgres-profile", "professional"))
        self.assertEqual(application.status_code, 201)
        payload = {"display_name": "Persistent profile", "headline": "Synthetic analyst", "bio": "Profile evidence", "skills": ["SQL"], "specializations": ["Operations"], "education": [], "experience": [], "portfolio": [], "evidence_references": [{"label": "Synthetic CV", "reference": "quarantine://synthetic/profile/cv", "classification": "application"}], "availability": "Part time"}
        saved = self.client.put("/api/professionals/postgres-profile/profile", headers=auth("postgres-profile", "professional"), json=payload)
        self.assertEqual(saved.status_code, 200, saved.text)
        self.assertEqual(saved.json()["version"], 1)
        loaded = self.client.get("/api/professionals/postgres-profile/profile", headers=auth("postgres-profile", "professional"))
        self.assertEqual(loaded.status_code, 200)
        self.assertEqual(loaded.json()["display_name"], "Persistent profile")
        self.assertEqual(loaded.json()["evidence_references"][0]["reference"], "quarantine://synthetic/profile/cv")
        self.assertEqual(self.client.get("/api/professionals/postgres-profile/profile", headers=auth("postgres-other", "professional")).status_code, 403)
        stale = self.client.put("/api/professionals/postgres-profile/profile", headers=auth("postgres-profile", "professional"), json={**payload, "expected_version": 99})
        self.assertEqual(stale.status_code, 409)
        review = self.client.post("/api/professionals/postgres-profile/review", headers=auth("postgres-reviewer", "reviewer"), json={"status": "under_review", "next_action": "Review synthetic evidence"})
        self.assertEqual(review.status_code, 200)
        self.assertEqual(review.json()["status"], "under_review")

    def test_admin_may_preview_a_specific_organizations_client_overview(self):
        org = self.client.post("/api/organizations", headers=self.admin, json={"name": "Preview Target Co"}).json()
        org_id = org["id"]
        self.client.post(
            f"/api/organizations/{org_id}/members", headers=self.admin,
            json={"actor_id": "preview-client", "role": "client"},
        ).raise_for_status()

        preview = self.client.get(f"/api/client/overview?organization_id={org_id}", headers=self.admin)
        self.assertEqual(preview.status_code, 200)
        self.assertEqual(preview.json()["organizations"][0]["id"], org_id)

        # Only an admin may pass the override; a real client asking for someone
        # else's organization this way is refused, not silently ignored.
        as_client = self.client.get(f"/api/client/overview?organization_id={org_id}", headers=auth("preview-client", "client"))
        self.assertEqual(as_client.status_code, 403)

        missing = self.client.get("/api/client/overview?organization_id=00000000-0000-0000-0000-000000000000", headers=self.admin)
        self.assertEqual(missing.status_code, 404)

        # A real client's own (unscoped) call is unaffected by the override existing.
        own = self.client.get("/api/client/overview", headers=auth("preview-client", "client"))
        self.assertEqual(own.status_code, 200)
        self.assertEqual(own.json()["organizations"][0]["id"], org_id)


if __name__ == "__main__":
    unittest.main()
