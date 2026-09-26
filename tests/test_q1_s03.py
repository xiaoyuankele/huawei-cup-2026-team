"""Focused checks for the audited reproduction's scale and pairing contract."""
import importlib.util
from pathlib import Path
import unittest

import numpy as np
import pandas as pd

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "q1_s03" / "reproduce.py"
SPEC = importlib.util.spec_from_file_location("q1_s03_reproduce", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ScaleAndMetricTests(unittest.TestCase):
    def test_delta_units_at_calibration_and_reference_scale(self):
        delta = np.array([[-1.0, -2.0], [-0.5, -0.8]])
        np.testing.assert_allclose(MODULE.scale_delta_correction(delta, np.full(2, MODULE.X60)), delta)
        np.testing.assert_array_equal(MODULE.scale_delta_correction(delta, np.zeros(2)), np.zeros_like(delta))

    def test_pairing_uses_original_ids_not_storage_order(self):
        rows = []
        for dataset, ids in [("left", [2, 1]), ("right", [1, 2])]:
            for original_id in ids:
                p = np.zeros(17)
                p[original_id - 1] = 1
                rows.append({"dataset": dataset, "index": original_id, **dict(zip(MODULE.P_COLS, p))})
        left, right = MODULE.paired_frames(pd.DataFrame(rows), "left", "right")
        self.assertEqual(left["index"].tolist(), [1, 2])
        np.testing.assert_array_equal(left[MODULE.P_COLS], right[MODULE.P_COLS])
        broken = pd.DataFrame(rows)
        broken.loc[broken.dataset.eq("right") & broken["index"].eq(2), "index"] = 3
        with self.assertRaises(ValueError):
            MODULE.paired_frames(broken, "left", "right")

    def test_global_domain_means_equal_but_domain_errors_differ(self):
        mean_delta = np.array([-1.0, -3.0])
        x = np.array([MODULE.X60, 2 * MODULE.X60])
        global_c = MODULE.correction_matrix("C1_global", x, mean_delta, None)
        domain_c = MODULE.correction_matrix("C1_domain", x, mean_delta, None)
        np.testing.assert_allclose(global_c.mean(1), domain_c.mean(1))
        global_metrics = MODULE.aggregate_metrics(domain_c, global_c)
        domain_metrics = MODULE.aggregate_metrics(domain_c, domain_c)
        self.assertAlmostEqual(global_metrics["rmse_mean_loss"], 0.0)
        self.assertGreater(global_metrics["rmse_domain_macro"], domain_metrics["rmse_domain_macro"])
        self.assertGreaterEqual(global_metrics["rmse_domain_macro"], global_metrics["rmse_mean_loss"])
        self.assertGreaterEqual(global_metrics["rmse_pooled_all_domains"], global_metrics["rmse_domain_macro"])


if __name__ == "__main__":
    unittest.main()
