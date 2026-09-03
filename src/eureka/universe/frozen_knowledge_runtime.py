import json
import os
from typing import Dict, Any, Optional, Tuple
from .publication_model import FrozenResult
from .canonical_state import CanonicalWorkState, ReusableKnowledgeContext
from pydantic import ValidationError

class FrozenSolutionStore:
    def __init__(self, base_dir: str = "D:/IA Agentes"):
        self.base_dir = base_dir

    def load_frozen_solution(self, filename: str) -> Optional[FrozenResult]:
        filepath = os.path.join(self.base_dir, filename)
        if not os.path.exists(filepath):
            return None
            
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            return FrozenResult(**data)
        except (json.JSONDecodeError, ValidationError) as e:
            return None
        except Exception as e:
            return None

class FrozenSolutionValidator:
    def validate_frozen_solution(self, result: Optional[FrozenResult]) -> str:
        if not result:
            return "INVALID"
            
        if not result.result_id or result.status != "FROZEN":
            return "INVALID"
            
        # Check integrity
        if not result.knowledge_version:
            return "INCOMPLETE"
            
        if not result.validated_knowledge and not result.validated_predictions and not result.validated_prescriptions:
            return "INCOMPLETE"
            
        # The artifact is structurally valid and complete enough to mount
        return "VALID"

class FrozenSolutionMount:
    def mount_frozen_solution(self, frozen: FrozenResult, canonical: CanonicalWorkState) -> bool:
        if not frozen:
            return False
            
        # Extract the historical decision from the validated_prescriptions if it exists
        historical_decision = None
        if frozen.validated_prescriptions:
            presc = frozen.validated_prescriptions[0]
            if "decision_rule" in presc and presc["decision_rule"].get("authority") == "HUMAN_OPERATOR":
                historical_decision = presc["decision_rule"]
        
        context = ReusableKnowledgeContext(
            frozen_solution_id=frozen.result_id,
            version=frozen.knowledge_version,
            original_problem=None,  # We would extract this if FrozenResult held original problem strictly, but we can mount what we have.
            historical_knowledge=frozen.validated_knowledge,
            historical_predictions=frozen.validated_predictions,
            historical_prescriptions=frozen.validated_prescriptions,
            historical_action_plan=frozen.validated_action_plan,
            historical_decision=historical_decision,
            provenance=["Mounted from Frozen Knowledge Store", f"Artifact ID: {frozen.result_id}"] + frozen.provenance,
            applicability_status="NOT_EVALUATED",
            deltas=[]
        )
        
        canonical.historical_context = context
        return True

class FrozenKnowledgeRuntime:
    def __init__(self, base_dir: str = "D:/IA Agentes"):
        self.store = FrozenSolutionStore(base_dir)
        self.validator = FrozenSolutionValidator()
        self.mount = FrozenSolutionMount()
        
    def load_validate_and_mount(self, filename: str, canonical: CanonicalWorkState) -> Tuple[str, Optional[FrozenResult]]:
        frozen = self.store.load_frozen_solution(filename)
        status = self.validator.validate_frozen_solution(frozen)
        
        if status == "VALID":
            self.mount.mount_frozen_solution(frozen, canonical)
            
        return status, frozen
