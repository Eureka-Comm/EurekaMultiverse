from typing import Dict, List
from datetime import datetime, timezone
from uuid import uuid4

from eureka_cognitive_sdk.core.exceptions.enterprise import EnterpriseError
from eureka_cognitive_sdk.core.identifiers.trace_id import TraceId
from eureka_cognitive_sdk.ekp.package import EnterpriseKnowledgePackage
from eureka_cognitive_sdk.ekp.collections.knowledge import KnowledgeCollection
from eureka_cognitive_sdk.ekp.provenance import Provenance
from eureka_cognitive_sdk.core.identifiers.module_id import ModuleId
from eureka_cognitive_sdk.core.identifiers.document_id import DocumentId
from eureka_cognitive_sdk.core.utilities.result import Result

from src.eureka.foundation.scientific.runtime.assembly import CapabilityRegistry, ExecutableRuntimeCapability, RuntimeAssemblyError

from .em_registry import EMRegistry
from eureka.foundation.cognitive.contracts.runner_contract import IGenericEMRunner


class GenericEMRunner(IGenericEMRunner):
    """
    Generic runner that orchestrates the execution of any registered Enterprise Module (EM).
    It resolves the EM, its mathematical capabilities, executes it, and mutates the EKP.
    """

    def __init__(self, em_registry: EMRegistry, capability_registry: CapabilityRegistry, runner_id: ModuleId):
        self._em_registry = em_registry
        self._capability_registry = capability_registry
        self._runner_id = runner_id

    def run(self, em_id: str, ekp: EnterpriseKnowledgePackage) -> Result[EnterpriseKnowledgePackage, EnterpriseError]:
        try:
            # 1. EM Discovery
            em = self._em_registry.resolve(em_id)

            # 2. Extract Requirements
            requirements = em.get_capability_requirements()

            # 3. Resolve required capabilities
            resolved_capabilities: Dict[str, ExecutableRuntimeCapability] = {}
            for req in requirements:
                try:
                    capability = self._capability_registry.resolve(req.capability_type)
                    resolved_capabilities[req.requirement_id] = capability
                except Exception as e:
                    raise EnterpriseError(f"Failed to resolve capability {req.capability_type} for EM {em_id}: {str(e)}")

            # 4. Create a TraceId for this execution
            trace_id = TraceId(value=str(uuid4()))

            # 4. Runtime Execution with flexible signature
            try:
                knowledge_outputs = em.execute(ekp, resolved_capabilities, trace_id)
            except TypeError as te:
                # Some legacy EMs may define execute(self, ekp, capabilities) without trace_id
                # Attempt a fallback call without trace_id
                try:
                    knowledge_outputs = em.execute(ekp, resolved_capabilities)
                except Exception as inner_e:
                    raise EnterpriseError(f"EM execution failed for {em_id}: {str(inner_e)}")
            except Exception as e:
                raise EnterpriseError(f"EM execution failed for {em_id}: {str(e)}")


            # Validate that knowledge_outputs is a list (no element type check)
            if not isinstance(knowledge_outputs, list):
                raise EnterpriseError(f"EM {em_id} returned invalid output type. Expected list.")

            # 6. Provenance Propagation & EKP Mutation
            kc = ekp.knowledge if ekp.knowledge else KnowledgeCollection()
            timestamp = datetime.now(timezone.utc)

            for k in knowledge_outputs:
                prov = Provenance(
                    source_document_id=DocumentId(value="N/A"),
                    produced_by_module=self._runner_id,
                    produced_at=timestamp,
                    produced_from=f"em_execution:{em_id}"
                )
                k_new = k.model_copy(update={"provenance": prov})
                kc = kc.add(k_new)

            new_ekp = ekp.model_copy(update={"knowledge": kc})
            return Result.ok(new_ekp)

        except EnterpriseError as ee:
            return Result.fail(ee)
        except Exception as e:
            return Result.fail(EnterpriseError(f"Unexpected orchestration failure: {str(e)}"))
