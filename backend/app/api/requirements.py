"""Requirements extraction and verification API."""

from __future__ import annotations

import uuid
from enum import Enum

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from app.core.extraction.pipeline import ExtractionPipeline
from app.core.extraction.schemas import ExtractedRequirement, ExtractionJobResult
from app.core.verification.schemas import VerificationResult
from app.core.verification.verifier import VerificationOrchestrator

router = APIRouter(prefix="/requirements", tags=["requirements"])

# In-memory job store (Milestone 1: Redis or SQLite)
_jobs: dict[str, ExtractionJobResult] = {}
_verify_jobs: dict[str, list[VerificationResult]] = {}


class Language(str, Enum):
    pl = "pl"
    en = "en"


class ExtractRequest(BaseModel):
    text: str | None = None
    language: Language = Language.pl
    product: str | None = None
    auto_detect_product: bool = False


class ExtractResponse(BaseModel):
    job_id: str
    status: str


class RequirementsListResponse(BaseModel):
    job_id: str
    requirements: list[ExtractedRequirement]
    product_suggestion: str | None = None
    auto_detect_warning: bool = False


class VerifyRequest(BaseModel):
    job_id: str
    requirement_ids: list[str] = Field(default_factory=list)
    product: str
    language: Language = Language.pl
    anonymize: bool = False


@router.post("/extract", response_model=ExtractResponse)
async def start_extraction(body: ExtractRequest, background_tasks: BackgroundTasks):
    if not body.text or not body.text.strip():
        raise HTTPException(400, "No text provided for extraction")
    job_id = str(uuid.uuid4())
    pipeline = ExtractionPipeline(language=body.language.value)

    def run():
        result = pipeline.run(text=body.text or "")
        _jobs[job_id] = result

    background_tasks.add_task(run)
    return ExtractResponse(job_id=job_id, status="processing")


@router.get("/extract/{job_id}", response_model=RequirementsListResponse)
def get_extraction(job_id: str):
    result = _jobs.get(job_id)
    if not result:
        raise HTTPException(404, "Job not found")
    return RequirementsListResponse(
        job_id=job_id,
        requirements=result.requirements,
        product_suggestion=result.product_suggestion,
        auto_detect_warning=result.auto_detect_warning,
    )


@router.post("/verify", response_model=ExtractResponse)
async def start_verification(body: VerifyRequest, background_tasks: BackgroundTasks):
    extraction = _jobs.get(body.job_id)
    if not extraction:
        raise HTTPException(404, "Extraction job not found")
    reqs = extraction.requirements
    if body.requirement_ids:
        ids = set(body.requirement_ids)
        reqs = [r for r in reqs if r.id in ids]
    job_id = str(uuid.uuid4())

    def run():
        orchestrator = VerificationOrchestrator(
            product=body.product,
            language=body.language.value,
            anonymize=body.anonymize,
        )
        results = orchestrator.verify_all(reqs)
        _verify_jobs[job_id] = results

    background_tasks.add_task(run)
    return ExtractResponse(job_id=job_id, status="processing")


@router.get("/verify/{job_id}")
def get_verification(job_id: str):
    results = _verify_jobs.get(job_id)
    if results is None:
        raise HTTPException(404, "Job not found")
    return {"job_id": job_id, "results": [r.model_dump() for r in results]}


@router.get("/verify/{job_id}/stream")
async def stream_verification(job_id: str):
    """SSE stream placeholder for per-requirement progress (Milestone 1)."""

    async def events():
        yield {"event": "status", "data": '{"phase":"pending"}'}

    return EventSourceResponse(events())
