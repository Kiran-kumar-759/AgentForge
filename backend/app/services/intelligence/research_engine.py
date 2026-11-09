import uuid
import datetime
import json
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.models.research import ResearchRequest, ResearchPlan, ResearchEvidence, ResearchClaim
from app.services.llm.router import ModelRouter
from app.services.intelligence.executor import CapabilityExecutor
from app.services.intelligence.cyclone_executor import CycloneExecutor
from app.services.intelligence.vessel_executor import VesselExecutor
from app.services.exposure.exposure import ExposureService
from app.services.intelligence.rag import DocumentRetriever
from app.core.events import EventPublisher

class ResearchEngine:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.llm = ModelRouter()
        self.capability_executor = CapabilityExecutor(db)
        self.cyclone_executor = CycloneExecutor(db)
        self.vessel_executor = VesselExecutor(db)
        self.exposure_service = ExposureService(db)
        self.doc_retriever = DocumentRetriever(db)
        self.events = EventPublisher()

    async def execute_research(self, request_id: uuid.UUID) -> ResearchRequest:
        stmt = select(ResearchRequest).where(ResearchRequest.id == request_id)
        res = await self.db.execute(stmt)
        req = res.scalars().first()
        if not req:
            raise ValueError("Request not found")
            
        await self.events.publish(
            topic="execution.events",
            event_type="research.requested",
            execution_id=str(req.id),
            status="started",
            metadata={"question": req.question}
        )
            
        req.status = "planning"
        await self.db.commit()
        
        await self.events.publish(
            topic="execution.events",
            event_type="research.planning.started",
            execution_id=str(req.id),
            status="running"
        )
        
        try:
            # 1. Planning Phase
            plan = await self._generate_plan(req)
            
            await self.events.publish(
                topic="execution.events",
                event_type="research.plan.created",
                execution_id=str(req.id),
                status="completed",
                metadata={"objectives": plan.objectives}
            )
            
            req.status = "researching"
            await self.db.commit()
            
            await self.events.publish(
                topic="execution.events",
                event_type="research.structured_retrieval.started",
                execution_id=str(req.id),
                status="running"
            )
            
            # 2. Evidence Retrieval (Structured)
            structured_evidence = await self._retrieve_structured_evidence(req, plan)
            
            await self.events.publish(
                topic="execution.events",
                event_type="research.structured_retrieval.completed",
                execution_id=str(req.id),
                status="completed",
                metadata={"count": len(structured_evidence)}
            )
            
            await self.events.publish(
                topic="execution.events",
                event_type="research.document_retrieval.started",
                execution_id=str(req.id),
                status="running"
            )
            
            # 3. Evidence Retrieval (Unstructured/RAG)
            document_evidence = await self._retrieve_document_evidence(req, plan)
            
            meta_payload = getattr(self, "_last_doc_meta", {})
            meta_payload["count"] = len(document_evidence)
            
            await self.events.publish(
                topic="execution.events",
                event_type="research.document_retrieval.completed",
                execution_id=str(req.id),
                status="completed",
                metadata=meta_payload
            )
            
            req.status = "synthesizing"
            await self.db.commit()
            
            await self.events.publish(
                topic="execution.events",
                event_type="research.synthesis.started",
                execution_id=str(req.id),
                status="running"
            )
            
            # 4. Analysis and Synthesis
            synthesis = await self._synthesize_research(req, plan, structured_evidence, document_evidence)
            
            # Update Request
            req.findings = synthesis.get("findings", [])
            req.limitations = synthesis.get("limitations", [])
            req.executive_summary = synthesis.get("executive_summary", "")
            req.status = "completed"
            req.completed_at = datetime.datetime.utcnow()
            
            # 5. Save Claims
            for claim_data in synthesis.get("claims", []):
                evidence_ids_str = claim_data.get("evidence_ids", [])
                evidence_ids = []
                for eid in evidence_ids_str:
                    try:
                        evidence_ids.append(uuid.UUID(eid))
                    except:
                        pass
                
                claim = ResearchClaim(
                    request_id=req.id,
                    text=claim_data.get("text"),
                    confidence=claim_data.get("confidence", "unknown"),
                    evidence_ids=evidence_ids,
                    verification_status="unverified"
                )
                self.db.add(claim)
                
            await self.db.commit()
            
            await self.events.publish(
                topic="execution.events",
                event_type="research.completed",
                execution_id=str(req.id),
                status="success"
            )
            
            return req
            
        except Exception as e:
            req.status = "failed"
            await self.db.commit()
            await self.events.publish(
                topic="execution.events",
                event_type="research.failed",
                execution_id=str(req.id),
                status="error",
                error=str(e)
            )
            raise e

    async def _generate_plan(self, req: ResearchRequest) -> ResearchPlan:
        prompt = f"""
        You are an advanced marine research planner.
        Question: {req.question}
        Geographic Scope: {req.geographic_scope}
        Temporal Scope: {req.temporal_scope}
        
        Generate a JSON plan with:
        - objectives (list of strings)
        - structured_queries (list of objects with service: 'weather'|'ocean'|'cyclone'|'vessel'|'exposure', and lat, lon, radius)
        - document_queries (list of strings for RAG search)
        
        Return ONLY valid JSON. No markdown.
        """
        response = await self.llm.generate(prompt)
        try:
            content = response.content.replace("```json", "").replace("```", "").strip()
            plan_data = json.loads(content)
        except:
            plan_data = {"objectives": ["Fallback objective"], "structured_queries": [], "document_queries": [req.question]}
            
        plan = ResearchPlan(
            request_id=req.id,
            objectives=plan_data.get("objectives", []),
            structured_queries=plan_data.get("structured_queries", []),
            document_queries=plan_data.get("document_queries", [])
        )
        self.db.add(plan)
        await self.db.flush()
        return plan

    def _map_service_status(self, status: str) -> str:
        s = status.upper()
        if s in ["SUCCESS", "AVAILABLE"]: return "AVAILABLE"
        if s in ["PARTIAL", "STALE"]: return s
        return "UNAVAILABLE"

    async def _retrieve_structured_evidence(self, req: ResearchRequest, plan: ResearchPlan) -> List[ResearchEvidence]:
        evidence_list = []
        for q in plan.structured_queries or []:
            svc = q.get("service")
            lat = q.get("lat")
            lon = q.get("lon")
            
            if not lat or not lon:
                if req.geographic_scope and req.geographic_scope.get("type") == "bbox":
                    coords = req.geographic_scope.get("coordinates", [])
                    if len(coords) == 4:
                        lat = (coords[1] + coords[3]) / 2
                        lon = (coords[0] + coords[2]) / 2
            
            if not lat or not lon:
                continue
                
            res = None
            if svc == "weather":
                res = await self.capability_executor.execute_weather_conditions(lat, lon)
            elif svc == "ocean":
                res = await self.capability_executor.execute_ocean_conditions(lat, lon)
            elif svc == "cyclone":
                res = await self.cyclone_executor.execute_cyclone_intelligence(lat=lat, lon=lon, radius_km=500)
            elif svc == "vessel":
                res = await self.vessel_executor.execute_vessel_intelligence(lat=lat, lon=lon, radius_km=50)
            elif svc == "exposure":
                geom = {"type": "Point", "coordinates": [lon, lat]}
                radius = q.get("radius", 50)
                try:
                    exp = await self.exposure_service.analyze_exposure(
                        geometry_geojson=geom,
                        analysis_type="research_query",
                        distance_km=radius
                    )
                    ev = ResearchEvidence(
                        request_id=req.id,
                        evidence_type="STRUCTURED_DATA",
                        status=self._map_service_status(exp.status),
                        query_context=json.dumps(q),
                        value=exp.population_total or 0.0,
                        unit="people",
                        quality="VALID" if exp.status in ["completed", "partial"] else "UNAVAILABLE",
                        text_snippet=f"Exposure within {radius}km: {exp.population_total} people, {exp.infrastructure_count} infrastructure assets."
                    )
                    self.db.add(ev)
                    evidence_list.append(ev)
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).error(f"Exposure capability failed: {e}")
                continue
                
            if res:
                ev = ResearchEvidence(
                    request_id=req.id,
                    evidence_type="STRUCTURED_DATA",
                    status=self._map_service_status(res.status),
                    query_context=json.dumps(q),
                    value=0.0, 
                    quality=res.status
                )
                self.db.add(ev)
                evidence_list.append(ev)
                
        await self.db.flush()
        return evidence_list

    async def _retrieve_document_evidence(self, req: ResearchRequest, plan: ResearchPlan) -> List[ResearchEvidence]:
        evidence_list = []
        overall_meta = {
            "retrieval_method": "unknown",
            "documents_considered": 0,
            "chunks_considered": 0,
            "chunks_returned": 0,
            "embedding_provider": None,
            "embedding_model": None
        }
        
        for dq in plan.document_queries or []:
            results, meta = await self.doc_retriever.retrieve(dq, top_k=3)
            overall_meta["retrieval_method"] = meta["retrieval_method"]
            overall_meta["documents_considered"] = max(overall_meta["documents_considered"], meta["documents_considered"])
            overall_meta["chunks_considered"] = max(overall_meta["chunks_considered"], meta["chunks_considered"])
            overall_meta["chunks_returned"] += meta["chunks_returned"]
            overall_meta["embedding_provider"] = meta["embedding_provider"]
            overall_meta["embedding_model"] = meta["embedding_model"]
            
            for r in results:
                ev = ResearchEvidence(
                    request_id=req.id,
                    evidence_type="DOCUMENT",
                    chunk_id=r["chunk_id"],
                    document_id=r["document_id"],
                    text_snippet=r["text_snippet"],
                    status="AVAILABLE",
                    query_context=dq,
                    retrieval_method=r["retrieval_method"],
                    retrieval_score=r["retrieval_score"]
                )
                self.db.add(ev)
                evidence_list.append(ev)
                
        await self.db.flush()
        # attach to current execution context so the caller can emit it
        self._last_doc_meta = overall_meta
        return evidence_list

    async def _synthesize_research(self, req: ResearchRequest, plan: ResearchPlan, structured: List[ResearchEvidence], docs: List[ResearchEvidence]) -> Dict[str, Any]:
        
        struct_summary = "\\n".join([f"[ID: {e.id}] Context: {e.query_context} Status: {e.status}" for e in structured])
        docs_summary = "\\n".join([f"[ID: {e.id}] Text: {e.text_snippet}" for e in docs])
        
        prompt = f"""
        You are an advanced marine research engine. Synthesize the findings. Do NOT invent or hallucinate data if status is UNAVAILABLE.
        Question: {req.question}
        
        Structured Data Evidence:
        {struct_summary}
        
        Document Evidence:
        {docs_summary}
        
        Return ONLY a JSON object with:
        - executive_summary (string)
        - findings (list of strings)
        - limitations (list of strings, explain if data was UNAVAILABLE)
        - claims (list of objects with 'text' (string), 'confidence' (string), 'evidence_ids' (list of exact IDs referenced from the evidence above))
        """
        response = await self.llm.generate(prompt)
        try:
            content = response.content.replace("```json", "").replace("```", "").strip()
            return json.loads(content)
        except:
            return {
                "executive_summary": "Analysis completed but synthesis formatting failed.",
                "findings": ["Evidence was collected."],
                "limitations": ["Could not parse LLM output"],
                "claims": []
            }
