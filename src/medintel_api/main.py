"""
MedIntel: Medication Intelligence for Proactive Healthcare Operations.
FastAPI Application Entry Point.
"""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from medintel_api.config import settings
from medintel_api.services.data_service import DataService
from medintel_api.routers import (
    health_router,
    medications_router,
    locations_router,
    risks_router,
    inventory_router,
    utilization_router,
    suppliers_router,
    intelligence_router,
    what_if_router,
    opportunities_router,
    metrics_router,
    chat_router
)
from medintel_api.utils.exceptions import http_exception_handler, generic_exception_handler


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler preloading in-memory caches on startup."""
    print("🚀 Initializing MedIntel API Data Service & Caching Layer...")
    ds = DataService.get_instance(data_dir=settings.data_dir)
    print(f"✅ MedIntel Cache Loaded: {len(ds.medications_by_id)} meds, {len(ds.locations_by_id)} locs, {len(ds.assessments_by_sku)} SKUs on snapshot {ds.snapshot_date_str}")
    yield
    print("🛑 Shutting down MedIntel API Service.")


def create_app() -> FastAPI:
    """FastAPI application factory."""
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=settings.app_subtitle,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan
    )
    
    # CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Register Exception Handlers
    app.add_exception_handler(Exception, generic_exception_handler)
    
    # Mount API Routers at root (for required endpoints GET /health, GET /medications, etc.)
    routers = [
        health_router,
        medications_router,
        locations_router,
        risks_router,
        inventory_router,
        utilization_router,
        suppliers_router,
        intelligence_router,
        what_if_router,
        opportunities_router,
        metrics_router,
        chat_router
    ]
    
    for r in routers:
        app.include_router(r)
        # Also mount under /api prefix for standard web API access
        app.include_router(r, prefix=settings.api_prefix)
        
    # Static files and Web Dashboard mounting
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    if os.path.exists(static_dir):
        app.mount("/static", StaticFiles(directory=static_dir), name="static")
        
        @app.get("/", include_in_schema=False)
        def serve_dashboard():
            return FileResponse(os.path.join(static_dir, "index.html"))
            
    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("medintel_api.main:app", host=settings.host, port=settings.port, reload=True)
