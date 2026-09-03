from typing import Dict, Any, List
import types
import ast
from src.eureka.foundation.scientific.compilation.compiler import CompilationArtifact

class RuntimeAssemblyError(Exception):
    """Raised when an artifact cannot be securely assembled into the runtime."""
    pass

class ExecutableRuntimeCapability:
    """
    Safely loaded mathematical capability.
    Provides execution isolated from the EM core.
    """
    def __init__(self, artifact: CompilationArtifact, registry: 'CapabilityRegistry'):
        self.formula_id = artifact.formula_id
        self.entrypoint = artifact.entrypoint
        self.input_contract = artifact.input_contract
        self.dependencies = artifact.dependencies
        self.provenance = artifact.provenance
        
        # 1. Resolve Dependencies
        self.resolved_deps = {}
        for dep_id in self.dependencies:
            dep_capability = registry.resolve(dep_id)
            if not dep_capability:
                raise RuntimeAssemblyError(f"Missing required dependency: {dep_id}")
            self.resolved_deps[dep_capability.entrypoint] = dep_capability.get_callable()
            
        # 2. Compile AST natively (No eval/exec strings)
        try:
            # We must compile the AST node.
            # ast.fix_missing_locations is already called by the compiler
            compiled_bytecode = compile(artifact.generated_ast, filename=f"<artifact_{self.formula_id}>", mode="exec")
        except Exception as e:
            raise RuntimeAssemblyError(f"Failed to compile AST for {self.formula_id}: {str(e)}")
            
        # 3. Create isolated module namespace
        import math
        self.module = types.ModuleType(f"eureka_capability_{self.formula_id}")
        self.module.__dict__["math"] = math
        
        # 4. Inject Dependencies into the module's namespace
        for dep_name, dep_func in self.resolved_deps.items():
            self.module.__dict__[dep_name] = dep_func
            
        # 5. Execute bytecode within module
        try:
            exec(compiled_bytecode, self.module.__dict__)
        except Exception as e:
            raise RuntimeAssemblyError(f"Failed to load module namespace for {self.formula_id}: {str(e)}")
            
        # 6. Validate Entrypoint exists
        if self.entrypoint not in self.module.__dict__:
            raise RuntimeAssemblyError(f"Entrypoint '{self.entrypoint}' not found in loaded artifact for {self.formula_id}")

    def get_callable(self):
        return self.module.__dict__[self.entrypoint]

    def execute(self, **kwargs) -> float:
        """Executes the capability with strict contract checking."""
        # Check input contract
        for param in self.input_contract:
            if param not in kwargs:
                raise RuntimeAssemblyError(f"Missing required parameter '{param}' in capability {self.formula_id}")
                
        # Invoke
        func = self.get_callable()
        try:
            result = func(**kwargs)
            
            # Log provenance trace if tracker exists
            if self.provenance:
                self.provenance.log("EXECUTION", "SUCCESS", f"Executed {self.formula_id}", "Runtime", "PASS")
                
            return result
        except Exception as e:
            if self.provenance:
                self.provenance.log("EXECUTION", "FAILURE", str(e), "Runtime", "FAIL")
            raise RuntimeAssemblyError(f"Execution failed for {self.formula_id}: {str(e)}")


class CapabilityRegistry:
    """
    Global capability registry where CompilationArtifacts are registered and resolved.
    Enforces Fail-Closed admission.
    """
    def __init__(self):
        self._artifacts: Dict[str, CompilationArtifact] = {}
        self._capabilities: Dict[str, ExecutableRuntimeCapability] = {}

    def register(self, artifact: CompilationArtifact):
        """Registers a compiled artifact."""
        if not artifact.admission:
            raise RuntimeAssemblyError(f"Artifact {artifact.formula_id} was not admitted.")
        if artifact.verification_status not in ["COMPILED", "DERIVED_COMPILED"]:
            raise RuntimeAssemblyError(f"Artifact {artifact.formula_id} has invalid status: {artifact.verification_status}")
            
        self._artifacts[artifact.formula_id] = artifact

    def resolve(self, formula_id: str) -> ExecutableRuntimeCapability:
        """Resolves an artifact into a runtime capability."""
        if formula_id in self._capabilities:
            return self._capabilities[formula_id]
            
        if formula_id not in self._artifacts:
            raise RuntimeAssemblyError(f"Failed to resolve required capability {formula_id}")
            
        artifact = self._artifacts[formula_id]
        
        # Build it
        capability = ExecutableRuntimeCapability(artifact, self)
        self._capabilities[formula_id] = capability
        return capability
