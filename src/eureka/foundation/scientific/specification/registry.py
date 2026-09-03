from typing import Dict, List, Optional
from .formula_spec import FormulaSpecification

class RegistryError(Exception):
    pass

class FormulaRegistry:
    """Immutable Registry for Formula Specifications"""
    def __init__(self):
        # Maps formula_id -> (maps version -> FormulaSpecification)
        self._store: Dict[str, Dict[str, FormulaSpecification]] = {}
        
    def register(self, spec: FormulaSpecification) -> None:
        if spec.formula_id not in self._store:
            self._store[spec.formula_id] = {}
            
        if spec.version in self._store[spec.formula_id]:
            raise RegistryError(f"Duplicate registration: Formula {spec.formula_id} v{spec.version} already exists. Silent overwrites are forbidden.")
            
        self._store[spec.formula_id][spec.version] = spec
        
    def get(self, formula_id: str, version: Optional[str] = None) -> FormulaSpecification:
        if formula_id not in self._store:
            raise RegistryError(f"Formula {formula_id} not found in registry.")
            
        versions = self._store[formula_id]
        if not versions:
            raise RegistryError(f"Formula {formula_id} has no registered versions.")
            
        if version is None:
            # Get latest version (using string max is basic but works for semantic versioning assuming simple format)
            # For exact deterministic resolution we just pick the latest registered version string chronologically
            # or require explicit version. Let's pick the highest version key.
            version = max(versions.keys())
            
        if version not in versions:
            raise RegistryError(f"Formula {formula_id} v{version} not found in registry.")
            
        return versions[version]
        
    def exists(self, formula_id: str, version: Optional[str] = None) -> bool:
        if formula_id not in self._store:
            return False
        if version is None:
            return len(self._store[formula_id]) > 0
        return version in self._store[formula_id]
        
    def list(self) -> List[str]:
        return list(self._store.keys())
