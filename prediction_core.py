"""Versioned, standard-library-only prediction core. No network or training data."""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import math
from pathlib import Path
import sys
from typing import Any, Mapping

APP_VERSION = "2.0.0"
FEATURES = ("RBC", "Hb", "MCV", "MCH", "RDW")
UNITS = {"RBC": "10^12/L", "Hb": "g/dL", "MCV": "fL", "MCH": "pg", "RDW": "%"}


def resource_path(name: str) -> Path:
    """Resolve bundled data in source and PyInstaller's extracted resource directory."""
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)) / name


def finite_number(value: Any, label: str, *, positive: bool = False) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{label}: a number is required")
    try:
        number = float(value)
    except (ValueError, TypeError, OverflowError) as exc:
        raise ValueError(f"{label}: a finite number is required") from exc
    if not math.isfinite(number) or (positive and number <= 0):
        requirement = "finite positive number" if positive else "finite number"
        raise ValueError(f"{label}: a {requirement} is required")
    return number


def haemoglobin_g_dl(value: Any, unit: str) -> float:
    """Convert only an explicitly supplied unit. Never infer units from the value."""
    value = finite_number(value, "Hb", positive=True)
    if unit == "g/dL":
        return value
    if unit == "g/L":
        return value / 10.0
    raise ValueError("Hb unit must be g/dL or g/L")


@dataclass(frozen=True)
class Inputs:
    RBC: float
    Hb: float
    MCV: float
    MCH: float
    RDW: float

    @classmethod
    def from_mapping(cls, values: Mapping[str, Any], *, hb_unit: str = "g/dL") -> Inputs:
        missing = set(FEATURES) - set(values)
        if missing:
            raise ValueError("Missing inputs: " + ", ".join(sorted(missing)))
        parsed = {name: finite_number(values[name], name, positive=True) for name in FEATURES}
        parsed["Hb"] = haemoglobin_g_dl(parsed["Hb"], hb_unit)
        return cls(**parsed)

    def values(self) -> dict[str, float]:
        # Validate direct construction as well as UI/import paths.
        return {name: finite_number(getattr(self, name), name, positive=True) for name in FEATURES}


def sigmoid(logit: float) -> float:
    logit = finite_number(logit, "Linear predictor")
    if logit >= 0:
        return 1.0 / (1.0 + math.exp(-logit))
    exponent = math.exp(logit)
    return exponent / (1.0 + exponent)


def threshold_positive(value: float, operator: str, threshold: float) -> bool:
    value = finite_number(value, "Score")
    threshold = finite_number(threshold, "Threshold")
    if operator == ">":
        return value > threshold
    if operator == "<":
        return value < threshold
    raise ValueError("Only strict > or < rules are supported")


def formula_value(expression_id: str, values: Mapping[str, float]) -> float:
    """Explicit formulas, never eval model text or an external expression."""
    rbc, hb, mcv, mch, rdw = (values[key] for key in FEATURES)
    functions = {
        "DF": lambda: 1.109 * mch - 0.391 * mcv + 1.182 * rbc + 0.116 * rdw,
        "Sirachainan": lambda: 1.5 * hb - 0.05 * mcv,
        "MDHL": lambda: mch * rbc / mcv,
        "England_Fraser": lambda: mcv - rbc - 5 * hb - 3.4,
        "Green_King": lambda: mcv ** 2 * rdw / (hb * 100),
        "Sirdah": lambda: mcv - rbc - 3 * hb,
    }
    if expression_id not in functions:
        raise ValueError(f"Unsupported formula ID: {expression_id}")
    try:
        return finite_number(functions[expression_id](), expression_id)
    except (OverflowError, ZeroDivisionError) as exc:
        raise ValueError("Inputs exceed the numerical range of the formula") from exc


@dataclass(frozen=True)
class RuleResult:
    name: str
    expression_id: str
    expression: str
    value: float
    operator: str
    threshold: float
    positive: bool
    full_cohort: dict[str, Any]


@dataclass(frozen=True)
class Prediction:
    model_id: str
    model_version: str
    model_sha256: str
    inputs: dict[str, float]
    input_units: dict[str, str]
    rules: tuple[RuleResult, ...]
    logit: float
    probability: float
    probability_threshold: float
    positive_votes: int
    required_positive_votes: int
    voting_positive: bool
    student_positive: bool
    combined_positive: bool
    ranking_score: float

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["rules"] = list(result["rules"])
        return result


class PredictionModel:
    def __init__(self, document: Mapping[str, Any], *, sha256: str = ""):
        self.document = json.loads(json.dumps(document, allow_nan=False))
        self.sha256 = sha256 or hashlib.sha256(
            json.dumps(self.document, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()
        ).hexdigest()
        if str(self.document.get("schema_version")) != "1.0":
            raise ValueError("Unsupported model schema_version")
        self.model_id = str(self.document["model_id"])
        self.version = str(self.document["model_version"])
        if not self.model_id or not self.version:
            raise ValueError("Model identification is missing")
        student = self.document["student"]
        if student.get("transform") != "sigmoid" or student.get("threshold_operator") != ">":
            raise ValueError("Unsupported student transform or threshold operator")
        self.intercept = finite_number(student["intercept"], "intercept")
        if set(student["coefficients"]) != set(FEATURES):
            raise ValueError("The model must define exactly five CBC coefficients")
        self.coefficients = {key: finite_number(student["coefficients"][key], key) for key in FEATURES}
        self.threshold = finite_number(student["probability_threshold"], "probability threshold")
        if not 0 < self.threshold < 1:
            raise ValueError("The probability threshold must be between zero and one")
        voting = self.document["voting"]
        self.required_votes = voting["required_positive"]
        self.rules = voting["rules"]
        if len(self.rules) != 5:
            raise ValueError("The combined model must contain exactly five voting rules")
        if type(self.required_votes) is not int or not 1 <= self.required_votes <= len(self.rules):
            raise ValueError("Invalid voting requirement")
        if len({r["expression_id"] for r in self.rules}) != len(self.rules):
            raise ValueError("Duplicate voting formulas")
        if self.document.get("score_definition") != "1_if_votes_at_least_2_else_probability" or self.required_votes != 2:
            raise ValueError("Unsupported combined ranking-score definition")
        if self.document.get("decision_rule") != "votes_at_least_2_OR_probability_strictly_above_threshold":
            raise ValueError("Unsupported combined decision rule")
        for rule in self.rules:
            finite_number(rule["threshold"], rule["name"])
            if rule["operator"] not in (">", "<"):
                raise ValueError("Unsupported voting operator")
            # Exercise IDs only on benign synthetic values to reject unknown implementations.
            formula_value(rule["expression_id"], dict(RBC=4, Hb=9, MCV=65, MCH=20, RDW=18))
        schema = self.document.get("input_schema", [])
        if isinstance(schema, list):
            self.input_schema = {item["name"]: item for item in schema}
        else:
            self.input_schema = schema
        if set(self.input_schema) != set(FEATURES):
            raise ValueError("Input schema must identify the five CBC inputs")
        if any(self.input_schema[key].get("unit") != UNITS[key] for key in FEATURES):
            raise ValueError("Input units do not match the implemented formulas")
        if self.document.get("positive_class") != "THA":
            raise ValueError("The positive class must be THA")
        if self.document.get("negative_class") != "IDA":
            raise ValueError("The negative class must be IDA")

    @classmethod
    def load(cls, path: str | Path | None = None) -> PredictionModel:
        raw = Path(path or resource_path("model.json")).read_bytes()
        return cls(json.loads(raw), sha256=hashlib.sha256(raw).hexdigest())

    def classify(self, probability: float, positive_votes: int) -> tuple[bool, bool, bool, float]:
        probability = finite_number(probability, "Probability")
        if not 0 <= probability <= 1:
            raise ValueError("Probability must be between zero and one")
        if type(positive_votes) is not int or not 0 <= positive_votes <= len(self.rules):
            raise ValueError("Invalid positive vote count")
        voting = positive_votes >= self.required_votes
        student = threshold_positive(probability, ">", self.threshold)
        return voting, student, voting or student, 1.0 if voting else probability

    def predict(self, inputs: Inputs | Mapping[str, Any]) -> Prediction:
        values = inputs.values() if isinstance(inputs, Inputs) else Inputs.from_mapping(inputs).values()
        for name, value in values.items():
            schema = self.input_schema[name]
            minimum = schema.get("valid_min_exclusive")
            maximum = schema.get("valid_max")
            if minimum is not None and value <= minimum:
                raise ValueError(f"{name} must be greater than {minimum}")
            if maximum is not None and value > maximum:
                raise ValueError(f"{name} must be no more than {maximum}")
        logit = finite_number(self.intercept + sum(self.coefficients[key] * values[key] for key in FEATURES), "Linear predictor")
        probability = sigmoid(logit)
        rules = []
        for rule in self.rules:
            value = formula_value(rule["expression_id"], values)
            rules.append(RuleResult(rule["name"], rule["expression_id"], rule["expression"], value,
                                    rule["operator"], float(rule["threshold"]),
                                    threshold_positive(value, rule["operator"], rule["threshold"]),
                                    rule.get("full_cohort", {})))
        votes = sum(rule.positive for rule in rules)
        voting, student, combined, ranking_score = self.classify(probability, votes)
        return Prediction(self.model_id, self.version, self.sha256, values, dict(UNITS), tuple(rules),
                          logit, probability, self.threshold, votes, self.required_votes,
                          voting, student, combined, ranking_score)

    def equation(self) -> str:
        terms = [format(self.intercept, ".17g")]
        for key in FEATURES:
            coefficient = self.coefficients[key]
            terms.append(f"{'+' if coefficient >= 0 else '-'} {abs(coefficient):.17g} × {key}")
        return "z = " + " ".join(terms) + "; q = 1 / (1 + exp(-z))"

    def performance(self, name: str = "Combined") -> dict[str, Any]:
        return self.document.get("performance", {}).get("fixed_full_cohort", {}).get(name, {})
