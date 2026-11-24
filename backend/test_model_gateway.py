import os
import unittest
from unittest.mock import patch

from backend import model_gateway


class ModelGatewayTests(unittest.TestCase):
    def test_synthetic_adapter_produces_a_bounded_work_breakdown(self):
        adapter = model_gateway.resolve_adapter("synthetic")
        result = adapter.run("Plan the approved inventory diagnostic.", ["planning"])
        self.assertTrue(result.output["synthetic"])
        self.assertEqual(result.output["type"], "work_breakdown")
        self.assertEqual(result.provider, "synthetic")
        self.assertEqual(result.cost_cents, 0)

    def test_synthetic_adapter_rejects_tools_outside_the_bounded_set(self):
        adapter = model_gateway.resolve_adapter("synthetic")
        with self.assertRaises(model_gateway.ModelGatewayError):
            adapter.run("Plan the approved inventory diagnostic.", ["deploy"])

    def test_real_provider_is_refused_without_explicit_operator_approval(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop(model_gateway.REAL_PROVIDER_APPROVAL_ENV, None)
            with self.assertRaises(model_gateway.ModelGatewayError):
                model_gateway.resolve_adapter("openai")

    def test_real_provider_still_has_no_adapter_even_when_approved(self):
        with patch.dict(os.environ, {model_gateway.REAL_PROVIDER_APPROVAL_ENV: "1"}):
            with self.assertRaises(model_gateway.ModelGatewayError):
                model_gateway.resolve_adapter("openai")


if __name__ == "__main__":
    unittest.main()
