from src.eureka.foundation.scientific.specification.formula_spec import (
    FormulaSpecification, ExpressionNode, VariableNode, ConstantNode, OperatorNode, FormulaNode
)
from src.eureka.foundation.scientific.compilation.compiler import (
    MathematicalFormulaIR, MathOperation, MathConstant, MathVariable
)
from src.eureka.foundation.scientific.compilation.routing import StructuralEvidence

class GenericIRBuilder:
    """Translates an agnostic FormulaSpecification into actionable Compilation IR."""
    
    @staticmethod
    def _translate_expression(node: ExpressionNode):
        if isinstance(node, VariableNode):
            return MathVariable(node.name)
        elif isinstance(node, ConstantNode):
            return MathConstant(node.value)
        elif isinstance(node, OperatorNode):
            left = GenericIRBuilder._translate_expression(node.left)
            right = GenericIRBuilder._translate_expression(node.right) if node.right else None
            return MathOperation(node.operator, left, right)
        elif isinstance(node, FormulaNode):
            # Translate args
            translated_args = tuple(GenericIRBuilder._translate_expression(arg) for arg in node.args)
            return type(node)(formula_id=node.formula_id, args=translated_args)
        raise ValueError(f"Unknown expression node type: {type(node)}")
        
    @staticmethod
    def build_ir(spec: FormulaSpecification) -> MathematicalFormulaIR:
        """Translates the spec expression into MathematicalFormulaIR"""
        translated_expr = GenericIRBuilder._translate_expression(spec.expression)
        return MathematicalFormulaIR(
            formula_id=spec.formula_id,
            expression=translated_expr
        )
        
    @staticmethod
    def extract_evidence(spec: FormulaSpecification) -> StructuralEvidence:
        """Projects observational traits from the specification into StructuralEvidence."""
        return StructuralEvidence(
            arity=spec.arity,
            has_own_compatible_generator=spec.has_own_compatible_generator,
            is_homogeneous_topology=spec.is_homogeneous_topology,
            primitive_compatible_mapping=spec.primitive_compatible_mapping,
            has_external_dependency=len(spec.dependencies) > 0,
            requires_composition=spec.requires_composition,
            requires_dag=spec.requires_dag
        )
