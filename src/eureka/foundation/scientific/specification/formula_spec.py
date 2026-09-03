from dataclasses import dataclass, field
from typing import List, Tuple, Union, Optional

# --- Abstract Mathematical Expression Tree ---
@dataclass(frozen=True)
class ExpressionNode:
    pass

@dataclass(frozen=True)
class VariableNode(ExpressionNode):
    name: str

@dataclass(frozen=True)
class ConstantNode(ExpressionNode):
    value: float

@dataclass(frozen=True)
class OperatorNode(ExpressionNode):
    operator: str
    left: ExpressionNode
    right: Optional[ExpressionNode] = None

@dataclass(frozen=True)
class FormulaNode(ExpressionNode):
    formula_id: str
    args: Tuple[ExpressionNode, ...]

# --- Specification Model ---
@dataclass(frozen=True)
class FormulaSpecification:
    formula_id: str
    scientific_identity: str
    arity: str
    domain: Tuple[str, ...]
    cardinality: str
    expression: ExpressionNode
    dependencies: Tuple[str, ...] = ()
    version: str = "1.0.0"
    
    # Metadata that maps to classification evidence (but is not the classification itself)
    has_own_compatible_generator: bool = False
    is_homogeneous_topology: bool = False
    primitive_compatible_mapping: bool = False
    requires_composition: bool = False
    requires_dag: bool = False
    has_external_dependency: bool = False
