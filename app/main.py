from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging import configure_logging, get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore[type-arg]
    configure_logging(settings.log_level)
    logger.info("critique_startup", provider=settings.llm_provider, env=settings.environment)
    yield
    logger.info("critique_shutdown")


app = FastAPI(
    title="Critique",
    description="Multi-agent system with LangGraph — privacy-aware, observable, production-grade.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow the frontend to call the API from the browser
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
from app.api.routers import audit, export, health, human, metrics, stream, tasks  # noqa: E402

app.include_router(health.router)
app.include_router(tasks.router)
app.include_router(stream.router)
app.include_router(human.router)
app.include_router(metrics.router)
app.include_router(audit.router)
app.include_router(export.router)
