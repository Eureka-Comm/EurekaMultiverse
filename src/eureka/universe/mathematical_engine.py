import ast
import math
from typing import Dict, Any, Tuple

SAFE_MATH_ENV = {
    "math": math,
    "abs": abs,
    "round": round,
    "min": min,
    "max": max,
    "sum": sum,
}

class MathematicalEngine:
    @staticmethod
    def execute_formula(formula: str, inputs: Dict[str, float], parameters: Dict[str, float]) -> Tuple[float, list]:
        local_env = {}
        local_env.update(parameters)
        local_env.update(inputs)
        
        trace = []
        trace.append(f"Formula: {formula}")
        trace.append(f"Inputs: {inputs}")
        trace.append(f"Parameters: {parameters}")
        
        try:
            ast.parse(formula, mode='eval')
            result = eval(formula, {"__builtins__": {}}, dict(SAFE_MATH_ENV, **local_env))
            trace.append(f"Computation Successful. Result: {result}")
            return float(result), trace
        except Exception as e:
            trace.append(f"Computation Failed: {str(e)}")
            raise RuntimeError(f"Mathematical execution failed: {str(e)}")
