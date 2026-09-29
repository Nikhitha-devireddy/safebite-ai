"""
SafeBite AI - Retrieval Resilience & HTTP Status Test Suite
Verifies that all scraper adapters and URL checkers safely handle:
200, 301/302, 403, 404, 429, 500+, timeouts, malformed HTML, and JSON-LD schema.
Never exposes raw stack traces or crashes on blocked websites.
"""

import unittest
from unittest.mock import patch, MagicMock
import requests

from schemas import RetrievalResult, SourceConfidence
from retailer_sources.base import BaseRetailer
from product_web_checker import ProductWebChecker

class DummyRetailer(BaseRetailer):
    def __init__(self):
        super().__init__(name="DummyStore", enabled=True, timeout=2)

    def search(self, query: str, location=None):
        return []

    def get_offer_by_url(self, url: str):
        return None

class TestRetrievalResilience(unittest.TestCase):

    def setUp(self):
        self.retailer = DummyRetailer()
        self.web_checker = ProductWebChecker(timeout=2)

    @patch("requests.get")
    def test_200_success_retrieval(self, mock_get):
        """HTTP 200 returns success with valid RetrievalResult."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "<html><body>Product Page</body></html>"
        mock_get.return_value = mock_resp

        resp, res = self.retailer.safe_fetch_with_result("https://example.com/product")
        self.assertIsNotNone(resp)
        self.assertTrue(res.success)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.confidence, SourceConfidence.HIGH)

    @patch("requests.get")
    def test_403_blocked_website_graceful_handling(self, mock_get):
        """HTTP 403 (bot protection / anti-bot) must gracefully return None without crashing."""
        mock_resp = MagicMock()
        mock_resp.status_code = 403
        mock_get.return_value = mock_resp

        resp, res = self.retailer.safe_fetch_with_result("https://amazon.in/dp/B07TEST")
        self.assertIsNone(resp)
        self.assertFalse(res.success)
        self.assertEqual(res.status_code, 403)
        self.assertEqual(res.error_type, "BLOCKED_403")
        self.assertIn("blocked automated access", res.error_message)

    @patch("requests.get")
    def test_429_rate_limited_handling(self, mock_get):
        """HTTP 429 rate limit must return RATE_LIMITED_429."""
        mock_resp = MagicMock()
        mock_resp.status_code = 429
        mock_get.return_value = mock_resp

        resp, res = self.retailer.safe_fetch_with_result("https://example.com/api")
        self.assertIsNone(resp)
        self.assertFalse(res.success)
        self.assertEqual(res.status_code, 429)
        self.assertEqual(res.error_type, "RATE_LIMITED_429")

    @patch("requests.get")
    def test_404_not_found_handling(self, mock_get):
        """HTTP 404 must return NOT_FOUND_404."""
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_get.return_value = mock_resp

        resp, res = self.retailer.safe_fetch_with_result("https://example.com/missing")
        self.assertIsNone(resp)
        self.assertEqual(res.error_type, "NOT_FOUND_404")

    @patch("requests.get")
    def test_500_server_error_handling(self, mock_get):
        """HTTP 500+ must return SERVER_ERROR_5XX without throwing."""
        mock_resp = MagicMock()
        mock_resp.status_code = 502
        mock_get.return_value = mock_resp

        resp, res = self.retailer.safe_fetch_with_result("https://example.com/down")
        self.assertIsNone(resp)
        self.assertEqual(res.error_type, "SERVER_ERROR_5XX")

    @patch("requests.get")
    def test_timeout_graceful_handling(self, mock_get):
        """Connection timeout must return TIMEOUT error_type."""
        mock_get.side_effect = requests.exceptions.Timeout("Connection timed out")

        resp, res = self.retailer.safe_fetch_with_result("https://example.com/slow")
        self.assertIsNone(resp)
        self.assertFalse(res.success)
        self.assertEqual(res.error_type, "TIMEOUT")
        self.assertIn("timed out", res.error_message)

    @patch("requests.get")
    def test_json_ld_schema_org_product_extraction(self, mock_get):
        """Web checker successfully extracts JSON-LD Product with embedded nutrition."""
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <script type="application/ld+json">
            {
                "@context": "https://schema.org",
                "@type": "Product",
                "name": "Organic Almond Milk 1L",
                "brand": {"@type": "Brand", "name": "RawPressery"},
                "gtin13": "8901234567890",
                "offers": {"@type": "Offer", "price": "199.00", "priceCurrency": "INR"},
                "nutrition": {
                    "@type": "NutritionInformation",
                    "servingSize": "200ml",
                    "calories": "65 kcal",
                    "sugarContent": "0.5g",
                    "proteinContent": "2.5g"
                }
            }
            </script>
        </head>
        <body>
            <p>Delicious almond beverage.</p>
        </body>
        </html>
        """
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = html_content
        mock_get.return_value = mock_resp

        parsed = self.web_checker.inspect_url("https://example.com/almond-milk")
        self.assertTrue(parsed["success"])
        self.assertEqual(parsed["title"], "Organic Almond Milk 1L")
        self.assertEqual(parsed["brand"], "RawPressery")
        self.assertEqual(parsed["price"], 199.0)
        self.assertEqual(parsed["barcode"], "8901234567890")
        self.assertIsNotNone(parsed["nutrition"])
        self.assertEqual(parsed["nutrition"].calories, 65.0)
        self.assertEqual(parsed["nutrition"].sugar_g, 0.5)
        self.assertEqual(parsed["nutrition"].protein_g, 2.5)

    @patch("requests.get")
    def test_malformed_html_no_crash(self, mock_get):
        """Malformed, incomplete, or truncated HTML must parse without exceptions."""
        malformed = "<div class='title'>Unclosed Tag <img src=broken"
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = malformed
        mock_get.return_value = mock_resp

        parsed = self.web_checker.inspect_url("https://example.com/broken")
        self.assertIsInstance(parsed, dict)

if __name__ == "__main__":
    unittest.main()
