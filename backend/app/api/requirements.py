"""Requirements extraction and verification API."""

from __future__ import annotations

import os
import uuid
from enum import Enum
from typing import Any

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile
from fastapi.responses import PlainTextResponse, Response
from pydantic import BaseModel, Field

from app.core.extraction.parser import parse_upload_bytes
from app.core.extraction.pipeline import ExtractionPipeline
from app.core.extraction.schemas import (
    ExtractedRequirement,
    ProductSuggestionOut,
)
from app.core.reporting.docx import export_docx
from app.core.reporting.markdown import export_markdown
from app.core.reporting.xlsx import export_xlsx
from app.core.verification.schemas import VerificationResult
from app.core.verification.verifier import VerificationOrchestrator

router = APIRouter(prefix="/requirements", tags=["requirements"])

_jobs: dict[str, dict[str, Any]] = {}
_verify_jobs: dict[str, dict[str, Any]] = {}


def _default_use_llm() -> bool:
    """Heuristic-only extraction in CI/E2E (SIWZ_E2E=1)."""
    return os.environ.get("SIWZ_E2E") != "1"


class Language(str, Enum):
    pl = "pl"
    en = "en"


class ExtractRequest(BaseModel):
    text: str | None = None
    language: Language = Language.pl
    product: str | None = None
    auto_detect_product: bool = False
    use_llm: bool = Field(default_factory=_default_use_llm)


class ExtractResponse(BaseModel):
    job_id: str
    status: str


class RequirementsListResponse(BaseModel):
    job_id: str
    status: str
    requirements: list[ExtractedRequirement] = Field(default_factory=list)
    product_suggestion: str | None = None
    product_suggestions: list[ProductSuggestionOut] = Field(default_factory=list)
    auto_detect_warning: bool = False
    blocks_processed: int = 0
    error: str | None = None


class RequirementsUpdateRequest(BaseModel):
    requirements: list[ExtractedRequirement]


class VerifyRequest(BaseModel):
    job_id: str
    requirement_ids: list[str] = Field(default_factory=list)
    product: str
    language: Language = Language.pl
    anonymize: bool = False


class VerifyStatusResponse(BaseModel):
    job_id: str
    status: str
    progress: int = 0
    total: int = 0
    results: list[VerificationResult] = Field(default_factory=list)
    error: str | None = None


def _run_extraction(job_id: str, text: str, language: str, auto_detect: bool, use_llm: bool):
    _jobs[job_id]["status"] = "processing"
    _jobs[job_id]["auto_detect_used"] = auto_detect
    try:
        pipeline = ExtractionPipeline(language=language, use_llm=use_llm)
        result = pipeline.run(text=text, auto_detect=auto_detect)
        _jobs[job_id].update(result.model_dump())
        _jobs[job_id]["status"] = "completed"
    except Exception as e:
        _jobs[job_id]["status"] = "failed"
        _jobs[job_id]["error"] = str(e)


def _run_verification(
    job_id: str,
    reqs: list[ExtractedRequirement],
    body: VerifyRequest,
    extract_job: dict[str, Any],
):
    _verify_jobs[job_id]["status"] = "processing"
    _verify_jobs[job_id]["total"] = len(reqs)
    _verify_jobs[job_id]["product"] = body.product
    _verify_jobs[job_id]["anonymize"] = body.anonymize
    _verify_jobs[job_id]["language"] = body.language.value
    _verify_jobs[job_id]["product_auto_detected"] = bool(
        extract_job.get("auto_detect_used") and extract_job.get("auto_detect_warning")
    )
    try:
        orchestrator = VerificationOrchestrator(
            product=body.product,
            language=body.language.value,
            anonymize=body.anonymize,
        )
        results: list[VerificationResult] = []
        for i, req in enumerate(reqs):
            results.append(orchestrator.verify_one(req))
            _verify_jobs[job_id]["progress"] = i + 1
            _verify_jobs[job_id]["results"] = results
        _verify_jobs[job_id]["status"] = "completed"
    except Exception as e:
        _verify_jobs[job_id]["status"] = "failed"
        _verify_jobs[job_id]["error"] = str(e)


@router.post("/extract", response_model=ExtractResponse)
async def start_extraction(body: ExtractRequest, background_tasks: BackgroundTasks):
    if not body.text or not body.text.strip():
        raise HTTPException(400, "No text provided for extraction")
    job_id = str(uuid.uuid4())
    _jobs[job_id] = {"status": "queued", "requirements": []}
    use_llm = body.use_llm if os.environ.get("SIWZ_E2E") != "1" else False
    background_tasks.add_task(
        _run_extraction,
        job_id,
        body.text,
        body.language.value,
        body.auto_detect_product,
        use_llm,
    )
    return ExtractResponse(job_id=job_id, status="queued")


@router.post("/extract/upload", response_model=ExtractResponse)
async def extract_upload(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    language: Language = Language.pl,
    auto_detect_product: bool = Form(False),
    pasted_text: str | None = Form(None),
    use_llm: bool = Form(True),
):
    effective_llm = _default_use_llm() if os.environ.get("SIWZ_E2E") == "1" else use_llm
    data = await file.read()
    text = parse_upload_bytes(data, file.filename or "upload.pdf")
    if pasted_text and pasted_text.strip():
        text = f"{text}\n\n{pasted_text.strip()}"
    job_id = str(uuid.uuid4())
    _jobs[job_id] = {"status": "queued", "requirements": []}
    background_tasks.add_task(
        _run_extraction,
        job_id,
        text,
        language.value,
        auto_detect_product,
        effective_llm,
    )
    return ExtractResponse(job_id=job_id, status="queued")


@router.get("/extract/{job_id}", response_model=RequirementsListResponse)
def get_extraction(job_id: str):
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    suggestions = job.get("product_suggestions", [])
    parsed_suggestions = [
        s if isinstance(s, ProductSuggestionOut) else ProductSuggestionOut.model_validate(s)
        for s in suggestions
    ]
    return RequirementsListResponse(
        job_id=job_id,
        status=job.get("status", "unknown"),
        requirements=job.get("requirements", []),
        product_suggestion=job.get("product_suggestion"),
        product_suggestions=parsed_suggestions,
        auto_detect_warning=job.get("auto_detect_warning", False),
        blocks_processed=job.get("blocks_processed", 0),
        error=job.get("error"),
    )


@router.put("/extract/{job_id}/requirements")
def update_requirements(job_id: str, body: RequirementsUpdateRequest):
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    job["requirements"] = [r.model_dump() for r in body.requirements]
    return {"ok": True, "count": len(body.requirements)}


@router.post("/verify", response_model=ExtractResponse)
async def start_verification(body: VerifyRequest, background_tasks: BackgroundTasks):
    job = _jobs.get(body.job_id)
    if not job:
        raise HTTPException(404, "Extraction job not found")
    raw_reqs = job.get("requirements", [])
    reqs = [ExtractedRequirement.model_validate(r) for r in raw_reqs]
    if body.requirement_ids:
        ids = set(body.requirement_ids)
        reqs = [r for r in reqs if r.id in ids]
    if not reqs:
        raise HTTPException(400, "No requirements to verify")
    job_id = str(uuid.uuid4())
    _verify_jobs[job_id] = {"status": "queued", "results": [], "progress": 0, "total": len(reqs)}
    background_tasks.add_task(_run_verification, job_id, reqs, body, job)
    return ExtractResponse(job_id=job_id, status="queued")


@router.get("/verify/{job_id}", response_model=VerifyStatusResponse)
def get_verification(job_id: str):
    job = _verify_jobs.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    results = job.get("results", [])
    parsed = [
        r if isinstance(r, VerificationResult) else VerificationResult.model_validate(r)
        for r in results
    ]
    return VerifyStatusResponse(
        job_id=job_id,
        status=job.get("status", "unknown"),
        progress=job.get("progress", 0),
        total=job.get("total", 0),
        results=parsed,
        error=job.get("error"),
    )


def _completed_verify_job(job_id: str) -> tuple[dict[str, Any], list[VerificationResult]]:
    job = _verify_jobs.get(job_id)
    if not job or job.get("status") != "completed":
        raise HTTPException(404, "Completed verification job not found")
    results = [VerificationResult.model_validate(r) for r in job.get("results", [])]
    return job, results


@router.get("/verify/{job_id}/report.md")
def export_report_md(
    job_id: str,
    language: Language | None = None,
    anonymize: bool = False,
):
    job, results = _completed_verify_job(job_id)
    lang = (language or Language(job.get("language", "pl"))).value
    md = export_markdown(
        results,
        language=lang,
        auto_detect_warning=job.get("product_auto_detected", False),
        product=job.get("product"),
        anonymize=anonymize or job.get("anonymize", False),
    )
    return PlainTextResponse(md, media_type="text/markdown; charset=utf-8")


@router.get("/verify/{job_id}/report.docx")
def export_report_docx(
    job_id: str,
    language: Language | None = None,
    anonymize: bool = False,
):
    job, results = _completed_verify_job(job_id)
    lang = (language or Language(job.get("language", "pl"))).value
    data = export_docx(
        results,
        language=lang,
        auto_detect_warning=job.get("product_auto_detected", False),
        product=job.get("product"),
        anonymize=anonymize or job.get("anonymize", False),
    )
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="siwz-report-{job_id[:8]}.docx"'},
    )


@router.get("/verify/{job_id}/report.xlsx")
def export_report_xlsx(
    job_id: str,
    language: Language | None = None,
    anonymize: bool = False,
):
    job, results = _completed_verify_job(job_id)
    lang = (language or Language(job.get("language", "pl"))).value
    data = export_xlsx(
        results,
        language=lang,
        product=job.get("product"),
        anonymize=anonymize or job.get("anonymize", False),
    )
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="siwz-report-{job_id[:8]}.xlsx"'},
    )
