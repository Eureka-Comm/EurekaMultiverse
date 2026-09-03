from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class DataProvenanceStatus(str, Enum):
    REAL = "REAL"
    DERIVED = "DERIVED"
    MOCK = "MOCK"
    SIMULATED = "SIMULATED"
    GAP = "GAP"
    UNAVAILABLE = "UNAVAILABLE"

class ProvenanceRecord(BaseModel):
    source_id: str
    status: DataProvenanceStatus
    description: str
    generated_at: str

class EurekaWork(BaseModel):
    """
    Universal representation of any work executed by EUREKA.
    """
    work_id: str
    title: str
    user_intent: str
    task_category: str
    problem_statement: str

    inputs: List[Dict[str, Any]] = Field(default_factory=list)
    evidence: List[Dict[str, Any]] = Field(default_factory=list)

    objective: Optional[str] = None
    constraints: List[str] = Field(default_factory=list)

    requested_capabilities: List[str] = Field(default_factory=list)
    selected_ems: List[str] = Field(default_factory=list)

    pipeline_state: str = "INITIALIZED"
    decision_state: str = "PENDING"
    
    artifacts: List[str] = Field(default_factory=list)
    provenance_log: List[ProvenanceRecord] = Field(default_factory=list)

    governance_state: str = "UNGOVERNED"
    visualization_state: str = "DEFAULT"
    status: str = "OPEN"
