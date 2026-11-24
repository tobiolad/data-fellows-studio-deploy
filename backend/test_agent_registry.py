import os
import unittest

from fastapi.testclient import TestClient

import backend.app as app_module
from backend.app import app, store


def auth(actor: str, role: str) -> dict[str, str]:
    return {"Authorization": f"Bearer test:{actor}:{role}"}


SYNTHETIC_AGENT = "00000000-0000-0000-0000-000000000001"


@unittest.skipUnless(os.getenv("STUDIO_TEST_DATABASE_URL"), "Set STUDIO_TEST_DATABASE_URL for PostgreSQL API tests")
class AgentRegistryIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        store.reset()
        os.environ["STUDIO_TEST_MODE"] = "true"
        os.environ["STUDIO_PERSISTENCE"] = "postgres"
        os.environ["STUDIO_DATABASE_URL"] = os.environ["STUDIO_TEST_DATABASE_URL"]
        os.environ.pop("STUDIO_AI_REAL_PROVIDER_APPROVED", None)
        app_module.postgres_repository.cache_clear()
        app_module.postgres_repository().migrate()
        self.client = TestClient(app)
        self.admin = auth("registry-admin", "admin")
        self.reviewer = auth("registry-reviewer", "reviewer")
        self.client_user = auth("registry-client", "client")

    def tearDown(self) -> None:
        os.environ.pop("STUDIO_PERSISTENCE", None)
        os.environ.pop("STUDIO_DATABASE_URL", None)
        os.environ.pop("STUDIO_AI_REAL_PROVIDER_APPROVED", None)
        app_module.postgres_repository.cache_clear()

    def make_package(self):
        org = self.client.post("/api/organizations", headers=self.admin, json={"name": "Agent registry client"}).json()
        engagement = self.client.post(
            "/api/engagements", headers=self.admin,
            json={"organization_id": org["id"], "name": "Agent engagement", "objective": "Exercise the agent registry"},
        ).json()
        project = self.client.post("/api/projects", headers=self.admin, json={"engagement_id": engagement["id"], "name": "Agent project"}).json()
        return self.client.post(
            "/api/work-packages", headers=self.admin,
            json={"project_id": project["id"], "title": "Bounded planning package", "acceptance_criteria": ["Plan is reviewed"]},
        ).json()

    def test_seeded_synthetic_agent_is_listed(self):
        response = self.client.get("/api/ai-agents", headers=self.admin)
        self.assertEqual(response.status_code, 200)
        names = {item["name"] for item in response.json()}
        self.assertIn("synthetic-planner-v1", names)

    def test_only_admin_may_register_an_agent(self):
        payload = {
            "name": "research-assistant-v1", "purpose": "Summarize public market research for diagnostics.",
            "capability_category": "research", "provider": "synthetic", "model": "planner", "model_version": "planning-only-v1",
            "allowed_tools": ["planning"], "data_access_scope": "work_package", "autonomy_level": "supervised",
            "requires_human_approval": True, "budget_cap_cents": 500, "owner_actor_id": "ops-owner",
        }
        denied = self.client.post("/api/ai-agents", headers=self.reviewer, json=payload)
        self.assertEqual(denied.status_code, 403)
        created = self.client.post("/api/ai-agents", headers=self.admin, json=payload)
        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.json()["status"], "active")
        listing = self.client.get("/api/ai-agents", headers=self.reviewer)
        self.assertEqual(listing.status_code, 200)
        self.assertIn("research-assistant-v1", {item["name"] for item in listing.json()})
        self.assertEqual(self.client.get("/api/ai-agents", headers=self.client_user).status_code, 403)

    def test_run_without_agent_id_resolves_to_seeded_synthetic_agent(self):
        package = self.make_package()
        run = self.client.post(
            "/api/ai-runs", headers=self.admin,
            json={"work_package_id": package["id"], "specification": "Prepare a bounded synthetic plan for the approved package."},
        )
        self.assertEqual(run.status_code, 201)
        body = run.json()
        self.assertEqual(body["agent"], "synthetic-planner-v1")
        self.assertEqual(body["agent_id"], SYNTHETIC_AGENT)
        self.assertEqual(body["provider"], "synthetic")
        self.assertEqual(body["model"], "planner")

    def test_run_rejects_budget_above_agent_cap(self):
        package = self.make_package()
        payload = {
            "name": "tight-budget-planner", "purpose": "Exercise the per-agent budget cap.",
            "capability_category": "planning", "provider": "synthetic", "model": "planner", "model_version": "planning-only-v1",
            "allowed_tools": ["planning"], "data_access_scope": "work_package", "autonomy_level": "supervised",
            "requires_human_approval": True, "budget_cap_cents": 50, "owner_actor_id": "ops-owner",
        }
        agent = self.client.post("/api/ai-agents", headers=self.admin, json=payload).json()
        over_budget = self.client.post(
            "/api/ai-runs", headers=self.admin,
            json={"work_package_id": package["id"], "specification": "Prepare a bounded synthetic plan for the approved package.",
                  "agent_id": agent["id"], "budget_cents": 100},
        )
        self.assertEqual(over_budget.status_code, 422)
        within_budget = self.client.post(
            "/api/ai-runs", headers=self.admin,
            json={"work_package_id": package["id"], "specification": "Prepare a bounded synthetic plan for the approved package.",
                  "agent_id": agent["id"], "budget_cents": 50},
        )
        self.assertEqual(within_budget.status_code, 201)

    def test_run_against_unknown_agent_is_rejected(self):
        package = self.make_package()
        response = self.client.post(
            "/api/ai-runs", headers=self.admin,
            json={"work_package_id": package["id"], "specification": "Prepare a bounded synthetic plan for the approved package.",
                  "agent_id": "00000000-0000-0000-0000-00000000dead"},
        )
        self.assertEqual(response.status_code, 404)

    def test_run_against_unapproved_real_provider_is_refused(self):
        package = self.make_package()
        payload = {
            "name": "frontier-research-v1", "purpose": "Would call a real model provider once approved.",
            "capability_category": "research", "provider": "openai", "model": "gpt-test", "model_version": "v1",
            "allowed_tools": ["planning"], "data_access_scope": "work_package", "autonomy_level": "supervised",
            "requires_human_approval": True, "budget_cap_cents": 500, "owner_actor_id": "ops-owner",
        }
        agent = self.client.post("/api/ai-agents", headers=self.admin, json=payload).json()
        self.assertNotIn("STUDIO_AI_REAL_PROVIDER_APPROVED", os.environ)
        response = self.client.post(
            "/api/ai-runs", headers=self.admin,
            json={"work_package_id": package["id"], "specification": "Prepare a bounded synthetic plan for the approved package.",
                  "agent_id": agent["id"]},
        )
        self.assertEqual(response.status_code, 409)
        self.assertIn("not approved", response.json()["detail"])
