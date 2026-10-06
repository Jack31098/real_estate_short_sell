from pathlib import Path
import sys
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from office_intersection_bounds import intersection_bounds  # noqa: E402


class OfficeIntersectionBoundsTests(unittest.TestCase):
    def test_colb_margins_do_not_identify_intersection(self):
        lower, upper, independent = intersection_bounds(5635, 3559, 27009)
        self.assertEqual(lower, 0)
        self.assertEqual(upper, 3559)
        self.assertAlmostEqual(independent, 742.3, delta=1)

    def test_impossible_margin_is_rejected(self):
        with self.assertRaises(ValueError):
            intersection_bounds(12, 5, 10)


if __name__ == "__main__":
    unittest.main()
