import math
from typing import Dict, Any, Optional, List
from .canonical_state import CanonicalWorkState, ExecutionStep, StateCondition
from .math_ir import (
    MathematicalExpression, Variable, Constant,
    GCLVMembership, GMBCLConjunction, ReichenbachImplication
)


# --------------------------------------------------------------------------- #
# M-2: GCLV interpretability — characteristic preimages (truth 1.0 and 0.5).
# ec. 4.17 with the natural-log ACFL-ELF generator f=-ln, f^-1=e^-y gives
#   GCLV_A(S_G) = S_G^m (1-S_G)^(1-m) / (m^m (1-m)^(1-m)).
# The characteristic preimages (thesis Tabla 4.5, Algoritmos 4.3/4.4):
#   truth = 1.0  -> S_G = m  -> x0 (the crisp centroid "≈ c")
#   truth = 0.5  -> two S_G in (0,m) and (m,1) -> [x1_minus, x1_plus] ("between a and b")
# and S_G(x;alpha,gamma) maps back via x = gamma - (1/alpha) ln(1/S_G - 1).
# --------------------------------------------------------------------------- #
def _gclv_pow(a: float, b: float) -> float:
    if a == 0.0 and b == 0.0:
        return 1.0
    if a == 0.0:
        return 0.0
    return math.pow(a, b)


def gclv_value(s_g: float, m: float) -> float:
    c = _gclv_pow(s_g, m) * _gclv_pow(1.0 - s_g, 1.0 - m)
    m_norm = _gclv_pow(m, m) * _gclv_pow(1.0 - m, 1.0 - m)
    return c / m_norm if m_norm > 0 else 0.0


def _bisect(target: float, m: float, lo: float, hi: float, increasing: bool) -> float:
    for _ in range(300):
        mid = 0.5 * (lo + hi)
        v = gclv_value(mid, m)
        if v < target:
            if increasing:
                lo = mid
            else:
                hi = mid
        else:
            if increasing:
                hi = mid
            else:
                lo = mid
    return 0.5 * (lo + hi)


def gclv_preimages(alpha: float, gamma: float, m: float) -> Dict[str, float]:
    """Characteristic preimages of the GCLV (natural-log ACFL-ELF base).

    Returns x0 (truth 1.0, the centroid "c"), and [x1_minus, x1_plus] (truth 0.5 -> "between a and b").
    Falls back to a degenerate single point when alpha is not positive (no sigmoid).
    """
    if alpha <= 0:
        return {"x0": gamma, "x1_minus": gamma, "x1_plus": gamma, "interval": [gamma, gamma]}
    m = min(max(m, 1e-6), 1.0 - 1e-6)

    def x_of_S(s: float) -> float:
        s = min(max(s, 1e-9), 1.0 - 1e-9)
        return gamma - (1.0 / alpha) * math.log(1.0 / s - 1.0)

    x0 = x_of_S(m)
    s_lo = _bisect(0.5, m, 1e-9, m, increasing=True)
    s_hi = _bisect(0.5, m, m, 1.0 - 1e-9, increasing=False)
    xm = x_of_S(s_lo)
    xp = x_of_S(s_hi)
    return {"x0": x0, "x1_minus": xm, "x1_plus": xp, "interval": [min(xm, xp), max(xm, xp)]}


class ACFLEngine:
    """
    Archimedean Compensatory Fuzzy Logic Engine.
    Executes certified RAFA mathematical theory deterministically.
    """
    
    def evaluate_expression(self, expr: MathematicalExpression, inputs: Dict[str, float]) -> float:
        """
        Recursively evaluates a MathematicalExpression AST against an input record.
        Strictly restricted to authorized mathematical operators.
        """
        if isinstance(expr, Constant):
            return expr.value
            
        elif isinstance(expr, Variable):
            if expr.name not in inputs:
                raise ValueError(f"Missing required input variable: {expr.name}")
            return inputs[expr.name]
            
        elif isinstance(expr, GCLVMembership):
            x = self.evaluate_expression(expr.input, inputs)
            # S_G(x; alpha, gamma) = 1 / (1 + e^(-alpha * (x - gamma)))
            # Prevent math overflow
            exponent = -expr.alpha * (x - expr.gamma)
            if exponent > 700:
                s_g = 0.0
            elif exponent < -700:
                s_g = 1.0
            else:
                s_g = 1.0 / (1.0 + math.exp(exponent))
                
            # GCLV_A(x; alpha, gamma, m) — RAFA ec. 4.17 (ACFL-ELF, natural-log generator f(t) = -ln t,
            # f^-1(y) = e^-y).  The compensatory truth is
            #   C = f^-1( m·f(S_G) + (1-m)·f(1-S_G) ) = S_G^m · (1-S_G)^(1-m)
            # and the global normalizer is M = max_x C = m^m · (1-m)^(1-m)
            # (the max of the weighted geometric mean S^m(1-S)^(1-m) over S in [0,1] is at S = m).
            # M-1 fix: the previous implementation computed S_G^m / max(S_G^m, (1-S_G)^(1-m)), which is
            # NOT ec. 4.17 (it dropped the generator and the global-M normalization, and returned e.g.
            # 0.5 instead of 0.8 for m=0.5, S_G=0.2). See _gclv_prove.py.
            def _p(a, b):
                # safe power: 0^0 -> 1 (needed for the m=0 / m=1 boundaries of the GCLV)
                if a == 0.0 and b == 0.0:
                    return 1.0
                if a == 0.0:
                    return 0.0
                return math.pow(a, b)

            c = _p(s_g, expr.m) * _p(1.0 - s_g, 1.0 - expr.m)
            m_norm = _p(expr.m, expr.m) * _p(1.0 - expr.m, 1.0 - expr.m)
            return c / m_norm if m_norm > 0 else 0.0

        elif isinstance(expr, ReichenbachImplication):
            p = self.evaluate_expression(expr.antecedent, inputs)
            q = self.evaluate_expression(expr.consequent, inputs)
            # R(p,q) = 1 - p + pq
            return 1.0 - p + p * q
            
        elif isinstance(expr, GMBCLConjunction):
            if not expr.inputs:
                raise ValueError("GMBCL must have at least one input.")
            product = 1.0
            n = len(expr.inputs)
            for child in expr.inputs:
                val = self.evaluate_expression(child, inputs)
                if val <= 0:
                    return 0.0  # Zero product means geometric mean is zero
                product *= val
            return math.pow(product, 1.0 / n)
            
        else:
            raise ValueError(f"UNSUPPORTED_MATHEMATICAL_OPERATOR: {expr.operator}")

    def execute(self, canonical: CanonicalWorkState, step: ExecutionStep):
        """
        Legacy execution boundary (optional, as Predictor usually calls evaluate_expression directly).
        For now, this remains backwards compatible for older tests if needed, but we should 
        mainly rely on EMPredictor calling ACFLEngine directly.
        """
        pass
