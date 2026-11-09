"""Vessel/AIS provider contracts (Phase 8).

Provider-specific logic stays inside concrete providers. Everything downstream consumes
the normalized ``NormalizedVessel`` / ``NormalizedVesselPosition`` records defined here.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict


class BBox(BaseModel):
    min_latitude: float
    min_longitude: float
    max_latitude: float
    max_longitude: float

    def intersects(self, other: "BBox") -> bool:
        return not (
            other.min_latitude > self.max_latitude
            or other.max_latitude < self.min_latitude
            or other.min_longitude > self.max_longitude
            or other.max_longitude < self.min_longitude
        )

    def contains(self, lat: float, lon: float) -> bool:
        return self.min_latitude <= lat <= self.max_latitude and self.min_longitude <= lon <= self.max_longitude

    def as_dict(self) -> Dict[str, float]:
        return self.model_dump()


class NormalizedVessel(BaseModel):
    """Vessel identity/metadata. Only fields the provider actually supplied are set."""
    external_id: str
    mmsi: Optional[str] = None
    imo: Optional[str] = None
    name: Optional[str] = None
    call_sign: Optional[str] = None
    vessel_type: Optional[str] = None
    ais_ship_type: Optional[int] = None
    flag: Optional[str] = None
    length_m: Optional[float] = None
    width_m: Optional[float] = None
    draught_m: Optional[float] = None
    destination: Optional[str] = None
    source_timestamp: Optional[datetime] = None
    metadata: Dict[str, Any] = {}

    model_config = ConfigDict(extra="ignore")


class NormalizedVesselPosition(BaseModel):
    """A single validated AIS position report."""
    external_id: str
    mmsi: Optional[str] = None
    latitude: float
    longitude: float
    timestamp: datetime
    speed_knots: Optional[float] = None
    course_degrees: Optional[float] = None
    heading_degrees: Optional[float] = None
    navigation_status: Optional[str] = None
    source_record_id: Optional[str] = None
    metadata: Dict[str, Any] = {}

    model_config = ConfigDict(extra="ignore")


@dataclass
class ProviderFetchResult:
    provider: str
    dataset: str
    request_reference: str
    retrieved_at: datetime
    positions: List[NormalizedVesselPosition] = field(default_factory=list)
    vessels: List[NormalizedVessel] = field(default_factory=list)
    records_received: int = 0
    records_rejected: int = 0
    rejection_reasons: Dict[str, int] = field(default_factory=dict)
    duplicates_in_payload: int = 0
    source_updated_at: Optional[datetime] = None
    warnings: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class ProviderDescriptor:
    code: str
    name: str
    data_source_name: str
    positions_dataset: str
    metadata_dataset: Optional[str]
    official_url: str
    api_url: str
    authentication: str
    coverage_description: str
    coverage_bbox: Optional[BBox]  # None = global
    update_frequency: str
    historical_support: str
    license: str


class VesselProviderError(Exception):
    """Raised when a provider request fails (HTTP error, timeout, malformed payload)."""

    def __init__(self, provider: str, reason: str, message: str):
        super().__init__(message)
        self.provider = provider
        self.reason = reason  # e.g. http_4xx, http_5xx, timeout, malformed_response, not_configured
        self.message = message


class VesselProvider(ABC):
    descriptor: ProviderDescriptor

    @property
    def code(self) -> str:
        return self.descriptor.code

    @property
    @abstractmethod
    def is_configured(self) -> bool:
        ...

    def covers(self, bbox: BBox) -> bool:
        cov = self.descriptor.coverage_bbox
        return True if cov is None else cov.intersects(bbox)

    @abstractmethod
    async def get_vessels(self, bbox: Optional[BBox], since: datetime) -> ProviderFetchResult:
        """Latest validated positions (and any metadata delivered alongside them)."""

    async def get_vessel_track(self, external_id: str, start: datetime, end: datetime) -> Optional[ProviderFetchResult]:
        """Provider-side history. Returns None when the provider has no history API."""
        return None

    async def get_vessel_details(self, external_id: str) -> Optional[NormalizedVessel]:
        """Provider-side metadata lookup. Returns None when unsupported."""
        return None

    async def get_vessels_metadata(self, since: datetime) -> List[NormalizedVessel]:
        """Bulk metadata refresh. Empty when unsupported."""
        return []
