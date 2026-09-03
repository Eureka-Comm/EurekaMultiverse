from dataclasses import dataclass
from typing import Tuple

# Placeholder entity and relation classes for the scientific language AST

@dataclass(frozen=True)
class Entity:
    name: str
    attributes: Tuple[str, ...] = ()

@dataclass(frozen=True)
class Relation:
    source: str
    target: str
    kind: str


@dataclass(frozen=True)
class ScientificSemanticModel:
    """Semantic model produced by the parser from the scientific language.
    This is the high‑level, language‑specific representation (AST‑like) that will
    later be lowered to a CanonicalIntermediateRepresentation.
    """
    entities: Tuple[Entity, ...]
    relations: Tuple[Relation, ...]
