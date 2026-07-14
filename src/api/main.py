import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from contextlib import asynccontextmanager

from src.api.routers import forecast, explanation, scenario, agent, anomaly
from src.api.dependencies import load_app_state
from src.utils.logger import setup_logger

logger = setup_logger("main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load and cache models, dataset, and explainers on startup
    logger.info("Initializing application models and dataset cache...")
    try:
        # Import database config and models to register on Base metadata before create_all
        from src.core.database import engine, Base
        import src.core.models
        
        logger.info("Ensuring database tables are created...")
        Base.metadata.create_all(bind=engine)
        
        load_app_state()
        logger.info("Application state initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize application state: {e}")
    yield
    logger.info("Shutting down application...")

app = FastAPI(
    title="AI-Powered Business Analytics Assistant ML Microservice",
    description="Production-grade intelligence engine and ML microservice for forecasting, explainability, scenario simulation, anomaly scanning, and NL2SQL data lookup.",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware for secure independent communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root status check
@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "timestamp": "2026-06-14T21:00:00Z"
    }

# Register API Routers
app.include_router(forecast.router, prefix="/api/v1")
app.include_router(explanation.router, prefix="/api/v1")
app.include_router(scenario.router, prefix="/api/v1")
app.include_router(agent.router, prefix="/api/v1")
app.include_router(anomaly.router, prefix="/api/v1")

# Serve static files from React build directory
frontend_dist_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "frontend", "dist")

if os.path.exists(frontend_dist_path):
    # Mount files other than index.html under /assets or root direct
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist_path, "assets")), name="assets")

@app.get("/{catchall:path}")
async def serve_react_app(catchall: str):
    # Skip routing if query is for API
    if catchall.startswith("api/") or catchall.startswith("docs") or catchall.startswith("redoc") or catchall.startswith("openapi.json"):
        raise HTTPException(status_code=404, detail="API endpoint not found")
        
    index_file = os.path.join(frontend_dist_path, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
        
    return HTMLResponse(
        content="<h1>AI Business Analytics Dashboard</h1><p>FastAPI backend is running. Please build the frontend React application to activate this visual dashboard.</p><p>API docs: <a href='/docs'>/docs</a></p>"
    )
