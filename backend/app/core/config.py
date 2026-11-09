from typing import List, Optional
# pyrefly: ignore [missing-import]
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    APP_NAME: str = "ORCA"
    APP_ENV: str = "development"
    DEBUG: bool = True

    DATABASE_URL: str

    REDIS_URL: str
    CELERY_BROKER_URL: str
    CELERY_RESULT_BACKEND: str

    # LLM providers
    GROQ_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    OPENROUTER_API_KEY: Optional[str] = None

    # LLM routing
    PRIMARY_LLM_PROVIDER: str = "groq"
    FALLBACK_LLM_PROVIDER_1: str = "gemini"
    FALLBACK_LLM_PROVIDER_2: str = "openrouter"

    GROQ_MODEL: str = "llama3-8b-8192"
    GEMINI_MODEL: str = "gemini-1.5-flash"
    OPENROUTER_MODEL: str = "openai/gpt-4o-mini"

    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"

    # Future scientific/data providers
    EARTHDATA_TOKEN: Optional[str] = None
    MOSDAC_USERNAME: Optional[str] = None
    MOSDAC_PASSWORD: Optional[str] = None

    # Application configuration
    BACKEND_CORS_ORIGINS: str = "http://localhost:5173"
    DATA_DIR: str = "data"
    
    # Phase 2 Providers
    OPEN_METEO_BASE_URL: str = "https://marine-api.open-meteo.com/v1/marine"
    OPEN_METEO_WEATHER_URL: str = "https://api.open-meteo.com/v1/forecast"
    OPEN_METEO_CACHE_TTL_SECONDS: int = 900
    
    NOAA_ERDDAP_BASE_URL: Optional[str] = "https://coastwatch.pfeg.noaa.gov/erddap"
    NOAA_ERDDAP_DATASET_ID: Optional[str] = "jplMURSST41"
    NOAA_CACHE_TTL_SECONDS: int = 3600
    
    EARTHDATA_CMR_BASE_URL: str = "https://cmr.earthdata.nasa.gov/search"
    NASA_DATASET_ID: Optional[str] = None
    NASA_CACHE_TTL_SECONDS: int = 21600
    
    MOSDAC_DATASET_ID: Optional[str] = None
    MOSDAC_CACHE_TTL_SECONDS: int = 21600
    
    DATA_REQUEST_TIMEOUT_SECONDS: int = 30
    DATA_MAX_QUERY_HOURS: int = 720
    DATA_MAX_RECORDS_PER_REQUEST: int = 10000

    # Phase 8 — Vessel Intelligence (backend-only; never exposed to the frontend)
    # Digitraffic Marine AIS (Fintraffic): open data, no API key, CC BY 4.0.
    DIGITRAFFIC_ENABLED: bool = True
    DIGITRAFFIC_BASE_URL: str = "https://meri.digitraffic.fi"
    DIGITRAFFIC_USER_HEADER: str = "ORCA/1.0"
    # AISStream.io: global terrestrial AIS WebSocket stream, requires a free API key.
    AISSTREAM_API_KEY: Optional[str] = None
    AISSTREAM_URL: str = "wss://stream.aisstream.io/v0/stream"
    AISSTREAM_COLLECT_SECONDS: int = 10
    AISSTREAM_MAX_MESSAGES: int = 5000

    VESSEL_REQUEST_TIMEOUT_SECONDS: int = 20
    VESSEL_DEFAULT_LIMIT: int = 500
    VESSEL_MAX_LIMIT: int = 5000
    VESSEL_TRACK_DEFAULT_LIMIT: int = 1000
    VESSEL_DEFAULT_MAX_AGE_MINUTES: int = 60
    VESSEL_MAX_QUERY_DAYS: int = 31
    VESSEL_DENSITY_MAX_CELLS: int = 10000
    # Freshness / fallback limits
    VESSEL_LIVE_MAX_AGE_SECONDS: int = 300
    VESSEL_CURRENT_FALLBACK_MAX_AGE_SECONDS: int = 1800
    # Cache TTLs (seconds)
    VESSEL_POSITIONS_CACHE_TTL: int = 60
    VESSEL_DETAILS_CACHE_TTL: int = 600
    VESSEL_TRACK_CACHE_TTL: int = 300
    VESSEL_DENSITY_RECENT_CACHE_TTL: int = 120
    VESSEL_DENSITY_HISTORICAL_CACHE_TTL: int = 21600
    VESSEL_METADATA_REFRESH_SECONDS: int = 900
    # Retention: positions older than this are removed ONLY when the purge task runs. 0 disables purging.
    VESSEL_POSITION_RETENTION_DAYS: int = 30
    # Periodic ingestion via Celery beat. 0 = disabled (default) to avoid unbounded storage growth.
    VESSEL_INGEST_INTERVAL_SECONDS: int = 0
    
    # Phase 10 — Exposure & Population
    WORLDPOP_BASE_URL: str = "https://api.worldpop.org/v2"
    WORLDPOP_API_KEY: Optional[str] = None
    WORLDPOP_DEFAULT_YEAR: Optional[int] = None
    WORLDPOP_DEFAULT_RESOLUTION: str = "100m"
    WORLDPOP_TIMEOUT_SECONDS: int = 30
    WORLDPOP_CACHE_TTL_SECONDS: int = 86400

    OVERPASS_BASE_URL: str = "https://overpass-api.de/api/interpreter"
    OVERPASS_TIMEOUT_SECONDS: int = 60
    OVERPASS_MAX_RESULTS: int = 500
    OVERPASS_USER_AGENT: str = "ORCA-Coastal-Exposure/1.0"
    OVERPASS_MIN_RETRY_DELAY_SECONDS: int = 30
    OVERPASS_CACHE_TTL_SECONDS: int = 86400

    EXPOSURE_CACHE_TTL_SECONDS: int = 21600
    EXPOSURE_MAX_AREA_KM2: float = 50000.0
    
    # Phase 9 — Research Engine (RAG)
    EMBEDDING_PROVIDER: Optional[str] = "ollama"
    EMBEDDING_MODEL: str = "embeddinggemma:latest"
    EMBEDDING_API_KEY: Optional[str] = None
    EMBEDDING_BASE_URL: str = "http://localhost:11434"
    EMBEDDING_DIMENSIONS: int = 768

    
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def cors_origins(self) -> List[str]:
        return [origin.strip() for origin in self.BACKEND_CORS_ORIGINS.split(",")]

settings = Settings()
