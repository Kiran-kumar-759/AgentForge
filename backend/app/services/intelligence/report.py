import uuid
import os
import json
from datetime import datetime
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.report import ReportPackage, ReportArtifact
from app.db.models.execution import ExecutionPlan, ExecutionNode
from app.db.models.evidence import Claim, Evidence
from app.core.config import settings

class ReportService:
    def __init__(self, db: AsyncSession):
        self.db = db
        template_dir = os.path.join(os.path.dirname(__file__), "../../templates")
        self.env = Environment(loader=FileSystemLoader(template_dir))
        
        # Define storage directory for reports
        self.storage_dir = os.path.join(settings.DATA_DIR, "reports")
        os.makedirs(self.storage_dir, exist_ok=True)
        
    async def create_report_package(self, execution_id: str, title: str, package_type: str = "MARINE_INTELLIGENCE_REPORT") -> str:
        """Create a pending report package in the database."""
        # Verify execution exists
        stmt = select(ExecutionPlan).where(ExecutionPlan.id == execution_id)
        res = await self.db.execute(stmt)
        plan = res.scalars().first()
        if not plan:
            raise ValueError(f"Execution {execution_id} not found")
            
        package_id = str(uuid.uuid4())
        
        pkg = ReportPackage(
            id=package_id,
            execution_id=execution_id,
            title=title,
            package_type=package_type,
            status="PENDING",
            summary=plan.user_query
        )
        self.db.add(pkg)
        await self.db.commit()
        return package_id
        
    async def generate_report(self, package_id: str):
        """Generate the PDF, HTML, and JSON artifacts for the package."""
        stmt = select(ReportPackage).where(ReportPackage.id == package_id)
        res = await self.db.execute(stmt)
        pkg = res.scalars().first()
        
        if not pkg:
            raise ValueError(f"Package {package_id} not found")
            
        pkg.status = "GENERATING"
        await self.db.commit()
        
        try:
            # 1. Collect Data
            execution_id = pkg.execution_id
            
            # Lineage tracking
            # We want nodes that actually ran. Wait, we want all claims for this execution or parent.
            # Usually claims are tied to execution_id of the current plan. But Phase 12 replanning means
            # reused nodes might have claims attached to their original plan, OR the reused node gets a new claim?
            # In Phase 13, I made EvidenceAdapter extract claims for reused nodes directly under the new execution_id.
            
            stmt = select(Claim).where(Claim.execution_id == execution_id)
            res = await self.db.execute(stmt)
            claims = res.scalars().all()
            
            # Eagerly load evidence?
            for c in claims:
                await self.db.refresh(c, ['evidence'])
            
            all_evidence = set()
            for c in claims:
                for e in c.evidence:
                    all_evidence.add(e)
                    
            evidence_list = list(all_evidence)
            
            # Format Data
            claims_data = []
            verification_counts = {
                "SUPPORTED": 0,
                "PARTIALLY_SUPPORTED": 0,
                "UNSUPPORTED": 0,
                "UNVERIFIABLE": 0,
                "CONFLICTING": 0
            }
            
            for c in claims:
                v_status = c.verification_status
                verification_counts[v_status] = verification_counts.get(v_status, 0) + 1
                
                ev_data = []
                for e in c.evidence:
                    ev_data.append({
                        "dataset_id": e.dataset_id,
                        "source_name": e.source_name,
                        "observation_time": e.observation_time.isoformat() if e.observation_time else None,
                        "computation": e.computation,
                        "summary": e.summary
                    })
                    
                claims_data.append({
                    "id": str(c.id),
                    "text": c.claim_text,
                    "type": c.claim_type,
                    "verification_status": v_status,
                    "reason": c.verification_reason,
                    "evidence": ev_data
                })
                
            evidence_data = []
            for e in evidence_list:
                evidence_data.append({
                    "id": str(e.id),
                    "dataset_id": e.dataset_id,
                    "source_name": e.source_name,
                    "observation_time": e.observation_time.isoformat() if e.observation_time else None
                })
                
            # Limit / Constraints
            limitations = []
            if any(c.verification_status == "UNVERIFIABLE" and "vessel" in c.claim_type.lower() for c in claims):
                limitations.append("Available vessel intelligence is geographically restricted (Fintraffic/Baltic coverage). Areas outside this coverage cannot be assessed.")

            template_data = {
                "title": pkg.title,
                "generated_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
                "execution_id": str(pkg.execution_id),
                "package_id": str(pkg.id),
                "version": pkg.version,
                "summary": pkg.summary,
                "claims": claims_data,
                "evidence": evidence_data,
                "verification_counts": verification_counts,
                "limitations": limitations
            }
            
            # 2. Render HTML
            template = self.env.get_template("report_template.html")
            html_content = template.render(**template_data)
            
            html_filename = f"orca_report_{package_id}.html"
            html_path = os.path.join(self.storage_dir, html_filename)
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html_content)
                
            # 3. Render PDF
            pdf_filename = f"orca_report_{package_id}.pdf"
            pdf_path = os.path.join(self.storage_dir, pdf_filename)
            HTML(string=html_content).write_pdf(pdf_path)
            
            # 4. JSON Package
            json_filename = f"orca_research_package_{package_id}.json"
            json_path = os.path.join(self.storage_dir, json_filename)
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(template_data, f, indent=2)
                
            # 5. Persist artifacts
            artifacts = [
                ReportArtifact(
                    id=str(uuid.uuid4()),
                    package_id=package_id,
                    artifact_type="HTML",
                    storage_reference=html_path,
                    mime_type="text/html",
                    size_bytes=str(os.path.getsize(html_path))
                ),
                ReportArtifact(
                    id=str(uuid.uuid4()),
                    package_id=package_id,
                    artifact_type="PDF",
                    storage_reference=pdf_path,
                    mime_type="application/pdf",
                    size_bytes=str(os.path.getsize(pdf_path))
                ),
                ReportArtifact(
                    id=str(uuid.uuid4()),
                    package_id=package_id,
                    artifact_type="JSON",
                    storage_reference=json_path,
                    mime_type="application/json",
                    size_bytes=str(os.path.getsize(json_path))
                )
            ]
            
            for art in artifacts:
                self.db.add(art)
                
            pkg.status = "COMPLETED"
            pkg.generated_at = datetime.utcnow()
            await self.db.commit()
            
        except Exception as e:
            pkg.status = "FAILED"
            pkg.summary = f"Generation failed: {str(e)}"
            await self.db.commit()
            raise e
