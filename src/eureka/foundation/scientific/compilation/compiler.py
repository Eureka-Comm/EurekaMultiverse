from dataclasses import dataclass
from typing import Union, Optional, List
import ast

from .routing import TaxonomicDecision, TopologicalTracker
from src.eureka.foundation.scientific.specification.formula_spec import FormulaNode

# --- Mathematical IR ---
@dataclass(frozen=True)
class MathVariable:
    name: str

@dataclass(frozen=True)
class MathConstant:
    value: float

@dataclass(frozen=True)
class MathOperation:
    operator: str  # e.g., "ADD", "SUBTRACT", "MULTIPLY", "DIVIDE", "MAX", "NEGATE", "LN", "SQRT"
    left: Union["MathVariable", "MathConstant", "MathOperation"]
    right: Optional[Union["MathVariable", "MathConstant", "MathOperation"]] = None

@dataclass(frozen=True)
class MathematicalFormulaIR:
    formula_id: str
    expression: MathOperation
    # Optional list of variables explicitly declared for primitive formulas
    variables: Optional[List[MathVariable]] = None

# --- Compilation Artifact ---
@dataclass(frozen=True)
class CompilationArtifact:
    formula_id: str
    taxonomy: TaxonomicDecision
    route: str
    admission: bool
    source_ir: MathematicalFormulaIR
    generated_ast: ast.Module
    generated_code: str
    provenance: TopologicalTracker
    verification_status: str
    entrypoint: str
    input_contract: List[str]
    dependencies: List[str]

# --- AST Emitter ---
class PythonASTEmitter:
    """Translate Mathematical IR into a pure Python AST (no eval)."""

    def emit_expression(self, expr: Union[MathVariable, MathConstant, MathOperation, FormulaNode]) -> ast.expr:
        if isinstance(expr, MathVariable):
            return ast.Name(id=expr.name, ctx=ast.Load())
        if isinstance(expr, MathConstant):
            return ast.Constant(value=expr.value)
        if isinstance(expr, MathOperation):
            left_ast = self.emit_expression(expr.left)
            # Unary operators
            if expr.operator == "NEGATE":
                return ast.UnaryOp(op=ast.USub(), operand=left_ast)
            if expr.operator == "LN":
                func = ast.Attribute(value=ast.Name(id='math', ctx=ast.Load()), attr='log', ctx=ast.Load())
                return ast.Call(func=func, args=[left_ast], keywords=[])
            if expr.operator == "EXP":
                func = ast.Attribute(value=ast.Name(id='math', ctx=ast.Load()), attr='exp', ctx=ast.Load())
                return ast.Call(func=func, args=[left_ast], keywords=[])
            if expr.operator == "SQRT":
                func = ast.Attribute(value=ast.Name(id='math', ctx=ast.Load()), attr='sqrt', ctx=ast.Load())
                return ast.Call(func=func, args=[left_ast], keywords=[])
            # Binary operators need a right operand
            if expr.right is None:
                raise ValueError(f"Binary operator {expr.operator} missing right operand")
            right_ast = self.emit_expression(expr.right)
            if expr.operator == "ADD":
                op = ast.Add()
            elif expr.operator == "SUBTRACT":
                op = ast.Sub()
            elif expr.operator == "MULTIPLY":
                op = ast.Mult()
            elif expr.operator == "DIVIDE":
                op = ast.Div()
            elif expr.operator == "MAX":
                return ast.Call(func=ast.Name(id='max', ctx=ast.Load()), args=[left_ast, right_ast], keywords=[])
            else:
                raise ValueError(f"Unsupported binary operator: {expr.operator}")
            return ast.BinOp(left=left_ast, op=op, right=right_ast)
        if isinstance(expr, FormulaNode):
            func_name = f"{expr.formula_id.lower().replace('-', '_')}_evaluate"
            func = ast.Name(id=func_name, ctx=ast.Load())
            args_ast = [self.emit_expression(arg) for arg in expr.args]
            return ast.Call(func=func, args=args_ast, keywords=[])
        raise ValueError(f"Unsupported expression node type: {type(expr)}")

    def emit_function(self, ir: MathematicalFormulaIR) -> ast.Module:
        """Create a module with a single evaluate(value) function.
        The real function name and arguments are injected by the compiler classes.
        """
        body_expr = self.emit_expression(ir.expression)
        return_stmt = ast.Return(value=body_expr)
        args = ast.arguments(posonlyargs=[], args=[ast.arg(arg='value')], kwonlyargs=[], kw_defaults=[], defaults=[])
        func_def = ast.FunctionDef(name='evaluate', args=args, body=[return_stmt], decorator_list=[], returns=None)
        module = ast.Module(body=[func_def], type_ignores=[])
        ast.fix_missing_locations(module)
        return module

# --- Compilers ---
class PrimitiveCompiler:
    """Compile primitive formulas (no nested FormulaNode calls)."""

    def __init__(self):
        self.emitter = PythonASTEmitter()

    def _collect_variables(self, expr) -> List[str]:
        if isinstance(expr, MathVariable):
            return [expr.name]
        if isinstance(expr, MathOperation):
            names = self._collect_variables(expr.left)
            if expr.right:
                names += self._collect_variables(expr.right)
            return names
        return []

    def compile(self, ir: MathematicalFormulaIR, routing_decision, is_admitted: bool, tracker: TopologicalTracker) -> CompilationArtifact:
        if not is_admitted:
            raise RuntimeError("Cannot compile formula: Admission Gate rejected the formula.")
        if routing_decision.target_route != "PRIMITIVE":
            raise RuntimeError(f"PrimitiveCompiler cannot compile route: {routing_decision.target_route}")
        if tracker:
            tracker.increment_metric("compiler_invocations")

        # Determine input variable names
        if ir.variables:
            input_vars = [v.name for v in ir.variables]
        else:
            input_vars = list(dict.fromkeys(self._collect_variables(ir.expression)))
        # Build AST with proper signature
        args = [ast.arg(arg=name, annotation=ast.Name(id='float', ctx=ast.Load())) for name in input_vars]
        func_name = f"{ir.formula_id.lower().replace('-', '_')}_evaluate"
        return_ast = ast.Return(value=self.emitter.emit_expression(ir.expression))
        func_def = ast.FunctionDef(name=func_name, args=ast.arguments(posonlyargs=[], args=args, kwonlyargs=[], kw_defaults=[], defaults=[]), body=[return_ast], decorator_list=[], returns=ast.Name(id='float', ctx=ast.Load()))
        body = [ast.Import(names=[ast.alias(name='math', asname=None)]), func_def]
        module = ast.Module(body=body, type_ignores=[])
        ast.fix_missing_locations(module)
        code = ast.unparse(module)
        if tracker:
            tracker.log("COMPILE", "SUCCESS", "AST generation successful", "Python Source", "PASS")
        return CompilationArtifact(
            formula_id=ir.formula_id,
            taxonomy=routing_decision.taxonomy,
            route=routing_decision.target_route,
            admission=is_admitted,
            source_ir=ir,
            generated_ast=module,
            generated_code=code,
            provenance=tracker,
            verification_status="COMPILED",
            entrypoint=func_name,
            input_contract=input_vars,
            dependencies=[]
        )

class DerivedCompiler:
    """Compile derived formulas (may reference other formulas)."""

    def __init__(self):
        self.emitter = PythonASTEmitter()

    def _collect_variables(self, expr) -> List[str]:
        if isinstance(expr, MathVariable):
            return [expr.name]
        if isinstance(expr, MathOperation):
            names = self._collect_variables(expr.left)
            if expr.right:
                names += self._collect_variables(expr.right)
            return names
        if isinstance(expr, FormulaNode):
            names = []
            for arg in expr.args:
                names += self._collect_variables(arg)
            return names
        return []

    def compile(self, ir: MathematicalFormulaIR, routing_decision, is_admitted: bool, tracker: TopologicalTracker) -> CompilationArtifact:
        if not is_admitted:
            raise RuntimeError("Cannot compile formula: Admission Gate rejected the formula.")
        if routing_decision.target_route != "DERIVED":
            raise RuntimeError(f"DerivedCompiler cannot compile route: {routing_decision.target_route}")
        if tracker:
            tracker.increment_metric("compiler_invocations")
        if not ir.expression:
            raise RuntimeError(f"Formula {ir.formula_id} has no explicit DAG expression. Cannot compile.")
        # Input variables handling
        if ir.variables:
            input_vars = [v.name for v in ir.variables]
        else:
            input_vars = list(dict.fromkeys(self._collect_variables(ir.expression)))
            if not input_vars:
                input_vars = ["value"]
        args = [ast.arg(arg=name, annotation=ast.Name(id='float', ctx=ast.Load())) for name in input_vars]
        func_name = f"{ir.formula_id.lower().replace('-', '_')}_evaluate"
        return_ast = ast.Return(value=self.emitter.emit_expression(ir.expression))
        func_def = ast.FunctionDef(name=func_name, args=ast.arguments(posonlyargs=[], args=args, kwonlyargs=[], kw_defaults=[], defaults=[]), body=[return_ast], decorator_list=[], returns=ast.Name(id='float', ctx=ast.Load()))
        body = [ast.Import(names=[ast.alias(name='math', asname=None)]), func_def]
        module = ast.Module(body=body, type_ignores=[])
        ast.fix_missing_locations(module)
        code = ast.unparse(module)
        if tracker:
            tracker.log("COMPILE", "SUCCESS", "AST generation successful", "Python Source", "PASS")
        return CompilationArtifact(
            formula_id=ir.formula_id,
            taxonomy=routing_decision.taxonomy,
            route=routing_decision.target_route,
            admission=is_admitted,
            source_ir=ir,
            generated_ast=module,
            generated_code=code,
            provenance=tracker,
            verification_status="UNVERIFIED",
            entrypoint=func_name,
            input_contract=input_vars,
            dependencies=[]
        )
