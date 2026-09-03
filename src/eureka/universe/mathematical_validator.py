import json
from typing import Dict, Any, Tuple
from .canonical_state import PredictionKnowledge
from .mathematical_engine import MathematicalEngine

class MathematicalValidator:
    @staticmethod
    def validate_prediction(prediction: PredictionKnowledge, current_evidence: Dict[str, Any]) -> PredictionKnowledge:
        # Check inputs
        missing = []
        for req_var, req_type in prediction.input_requirements.items():
            if req_var not in current_evidence:
                missing.append(req_var)
        
        print("DEBUG MISSING:", missing)
        if missing:
            prediction.validation_status = "INSUFFICIENT_DATA"
            prediction.computation_trace.append(f"Missing inputs: {missing}")
            return prediction
            
        # Check validity conditions
        for cond in prediction.validity_conditions:
            try:
                if not eval(cond, {"__builtins__": {}}, current_evidence):
                    prediction.validation_status = "OUT_OF_VALIDITY_DOMAIN"
                    prediction.computation_trace.append(f"Violated condition: {cond}")
                    return prediction
            except Exception as e:
                prediction.validation_status = "OUT_OF_VALIDITY_DOMAIN"
                prediction.computation_trace.append(f"Failed to evaluate condition {cond}: {e}")
                return prediction
                
        # Execute model
        try:
            inputs = {k: current_evidence[k] for k in prediction.input_requirements.keys()}
            if prediction.model_type == "FORMULA":
                result, trace = MathematicalEngine.execute_formula(
                    formula=prediction.formula,
                    inputs=inputs,
                    parameters=prediction.model_parameters
                )
                prediction.predicted_value = result
                prediction.computation_trace.extend(trace)
                prediction.validation_status = "VALIDATED"
                prediction.reproducibility = True
            else:
                prediction.validation_status = "INVALID_MODEL"
                prediction.computation_trace.append(f"Unsupported model type: {prediction.model_type}")
        except Exception as e:
            prediction.validation_status = "MATHEMATICAL_EXECUTION_FAILED"
            prediction.computation_trace.append(str(e))
            
        return prediction
