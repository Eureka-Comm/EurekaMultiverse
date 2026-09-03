from eureka_cognitive_sdk.ekp.package import EnterpriseKnowledgePackage
from eureka_cognitive_sdk.ekp.artifacts.authority import ExecutionAuthority
from eureka_cognitive_sdk.core.value_objects.enumerations import KnowledgeState

class ActionerUnfreezer:
    """
    Implements the explicit UNFREEZE event as defined by EM 5.1 instructions.
    Converts a FROZEN package into an AUTHORIZED package if the provided
    ExecutionAuthority is strictly valid.
    """
    
    @staticmethod
    def unfreeze(ekp: EnterpriseKnowledgePackage, authority: ExecutionAuthority) -> EnterpriseKnowledgePackage:
        if ekp.metadata.lifecycle_state != KnowledgeState.FROZEN:
            raise ValueError(f"Cannot unfreeze package. Current state is {ekp.metadata.lifecycle_state.value}, expected FROZEN.")
            
        if authority.authority_type != "HUMAN_EXTERNAL":
            raise ValueError(f"Invalid authority type. Execution requires HUMAN_EXTERNAL, got {authority.authority_type}")
            
        if not authority.is_explicit_confirmation:
            raise ValueError("Execution authority must be an explicit confirmation.")
            
        # Verify the artifact exists in the package
        if not ekp.knowledge:
            raise ValueError("Cannot unfreeze an empty package.")
            
        found = False
        for k in ekp.knowledge:
            if str(k.identity.value) == str(authority.target_knowledge_id.value):
                found = True
                break
                
        if not found:
            raise ValueError(f"Target artifact {authority.target_knowledge_id.value} not found in this package.")
            
        new_meta = ekp.metadata.model_copy(update={"lifecycle_state": KnowledgeState.AUTHORIZED})
        new_ekp = ekp.model_copy(update={
            "metadata": new_meta,
            "execution_authority": authority
        })
        return new_ekp
