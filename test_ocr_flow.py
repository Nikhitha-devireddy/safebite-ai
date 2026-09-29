"""
SafeBite AI - Multimodal OCR Flow & Guardrail Test Suite
Specifically verifies that the 'name result is not defined' bug cannot recur,
that empty or corrupt images are caught early, and that OcrAnalysisResult
always returns a predictable, typed object.
"""

import io
import unittest
from unittest.mock import patch
from PIL import Image

from ocr_engine import OcrEngine, OcrAnalysisResult
from schemas import SourceConfidence

class TestOcrFlow(unittest.TestCase):

    def setUp(self):
        # Create a valid test in-memory image
        img = Image.new("RGB", (100, 100), color="white")
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        self.valid_image_bytes = buf.getvalue()

    def test_image_validation_empty_bytes(self):
        """Empty or tiny byte arrays must fail validation gracefully."""
        is_valid, msg = OcrEngine.validate_image(b"")
        self.assertFalse(is_valid)
        self.assertIn("empty", msg.lower())

    def test_image_validation_corrupt_format(self):
        """Random non-image bytes must fail validation."""
        is_valid, msg = OcrEngine.validate_image(b"not an image at all random bytes")
        self.assertFalse(is_valid)

    def test_ocr_flow_unreadable_blurry_label_no_undefined_variables(self):
        """
        REGRESSION TEST FOR: name 'result' is not defined.
        When vision assessment returns 'VERDICT: UNABLE TO ASSESS',
        the engine must return a valid OcrAnalysisResult object with all fields present.
        """
        with patch("ocr_engine.generate_clinical_assessment") as mock_gen:
            mock_gen.return_value = (
                "VERDICT: UNABLE TO ASSESS\n\n"
                "The uploaded photo does not clearly show the ingredient list. "
                "Please upload a clear close-up photo.",
                "Gemini Vision Guardrail"
            )

            res = OcrEngine.analyze_label_image(
                image_bytes=self.valid_image_bytes,
                mime_type="image/jpeg",
                user_name="John",
                medical_history="Hypertension",
                allergies=["Peanuts"]
            )

            self.assertIsInstance(res, OcrAnalysisResult)
            self.assertFalse(res.success)
            self.assertEqual(res.verdict, "UNABLE TO ASSESS")
            # Verify scrape_reason is defined and non-empty (the exact field that crashed earlier)
            self.assertTrue(hasattr(res, "scrape_reason"))
            self.assertGreater(len(res.scrape_reason), 0)
            self.assertTrue(hasattr(res, "final_output"))
            self.assertIn("VERDICT: UNABLE TO ASSESS", res.final_output)

    def test_ocr_flow_successful_transcription(self):
        """When label contains clear text, parses nutrition and assigns clinical safety."""
        ocr_text = """
        Product: Pascati Dark Chocolate Bar
        Ingredients: Organic cocoa beans, organic cocoa butter, cane sugar.
        Nutrition Facts per 100g:
        Calories: 550 kcal
        Protein: 8.0g
        Total Sugars: 4.0g
        Total Fat: 45.0g
        Sodium: 10mg
        Allergen Statement: Contains no allergens. Free from dairy, gluten, nuts.
        """
        with patch("ocr_engine.generate_clinical_assessment") as mock_gen:
            mock_gen.return_value = (ocr_text, "Gemini Vision Test")

            res = OcrEngine.analyze_label_image(
                image_bytes=self.valid_image_bytes,
                mime_type="image/jpeg",
                user_name="Alex",
                medical_history="Type 2 Diabetes",
                allergies=["Dairy"]
            )

            self.assertTrue(res.success)
            self.assertIsNotNone(res.nutrition)
            self.assertEqual(res.nutrition.calories, 550.0)
            self.assertEqual(res.nutrition.sugar_g, 4.0)
            self.assertIsNotNone(res.ingredients)
            self.assertEqual(res.verdict, "SAFE")

if __name__ == "__main__":
    unittest.main()
