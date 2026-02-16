"""Main FastAPI application."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.api import assets, outages, pricing, zones
from backend.config import get_settings
from backend.database import async_engine, Base

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    yield
    # Shutdown
    await async_engine.dispose()


app = FastAPI(
    title="Power Market Geospatial Platform",
    description="API for visualizing power market geospatial data including assets, outages, and pricing",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(assets.router, prefix="/api")
app.include_router(outages.router, prefix="/api")
app.include_router(pricing.router, prefix="/api")
app.include_router(zones.router, prefix="/api")


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "1.0.0"}


@app.get("/api/config")
async def get_map_config():
    """Get map configuration."""
    return {
        "center": {
            "lat": settings.default_map_center_lat,
            "lon": settings.default_map_center_lon,
        },
        "zoom": settings.default_map_zoom,
        "maxAssets": settings.max_assets_per_request,
    }


# Mount static files for frontend
try:
    app.mount("/static", StaticFiles(directory="frontend/static"), name="static")
except RuntimeError:
    pass  # Static directory doesn't exist yet


@app.get("/")
async def serve_frontend():
    """Serve the frontend application."""
    return FileResponse("frontend/index.html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
    )
