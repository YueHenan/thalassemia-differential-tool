"""Independent R/Python parity check on deliberately synthetic, non-patient vectors."""
from __future__ import annotations

import csv
import math
from pathlib import Path
from prediction_core import FEATURES, PredictionModel, resource_path


def run_self_check(model_path=None, reference_path=None):
    model = PredictionModel.load(model_path)
    reference = Path(reference_path or resource_path("tests/synthetic_reference.csv"))
    failures = []
    maximum_error = 0.0
    count = 0
    with reference.open(encoding="utf-8-sig", newline="") as stream:
        for count, row in enumerate(csv.DictReader(stream), 1):
            prediction = model.predict({key: float(row[key]) for key in FEATURES})
            actual = {"logit": prediction.logit, "probability": prediction.probability,
                      "ranking_score": prediction.ranking_score}
            actual.update({"formula_" + rule.expression_id: rule.value for rule in prediction.rules})
            for key, value in actual.items():
                expected = float(row[key])
                maximum_error = max(maximum_error, abs(value - expected))
                if not math.isclose(value, expected, rel_tol=1e-12, abs_tol=1e-11):
                    failures.append({"vector": count, "field": key, "python": value, "R": expected})
            for key, value in {"votes": prediction.positive_votes,
                               "distill_positive": prediction.student_positive,
                               "combined_positive": prediction.combined_positive}.items():
                expected = int(row[key]) if key == "votes" else row[key].upper() == "TRUE"
                if value != expected:
                    failures.append({"vector": count, "field": key, "python": value, "R": expected})
    if count < 10:
        failures.append({"error": "At least ten independent synthetic vectors are required"})
    return {"passed": not failures, "model_id": model.model_id, "model_version": model.version,
            "model_sha256": model.sha256, "vectors_checked": count,
            "maximum_absolute_numeric_error": maximum_error,
            "relative_tolerance": 1e-12, "absolute_tolerance": 1e-11, "failures": failures}
