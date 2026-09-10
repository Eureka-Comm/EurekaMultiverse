import uvicorn
import traceback
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import uuid
import hashlib
import os
import requests
from dotenv import load_dotenv

load_dotenv()

from src.eureka.universe.capability_fabric import CapabilityRegistry
from src.eureka.universe.orchestrator import WorkOrchestrator
from src.eureka.universe.work_runtime import WorkRuntime
from src.eureka.universe.canonical_state import StateCondition
from src.eureka.universe.artifact_exporter import export_work, SUPPORTED_FORMATS
from fastapi import APIRouter
from src.eureka.universe.scenario_transport import make_router as _make_scenario_router
from src.eureka.universe.scenario_service import ScenarioService
from src.eureka.universe.scenario_repository import ScenarioRepository
from src.eureka.identity import (make_auth_router, make_admin_router, identity_config,
                                 IdentityStore)

app = FastAPI(title="EUREKA Universal Work Runtime")
# Scenario What-If API — mounted ON the single main FastAPI app (no second server/app).
# Router -> ScenarioService -> ScenarioLifecycle -> ScenarioRuntime -> ACFL -> ProjectedArtifact.
# Storage is a bounded, file-backed ScenarioRepository (consistent with the repo's JSON convention).
_scenario_parent = APIRouter()
# work_resolver: Scenario WHAT-IF can resolve a REAL canonical work from the main in-memory store
# (works_db) by work_id — the existing Work authority. The client never supplies canonical state.
_scenario_parent.include_router(
    _make_scenario_router(
        ScenarioService(repository=ScenarioRepository()),
        work_resolver=lambda work_id: works_db.get(work_id),
    )
)
app.include_router(_scenario_parent, prefix="/api")

# CORS is configurable via EUREKA_CORS_ORIGINS (comma-separated origins). The default is a
# safe local-dev allow-list (localhost/127.0.0.1 on the frontend and backend ports) — NOT a
# public wildcard. For a production deployment set EUREKA_CORS_ORIGINS to the real browser
# origin(s). Setting it to "*" is allowed but then credentials are disabled (a browser rejects
# "Allow-Credentials: true" together with "Allow-Origin: *"). Security/runtime config only.
_cors_env = os.getenv("EUREKA_CORS_ORIGINS", "").strip()
if _cors_env == "*":
    _allow_origins = ["*"]
    _allow_credentials = False
else:
    _cors_default = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:8000,http://127.0.0.1:8000"
    _allow_origins = [o.strip() for o in (_cors_env or _cors_default).split(",") if o.strip()]
    _allow_credentials = True

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allow_origins,
    allow_credentials=_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------------------------------------------------------------------------- #
# Security headers (safe, must not break the existing SPA). CSP/HSTS are set at the reverse-proxy
# layer for production; here we apply the response headers that are safe for any origin.
# --------------------------------------------------------------------------- #
_http_only = os.environ.get("EUREKA_SECURE_COOKIES", "false").lower() == "true"

@app.middleware("http")
async def _security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    if _http_only:
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains; preload"
    return response

# Global registries and engines
cr = CapabilityRegistry()
cr.load_defaults()

from src.eureka.universe.orchestrator import WorkOrchestrator
from src.eureka.universe.cognitive_engine import DeepSeekAdapter, TestDoubleCognitiveEngine
from src.eureka.universe.provider_backed_cognitive_engine import ProviderBackedCognitiveEngine
from src.eureka.universe.ollama_provider import OllamaProvider
import os

engine_type = os.getenv("COGNITIVE_ENGINE", "deepseek")
if engine_type == "test_double":
    cognitive_engine = TestDoubleCognitiveEngine()
elif engine_type == "ollama":
    # Select model (default to deepseek-r1:14b) and instantiate provider
    model_name = os.getenv("OLLAMA_MODEL", "deepseek-r1:14b")
    provider = OllamaProvider(model_name=model_name)
    cognitive_engine = ProviderBackedCognitiveEngine(provider)
else:
    cognitive_engine = DeepSeekAdapter()
    
orchestrator = WorkOrchestrator(cr, cognitive_engine)
runtime = WorkRuntime(cognitive_engine=cognitive_engine)

# In-memory store for works and evidence
# The Work authority is DURABLE (restart-safe): `works_db` is a WorkStore, NOT a plain dict. It keeps
# the same dict-like surface (`.get` / `[]` / `in`) used by the work endpoints, the Scenario work_id
# resolver and the evolution API, so there is still ONE Work authority — but it survives a restart.
from src.eureka.universe.work_store import WorkStore
works_db = WorkStore(os.environ.get("EUREKA_WORK_STORAGE_DIR", "data/works"))
evidence_store = {}
evidence_work_index = {} # Map[evidence_id, set(work_ids)]

# Supervised evolution loop (multi-layer orchestrator + HITL gate).
from src.eureka.evolution.api import create_evolution_api
app.include_router(create_evolution_api(works_db))

# --------------------------------------------------------------------------- #
# EUREKA IDENTITY & ACCESS — distinct domain authority (users/sessions/auth-events/tokens/MFA).
# Durable + restart-safe; mounted on the SAME app. USER identity is NEVER canonical identity.
# --------------------------------------------------------------------------- #
_auth_cfg = identity_config()
identity_store = IdentityStore(_auth_cfg["storage_dir"])
app.state.identity_store = identity_store
app.state.identity_cookie = _auth_cfg["session_cookie"]
app.include_router(make_auth_router(identity_store, _auth_cfg))
app.include_router(make_admin_router(identity_store, _auth_cfg))

class IntakeRequest(BaseModel):
    user_intent: str
    attachments: Optional[List[str]] = []
    previous_solution_id: Optional[str] = None

class ToolCallRequest(BaseModel):
    capability: str
    parameters: Dict[str, Any]

def _repopulate_evidence(canonical):
    """Reflect the idempotent evidence snapshot from the global store (no pipeline mutation)."""
    from src.eureka.universe.canonical_state import Evidence, ExtractedEvidence
    canonical.evidence = []
    # Preserve the runtime-created EVI-CONTEXT unit (descriptor.py) even though it is NOT in the
    # evidence_store: it is the governing context source that findings cite as EVI-CONTEXT.
    prev_extracted = dict(canonical.extracted_evidence)
    canonical.extracted_evidence = {}
    for eid in canonical.evidence_ids:
        if eid in evidence_store:
            e_data = evidence_store[eid]
            ev = Evidence(**{k: v for k, v in e_data.items() if k != "extracted_evidence"})
            canonical.evidence.append(ev)
            if "extracted_evidence" in e_data:
                canonical.extracted_evidence[eid] = ExtractedEvidence(**e_data["extracted_evidence"])
    if "EVI-CONTEXT" in prev_extracted:
        canonical.extracted_evidence["EVI-CONTEXT"] = prev_extracted["EVI-CONTEXT"]
    return canonical


def _project_state(canonical, tool_call_id: Optional[str] = None):
    """READ-ONLY projection (F-1): serialize the CanonicalWorkState WITHOUT advancing the runtime.

    A GET /state must NOT mutate execution: no advance, no revision bump, no step.status change,
    no capability execution, no LLM call. The only touch is the idempotent evidence snapshot, which
    mirrors the global truth in evidence_store. This is the model that `GET /api/work/{id}/state`
    and the `retrieve_result` tool-call read; neither may become a write.
    """
    from src.eureka.universe.canonical_state import EMStatus, Evidence
    canonical = _repopulate_evidence(canonical)

    # F-3: consolidate the execution-evidence container into the canonical evidence graph so the
    # frontend's Evidence surface and any provenance query see it. The EV-* execution evidence
    # (created by controlled_execution_adapter / installer) lives in execution_state.evidence, not in
    # the uploaded-evidence registry (EVI-*); without this merge the state's evidence graph is split
    # and the frontend shows an empty Evidence surface despite real artifacts. Idempotent (no dupes).
    if canonical.execution_state and canonical.execution_state.evidence:
        for ev in canonical.execution_state.evidence:
            eid = getattr(ev, "evidence_id", None)
            if eid and eid not in canonical.evidence_ids:
                canonical.evidence_ids.append(eid)
            if eid and not any(e.evidence_id == eid for e in canonical.evidence):
                canonical.evidence.append(Evidence(
                    evidence_id=eid,
                    filename=f"execution_evidence_{getattr(ev, 'action_id', 'action')}",
                    media_type="application/json",
                    size=0,
                    source="action_execution",
                    ingestion_status="EXTRACTED",
                    extraction_status="EXTRACTED",
                    content_reference="execution_state.evidence",
                    provenance=["runtime.execution_state.evidence"],
                ))

    # Calculate holistic EM pipeline state
    canonical_ems = [
        "EM Core", "EM Structurer", "EM Descriptor", "EM Predictor",
        "EM Prescriptor", "EM Actioner", "EM Installer", "EM Publisher"
    ]
    em_pipeline = []
    
    for em_name in canonical_ems:
        em_steps = [s for s in canonical.execution_plan.steps if s.canonical_em == em_name]
        
        if not em_steps:
            # LS60: EM Core and EM Structurer ALWAYS execute during intake (Core formulates the
            # problem, Structurer builds the task network/plan) even though they produce no runtime
            # steps — mark them COMPLETED for a truthful pipeline rail.
            # LS92: any other EM with no runtime steps is NOT APPLICABLE to this operation
            # (e.g. Predictor/Prescriptor/Actioner/Installer are pruned for a KNOWLEDGE_ANSWER
            # routing) — show NOT_APPLICABLE, never a fake COMPLETED.
            status = "COMPLETED" if em_name in ["EM Core", "EM Structurer"] else "NOT_APPLICABLE"
            em_pipeline.append(EMStatus(canonical_em=em_name, status=status, step_ids=[]))
            continue
            
        step_ids = [s.step_id for s in em_steps]
        
        # Calculate aggregated status
        if any(s.status == "FAILED" for s in em_steps):
            status = "FAILED"
        elif any(s.status == "BLOCKED" for s in em_steps):
            status = "BLOCKED"
        elif any(s.status == "GAP" for s in em_steps):
            status = "GAP"
        elif any(s.status == "WAITING_FOR_HUMAN_INPUT" for s in em_steps):
            status = "WAITING_FOR_HUMAN_INPUT"
        elif any(s.status == "WAITING_FOR_EVIDENCE" for s in em_steps):
            status = "WAITING_FOR_EVIDENCE"
        elif any(s.status == "RUNNING" for s in em_steps):
            status = "RUNNING"
        elif any(s.status in ["READY", "PARTIAL"] for s in em_steps):
            if any(s.status == "COMPLETED" for s in em_steps):
                status = "RUNNING" # Partially complete means the EM is still working
            else:
                status = "READY"
        elif any(s.status == "PENDING" for s in em_steps):
            status = "PENDING"
        else:
            status = "COMPLETED"
            
        em_pipeline.append(EMStatus(canonical_em=em_name, status=status, step_ids=step_ids))
        
    canonical.em_pipeline = em_pipeline

    dump = canonical.model_dump(mode="json")
    
    # Transform to fulfill API contract
    dump["tool_call_id"] = tool_call_id
    dump["available_capabilities"] = dump["work"].get("requested_capabilities", [])
    
    dump["work"] = {
        "workId": canonical.work.work_id,
        "taskCategory": canonical.problem.domain_context if canonical.problem else "UNKNOWN", 
        "status": canonical.status,
        "userIntent": canonical.work.user_intent,
        # L-1: preserve the provenance log so consumers can read REAL provenance (not ad-hoc strings).
        "provenance_log": [p.model_dump(mode="json") for p in canonical.work.provenance_log],
    }
    
    dump["state"] = {
        "acfl": dump.get("acfl", {}),
        "feasible_only": dump.get("feasible_only", False),
        "result": dump.get("result", None)
    }
    
    # Ensure active pointers and execution_events are explicitly available
    dump["active_em"] = canonical.active_em
    dump["active_step_id"] = canonical.active_step_id
    dump["active_capability"] = canonical.active_capability
    dump["execution_phase"] = canonical.execution_phase
    dump["waiting_reason"] = canonical.waiting_reason
    dump["waiting_for_evidence_ids"] = canonical.waiting_for_evidence_ids
    dump["execution_progress"] = canonical.execution_progress
    dump["execution_events"] = [e.model_dump(mode="json") for e in canonical.execution_events]
    
    dump["evidence_ids"] = dump.get("evidence_ids", [])
    dump["evidence"] = [e.model_dump(mode="json") for e in canonical.evidence]

    # LS79.4: persist the extracted_evidence graph (incl. EVI-CONTEXT text_blocks) so findings
    # that cite EVI-CONTEXT resolve to the ACTUAL evidence text (not inferred by continuity).
    dump["extracted_evidence"] = {
        eid: ev.model_dump(mode="json") for eid, ev in (canonical.extracted_evidence or {}).items()
    }

    # LS85: expose the governed cognitive story (story_arc) so the frontend receives the
    # authoritative narrative (human decision, sources, authority) — not just a PDF-only artifact.
    _story = getattr(canonical, "extracted_entities", {}) or {}
    dump["story"] = {"arc": _story.get("story_arc", []) or []}

    # LS90: expose the governed OPEN-RESEARCH / "what remains open" projection. This is a
    # Python-derived, read-only view of the leading edge of an open cognitive operation
    # (open research question with NO decision yet). It is computed deterministically from
    # the real canonical fields (unknowns / uncertainty / insufficient information /
    # pending human decision / not-evaluated) — never an LLM output, never a decision.
    from .canonical_state import build_open_research_state
    _open = build_open_research_state(canonical)
    dump["open_research"] = _open.model_dump(mode="json") if _open is not None else None

    return dump


def _process_state(canonical, tool_call_id: Optional[str] = None):
    """WRITE path (F-1): advance the runtime ONE step, then project the resulting state.

    Used by the background execution loop and by write-triggered endpoints (intake / execute /
    tool_call / human_input / evidence). It is NOT used by `GET /state` nor `retrieve_result`
    (both are pure `_project_state` reads), so a poll can never execute a capability.
    """
    canonical = runtime.advance(canonical)
    # Loop 83: refresh the EM Core `core_analysis` projection (status/monitor) after advancing.
    canonical.core_analysis = build_core_analysis(canonical)
    return _project_state(canonical, tool_call_id)

from src.eureka.universe.canonical_state import Evidence, ExtractedEvidence, build_core_analysis
from src.eureka.universe.evidence_fabric import EvidenceParserRegistry
from datetime import datetime, timezone
import asyncio
from fastapi import BackgroundTasks

parser_registry = EvidenceParserRegistry()

async def run_extraction_background(evidence_id: str):
    if evidence_id not in evidence_store:
        return
        
    e_data = evidence_store[evidence_id]
    ev = Evidence(**e_data)
    
    ev.extraction_status = "PARSING"
    evidence_store[evidence_id] = ev.model_dump(mode="json")
    
    # Allow state transition to be observable
    await asyncio.sleep(0.5)
    
    parser = parser_registry.get_parser(ev)
    if not parser:
        ev.extraction_status = "GAP"
        ev.extraction_error = f"No suitable parser found for extension {ev.extension} or MIME {ev.media_type}"
        ev.extraction_reason_code = "UNSUPPORTED_EVIDENCE_FORMAT"
        evidence_store[evidence_id] = ev.model_dump(mode="json")
        return
        
    # Execute extraction
    # Since parsing might be CPU intensive and blocking, in a real system we'd use run_in_executor
    loop = asyncio.get_event_loop()
    try:
        result = await loop.run_in_executor(None, parser.parse, ev)
        
        if result.extracted_evidence:
            ev.extraction_status = "EXTRACTED"
            # If there are warnings (like OCR unavailable on some pages) we could mark PARTIAL
            if result.extracted_evidence.warnings:
                ev.extraction_status = "PARTIAL"
                ev.extraction_error = "; ".join(result.extracted_evidence.warnings)
                ev.extraction_reason_code = "PARTIAL_EXTRACTION"
            
            # Save extracted evidence to a global store (or attach it directly)
            e_data = ev.model_dump(mode="json")
            e_data["extracted_evidence"] = result.extracted_evidence.model_dump(mode="json")
            evidence_store[evidence_id] = e_data
        else:
            # Handle failure or GAP from parser
            ev.extraction_status = "GAP" if result.reason_code in ["OCR_UNAVAILABLE"] else "FAILED"
            ev.extraction_error = result.error or "Unknown extraction failure"
            ev.extraction_reason_code = result.reason_code or "DOCUMENT_PARSE_ERROR"
            evidence_store[evidence_id] = ev.model_dump(mode="json")
            
    except Exception as e:
        traceback.print_exc()
        ev.extraction_status = "FAILED"
        ev.extraction_error = str(e)
        ev.extraction_reason_code = "SYSTEM_ERROR"
        evidence_store[evidence_id] = ev.model_dump(mode="json")
        
    finally:
        # AUTOMATIC RESUME: Wake up any works waiting for this evidence
        if evidence_id in evidence_work_index:
            for w_id in evidence_work_index[evidence_id]:
                if w_id in works_db:
                    canonical = works_db[w_id]
                    # F-1b: the wait is reflected in execution_phase / step.status, NOT in
                    # execution_state (which is never "WAITING_FOR_EVIDENCE"). Re-trigger when a
                    # step is actually blocked on evidence — otherwise purifying GET /state would
                    # strand the flow after evidence arrives.
                    waiting = canonical.execution_phase == "WAITING_FOR_EVIDENCE" \
                        or any(s.status == "WAITING_FOR_EVIDENCE" for s in canonical.execution_plan.steps)
                    if waiting:
                        # Reschedule the background task to re-evaluate now that evidence changed
                        loop = asyncio.get_event_loop()
                        # Use call_soon to schedule background task
                        loop.create_task(run_work_background(w_id))


@app.post("/api/evidence")
async def upload_evidence(file: UploadFile, background_tasks: BackgroundTasks):
    try:
        content = await file.read()
        size = len(content)
        sha256 = hashlib.sha256(content).hexdigest()
        
        evidence_id = f"EVI-{str(uuid.uuid4())[:8].upper()}"
        
        os.makedirs("data/evidence", exist_ok=True)
        file_path = f"data/evidence/{evidence_id}_{file.filename}"
        with open(file_path, "wb") as f:
            f.write(content)
            
        extension = os.path.splitext(file.filename)[1].lower()
        
        ev = Evidence(
            evidence_id=evidence_id,
            filename=file.filename,
            media_type=file.content_type or "application/octet-stream",
            extension=extension,
            size=size,
            sha256=sha256,
            source="USER_UPLOAD",
            ingestion_status="INGESTED",
            extraction_status="NOT_STARTED",
            content_reference=file_path,
            created_at=datetime.now(timezone.utc).isoformat(),
            provenance=[f"Ingested via /api/evidence with SHA256: {sha256}"]
        )
        
        evidence_store[evidence_id] = ev.model_dump(mode="json")
        await run_extraction_background(evidence_id)
        return evidence_store[evidence_id]
        
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail={"reason_code": "SYSTEM_ERROR", "message": str(e)})

class HumanInputRequest(BaseModel):
    request_id: Optional[str] = None
    decision_id: Optional[str] = None
    type: str # 'INFORMATION', 'SELECTION', 'PARAMETER'
    value: Any
    rationale: str = ""

@app.post("/api/work/{work_id}/human_input")
async def provide_human_input(work_id: str, req: HumanInputRequest, background_tasks: BackgroundTasks):
    canonical = works_db.get(work_id)
    if not canonical:
        raise HTTPException(status_code=404, detail="Work not found")
        
    from .canonical_state import HumanKnowledgeContribution, StructuredFinding
    import uuid
    
    contribution = HumanKnowledgeContribution(
        type=req.type,
        value=req.value,
        affected_component="HUMAN_LOOP",
        rationale=req.rationale
    )
    canonical.human_contributions.append(contribution)
    
    if req.type == "INFORMATION":
        # Resolve the missing information request
        if canonical.human_requests:
            for hr in canonical.human_requests:
                if hr.request_id == req.request_id or not req.request_id:
                    hr.status = "ANSWERED"
                    hr.response_data = {"value": req.value}
        
        # We need to add the information to the knowledge base so the LLM sees it
        if isinstance(req.value, dict):
            content = ", ".join(f"{k}: {v}" for k, v in req.value.items())
        else:
            content = str(req.value)
            
        canonical.knowledge.findings.append(StructuredFinding(
            finding_id="FIND-" + str(uuid.uuid4())[:6],
            statement=f"Human provided missing information: {content}",
            finding_type="QUANTITATIVE",
            status="VALIDATED",
            evidence_refs=["HUMAN_INPUT"]
        ))
        
        # Unblock predictor
        for step in canonical.execution_plan.steps:
            if step.status == "WAITING_FOR_HUMAN_INPUT":
                step.status = "READY"
                step.waiting_reason = ""
                
    elif req.type == "SELECTION":
        from .canonical_state import HumanDecision
        import uuid
        import datetime
        decision_id = req.decision_id if req.decision_id else f"DEC-{uuid.uuid4()}"
        
        canonical.human_decision = HumanDecision(
            decision_id=decision_id,
            work_id=work_id,
            decision_type="REJECT_ALL" if req.value == "REJECT_ALL" else "SELECT_ALTERNATIVE",
            selected_alternative_id=None if req.value == "REJECT_ALL" else req.value,
            selected_prescription_id=None,
            rationale=req.rationale,
            timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat()
        )
        
        if canonical.decision_points:
            for dp in canonical.decision_points:
                if dp.decision_id == req.decision_id or not req.decision_id:
                    dp.status = "ANSWERED"
                    dp.human_selection = req.value
                    
        for step in canonical.execution_plan.steps:
            if step.status == "WAITING_FOR_HUMAN_INPUT":
                if step.canonical_em == "EM Prescriptor":
                    if req.value != "REJECT_ALL":
                        step.status = "COMPLETED"
                        step.waiting_reason = ""
                    else:
                        step.waiting_reason = "HUMAN_REJECTED_ALL_ALTERNATIVES"
                elif step.canonical_em == "EM Core":
                    step.status = "COMPLETED"
                    step.waiting_reason = ""
                elif step.canonical_em == "EM Installer":
                    # LS47: re-arm the installer step; EMInstaller.execute_task applies a
                    # resume-aware freeze path from the existing execution_state.
                    step.status = "READY"
                    step.waiting_reason = ""

        if req.value != "REJECT_ALL":
            if canonical.prescriptive_knowledge and canonical.prescriptive_knowledge.prescriptions:
                presc = canonical.prescriptive_knowledge.prescriptions[-1]
                matched = next((a for a in presc.alternatives if a.alternative_id == req.value), None)
                if matched:
                    presc.selected_alternative = matched
                    presc.decision_rule.status = "HUMAN_PROVIDED"   # valid literal (was OVERRIDDEN)
                    presc.decision_rule.rule_type = "HUMAN"
                    presc.decision_rule.authority = "HUMAN_OPERATOR"
                    presc.decision_rule.description = req.rationale
                    presc.validation_status = "SELECTED"
                    presc.authority = "HUMAN"
                    canonical.human_decision.selected_prescription_id = presc.prescription_id
                    
    elif req.type == "PARAMETER":
        # Store parameter changes in human decision
        from .canonical_state import HumanDecision
        import uuid
        import datetime
        # Ensure a HumanDecision exists
        if not canonical.human_decision:
            canonical.human_decision = HumanDecision(
                decision_id=getattr(req, "decision_id", f"DEC-{uuid.uuid4()}"),
                work_id=work_id,
                decision_type="PARAMETER",
                selected_alternative_id=None,
                selected_prescription_id=None,
                timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat()
            )
        # Expect value to be a dict of parameter changes
        if isinstance(req.value, dict):
            canonical.human_decision.parameters_modified.update(req.value)
        else:
            # Store non-dict as a single parameter named 'value'
            canonical.human_decision.parameters_modified["value"] = req.value
        
    # Resume the workflow
    canonical.status = "READY"
    background_tasks.add_task(run_work_background, work_id)
    return {"status": "RESUMED", "contribution_id": contribution.contribution_id}

@app.get("/api/health")
def get_health():
    return {"status": "OK"}

@app.get("/api/evidence/{evidence_id}")
def get_evidence(evidence_id: str):
    if evidence_id not in evidence_store:
        raise HTTPException(status_code=404, detail="Evidence not found")
    return evidence_store[evidence_id]

@app.post("/api/evidence/{evidence_id}/extract")
def retry_extraction(evidence_id: str, background_tasks: BackgroundTasks):
    if evidence_id not in evidence_store:
        raise HTTPException(status_code=404, detail="Evidence not found")
    background_tasks.add_task(run_extraction_background, evidence_id)
    return {"status": "EXTRACTION_QUEUED"}

# ==== Copilot (LLM chat completions) — the DeepSeek API key lives ONLY on the backend. ====
# The browser/frontend never needs (nor sees) DEEPSEEK_API_KEY: the frontend calls the EUREKA
# backend, and only the backend (which holds the env key) talks to DeepSeek. This is required
# for producing a public deployment — the key must never reach the browser.
class CopilotRequest(BaseModel):
    model: str = "deepseek-chat"
    messages: List[Dict[str, Any]]
    temperature: float = 0.3
    tools: Optional[List[Dict[str, Any]]] = None

@app.post("/api/copilot")
def copilot_chat(req: CopilotRequest):
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    base_url = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/")
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail={"reason_code": "MISSING_DEEPSEEK_API_KEY",
                    "message": "DEEPSEEK_API_KEY not configured on the EUREKA backend."},
        )
    payload: Dict[str, Any] = {
        "model": req.model,
        "messages": req.messages,
        "temperature": req.temperature,
        "stream": False,
    }
    if req.tools:
        payload["tools"] = req.tools
    url = f"{base_url}/chat/completions"
    try:
        r = requests.post(
            url,
            json=payload,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            timeout=180,
        )
        r.raise_for_status()
        # Pass DeepSeek's response through verbatim. The frontend reads choices[].message
        # (.content / .tool_calls / .reasoning_content) and usage, exactly as before.
        return r.json()
    except requests.RequestException as e:
        raise HTTPException(
            status_code=502,
            detail={"reason_code": "PROVIDER_ERROR", "message": f"DeepSeek request failed: {e}"},
        )

import asyncio
from fastapi import BackgroundTasks

async def run_work_background(work_id: str):
    canonical = works_db.get(work_id)
    if not canonical:
        return
        
    loop_count = 0
    while canonical.status in ["RUNNING", "READY"]:
        loop_count += 1
        print(f"Background Loop {loop_count}: status={canonical.status}")
        # Execute one step. _process_state runs the EM step synchronously and may make a
        # BLOCKING LLM call (deepseek). Run it in a worker thread so it does NOT block the
        # uvicorn event loop; otherwise every /state poll (frontend observability) times out
        # and the pipeline looks FROZEN/stuck while a slow LLM call is in flight.
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, _process_state, canonical)
        # Durability: persist the work after each runtime step so the durable authority reflects
        # the LATEST canonical state (the scenario seam binds to this stable snapshot; a restart
        # loads the same state). This is a write-through via the ONE Work authority (no new store).
        works_db[work_id] = canonical
        print(f"After process: status={canonical.status}")
        # Yield to event loop to allow API polling (observability)
        await asyncio.sleep(0.5)
        if loop_count > 50:
            print("Infinite loop detected! Breaking.")
            break

@app.post("/api/work/intake")
async def work_intake(req: IntakeRequest, background_tasks: BackgroundTasks):
    try:
        # EUREKA discovers the structure and generates the CanonicalWorkState dynamically
        canonical = orchestrator.orchestrate(req.user_intent)
        
        # Initialize properties
        canonical.revision = 1
        
        # Load Frozen Solution if requested
        if req.previous_solution_id:
            from src.eureka.universe.frozen_knowledge_runtime import FrozenKnowledgeRuntime
            fkr = FrozenKnowledgeRuntime()
            status, frozen = fkr.load_validate_and_mount(req.previous_solution_id, canonical)
            if status != "VALID":
                canonical.status = "FAILED"
                canonical.conditions.append(StateCondition(
                    status="FAILED",
                    reason_code="FROZEN_SOLUTION_INVALID",
                    message=f"Could not mount frozen solution {req.previous_solution_id}: {status}"
                ))
            else:
                # Add Applicability task as the very first step
                from src.eureka.universe.canonical_state import ExecutionStep
                app_step = ExecutionStep(
                    step_id="task_applicability",
                    capability_id="frozen_knowledge.evaluate_applicability",
                    target="EM[CORE]",
                    canonical_em="EM Core",
                    status="PENDING",
                    produces_result=False,
                    provenance=["Inserted by Universe Intake for Frozen Solution Assessment"]
                )
                delta_step = ExecutionStep(
                    step_id="task_detect_delta",
                    capability_id="frozen_knowledge.detect_delta",
                    target="EM[DESCRIPTOR]",
                    canonical_em="EM Descriptor",
                    status="PENDING",
                    dependencies=["task_applicability"],
                    produces_result=False,
                    provenance=["Inserted by Universe Intake for Frozen Solution Assessment"]
                )
                math_step = ExecutionStep(
                    step_id="task_math_revalidation",
                    capability_id="frozen_knowledge.mathematical_revalidation",
                    target="EM[PREDICTOR]",
                    canonical_em="EM Predictor",
                    status="PENDING",
                    dependencies=["task_detect_delta"],
                    produces_result=False,
                    provenance=["Inserted by Universe Intake for Frozen Solution Assessment"]
                )
                cog_step = ExecutionStep(
                    step_id="task_cognitive_reeval",
                    capability_id="frozen_knowledge.cognitive_reevaluation",
                    target="EM[PRESCRIPTOR]",
                    canonical_em="EM Prescriptor",
                    status="PENDING",
                    dependencies=["task_math_revalidation"],
                    produces_result=False,
                    provenance=["Inserted by Universe Intake for Frozen Solution Assessment"]
                )
                act_step = ExecutionStep(
                    step_id="task_action_plan_gen",
                    capability_id="frozen_knowledge.action_plan_generation",
                    target="EM[ACTIONER]",
                    canonical_em="EM Actioner",
                    status="PENDING",
                    dependencies=["task_cognitive_reeval"],
                    produces_result=False,
                    provenance=["Inserted by Universe Intake for Frozen Solution Assessment"]
                )
                ver_step = ExecutionStep(
                    step_id="task_action_plan_ver",
                    capability_id="frozen_knowledge.action_plan_verification",
                    target="EM[ACTIONER]",
                    canonical_em="EM Actioner",
                    status="PENDING",
                    dependencies=["task_action_plan_gen"],
                    produces_result=True,
                    provenance=["Inserted by Universe Intake for Frozen Solution Assessment"]
                )
                canonical.execution_plan.steps.insert(0, ver_step)
                canonical.execution_plan.steps.insert(0, act_step)
                canonical.execution_plan.steps.insert(0, cog_step)
                canonical.execution_plan.steps.insert(0, math_step)
                canonical.execution_plan.steps.insert(0, delta_step)
                canonical.execution_plan.steps.insert(0, app_step)
        
        if req.attachments:
            from src.eureka.universe.canonical_state import Evidence, ExtractedEvidence
            for eid in req.attachments:
                if eid in evidence_store:
                    canonical.evidence_ids.append(eid)
                    if eid not in evidence_work_index:
                        evidence_work_index[eid] = set()
                    evidence_work_index[eid].add(canonical.work.work_id)
            if canonical.evidence_ids:
                canonical.revision += 1
                
        works_db[canonical.work.work_id] = canonical
        _process_state(canonical) # Initialize state
        
        if canonical.status in ["READY", "RUNNING"]:
            background_tasks.add_task(run_work_background, canonical.work.work_id)
            
        return _process_state(canonical)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail={"reason_code": "SYSTEM_ERROR", "message": str(e)})

class ExecuteRequest(BaseModel):
    intent: str

@app.post("/api/work/{work_id}/execute")
def execute_work_eureka(work_id: str, req: ExecuteRequest, background_tasks: BackgroundTasks):
    if work_id not in works_db:
        raise HTTPException(status_code=404, detail={"reason_code": "SYSTEM_ERROR", "message": "Work not found"})
        
    canonical = works_db[work_id]
    
    try:
        new_canonical = orchestrator.orchestrate(req.intent)
        new_canonical.work.work_id = work_id
        new_canonical.evidence_ids = canonical.evidence_ids.copy()
        new_canonical.evidence = canonical.evidence.copy()
        new_canonical.extracted_evidence = canonical.extracted_evidence.copy()
        
        works_db[work_id] = new_canonical
        _process_state(new_canonical)
        
        if new_canonical.status in ["READY", "RUNNING"]:
            background_tasks.add_task(run_work_background, work_id)
            
        return {"work_id": work_id, "status": new_canonical.status, "state": _process_state(new_canonical)}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail={"reason_code": "SYSTEM_ERROR", "message": str(e)})

@app.get("/api/work/{work_id}/state")
def get_work_state(work_id: str):
    if work_id not in works_db:
        raise HTTPException(status_code=404, detail="Work not found")
    # F-1: GET /state is a pure read — it must NOT advance the runtime (no mutation).
    return _project_state(works_db[work_id])

@app.get("/api/work/{work_id}/publication")
def get_work_publication(work_id: str):
    """READ-ONLY, VERIFIED consumption of the durable, signed publication artifact(s) for a Work.

    Resolves the artifact SERVER-SIDE by work_id and verifies schema + integrity (via the reused
    `_freeze_signature`/`_signature_from_frozen`) + currentness. Never mutates; never executes.
    """
    from src.eureka.universe.publication_consumption import build_publication_consumption
    try:
        return build_publication_consumption(works_db, runtime.publisher, work_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.get("/api/work/{work_id}/audit")
def get_work_audit(work_id: str):
    """READ-ONLY canonical observability: Work → Execution → Result → Publish → Consumption/verify."""
    from src.eureka.universe.work_observability import build_work_audit
    try:
        return build_work_audit(works_db, runtime.publisher, work_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.post("/api/work/{work_id}/advance")
def advance_work(work_id: str):
    """Explicit, write-triggered state advancement (F-1).

    GET /state is now pure; this is the intentional write endpoint used to step the runtime
    from an external trigger (in addition to the background execution loop). It advances the
    canonical state one step and returns the resulting projection.
    """
    if work_id not in works_db:
        raise HTTPException(status_code=404, detail="Work not found")
    canonical = works_db[work_id]
    return {"status": canonical.status, "state": _process_state(canonical)}

@app.get("/api/export/formats")
def list_export_formats():
    """Advertise the artifact formats EUREKA can materialize."""
    return {"formats": SUPPORTED_FORMATS}

@app.get("/api/work/{work_id}/download")
def download_work_artifact(work_id: str, format: str = "txt"):
    """Export the work as a real artifact (txt/md/docx/pdf/pptx/png/svg).

    The artifact is rendered from the live canonical state — including the ACFL
    fuzzy decision layer — and also persisted to ./generated for durability.
    """
    if work_id not in works_db:
        raise HTTPException(status_code=404, detail="Work not found")

    canonical = works_db[work_id]
    fmt = (format or "txt").lower().lstrip(".")

    if fmt not in SUPPORTED_FORMATS:
        raise HTTPException(
            status_code=400,
            detail={"reason_code": "UNSUPPORTED_FORMAT",
                    "message": f"Formato '{fmt}' no soportado. Válidos: {', '.join(SUPPORTED_FORMATS)}"},
        )

    try:
        # Render once, then persist to ./generated so the artifact survives the
        # in-memory works_db lifetime.
        data, filename, media_type = export_work(canonical, fmt)
        os.makedirs("generated", exist_ok=True)
        path = os.path.join("generated", filename)
        with open(path, "wb") as f:
            f.write(data)
    except Exception as e:  # noqa: BLE001
        traceback.print_exc()
        raise HTTPException(status_code=500, detail={"reason_code": "EXPORT_ERROR", "message": str(e)})

    return FileResponse(
        path=path,
        media_type=media_type,
        filename=filename,
    )

@app.post("/api/work/{work_id}/tool_call")
def execute_tool_call(work_id: str, req: ToolCallRequest, background_tasks: BackgroundTasks):
    if work_id not in works_db:
        raise HTTPException(status_code=404, detail={"reason_code": "SYSTEM_ERROR", "message": "Work not found"})
    
    canonical = works_db[work_id]
    tool_call_id = f"TOOL-{str(uuid.uuid4())[:6]}"
    canonical.revision += 1
    
    try:
        # Hard Failure Tests
        if req.capability == "actioner":
            # Execution Governance Block
            canonical.conditions.append(StateCondition(
                status="BLOCKED",
                reason_code="GOVERNANCE_RESTRICTION",
                message="Execution Authority missing for ACTIONER.",
                target=req.capability
            ))
            canonical.status = "BLOCKED"
            return {"status": "BLOCKED", "reason_code": "GOVERNANCE_RESTRICTION", "state": _process_state(canonical, tool_call_id)}

        if req.capability == "invented_capability":
            # Capability Unavailable Gap
            canonical.conditions.append(StateCondition(
                status="GAP",
                reason_code="CAPABILITY_UNAVAILABLE",
                message="Unknown capability requested by DeepSeek.",
                target=req.capability
            ))
            return {"status": "GAP", "reason_code": "CAPABILITY_UNAVAILABLE", "state": _process_state(canonical, tool_call_id)}

        if req.capability == "retrieve_result":
            if not canonical.result or canonical.result.status != "AVAILABLE":
                # Do NOT change canonical.status. Just return the failure reason so DeepSeek knows it's unavailable.
                return {"status": "GAP", "reason_code": "RESULT_UNAVAILABLE", "state": _project_state(canonical, tool_call_id)}
            # Successful retrieval: Work state remains intact (pure read, no advance).
            return {"status": "SUCCESS", "state": _project_state(canonical, tool_call_id)}

        if req.capability == "trigger_system_error":
            # Force a python exception
            raise RuntimeError("Simulated Python Exception")

        # Execution changes for ACFL via tool_call boundary
        def _safe_mark_ready():
            # Do NOT override a paused HITL state: if any step is WAITING_FOR_HUMAN_INPUT,
            # keep canonical.status so the frontend ACTIVE_NOW selector keeps matching and the
            # HITL widget stays visible (the runtime is paused for human input, not ready).
            if any(s.status == "WAITING_FOR_HUMAN_INPUT" for s in canonical.execution_plan.steps):
                return
            canonical.status = "READY"

        if req.capability == "adjust_acfl_weights":
            canonical.acfl.weights.update(req.parameters)
            # Re-run runtime (unless paused on a human decision)
            _safe_mark_ready()
        elif req.capability == "filter_alternatives":
            canonical.feasible_only = req.parameters.get("feasible", False)
            _safe_mark_ready()

        state = _process_state(canonical, tool_call_id)
        # F-1b: GET /state is now pure, so a config/weight change must not strand the work.
        # Re-arm the background execution loop when the work is still actionable. Use FastAPI's
        # BackgroundTasks (safe from a sync endpoint's worker thread) — asyncio.get_event_loop()
        # here would raise "no current event loop" in the AnyIO worker thread (regression caught
        # by the full frontend flow; _f1_verify used direct POSTs and missed it).
        if canonical.status in ("RUNNING", "READY"):
            background_tasks.add_task(run_work_background, work_id)
        return {"status": "SUCCESS", "state": state}
        
    except Exception as e:
        traceback.print_exc()
        canonical.conditions.append(StateCondition(
            status="FAILED",
            reason_code="SYSTEM_ERROR",
            message=str(e),
            target=req.capability
        ))
        canonical.status = "FAILED"
        return {"status": "FAILED", "reason_code": "SYSTEM_ERROR", "state": _process_state(canonical, tool_call_id)}

@app.post("/api/work/{work_id}/evidence")
def attach_evidence_to_work(work_id: str, payload: dict):
    # Payload should contain "evidence_id"
    if work_id not in works_db:
        raise HTTPException(status_code=404, detail={"reason_code": "SYSTEM_ERROR", "message": "Work not found"})
        
    evidence_id = payload.get("evidence_id")
    if not evidence_id or evidence_id not in evidence_store:
        raise HTTPException(status_code=404, detail={"reason_code": "SYSTEM_ERROR", "message": "Evidence not found"})
        
    canonical = works_db[work_id]
    
    # Do not add duplicate
    if evidence_id in canonical.evidence_ids:
        return {"status": "SUCCESS", "state": _process_state(canonical)}
        
    canonical.evidence_ids.append(evidence_id)
    if evidence_id not in evidence_work_index:
        evidence_work_index[evidence_id] = set()
    evidence_work_index[evidence_id].add(work_id)
        
    canonical.revision += 1
    
    # Append provenance to work
    from src.eureka.universe.work_model import ProvenanceRecord
    filename = evidence_store[evidence_id].get("filename", evidence_id)
    canonical.work.provenance_log.append(ProvenanceRecord(
        source_id=evidence_id,
        status="REAL",
        description=f"Evidence {filename} attached to work.",
        generated_at=__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat()
    ))
    
    # We may want to mark the work as READY so the runtime can evaluate it again
    if canonical.status in ["PARTIAL", "COMPLETED", "GAP"]:
        canonical.status = "READY"
        
    return {"status": "SUCCESS", "state": _process_state(canonical)}

if __name__ == "__main__":
    uvicorn.run("src.eureka.universe.server:app", host="0.0.0.0", port=8000, reload=True)

