"""Real fuzzy layer (cap 2) + ACFL bridge.

A Mamdani fuzzy controller is built with scikit-fuzzy from a declarative spec.
The LLM only *specifies* the rules/terms in JSON — the math (membership +
defuzzification) lives here in Python, matching the orchestrator contract:
cap 2 "define o reutiliza funciones de membresía y evalúa reglas SI-ENTONCES".

ACFLBridge maps EUREKA's acfl.normalized_scores (0..1 satisfaction, itself a
derived fuzzy membership) into fuzzy terms and a drivable controller, so the
existing mathematical layer plugs into the same fuzzy engine.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

try:
    import skfuzzy as fuzz
    from skfuzzy import control as ctrl
    _HAS_SKFUZZY = True
except Exception:  # pragma: no cover - skfuzzy is installed in this env
    _HAS_SKFUZZY = False


_RULE_RE = re.compile(r"^if\s+(.+?)\s+then\s+(.+?)\s+is\s+(\w+)$", re.IGNORECASE)
_CLAUSE_RE = re.compile(r"^(.+?)\s+is\s+(\w+)$", re.IGNORECASE)


class FuzzyError(Exception):
    """Raised on an invalid fuzzy spec or evaluation."""


def _universe(lo: float, hi: float) -> np.ndarray:
    step = max((hi - lo) / 100.0, 1e-3)
    return np.arange(lo, hi + step / 2, step)


def _mf(spec: List[float], universe: np.ndarray) -> np.ndarray:
    if not _HAS_SKFUZZY:
        raise FuzzyError("scikit-fuzzy no está disponible.")
    spec = [float(x) for x in spec]
    if len(spec) == 3:
        return fuzz.trimf(universe, spec)
    if len(spec) == 4:
        return fuzz.trapmf(universe, spec)
    raise FuzzyError(f"MF debe ser [a,b,c] (trimf) o [a,b,c,d] (trapmf); recibido {spec}")


class ParsedRule:
    __slots__ = ("text", "clauses", "connectors", "consequent_var", "consequent_term")

    def __init__(self, text: str, clauses: List[Tuple[str, str]], connectors: List[str],
                 cons_var: str, cons_term: str):
        self.text = text
        self.clauses = clauses
        self.connectors = connectors
        self.consequent_var = cons_var
        self.consequent_term = cons_term


def parse_rule(rule_text: str) -> ParsedRule:
    m = _RULE_RE.match(rule_text.strip())
    if not m:
        raise FuzzyError(f"Regla mal formada: '{rule_text}' (esperado: 'if X is A ... then Y is Z')")
    antecedent_text, cons_var, cons_term = m.group(1), m.group(2).strip(), m.group(3).strip()
    toks = re.split(r"\s+(and|or)\s+", antecedent_text, flags=re.IGNORECASE)
    clauses: List[Tuple[str, str]] = []
    connectors: List[str] = []
    for i, t in enumerate(toks):
        t = t.strip()
        if i % 2 == 1:
            connectors.append(t.lower())
        else:
            cm = _CLAUSE_RE.match(t)
            if not cm:
                raise FuzzyError(f"Cláusula mal formada: '{t}'")
            clauses.append((cm.group(1).strip(), cm.group(2).strip()))
    if len(connectors) != len(clauses) - 1:
        raise FuzzyError("Conectores incoherentes en la regla.")
    return ParsedRule(rule_text.strip(), clauses, connectors, cons_var, cons_term)


class FuzzyController:
    """Mamdani controller built from a declarative spec.

    Spec shape:
    {
      "antecedents": {"costo": {"universe":[0,100], "terms":{"bajo":[0,0,50],"alto":[50,100,100]}}},
      "consequents": {"decision": {"universe":[0,1], "terms":{"baja":[0,0,0.5],"media":[0.25,0.5,0.75],"alta":[0.5,1,1]}}},
      "rules": ["if costo is alto and riesgo is alto then decision is baja", ...]
    }
    """

    def __init__(self, spec: Dict[str, Any]):
        if not _HAS_SKFUZZY:
            raise FuzzyError("scikit-fuzzy no está instalado; no se puede construir el controlador.")
        self.spec = spec
        self.antecedents: Dict[str, Any] = {}
        self.consequents: Dict[str, Any] = {}
        self._terms: Dict[Tuple[str, str], Tuple[np.ndarray, np.ndarray]] = {}
        self.rules: List[ParsedRule] = []
        self._system = None
        self._sim = None
        self._build()

    def _build(self) -> None:
        cls_in = ctrl.Antecedent
        cls_out = ctrl.Consequent
        for group, cls in (("antecedents", cls_in), ("consequents", cls_out)):
            for name, cfg in (self.spec.get(group, {}) or {}).items():
                lo, hi = float(cfg["universe"][0]), float(cfg["universe"][1])
                universe = _universe(lo, hi)
                var = cls(universe, name)
                for term, mfspec in (cfg.get("terms", {}) or {}).items():
                    mf = _mf(mfspec, universe)
                    var[term] = mf
                    self._terms[(name, term)] = (universe, mf)
                if group == "antecedents":
                    self.antecedents[name] = var
                else:
                    self.consequents[name] = var

        for rtext in (self.spec.get("rules", []) or []):
            rule = parse_rule(rtext)
            if rule.consequent_var not in self.consequents:
                raise FuzzyError(f"Consecuente desconocido '{rule.consequent_var}' en regla.")
            for var, term in rule.clauses:
                if var not in self.antecedents:
                    raise FuzzyError(f"Antecedente desconocido '{var}' en regla.")
                if term not in self.antecedents[var].terms:
                    raise FuzzyError(f"Término '{term}' no existe para '{var}'.")
            self.rules.append(rule)

        if not self.consequents:
            raise FuzzyError("El spec debe declarar al menos un consecuente.")
        if not self.rules:
            raise FuzzyError("El spec debe declarar al menos una regla.")

        ctrl_rules = []
        for rule in self.rules:
            expr = None
            for i, (var, term) in enumerate(rule.clauses):
                node = self.antecedents[var][term]
                if expr is None:
                    expr = node
                else:
                    op = rule.connectors[i - 1]
                    expr = (expr & node) if op == "and" else (expr | node)
            ctrl_rules.append(ctrl.Rule(expr, self.consequents[rule.consequent_var][rule.consequent_term]))
        self._system = ctrl.ControlSystem(ctrl_rules)

    def _membership(self, var: str, term: str, x: Optional[float]) -> float:
        if x is None:
            return 0.0
        key = (var, term)
        if key not in self._terms:
            return 0.0
        universe, mf = self._terms[key]
        lo, hi = float(universe[0]), float(universe[-1])
        x = min(max(float(x), lo), hi)
        return float(fuzz.interp_membership(universe, mf, x))

    def _activation(self, rule: ParsedRule, inputs: Dict[str, float]) -> float:
        val = None
        for i, (var, term) in enumerate(rule.clauses):
            mv = self._membership(var, term, inputs.get(var))
            if val is None:
                val = mv
            else:
                op = rule.connectors[i - 1]
                val = min(val, mv) if op == "and" else max(val, mv)
        return round(float(val or 0.0), 4)

    def evaluate(self, inputs: Dict[str, float]) -> Dict[str, Any]:
        if self._sim is None:
            self._sim = ctrl.ControlSystemSimulation(self._system)
        for var in self.antecedents:
            self._sim.input[var] = float(inputs.get(var, 0.0)) if inputs.get(var) is not None else 0.0
        self._sim.compute()

        salidas: Dict[str, float] = {}
        for name in self.consequents:
            salidas[name] = float(self._sim.output[name])

        fired = [r.text for r in self.rules if self._activation(r, inputs) > 0.0]

        membresias: Dict[str, Dict[str, float]] = {}
        for var in self.antecedents:
            x = inputs.get(var)
            membresias[var] = {
                term: self._membership(var, term, x)
                for term in self.antecedents[var].terms
            }

        salida_crisp = salidas.get(next(iter(self.consequents))) if salidas else None
        return {
            "variable": next(iter(self.consequents)),
            "membresias": membresias,
            "reglas_disparadas": fired,
            "salida_crisp": salida_crisp,
            "salidas": salidas,
        }


class ACFLBridge:
    """Bridges EUREKA's ACFL satisfaction matrix into the fuzzy layer.

    acfl.normalized_scores is {alternative: {criteria: 0..1}}; each 0..1 value is
    already a fuzzy membership of "satisfaction". We expose it as baja/alta terms
    and build a drivable controller where satisfaction maps to a crisp decision.
    """

    @staticmethod
    def to_memberships(normalized_scores: Dict[str, Any]) -> Dict[str, Dict[str, Dict[str, float]]]:
        out: Dict[str, Dict[str, Dict[str, float]]] = {}
        for alt, row in (normalized_scores or {}).items():
            out[alt] = {}
            for crit, s in (row or {}).items():
                try:
                    s = float(s)
                except (TypeError, ValueError):
                    s = 0.0
                s = min(1.0, max(0.0, s))
                out[alt][crit] = {"baja": round(1.0 - s, 3), "alta": round(s, 3)}
        return out

    @staticmethod
    def build_controller(criteria: List[str]) -> FuzzyController:
        """A controller where each criterion is an antecedent (baja/alta) driving a decision."""
        ants: Dict[str, Any] = {}
        for c in criteria:
            ants[c] = {"universe": [0, 1], "terms": {"baja": [0, 0, 0.5], "alta": [0.5, 1, 1]}}
        rules = []
        for c in criteria:
            rules.append(f"if {c} is alta then decision is alta")
            rules.append(f"if {c} is baja then decision is baja")
        spec = {
            "antecedents": ants,
            "consequents": {"decision": {"universe": [0, 1], "terms": {
                "baja": [0, 0, 0.5], "media": [0.25, 0.5, 0.75], "alta": [0.5, 1, 1]}}},
            "rules": rules,
        }
        return FuzzyController(spec)

    @staticmethod
    def evaluate_alternative(controller: FuzzyController, memberships: Dict[str, Dict[str, float]]) -> Dict[str, Any]:
        """Feed an alternative's baja/alta memberships as crisp inputs (use 'alta' membership)."""
        inputs = {crit: row.get("alta", 0.0) for crit, row in memberships.items()}
        return controller.evaluate(inputs)
