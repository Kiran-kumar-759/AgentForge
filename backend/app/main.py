# pyrefly: ignore [missing-import]
from fastapi import FastAPI, Request
# pyrefly: ignore [missing-import]
from fastapi.responses import JSONResponse
# pyrefly: ignore [missing-import]
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.exceptions import ORCAException
from app.api.routes import health, system, llm, workspaces, data, registry, intelligence, cyclones, exposure, agent, research, vessels, report
from app.core.logging import logger

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info(f"Starting {settings.APP_NAME} in {settings.APP_ENV} mode")
    yield
    # Shutdown
    logger.info(f"Shutting down {settings.APP_NAME}")

app = FastAPI(
    title=settings.APP_NAME,
    lifespan=lifespan,
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(ORCAException)
async def orca_exception_handler(request: Request, exc: ORCAException):
    logger.error(f"ORCAException: {exc.message} - Path: {request.url.path}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": exc.message},
    )

app.include_router(health.router)
app.include_router(system.router, prefix="/api/v1")
app.include_router(workspaces.router, prefix="/api/v1/workspaces")
app.include_router(llm.router, prefix="/api/v1/llm")
app.include_router(data.router, prefix="/api/v1")
app.include_router(registry.router, prefix="/api/v1")
app.include_router(intelligence.router, prefix="/api/v1")
app.include_router(cyclones.router, prefix="/api/v1/cyclones")
app.include_router(exposure.router, prefix="/api/v1")
app.include_router(agent.router, prefix="/api/v1")
app.include_router(research.router, prefix="/api/v1/research")
app.include_router(vessels.router, prefix="/api/v1")
app.include_router(report.router, prefix="/api/v1")
