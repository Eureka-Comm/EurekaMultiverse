from typing import List, Dict, Optional
from pydantic import BaseModel, Field

class TaskDefinition(BaseModel):
    task_id: str
    name: str
    category: str
    description: str
    input_types: List[str]
    recommended_capabilities: List[str]
    recommended_visualizations: List[str]
    recommended_artifacts: List[str]
    required_governance: str

class TaskRegistry:
    def __init__(self):
        self._tasks: Dict[str, TaskDefinition] = {}

    def register(self, task: TaskDefinition):
        self._tasks[task.task_id] = task

    def get_by_category(self, category: str) -> List[TaskDefinition]:
        return [t for t in self._tasks.values() if t.category.upper() == category.upper()]

    def resolve(self, task_id: str) -> Optional[TaskDefinition]:
        return self._tasks.get(task_id)

    def load_defaults(self):
        # Education
        self.register(TaskDefinition(
            task_id="edu_eval_work", name="Evaluate Student Work", category="EDUCATION",
            description="Evaluates assignments against a rubric.",
            input_types=["PDF", "DOCX", "TEXT"],
            recommended_capabilities=["extract_evidence", "compare_entities", "evaluate_alternatives"],
            recommended_visualizations=["Evidence Map", "Rubric Matrix", "Score Distribution"],
            recommended_artifacts=["Report", "Rubric"],
            required_governance="HUMAN_IN_THE_LOOP"
        ))
        # Business
        self.register(TaskDefinition(
            task_id="bus_supplier_eval", name="Supplier Evaluation", category="BUSINESS",
            description="Compare and select suppliers based on risk and utility.",
            input_types=["PDF", "XLSX"],
            recommended_capabilities=["analyze_dataset", "evaluate_alternatives", "generate_chart"],
            recommended_visualizations=["Decision Field", "Phase Space", "Temporal Rail"],
            recommended_artifacts=["Executive Story", "Decision Story"],
            required_governance="AUTHORITY_REQUIRED"
        ))
        # Scientific
        self.register(TaskDefinition(
            task_id="sci_hypothesis", name="Hypothesis Analysis", category="SCIENTIFIC",
            description="Analyze evidence to validate a scientific hypothesis.",
            input_types=["DATASET", "CSV", "PDF"],
            recommended_capabilities=["extract_evidence", "analyze_dataset", "generate_chart"],
            recommended_visualizations=["Scientific Surface", "Evidence Graph"],
            recommended_artifacts=["Scientific Report", "Technical Story"],
            required_governance="SCIENTIFIC_VALIDATION_REQUIRED"
        ))
        # Other
        self.register(TaskDefinition(
            task_id="custom_problem", name="Custom Problem", category="OTHER",
            description="An arbitrary user problem that doesn't fit standard templates.",
            input_types=["ANY"],
            recommended_capabilities=["inspect_document"],
            recommended_visualizations=["EM Flow", "Inspector"],
            recommended_artifacts=["JSON"],
            required_governance="DYNAMIC"
        ))
