from src.eureka.universe.task_fabric import TaskRegistry
from src.eureka.universe.work_model import EurekaWork
from src.eureka.universe.capability_fabric import CapabilityRegistry
from src.eureka.universe.canonical_state import CanonicalWorkState

def run_mini_test():
    print("--- MINI TEST: PIPELINE RESOLUTION ---")
    
    # 1. User Input
    user_input = "Compare these three suppliers"
    print(f"INPUT: {user_input}")
    
    # 2. Task Fabric determines this is a Business Supplier Evaluation
    task_registry = TaskRegistry()
    task_registry.load_defaults()
    task_def = task_registry.resolve("bus_supplier_eval")
    print(f"TaskDefinition: {task_def.name} ({task_def.category})")
    
    # 3. Create EurekaWork
    work = EurekaWork(
        work_id="WORK-SUPPLIER-001",
        title="Supplier Comparison Q3",
        user_intent=user_input,
        task_category=task_def.category,
        problem_statement=task_def.description,
        requested_capabilities=task_def.recommended_capabilities
    )
    print(f"EurekaWork created: {work.work_id}")
    
    # 4. Resolve Capabilities and EMs
    cap_registry = CapabilityRegistry()
    cap_registry.load_defaults()
    
    pipeline = []
    print("\nResolving pipeline...")
    for cap_id in work.requested_capabilities:
        cap = cap_registry.resolve(cap_id)
        if cap:
            print(f"  -> Capability: {cap.capability_id} maps to EM: {cap.target_em_id}")
            pipeline.append(cap.target_em_id)
            work.selected_ems.append(cap.target_em_id)
        else:
            print(f"  -> Capability: {cap_id} -> GAP")
    
    # Ensure standard cognitive EM prefix
    resolved_pipeline = ["COGNITION", "SEMANTIC"] + pipeline
    # Ensure governance suffix (from TaskDef)
    if task_def.required_governance == "AUTHORITY_REQUIRED":
        resolved_pipeline += ["FREEZE", "HUMAN_EXTERNAL", "UNFREEZE", "ACTIONER"]
    
    print(f"Resolved Pipeline: {' -> '.join(resolved_pipeline)}")
    
    # 5. Build Canonical State
    canonical_state = CanonicalWorkState(
        work=work,
        resolved_pipeline=resolved_pipeline,
        active_visualizations=task_def.recommended_visualizations
    )
    
    print("\nCanonical Work State successfully built.")
    print(f"Active Visualizations: {canonical_state.active_visualizations}")

if __name__ == "__main__":
    run_mini_test()
