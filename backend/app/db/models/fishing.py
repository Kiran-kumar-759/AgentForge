from sqlalchemy import Column, String, DateTime, Float, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from geoalchemy2 import Geometry
import uuid
from app.db.base import Base
from datetime import datetime, timezone

class FishingZone(Base):
    __tablename__ = "fishing_zones"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider = Column(String, index=True) # e.g. 'INCOIS'
    zone_type = Column(String) # e.g. 'PFZ'
    geom = Column(Geometry("POLYGON", srid=4326), index=True)
    depth_min = Column(Float)
    depth_max = Column(Float)
    valid_from = Column(DateTime(timezone=True))
    valid_to = Column(DateTime(timezone=True))
    metadata_ = Column("metadata", JSON)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
