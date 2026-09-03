from src.eureka.universe.task_fabric import TaskRegistry, TaskDefinition
from src.eureka.universe.capability_fabric import CapabilityRegistry, CapabilityContract
from src.eureka.universe.orchestrator import WorkOrchestrator
from src.eureka.universe.deepseek_boundary import DeepSeekToolBoundary

def setup_registries():
    tr = TaskRegistry()
    tr.load_defaults()
    
    # Add a Presentation Task for WORK-C
    tr.register(TaskDefinition(
        task_id="pres_creation", name="Presentation Creation", category="CREATIVE",
        description="Create a presentation from evidence.",
        input_types=["PDF", "TEXT"],
        recommended_capabilities=["extract_evidence", "create_story", "generate_presentation"],
        recommended_visualizations=["Story Timeline", "Narrative Canvas"],
        recommended_artifacts=["PPTX"],
        required_governance="NONE"
    ))
    
    cr = CapabilityRegistry()
    cr.load_defaults()
    # Add Story capability mapping to PUBLISHER (or STORY)
    cr.register(CapabilityContract(
        capability_id="create_story",
        description="Creates a narrative story.",
        input_schema={"type": "object", "properties": {}},
        output_schema={"type": "object", "properties": {}},
        required_evidence=[], allowed_state=[], produces=[], visualizations=[], artifacts=[],
        target_em_id="PUBLISHER"
    ))
    # Note: generate_presentation is NOT registered, so it will be a GAP
    
    return tr, cr

def run_mini_test_2():
    tr, cr = setup_registries()
    orchestrator = WorkOrchestrator(tr, cr)
    boundary = DeepSeekToolBoundary(cr)
    
    print("=== MINI-TEST 2: UNIVERSAL ORCHESTRATOR & BOUNDARY ===")
    
    cases = [
        ("WORK-A", "Evalúa estos tres proveedores", "bus_supplier_eval"),
        ("WORK-B", "Evalúa estos trabajos de estudiantes", "edu_eval_work"),
        ("WORK-C", "Necesito una presentación sobre este tema", "pres_creation"),
        ("WORK-D", "Quiero resolver este problema completamente nuevo", "custom_problem"),
    ]
    
    for case_name, intent, task_id in cases:
        print(f"\n--- {case_name} ---")
        print(f"User Intent: '{intent}'")
        
        # Orchestrate
        canonical_state = orchestrator.orchestrate(intent, "AUTO", task_id)
        
        print(f"Task Category: {canonical_state.work.task_category}")
        print(f"Resolved Pipeline: {' -> '.join(canonical_state.resolved_pipeline)}")
        print(f"Visualizations: {canonical_state.active_visualizations}")
        
        # Test Boundary
        print("\nBoundary Checks:")
        # DeepSeek tries to extract evidence
        res = boundary.handle_tool_call("extract_evidence", {})
        print(f"DeepSeek calls 'extract_evidence': {res.get('status')} - {res.get('reason', '')}")
        
        # DeepSeek tries an unknown capability
        res = boundary.handle_tool_call("unknown_capability", {})
        print(f"DeepSeek calls 'unknown_capability': {res.get('status')} - {res.get('reason', '')}")

        # DeepSeek tries to hack execution authority
        # Let's add a malicious capability to the registry just for testing
        cr.register(CapabilityContract(
            capability_id="execute_action",
            description="Executes action",
            input_schema={"type": "object", "properties": {}},
            output_schema={"type": "object", "properties": {}},
            required_evidence=[], allowed_state=[], produces=[], visualizations=[], artifacts=[],
            target_em_id="ACTIONER"
        ))
        res = boundary.handle_tool_call("execute_action", {})
        print(f"DeepSeek calls 'execute_action': {res.get('status')} - {res.get('reason', '')}")

if __name__ == "__main__":
    run_mini_test_2()
