from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

@dataclass
class CapabilityContract:
    capability_id: str
    description: str
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    required_evidence: List[str]
    allowed_state: List[str]
    produces: List[str]
    visualizations: List[str]
    artifacts: List[str]
    execution_target: str = "EM" # "EM" or "SUBSYSTEM"
    target_em_id: Optional[str] = None
    canonical_em: Optional[str] = None # The exact 8-EM identity
    runtime_subsystem: Optional[List[str]] = None
    governance_level: str = "LOW"
    failure_mode: str = "CAPABILITY_UNAVAILABLE"
    produces_result: bool = False

class CapabilityRegistry:
    """
    The Fail-Closed registry of operations DeepSeek is allowed to request.
    If a capability doesn't exist or map to an EM, the system responds with GAP/BLOCKED.
    """
    def __init__(self):
        self._capabilities: Dict[str, CapabilityContract] = {}

    def register(self, cap: CapabilityContract):
        self._capabilities[cap.capability_id] = cap

    def resolve(self, capability_id: str) -> Optional[CapabilityContract]:
        return self._capabilities.get(capability_id)

    def load_defaults(self):
        self.register(CapabilityContract(
            capability_id="execute_action",
            description="Executes a cognitive action plan.",
            input_schema={"type": "object", "properties": {}},
            output_schema={"type": "object", "properties": {}},
            required_evidence=[], allowed_state=["OPEN", "PENDING"], produces=["ACTION_PLAN"], visualizations=[], artifacts=[],
            execution_target="EM", target_em_id="ACTIONER", canonical_em="EM Actioner"
        ))

        self.register(CapabilityContract(
            capability_id="frozen_knowledge.load",
            description="Loads a previously frozen solution from persistence.",
            input_schema={"type": "object", "properties": {"frozen_solution_id": {"type": "string"}}},
            output_schema={"type": "object", "properties": {}},
            required_evidence=[], allowed_state=["OPEN"], produces=["FROZEN_RESULT"], visualizations=[], artifacts=[],
            execution_target="EM", target_em_id="CORE", canonical_em="EM Core"
        ))

        self.register(CapabilityContract(
            capability_id="frozen_knowledge.validate",
            description="Validates a loaded frozen solution artifact.",
            input_schema={"type": "object", "properties": {}},
            output_schema={"type": "object", "properties": {}},
            required_evidence=[], allowed_state=["OPEN"], produces=["VALIDATION_RESULT"], visualizations=[], artifacts=[],
            execution_target="EM", target_em_id="CORE", canonical_em="EM Core"
        ))

        self.register(CapabilityContract(
            capability_id="frozen_knowledge.mount",
            description="Mounts a validated frozen solution into the canonical work context.",
            input_schema={"type": "object", "properties": {}},
            output_schema={"type": "object", "properties": {}},
            required_evidence=[], allowed_state=["OPEN"], produces=["REUSABLE_KNOWLEDGE_CONTEXT"], visualizations=[], artifacts=[],
            execution_target="EM", target_em_id="CORE", canonical_em="EM Core"
        ))

        self.register(CapabilityContract(
            capability_id="frozen_knowledge.evaluate_applicability",
            description="Evaluates if a mounted historical solution remains applicable to the current problem based on context and evidence.",
            input_schema={"type": "object", "properties": {}},
            output_schema={"type": "object", "properties": {}},
            required_evidence=[], allowed_state=["OPEN", "PENDING", "RUNNING"], produces=["APPLICABILITY_ASSESSMENT"], visualizations=[], artifacts=[],
            execution_target="EM", target_em_id="CORE", canonical_em="EM Core"
        ))

        self.register(CapabilityContract(
            capability_id="install_action",
            description="Installs a cognitive action plan into the environment.",
            input_schema={"type": "object", "properties": {}},
            output_schema={"type": "object", "properties": {}},
            required_evidence=[], allowed_state=["OPEN", "PENDING"], produces=["INSTALLATION_RESULT"], visualizations=[], artifacts=[],
            execution_target="EM", target_em_id="INSTALLER", canonical_em="EM Installer"
        ))
        
        self.register(CapabilityContract(
            capability_id="understand_input",
            description="Normalizes and understands unstructured input.",
            input_schema={"type": "object", "properties": {}},
            output_schema={"type": "object", "properties": {}},
            required_evidence=[], allowed_state=["OPEN"], produces=["NORMALIZED_INPUT"], visualizations=[], artifacts=[],
            execution_target="EM", target_em_id="SEMANTIC", canonical_em="EM Core"
        ))

        self.register(CapabilityContract(
            capability_id="extract_relevant_information",
            description="Extracts specific entities from the input.",
            input_schema={"type": "object", "properties": {}},
            output_schema={"type": "object", "properties": {}},
            required_evidence=["NORMALIZED_INPUT"], allowed_state=["OPEN"], produces=["EXTRACTED_KNOWLEDGE"], visualizations=[], artifacts=[],
            execution_target="EM", target_em_id="SEMANTIC", canonical_em="EM Descriptor"
        ))

        self.register(CapabilityContract(
            capability_id="synthesize_information",
            description="Synthesizes and structures the information.",
            input_schema={"type": "object", "properties": {}},
            output_schema={"type": "object", "properties": {}},
            required_evidence=["EXTRACTED_KNOWLEDGE"], allowed_state=["OPEN"], produces=["SYNTHESIS"], visualizations=[], artifacts=[],
            execution_target="SUBSYSTEM", runtime_subsystem=["ExplanatoryAnalyticsEngine"], canonical_em=None
        ))

        self.register(CapabilityContract(
            capability_id="generate_summary",
            description="Generates a narrative summary.",
            input_schema={"type": "object", "properties": {}},
            output_schema={"type": "object", "properties": {}},
            required_evidence=["SYNTHESIS"], allowed_state=["OPEN"], produces=["STORY"], visualizations=["Story Canvas"], artifacts=["Report"],
            execution_target="SUBSYSTEM", runtime_subsystem=["StoryEngine", "ArtifactEngine"], canonical_em="EM Publisher",
            produces_result=True
        ))
        
        self.register(CapabilityContract(
            capability_id="generate_report",
            description="Generates a comprehensive report.",
            input_schema={"type": "object", "properties": {}},
            output_schema={"type": "object", "properties": {}},
            required_evidence=["SYNTHESIS"], allowed_state=["OPEN"], produces=["REPORT"], visualizations=["Story Canvas"], artifacts=["Report"],
            execution_target="SUBSYSTEM", runtime_subsystem=["StoryEngine", "ArtifactEngine"], canonical_em="EM Publisher",
            produces_result=True
        ))

        self.register(CapabilityContract(
            capability_id="inspect_document",
            description="Extracts raw text and semantic structure from an uploaded document.",
            input_schema={"type": "object", "properties": {"file_id": {"type": "string"}}},
            output_schema={"type": "object", "properties": {"semantic_tree": {"type": "object"}}},
            required_evidence=["RAW_DOCUMENT"],
            allowed_state=["OPEN", "PENDING"],
            produces=["EXTRACTED_KNOWLEDGE"],
            visualizations=["Evidence Map"],
            artifacts=[],
            execution_target="EM",
            target_em_id="SEMANTIC",
            canonical_em="EM Structurer"
        ))

        self.register(CapabilityContract(
            capability_id="evaluate_alternatives",
            description="Evaluates a set of alternatives against a set of constraints.",
            input_schema={"type": "object", "properties": {"alternatives": {"type": "array"}}},
            output_schema={"type": "object", "properties": {"rankings": {"type": "array"}}},
            required_evidence=["ALTERNATIVES_LIST", "CONSTRAINTS_LIST"],
            allowed_state=["EVALUATION_READY"],
            produces=["RANKED_ALTERNATIVES"],
            visualizations=["Phase Space"],
            artifacts=["Decision Story"],
            execution_target="EM",
            target_em_id="RANKING",
            canonical_em="EM Prescriptor"
        ))

        self.register(CapabilityContract(
            capability_id="analyze_dataset",
            description="Performs scientific and statistical analysis on a dataset.",
            input_schema={"type": "object", "properties": {"dataset_id": {"type": "string"}}},
            output_schema={"type": "object", "properties": {"distribution": {"type": "object"}}},
            required_evidence=["STRUCTURED_DATA"],
            allowed_state=["ANALYSIS_READY"],
            produces=["SCIENTIFIC_METRICS"],
            visualizations=["Scientific Surface"],
            artifacts=["Technical Story"],
            execution_target="EM",
            target_em_id="SCIENTIFIC",
            canonical_em="EM Predictor"
        ))

        self.register(CapabilityContract(
            capability_id="extract_evidence",
            description="Extracts evidence from text.",
            input_schema={"type": "object", "properties": {"text": {"type": "string"}}},
            output_schema={"type": "object", "properties": {"evidence": {"type": "array"}}},
            required_evidence=[],
            allowed_state=["OPEN"],
            produces=["EVIDENCE"],
            visualizations=[],
            artifacts=[],
            execution_target="EM",
            target_em_id="SEMANTIC",
            canonical_em="EM Descriptor"
        ))

        self.register(CapabilityContract(
            capability_id="retrieve_result",
            description="Retrieves the already generated result of the current work.",
            input_schema={"type": "object", "properties": {}},
            output_schema={"type": "object", "properties": {"result": {"type": "object"}}},
            required_evidence=[], 
            allowed_state=["COMPLETED"], 
            produces=[], 
            visualizations=[], 
            artifacts=[],
            execution_target="SUBSYSTEM", 
            produces_result=False
        ))

        self.register(CapabilityContract(
            capability_id="generate_chart",
            description="Generates a chart or visual representation of the data.",
            input_schema={"type": "object", "properties": {}},
            output_schema={"type": "object", "properties": {}},
            required_evidence=[], allowed_state=[], produces=[], visualizations=["Intelligence Network"], artifacts=[],
            execution_target="SUBSYSTEM",
            runtime_subsystem=["VisualizationEngine"],
            canonical_em=None
        ))

        self.register(CapabilityContract(
            capability_id="generate_presentation",
            description="Generates a presentation artifact.",
            input_schema={"type": "object", "properties": {}},
            output_schema={"type": "object", "properties": {}},
            required_evidence=[], allowed_state=[], produces=[], visualizations=["Story Canvas"], artifacts=["PPTX"],
            execution_target="SUBSYSTEM",
            runtime_subsystem=["StoryEngine", "ArtifactEngine"],
            canonical_em="EM Publisher",
            produces_result=True
        ))

        self.register(CapabilityContract(
            capability_id="compare_entities",
            description="Compares multiple entities to find their differences.",
            input_schema={"type": "object", "properties": {}},
            output_schema={"type": "object", "properties": {}},
            required_evidence=[], allowed_state=[], produces=[], visualizations=["Compensation Surface"], artifacts=[],
            execution_target="EM",
            target_em_id="RANKING",
            canonical_em="EM Prescriptor"
        ))

        self.register(CapabilityContract(
            capability_id="adjust_acfl_weights",
            description="Adjusts the ACFL compensatory weights for ranking recalculation.",
            input_schema={"type": "object", "properties": {"cost": {"type": "number"}, "risk": {"type": "number"}}},
            output_schema={"type": "object", "properties": {}},
            required_evidence=[], allowed_state=[], produces=[], visualizations=[], artifacts=[],
            execution_target="EM",
            target_em_id="RANKING",
            canonical_em="EM Prescriptor"
        ))

        self.register(CapabilityContract(
            capability_id="filter_alternatives",
            description="Filters alternatives based on feasibility or constraints.",
            input_schema={"type": "object", "properties": {"feasible": {"type": "boolean"}}},
            output_schema={"type": "object", "properties": {}},
            required_evidence=[], allowed_state=[], produces=[], visualizations=[], artifacts=[],
            execution_target="EM",
            target_em_id="SELECT",
            canonical_em="EM Prescriptor"
        ))
