"""
SafeBite AI - Product Identity & Variant Matching Test Suite
Verifies that conflicting variants (e.g. Chocolate vs Peanut Butter, 50g vs 500g)
are never merged, preventing variant cross-contamination.
"""

import unittest
from schemas import ProductIdentityConfidence
from product_identity import ProductIdentityMatcher

class TestProductIdentity(unittest.TestCase):

    def test_barcode_exact_match(self):
        """Identical barcodes must produce EXACT confidence."""
        conf, reason = ProductIdentityMatcher.evaluate_match(
            target_name="Protein Bar",
            candidate_name="Protein Bar Energy",
            target_barcode="890600102030",
            candidate_barcode="890600102030"
        )
        self.assertEqual(conf, ProductIdentityConfidence.EXACT)
        self.assertTrue(ProductIdentityMatcher.can_merge_clinical_evidence(conf))

    def test_barcode_mismatch(self):
        """Conflicting barcodes must produce UNVERIFIED confidence."""
        conf, reason = ProductIdentityMatcher.evaluate_match(
            target_name="Protein Bar",
            candidate_name="Protein Bar",
            target_barcode="890600102030",
            candidate_barcode="123456789012"
        )
        self.assertEqual(conf, ProductIdentityConfidence.UNVERIFIED)
        self.assertFalse(ProductIdentityMatcher.can_merge_clinical_evidence(conf))

    def test_variant_conflict_prevention(self):
        """CRITICAL: 'Protein Bar Chocolate 50g' must NOT match 'Protein Bar Peanut 50g'."""
        conf, reason = ProductIdentityMatcher.evaluate_match(
            target_name="Energy Protein Bar Double Cocoa 50g",
            candidate_name="Energy Protein Bar Peanut Butter 50g",
            target_brand="EnergyCo",
            candidate_brand="EnergyCo"
        )
        self.assertEqual(conf, ProductIdentityConfidence.UNVERIFIED)
        self.assertIn("Variant conflict", reason)
        self.assertFalse(ProductIdentityMatcher.can_merge_clinical_evidence(conf))

    def test_pack_size_difference(self):
        """Pack size difference (50g vs 500g) must produce POSSIBLE confidence, not EXACT."""
        conf, reason = ProductIdentityMatcher.evaluate_match(
            target_name="Whole Oats Double Cocoa Bar 50g",
            candidate_name="Whole Oats Double Cocoa Bar 500g",
            target_brand="OatCo",
            candidate_brand="OatCo",
            target_pack="50g",
            candidate_pack="500g"
        )
        self.assertEqual(conf, ProductIdentityConfidence.POSSIBLE)
        self.assertIn("Pack size difference", reason)

    def test_brand_conflict_prevention(self):
        """Different brands must not match."""
        conf, reason = ProductIdentityMatcher.evaluate_match(
            target_name="Organic Almond Butter",
            candidate_name="Organic Almond Butter",
            target_brand="The Whole Truth",
            candidate_brand="Pintola"
        )
        self.assertEqual(conf, ProductIdentityConfidence.UNVERIFIED)
        self.assertIn("Brand mismatch", reason)

if __name__ == "__main__":
    unittest.main()
