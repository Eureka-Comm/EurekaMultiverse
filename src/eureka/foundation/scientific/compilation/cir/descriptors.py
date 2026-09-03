# Descriptors for module identity

from dataclasses import dataclass

# Simple identifier value objects (placeholders, to be refined later)

@dataclass(frozen=True)
class ModuleId:
    value: str

@dataclass(frozen=True)
class ModuleNamespace:
    value: str

@dataclass(frozen=True)
class ModuleVersion:
    value: str

# ModuleDescriptor combines the identifiers

@dataclass(frozen=True)
class ModuleDescriptor:
    module_id: ModuleId
    namespace: ModuleNamespace
    version: ModuleVersion
