# Canonical Intermediate Representation (CIR) definitions

from dataclasses import dataclass
from typing import Tuple

# Import placeholder identifier/value object types (to be defined later)
# For now we use simple string aliases for illustration

@dataclass(frozen=True)
class CanonicalIntermediateRepresentation:
    """Pure compiled representation derived from the scientific semantic model.
    It contains no packaging metadata, hashes, signatures, or runtime information.
    """
    descriptor: "ModuleDescriptor"
    capabilities: Tuple["ModuleCapability", ...]
    inputs: Tuple["ModuleInput", ...]
    outputs: Tuple["ModuleOutput", ...]
    lifecycle: "ModuleLifecycle"
    manifest: "CanonicalModuleManifest"

# Alias for convenience in the rest of the codebase
CIR = CanonicalIntermediateRepresentation
