from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, Field

class MathematicalExpression(BaseModel):
    """
    Base class for the Mathematical Abstract Syntax Tree (AST).
    Only strictly certified operations are allowed.
    """
    operator: str
    authority_reference: str = Field(default="UNKNOWN", description="Documentary authority backing this operator")

class Variable(MathematicalExpression):
    operator: Literal["VARIABLE"] = "VARIABLE"
    name: str

class Constant(MathematicalExpression):
    operator: Literal["CONSTANT"] = "CONSTANT"
    value: float

class GCLVMembership(MathematicalExpression):
    operator: Literal["GCLV"] = "GCLV"
    input: Union['MathematicalExpression', 'Variable', 'Constant']
    alpha: float
    gamma: float
    m: float
    authority_reference: str = "Tesis Carlos Llorente Eq 4.17"

class GMBCLConjunction(MathematicalExpression):
    operator: Literal["GMBCL"] = "GMBCL"
    inputs: List[Union['MathematicalExpression', 'Variable', 'Constant', 'GCLVMembership', 'ReichenbachImplication', 'GMBCLConjunction']]
    authority_reference: str = "rafa_dump.txt Formula 9"

class ReichenbachImplication(MathematicalExpression):
    operator: Literal["REICHENBACH"] = "REICHENBACH"
    antecedent: Union['MathematicalExpression', 'Variable', 'Constant', 'GCLVMembership', 'GMBCLConjunction', 'ReichenbachImplication']
    consequent: Union['MathematicalExpression', 'Variable', 'Constant', 'GCLVMembership', 'GMBCLConjunction', 'ReichenbachImplication']
    authority_reference: str = "Tesis Carlos Llorente p. 52"

# Update forward refs
GCLVMembership.model_rebuild()
GMBCLConjunction.model_rebuild()
ReichenbachImplication.model_rebuild()

AnyMathematicalExpression = Union[
    Variable,
    Constant,
    GCLVMembership,
    GMBCLConjunction,
    ReichenbachImplication
]
