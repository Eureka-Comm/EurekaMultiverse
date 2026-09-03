import os
import hashlib
import mimetypes
from typing import List, Dict

from src.eureka.universe.canonical_state import Evidence, CanonicalWorkState


def _derive_extension(filename: str) -> str:
    """Return the file extension (including leading dot) in lower case."""
    _, ext = os.path.splitext(filename)
    return ext.lower()


def _derive_media_type(extension: str) -> str:
    """Return a MIME type based on extension; fallback to 'application/octet-stream'."""
    mime, _ = mimetypes.guess_type(f"dummy{extension}")
    return mime or "application/octet-stream"


def _file_size(path: str) -> int:
    return os.path.getsize(path)


def _file_sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def construct_evidence(evidence_input: Dict) -> Evidence:
    """Validate an EvidenceInput dictionary and return a canonical ``Evidence`` instance.

    Required keys:
        evidence_id, filename, content_reference, media_type, source, ingestion_status
    The function derives ``extension``, ``size`` and ``sha256`` from the referenced file.
    If validation fails, a ``ValueError`` is raised.
    """
    required = [
        "evidence_id",
        "filename",
        "content_reference",
        "media_type",
        "source",
        "ingestion_status",
    ]
    for key in required:
        if key not in evidence_input:
            raise ValueError(f"EvidenceInput missing required field: {key}")

    content_ref: str = evidence_input["content_reference"]
    if not isinstance(content_ref, str) or not os.path.isabs(content_ref):
        raise ValueError("content_reference must be an absolute path string")
    if not os.path.isfile(content_ref):
        raise ValueError(f"File not found at content_reference: {content_ref}")
    if not os.access(content_ref, os.R_OK):
        raise ValueError(f"File not readable at content_reference: {content_ref}")

    # Derive additional fields
    ext = _derive_extension(evidence_input["filename"])
    size = _file_size(content_ref)
    sha256 = _file_sha256(content_ref)

    if evidence_input["ingestion_status"] != "INGESTED":
        raise ValueError("ingestion_status must be 'INGESTED'")

    ev = Evidence(
        evidence_id=evidence_input["evidence_id"],
        filename=evidence_input["filename"],
        media_type=evidence_input["media_type"],
        extension=ext,
        size=size,
        sha256=sha256,
        source=evidence_input["source"],
        ingestion_status=evidence_input["ingestion_status"],
        content_reference=content_ref,
        created_at="",
        provenance=[],
        extraction_status="NOT_STARTED",
        extraction_error=None,
        extraction_reason_code=None,
    )
    return ev


def attach_evidence_to_canonical(canonical: CanonicalWorkState, evidence_list: List[Dict]) -> CanonicalWorkState:
    """Convert a list of EvidenceInput dicts to ``Evidence`` objects and attach them to ``canonical``.

    The ``canonical.evidence`` attribute is replaced with the newly built list.
    Returns the modified ``canonical`` for convenience.
    """
    built: List[Evidence] = []
    for inp in evidence_list:
        built.append(construct_evidence(inp))
    canonical.evidence = built
    return canonical
