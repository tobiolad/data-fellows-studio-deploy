"""Stripe billing boundary for Studio.

One Stripe customer per organization; every invoice is created, finalized
and sent through Stripe's own hosted pages, never a card form inside Studio.
Nothing here ever decides an invoice is paid -- that only ever comes from a
signature-verified webhook event, read back from Stripe's own report of
what happened, never from a client-side redirect or a guess.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BILLING_ENABLED_ENV = "STUDIO_BILLING_ENABLED"
WEBHOOK_SIGNATURE_TOLERANCE_SECONDS = 5 * 60


class StripeBillingError(ValueError):
    """Raised for any invalid Stripe billing call or webhook verification."""


@dataclass(frozen=True)
class StripeBillingSettings:
    secret_key: str

    @classmethod
    def from_environment(cls) -> "StripeBillingSettings":
        secret_key = os.getenv("STRIPE_SECRET_KEY", "").strip()
        if not secret_key:
            raise StripeBillingError("STRIPE_SECRET_KEY is required")
        return cls(secret_key=secret_key)


class StripeBillingClient:
    """Thin wrapper over the Stripe REST API.

    HTTP calls go through small overridable methods so tests can substitute
    a fake transport instead of reaching Stripe.
    """

    base_url = "https://api.stripe.com/v1"

    def __init__(self, settings: StripeBillingSettings, timeout_seconds: float = 10.0) -> None:
        self.settings = settings
        self.timeout_seconds = timeout_seconds

    def create_customer(self, email: str, name: str) -> dict[str, Any]:
        return self._post("/customers", {"email": email, "name": name})

    def create_invoice(self, customer_id: str, currency: str, days_until_due: int = 14) -> dict[str, Any]:
        # Stripe otherwise defaults a new invoice to the account's own default currency,
        # which conflicts with the invoice item's currency the moment they differ.
        return self._post("/invoices", {
            "customer": customer_id,
            "currency": currency,
            "collection_method": "send_invoice",
            "days_until_due": str(days_until_due),
            "auto_advance": "false",
        })

    def add_invoice_item(self, customer_id: str, invoice_id: str, amount_cents: int, currency: str, description: str) -> dict[str, Any]:
        return self._post("/invoiceitems", {
            "customer": customer_id,
            "invoice": invoice_id,
            "amount": str(amount_cents),
            "currency": currency,
            "description": description,
        })

    def finalize_invoice(self, invoice_id: str) -> dict[str, Any]:
        return self._post(f"/invoices/{invoice_id}/finalize", {})

    def send_invoice(self, invoice_id: str) -> dict[str, Any]:
        return self._post(f"/invoices/{invoice_id}/send", {})

    def retrieve_invoice(self, invoice_id: str) -> dict[str, Any]:
        return self._get(f"/invoices/{invoice_id}")

    def void_invoice(self, invoice_id: str) -> dict[str, Any]:
        return self._post(f"/invoices/{invoice_id}/void", {})

    def delete_draft_invoice(self, invoice_id: str) -> dict[str, Any]:
        """A draft was never sent, so Stripe deletes it outright rather than voiding it."""
        request = Request(f"{self.base_url}/invoices/{invoice_id}", method="DELETE")
        return self._send(request)

    def _post(self, path: str, fields: dict[str, str]) -> dict[str, Any]:
        data = urlencode(fields).encode("utf-8") if fields else b""
        request = Request(f"{self.base_url}{path}", data=data, method="POST")
        return self._send(request)

    def _get(self, path: str) -> dict[str, Any]:
        request = Request(f"{self.base_url}{path}", method="GET")
        return self._send(request)

    def _send(self, request: Request) -> dict[str, Any]:
        request.add_header("Authorization", "Basic " + _basic_auth(self.settings.secret_key))
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                return json.loads(response.read(256 * 1024).decode("utf-8"))
        except HTTPError as exc:
            body = exc.read(4096).decode("utf-8", "replace")
            raise StripeBillingError(f"Stripe returned an error: {body}") from exc
        except StripeBillingError:
            raise
        except Exception as exc:
            raise StripeBillingError("Stripe could not be reached") from exc


def _basic_auth(secret_key: str) -> str:
    return base64.b64encode(f"{secret_key}:".encode("utf-8")).decode("ascii")


def verify_webhook_signature(payload: bytes, signature_header: str, webhook_secret: str) -> dict[str, Any]:
    """Verify Stripe's `Stripe-Signature` header and return the parsed event.

    Stripe signs `{timestamp}.{raw body}` with HMAC-SHA256 using the webhook
    endpoint's own secret. The event's `type`/`data` are never trusted until
    this passes, and anything outside a 5-minute window is rejected to block
    replay of an intercepted request.
    """
    if not signature_header:
        raise StripeBillingError("Missing Stripe-Signature header")
    parts = dict(item.split("=", 1) for item in signature_header.split(",") if "=" in item)
    timestamp = parts.get("t")
    signature = parts.get("v1")
    if not timestamp or not signature:
        raise StripeBillingError("Malformed Stripe-Signature header")
    try:
        signed_at = int(timestamp)
    except ValueError as exc:
        raise StripeBillingError("Malformed Stripe-Signature timestamp") from exc
    if abs(time.time() - signed_at) > WEBHOOK_SIGNATURE_TOLERANCE_SECONDS:
        raise StripeBillingError("Stripe webhook signature has expired")
    signed_payload = f"{timestamp}.".encode("utf-8") + payload
    expected = hmac.new(webhook_secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise StripeBillingError("Stripe webhook signature did not match")
    try:
        return json.loads(payload.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise StripeBillingError("Stripe webhook payload was not valid JSON") from exc
