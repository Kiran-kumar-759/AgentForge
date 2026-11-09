import uuid
import os
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.services.intelligence.report import ReportService
from app.db.models.report import ReportPackage, ReportArtifact
from app.workers.tasks.report import generate_report_task

router = APIRouter(prefix="/reports", tags=["reports"])

class CreateReportRequest(BaseModel):
    execution_id: str
    title: str
    package_type: str = "MARINE_INTELLIGENCE_REPORT"

@router.get("")
async def list_reports(workspace: str = None, limit: int = 10, db: AsyncSession = Depends(get_db)):
    stmt = select(ReportPackage).order_by(ReportPackage.created_at.desc()).limit(limit)
    res = await db.execute(stmt)
    pkgs = res.scalars().all()
    
    return {
        "reports": [
            {
                "id": str(pkg.id),
                "title": pkg.title,
                "status": pkg.status,
                "created_at": pkg.created_at.isoformat() if pkg.created_at else None
            } for pkg in pkgs
        ]
    }

@router.post("")
async def create_report(req: CreateReportRequest, db: AsyncSession = Depends(get_db)):
    service = ReportService(db)
    package_id = await service.create_report_package(
        execution_id=req.execution_id,
        title=req.title,
        package_type=req.package_type
    )
    
    # Enqueue task
    generate_report_task.delay(package_id)
    
    return {"package_id": package_id, "status": "PENDING"}

@router.get("/{package_id}")
async def get_report_status(package_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(ReportPackage).where(ReportPackage.id == package_id).options(selectinload(ReportPackage.artifacts))
    res = await db.execute(stmt)
    pkg = res.scalars().first()
    
    if not pkg:
        raise HTTPException(status_code=404, detail="Package not found")
        
    return {
        "package_id": str(pkg.id),
        "execution_id": str(pkg.execution_id),
        "title": pkg.title,
        "status": pkg.status,
        "summary": pkg.summary,
        "artifacts": [
            {
                "type": a.artifact_type,
                "url": f"/api/v1/reports/{package_id}/{a.artifact_type.lower()}"
            } for a in pkg.artifacts
        ]
    }

@router.get("/{package_id}/{artifact_type}")
async def download_artifact(package_id: str, artifact_type: str, db: AsyncSession = Depends(get_db)):
    stmt = select(ReportArtifact).where(ReportArtifact.package_id == package_id, ReportArtifact.artifact_type == artifact_type.upper())
    res = await db.execute(stmt)
    artifact = res.scalars().first()
    
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")
        
    if not os.path.exists(artifact.storage_reference):
        raise HTTPException(status_code=404, detail="File not found on disk")
        
    filename = os.path.basename(artifact.storage_reference)
    return FileResponse(artifact.storage_reference, media_type=artifact.mime_type, filename=filename)
