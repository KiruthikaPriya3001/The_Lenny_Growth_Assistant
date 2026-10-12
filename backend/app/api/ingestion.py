"""Ingestion API — trigger and monitor transcript ingestion jobs."""
from __future__ import annotations

import threading
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import SessionLocal, get_db
from app.models.models import IngestionJob
from app.schemas.schemas import IngestionJobCreate, IngestionJobOut

router = APIRouter()


def _run_ingestion_in_background(job_id: str):
    """Run ingestion in a background thread with its own DB session."""
    db = SessionLocal()
    try:
        from app.ingestion.ingestion_service import IngestionService
        service = IngestionService(db)
        service.run_full_ingestion(job_id)
    except Exception as exc:
        # Mark job failed
        job = db.query(IngestionJob).filter(IngestionJob.id == job_id).first()
        if job:
            job.status = "failed"
            job.completed_at = datetime.utcnow()
            job.errors = [{"error": str(exc)[:200]}]
            db.commit()
    finally:
        db.close()


@router.post("/ingestion/jobs", response_model=IngestionJobOut, status_code=202)
def start_ingestion(body: IngestionJobCreate, db: Session = Depends(get_db)):
    """Start a background transcript ingestion job."""
    # Check if one is already running
    running = db.query(IngestionJob).filter(IngestionJob.status == "running").first()
    if running:
        raise HTTPException(
            status_code=409,
            detail={"error_code": "JOB_ALREADY_RUNNING", "message": f"Ingestion job {running.id} is already running."},
        )

    job = IngestionJob(id=str(uuid.uuid4()), status="pending")
    db.add(job)
    db.commit()
    db.refresh(job)

    # Start in background thread
    thread = threading.Thread(target=_run_ingestion_in_background, args=(job.id,), daemon=True)
    thread.start()

    return IngestionJobOut(
        id=job.id,
        status=job.status,
        started_at=job.started_at,
    )


@router.get("/ingestion/jobs/{job_id}", response_model=IngestionJobOut)
def get_ingestion_job(job_id: str, db: Session = Depends(get_db)):
    """Get status of an ingestion job."""
    job = db.query(IngestionJob).filter(IngestionJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail={"error_code": "NOT_FOUND", "message": "Job not found."})
    return IngestionJobOut(
        id=job.id,
        status=job.status,
        started_at=job.started_at,
        completed_at=job.completed_at,
        total_files=job.total_files,
        processed_files=job.processed_files,
        failed_files=job.failed_files,
        sources_created=job.sources_created,
        chunks_created=job.chunks_created,
        errors=job.errors,
    )


@router.get("/ingestion/jobs", response_model=list)
def list_jobs(db: Session = Depends(get_db)):
    """List all ingestion jobs, most recent first."""
    jobs = db.query(IngestionJob).order_by(IngestionJob.started_at.desc()).limit(10).all()
    return [
        IngestionJobOut(
            id=j.id,
            status=j.status,
            started_at=j.started_at,
            completed_at=j.completed_at,
            total_files=j.total_files,
            processed_files=j.processed_files,
            failed_files=j.failed_files,
            sources_created=j.sources_created,
            chunks_created=j.chunks_created,
        )
        for j in jobs
    ]
