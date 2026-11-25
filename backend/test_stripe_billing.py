import hashlib
import hmac
import json
import os
import time
import unittest
from unittest.mock import patch

from backend import stripe_billing


def _settings() -> stripe_billing.StripeBillingSettings:
    return stripe_billing.StripeBillingSettings(secret_key="rk_test_abc123")


class StripeBillingSettingsTests(unittest.TestCase):
    def test_requires_a_secret_key(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("STRIPE_SECRET_KEY", None)
            with self.assertRaises(stripe_billing.StripeBillingError):
                stripe_billing.StripeBillingSettings.from_environment()

    def test_reads_the_secret_key_from_the_environment(self):
        with patch.dict(os.environ, {"STRIPE_SECRET_KEY": "rk_test_xyz"}):
            settings = stripe_billing.StripeBillingSettings.from_environment()
            self.assertEqual(settings.secret_key, "rk_test_xyz")


class StripeBillingClientTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = stripe_billing.StripeBillingClient(_settings())

    def _stub(self, response: dict):
        return patch.object(self.client, "_send", return_value=response)

    def test_create_customer_posts_email_and_name(self):
        with self._stub({"id": "cus_123", "email": "finance@acme.test"}) as fake:
            result = self.client.create_customer("finance@acme.test", "Acme Logistics")
        self.assertEqual(result["id"], "cus_123")
        request = fake.call_args.args[0]
        self.assertEqual(request.full_url, "https://api.stripe.com/v1/customers")
        self.assertIn(b"email=finance%40acme.test", request.data)

    def test_create_invoice_uses_send_invoice_collection_method(self):
        with self._stub({"id": "in_123", "status": "draft"}) as fake:
            self.client.create_invoice("cus_123", "usd")
        request = fake.call_args.args[0]
        self.assertIn(b"collection_method=send_invoice", request.data)
        self.assertIn(b"auto_advance=false", request.data)

    def test_create_invoice_sets_the_invoice_currency_explicitly(self):
        # Stripe otherwise defaults a new invoice to the account's own default
        # currency, which then conflicts with the invoice item's currency.
        with self._stub({"id": "in_123", "status": "draft"}) as fake:
            self.client.create_invoice("cus_123", "eur")
        request = fake.call_args.args[0]
        self.assertIn(b"currency=eur", request.data)

    def test_add_invoice_item_attaches_to_the_given_invoice(self):
        with self._stub({"id": "ii_1"}) as fake:
            self.client.add_invoice_item("cus_123", "in_123", 150000, "usd", "Q1 engagement")
        request = fake.call_args.args[0]
        self.assertIn(b"invoice=in_123", request.data)
        self.assertIn(b"amount=150000", request.data)

    def test_finalize_and_send_hit_the_expected_paths(self):
        with self._stub({"status": "open"}) as fake:
            self.client.finalize_invoice("in_123")
        self.assertEqual(fake.call_args.args[0].full_url, "https://api.stripe.com/v1/invoices/in_123/finalize")
        with self._stub({"status": "open", "hosted_invoice_url": "https://invoice.stripe.com/i/abc"}) as fake:
            self.client.send_invoice("in_123")
        self.assertEqual(fake.call_args.args[0].full_url, "https://api.stripe.com/v1/invoices/in_123/send")

    def test_delete_draft_invoice_uses_delete_method(self):
        with self._stub({"deleted": True}) as fake:
            self.client.delete_draft_invoice("in_123")
        self.assertEqual(fake.call_args.args[0].get_method(), "DELETE")

    def test_an_http_error_is_translated_to_a_billing_error(self):
        with patch.object(self.client, "_send", side_effect=stripe_billing.StripeBillingError("Stripe returned an error: {}")):
            with self.assertRaises(stripe_billing.StripeBillingError):
                self.client.create_customer("a@b.com", "A")


def _sign(payload: bytes, secret: str, timestamp: int) -> str:
    signed_payload = f"{timestamp}.".encode("utf-8") + payload
    signature = hmac.new(secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
    return f"t={timestamp},v1={signature}"


class WebhookSignatureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.secret = "whsec_test_123"
        self.payload = json.dumps({"id": "evt_1", "type": "invoice.paid", "data": {"object": {"id": "in_123"}}}).encode("utf-8")

    def test_a_correctly_signed_event_is_accepted(self):
        header = _sign(self.payload, self.secret, int(time.time()))
        event = stripe_billing.verify_webhook_signature(self.payload, header, self.secret)
        self.assertEqual(event["id"], "evt_1")
        self.assertEqual(event["type"], "invoice.paid")

    def test_a_tampered_payload_is_rejected(self):
        header = _sign(self.payload, self.secret, int(time.time()))
        tampered = self.payload.replace(b"invoice.paid", b"invoice.voided")
        with self.assertRaises(stripe_billing.StripeBillingError):
            stripe_billing.verify_webhook_signature(tampered, header, self.secret)

    def test_the_wrong_secret_is_rejected(self):
        header = _sign(self.payload, "a-different-secret", int(time.time()))
        with self.assertRaises(stripe_billing.StripeBillingError):
            stripe_billing.verify_webhook_signature(self.payload, header, self.secret)

    def test_an_expired_signature_is_rejected(self):
        header = _sign(self.payload, self.secret, int(time.time()) - 10 * 60)
        with self.assertRaises(stripe_billing.StripeBillingError):
            stripe_billing.verify_webhook_signature(self.payload, header, self.secret)

    def test_a_missing_header_is_rejected(self):
        with self.assertRaises(stripe_billing.StripeBillingError):
            stripe_billing.verify_webhook_signature(self.payload, "", self.secret)

    def test_a_malformed_header_is_rejected(self):
        with self.assertRaises(stripe_billing.StripeBillingError):
            stripe_billing.verify_webhook_signature(self.payload, "not-a-real-header", self.secret)


if __name__ == "__main__":
    unittest.main()
