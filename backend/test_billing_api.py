import hashlib
import hmac
import json
import os
import time
import unittest
from unittest.mock import patch
from uuid import uuid4

from fastapi.testclient import TestClient

import backend.app as app_module
from backend.app import app, store


def auth(actor: str, role: str) -> dict[str, str]:
    return {"Authorization": f"Bearer test:{actor}:{role}"}


class _FakeStripeClient:
    def __init__(self, settings):
        self.created_customers: list[dict] = []
        self.created_invoices: list[dict] = []
        self.sent_invoices: list[str] = []
        self.voided_invoices: list[str] = []
        self.deleted_invoices: list[str] = []

    def _next(self, prefix: str) -> str:
        # Globally unique (not a per-instance counter): the integration database
        # persists rows across test methods within one pytest run, and
        # stripe_customer_id/stripe_invoice_id both carry a UNIQUE constraint.
        return f"{prefix}_{uuid4().hex[:12]}"

    def create_customer(self, email, name):
        customer_id = self._next("cus")
        self.created_customers.append({"email": email, "name": name, "id": customer_id})
        return {"id": customer_id, "email": email}

    def create_invoice(self, customer_id, currency, days_until_due=14):
        invoice_id = self._next("in")
        self.created_invoices.append({"customer": customer_id, "currency": currency, "id": invoice_id})
        return {"id": invoice_id, "status": "draft"}

    def add_invoice_item(self, customer_id, invoice_id, amount_cents, currency, description):
        return {"id": self._next("ii"), "invoice": invoice_id, "amount": amount_cents}

    def finalize_invoice(self, invoice_id):
        return {"id": invoice_id, "status": "open"}

    def send_invoice(self, invoice_id):
        self.sent_invoices.append(invoice_id)
        return {"id": invoice_id, "status": "open", "hosted_invoice_url": f"https://invoice.stripe.com/i/{invoice_id}"}

    def void_invoice(self, invoice_id):
        self.voided_invoices.append(invoice_id)
        return {"id": invoice_id, "status": "void"}

    def delete_draft_invoice(self, invoice_id):
        self.deleted_invoices.append(invoice_id)
        return {"deleted": True}


@unittest.skipUnless(os.getenv("STUDIO_TEST_DATABASE_URL"), "Set STUDIO_TEST_DATABASE_URL for PostgreSQL API tests")
class BillingIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        store.reset()
        os.environ["STUDIO_TEST_MODE"] = "true"
        os.environ["STUDIO_PERSISTENCE"] = "postgres"
        os.environ["STUDIO_DATABASE_URL"] = os.environ["STUDIO_TEST_DATABASE_URL"]
        os.environ["STUDIO_BILLING_ENABLED"] = "true"
        os.environ["STRIPE_SECRET_KEY"] = "rk_test_fake"
        os.environ["STRIPE_WEBHOOK_SECRET"] = "whsec_test_fake"
        app_module.postgres_repository.cache_clear()
        app_module.stripe_billing_client.cache_clear()
        app_module.postgres_repository().migrate()
        self.client = TestClient(app)
        self.admin = auth("billing-admin", "admin")
        self.fake_stripe_patch = patch("backend.app.StripeBillingClient", _FakeStripeClient)
        self.fake_stripe_patch.start()
        self.addCleanup(self.fake_stripe_patch.stop)

    def tearDown(self) -> None:
        for key in ["STUDIO_PERSISTENCE", "STUDIO_DATABASE_URL", "STUDIO_BILLING_ENABLED", "STRIPE_SECRET_KEY", "STRIPE_WEBHOOK_SECRET"]:
            os.environ.pop(key, None)
        app_module.postgres_repository.cache_clear()
        app_module.stripe_billing_client.cache_clear()

    def _create_org(self) -> str:
        response = self.client.post("/api/organizations", headers=self.admin, json={"name": "Acme Logistics"})
        self.assertEqual(response.status_code, 201)
        return response.json()["id"]

    def test_creating_an_invoice_for_a_new_organization_requires_a_billing_email_and_name(self):
        org_id = self._create_org()
        response = self.client.post(
            f"/api/organizations/{org_id}/invoices",
            headers=self.admin,
            json={"description": "Q1 engagement", "amount_cents": 150000, "currency": "usd"},
        )
        self.assertEqual(response.status_code, 422)

    def test_creating_sending_and_reading_back_an_invoice(self):
        org_id = self._create_org()
        created = self.client.post(
            f"/api/organizations/{org_id}/invoices",
            headers=self.admin,
            json={"description": "Q1 engagement", "amount_cents": 150000, "currency": "usd",
                  "billing_email": "finance@acme.test", "billing_name": "Acme Logistics"},
        )
        self.assertEqual(created.status_code, 201)
        body = created.json()
        self.assertEqual(body["status"], "draft")
        self.assertIsNone(body["hosted_invoice_url"])
        invoice_id = body["id"]

        # A second invoice for the same organization reuses the Stripe customer already on file.
        second = self.client.post(
            f"/api/organizations/{org_id}/invoices",
            headers=self.admin,
            json={"description": "Q2 engagement", "amount_cents": 90000, "currency": "usd"},
        )
        self.assertEqual(second.status_code, 201)

        listed = self.client.get(f"/api/organizations/{org_id}/invoices", headers=self.admin)
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(len(listed.json()), 2)

        sent = self.client.post(f"/api/invoices/{invoice_id}/send", headers=self.admin)
        self.assertEqual(sent.status_code, 200)
        self.assertEqual(sent.json()["status"], "open")
        self.assertTrue(sent.json()["hosted_invoice_url"].startswith("https://invoice.stripe.com/"))

        fetched = self.client.get(f"/api/invoices/{invoice_id}", headers=self.admin)
        self.assertEqual(fetched.status_code, 200)
        self.assertEqual(fetched.json()["status"], "open")

        # Sending an already-sent invoice again is refused, not silently repeated.
        resent = self.client.post(f"/api/invoices/{invoice_id}/send", headers=self.admin)
        self.assertEqual(resent.status_code, 409)

    def test_a_client_may_read_only_their_own_organizations_invoices(self):
        org_id = self._create_org()
        other_org_id = self._create_org()
        created = self.client.post(
            f"/api/organizations/{org_id}/invoices", headers=self.admin,
            json={"description": "Q1", "amount_cents": 50000, "currency": "usd", "billing_email": "a@b.test", "billing_name": "Acme"},
        )
        self.client.post(f"/api/invoices/{created.json()['id']}/send", headers=self.admin).raise_for_status()
        self.client.post(
            f"/api/organizations/{org_id}/members", headers=self.admin,
            json={"actor_id": "billing-client", "role": "client"},
        ).raise_for_status()

        client_header = auth("billing-client", "client")
        own = self.client.get(f"/api/organizations/{org_id}/invoices", headers=client_header)
        self.assertEqual(own.status_code, 200)
        self.assertEqual(len(own.json()), 1)

        other = self.client.get(f"/api/organizations/{other_org_id}/invoices", headers=client_header)
        self.assertEqual(other.status_code, 403)

    def test_a_client_never_sees_a_draft_invoice_not_yet_sent(self):
        org_id = self._create_org()
        draft = self.client.post(
            f"/api/organizations/{org_id}/invoices", headers=self.admin,
            json={"description": "Unfinished", "amount_cents": 50000, "currency": "usd", "billing_email": "a@b.test", "billing_name": "Acme"},
        )
        invoice_id = draft.json()["id"]
        self.client.post(
            f"/api/organizations/{org_id}/members", headers=self.admin,
            json={"actor_id": "billing-client-3", "role": "client"},
        ).raise_for_status()
        client_header = auth("billing-client-3", "client")

        listed = self.client.get(f"/api/organizations/{org_id}/invoices", headers=client_header)
        self.assertEqual(listed.json(), [])

        fetched = self.client.get(f"/api/invoices/{invoice_id}", headers=client_header)
        self.assertEqual(fetched.status_code, 404)

        # Still visible to admin.
        self.assertEqual(self.client.get(f"/api/invoices/{invoice_id}", headers=self.admin).status_code, 200)

    def test_a_non_admin_may_not_create_or_send_an_invoice(self):
        org_id = self._create_org()
        self.client.post(
            f"/api/organizations/{org_id}/members", headers=self.admin,
            json={"actor_id": "billing-client-2", "role": "client"},
        ).raise_for_status()
        client_header = auth("billing-client-2", "client")
        response = self.client.post(
            f"/api/organizations/{org_id}/invoices", headers=client_header,
            json={"description": "Q1", "amount_cents": 50000, "currency": "usd", "billing_email": "a@b.test", "billing_name": "Acme"},
        )
        self.assertEqual(response.status_code, 403)

    def test_billing_is_refused_while_switched_off(self):
        os.environ["STUDIO_BILLING_ENABLED"] = "false"
        org_id = self._create_org()
        response = self.client.post(
            f"/api/organizations/{org_id}/invoices", headers=self.admin,
            json={"description": "Q1", "amount_cents": 50000, "currency": "usd", "billing_email": "a@b.test", "billing_name": "Acme"},
        )
        self.assertEqual(response.status_code, 503)

    def test_discarding_a_draft_invoice_deletes_it(self):
        org_id = self._create_org()
        created = self.client.post(
            f"/api/organizations/{org_id}/invoices", headers=self.admin,
            json={"description": "Mistake", "amount_cents": 1000, "currency": "usd", "billing_email": "a@b.test", "billing_name": "Acme"},
        )
        invoice_id = created.json()["id"]
        discarded = self.client.post(f"/api/invoices/{invoice_id}/void", headers=self.admin)
        self.assertEqual(discarded.status_code, 200)
        self.assertEqual(discarded.json()["status"], "discarded")
        self.assertEqual(self.client.get(f"/api/invoices/{invoice_id}", headers=self.admin).status_code, 404)

    def test_voiding_a_sent_invoice(self):
        org_id = self._create_org()
        created = self.client.post(
            f"/api/organizations/{org_id}/invoices", headers=self.admin,
            json={"description": "Q1", "amount_cents": 1000, "currency": "usd", "billing_email": "a@b.test", "billing_name": "Acme"},
        )
        invoice_id = created.json()["id"]
        self.client.post(f"/api/invoices/{invoice_id}/send", headers=self.admin)
        voided = self.client.post(f"/api/invoices/{invoice_id}/void", headers=self.admin)
        self.assertEqual(voided.status_code, 200)
        self.assertEqual(voided.json()["status"], "void")
        # A second void of an already-void invoice is refused, not silently repeated.
        self.assertEqual(self.client.post(f"/api/invoices/{invoice_id}/void", headers=self.admin).status_code, 409)

    def _webhook_body(self, event_id: str, event_type: str, stripe_invoice_id: str) -> bytes:
        return json.dumps({"id": event_id, "type": event_type, "data": {"object": {"id": stripe_invoice_id}}}).encode("utf-8")

    def _sign(self, payload: bytes) -> str:
        timestamp = int(time.time())
        signed_payload = f"{timestamp}.".encode("utf-8") + payload
        signature = hmac.new(b"whsec_test_fake", signed_payload, hashlib.sha256).hexdigest()
        return f"t={timestamp},v1={signature}"

    def test_a_webhook_event_marks_the_matching_invoice_paid(self):
        org_id = self._create_org()
        created = self.client.post(
            f"/api/organizations/{org_id}/invoices", headers=self.admin,
            json={"description": "Q1", "amount_cents": 1000, "currency": "usd", "billing_email": "a@b.test", "billing_name": "Acme"},
        )
        invoice_id = created.json()["id"]
        self.client.post(f"/api/invoices/{invoice_id}/send", headers=self.admin)
        stripe_invoice_id = app_module.postgres_repository().get_invoice_for_actor(__import__("uuid").UUID(invoice_id), "billing-admin", True)["stripe_invoice_id"]

        payload = self._webhook_body("evt_1", "invoice.paid", stripe_invoice_id)
        response = self.client.post("/api/stripe/webhook", content=payload, headers={"stripe-signature": self._sign(payload)})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get(f"/api/invoices/{invoice_id}", headers=self.admin).json()["status"], "paid")

        # A redelivery of the same event id is acknowledged but changes nothing new.
        replay = self.client.post("/api/stripe/webhook", content=payload, headers={"stripe-signature": self._sign(payload)})
        self.assertEqual(replay.status_code, 200)
        self.assertTrue(replay.json()["deduplicated"])

    def test_a_webhook_with_a_bad_signature_is_refused(self):
        payload = self._webhook_body("evt_2", "invoice.paid", "in_does_not_matter")
        response = self.client.post("/api/stripe/webhook", content=payload, headers={"stripe-signature": "t=1,v1=wrong"})
        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
