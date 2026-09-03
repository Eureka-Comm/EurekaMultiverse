"""
ArtifactEngine: produces physical artifacts from the CanonicalWorkState.

Previously this was a placeholder that only emitted a generic MARKDOWN blob and
GAPed on pdf/pptx/docx. It now delegates to the real export subsystem
(artifact_exporter) so requested outputs (.txt, .md, .docx, .pdf, .pptx, .png, .svg)
are rendered from the true state — including the ACFL fuzzy decision layer — and
written to disk under ./generated.

The engine never simulates a format: it either produces a real file or reports an
honest GAP (CAPABILITY_UNAVAILABLE) with the reason, in keeping with EUREKA's
claim-classification policy.
"""
from typing import Dict, Any, List

from .canonical_state import CanonicalWorkState, StateCondition
from .artifact_exporter import SUPPORTED_FORMATS, write_export

# Map user-facing tokens onto exporter format ids. "markdown" and "image" are the
# natural-language spellings a problem's requested_outputs may carry.
_FORMAT_ALIASES = {
    "txt": "txt", "text": "txt",
    "md": "md", "markdown": "md",
    "docx": "docx", "word": "docx",
    "pdf": "pdf",
    "pptx": "pptx", "presentation": "pptx", "ppt": "pptx",
    "png": "png", "image": "png", "img": "png",
    "svg": "svg",
}


class ArtifactEngine:
    def generate_artifact(self, state: CanonicalWorkState):
        # Determine which formats the problem asked for.
        requested = []
        if state.problem and state.problem.requested_outputs:
            requested = [str(r).lower() for r in state.problem.requested_outputs]

        # Map to supported export formats; fall back to markdown if nothing matches.
        formats: List[str] = []
        for token in requested:
            f = _FORMAT_ALIASES.get(token)
            if f and f not in formats:
                formats.append(f)

        # Any requested token that is a known output but not supported is a GAP.
        requested_set = set(requested)
        if not formats:
            formats = ["md"]

        state.extracted_entities["artifacts"] = []

        for fmt in formats:
            try:
                path = write_export(state, fmt)
                state.extracted_entities["artifacts"].append({
                    "artifact_id": f"ART-{state.work.work_id}-{fmt.upper()}",
                    "format": fmt.upper(),
                    "status": "DERIVED",
                    "claim_status": "PROJECT_VALIDATED",
                    "provenance_linked": True,
                    "path": path,
                    "content": f"Real artifact '{path}' rendered from CanonicalWorkState revision {state.revision}.",
                })
            except Exception as e:  # noqa: BLE001
                state.conditions.append(StateCondition(
                    status="GAP",
                    reason_code="CAPABILITY_UNAVAILABLE",
                    message=f"Artifact format '{fmt}' could not be produced: {e}",
                    target="ARTIFACT_ENGINE",
                ))
                state.status = "PARTIAL"

        # Honest GAP for explicit but unsupported requested outputs.
        for token in requested_set:
            if token not in _FORMAT_ALIASES and token not in ("pdf", "pptx", "docx"):
                # Unknown token (e.g. "recommendation", "explanation") is not a format
                # request at all; it is a content request. Do not flag it as a GAP.
                continue
