import copy
import math
import unittest
from prediction_core import Inputs, PredictionModel, haemoglobin_g_dl, sigmoid, threshold_positive
from self_check import run_self_check


class PredictionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = PredictionModel.load()
        cls.sample = dict(RBC=4.5, Hb=10, MCV=68, MCH=22, RDW=16)

    def test_independent_R_predictions(self):
        report = run_self_check()
        self.assertTrue(report["passed"], report)
        self.assertGreaterEqual(report["vectors_checked"], 12)

    def test_student_threshold_is_strict_at_boundary(self):
        threshold = self.model.threshold
        self.assertFalse(self.model.classify(threshold, 0)[1])
        self.assertFalse(self.model.classify(math.nextafter(threshold, 0), 0)[1])
        self.assertTrue(self.model.classify(math.nextafter(threshold, 1), 0)[1])

    def test_voting_and_OR_boundary_and_score_are_distinct(self):
        q = self.model.threshold / 2
        self.assertEqual(self.model.classify(q, 1), (False, False, False, q))
        self.assertEqual(self.model.classify(q, 2), (True, False, True, 1.0))
        self.assertEqual(self.model.classify(self.model.threshold, 2), (True, False, True, 1.0))
        for count in (-1, 6, True):
            with self.assertRaises(ValueError):
                self.model.classify(q, count)

    def test_each_formula_threshold_equality_is_negative(self):
        for rule in self.model.rules:
            t = rule["threshold"]
            with self.subTest(rule=rule["name"]):
                self.assertFalse(threshold_positive(t, rule["operator"], t))
                positive_side = math.inf if rule["operator"] == ">" else -math.inf
                self.assertTrue(threshold_positive(math.nextafter(t, positive_side), rule["operator"], t))

    def test_explicit_Hb_conversion_preserves_equivalence(self):
        dl = Inputs.from_mapping(self.sample)
        litre = Inputs.from_mapping({**self.sample, "Hb": 100}, hb_unit="g/L")
        self.assertEqual(self.model.predict(dl), self.model.predict(litre))
        self.assertEqual(haemoglobin_g_dl(89, "g/L"), 8.9)
        self.assertEqual(haemoglobin_g_dl(89, "g/dL"), 89)
        with self.assertRaises(ValueError):
            haemoglobin_g_dl(89, "automatic")

    def test_nonfinite_nonpositive_and_missing_inputs_rejected(self):
        for key in self.sample:
            for invalid in (0, -1, math.nan, math.inf, -math.inf, True, ""):
                with self.subTest(key=key, value=invalid), self.assertRaises(ValueError):
                    self.model.predict({**self.sample, key: invalid})
        with self.assertRaises(ValueError):
            self.model.predict({"Hb": 10})
        with self.assertRaises(ValueError):
            self.model.predict(Inputs(4.5, 10, 0, 22, 16))

    def test_sigmoid_extreme_finite_logits(self):
        self.assertEqual(sigmoid(1000), 1)
        self.assertEqual(sigmoid(-1000), 0)
        self.assertEqual(sigmoid(0), .5)

    def test_config_is_the_only_source_of_fitted_values(self):
        document = copy.deepcopy(self.model.document)
        document["student"]["intercept"] += 2
        document["voting"]["rules"][0]["threshold"] = 100
        modified = PredictionModel(document)
        base, changed = self.model.predict(self.sample), modified.predict(self.sample)
        self.assertAlmostEqual(changed.logit - base.logit, 2)
        self.assertNotEqual(base.probability, changed.probability)
        self.assertFalse(changed.rules[0].positive)
        self.assertNotEqual(base.model_sha256, changed.model_sha256)

    def test_unsupported_or_incomplete_model_is_rejected(self):
        for mutation in (lambda d: d.update(schema_version="999"),
                         lambda d: d["student"].update(transform="identity"),
                         lambda d: d["student"]["coefficients"].pop("Hb"),
                         lambda d: d.update(decision_rule="AND"),
                         lambda d: d["voting"]["rules"].pop(),
                         lambda d: d.update(negative_class="healthy"),
                         lambda d: d["voting"]["rules"][0].update(expression_id="eval_arbitrary_text")):
            document = copy.deepcopy(self.model.document)
            mutation(document)
            with self.assertRaises(ValueError):
                PredictionModel(document)


if __name__ == "__main__":
    unittest.main()
