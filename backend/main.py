"""
FastAPI Application Entry Point.

Includes:
- Lifespan context manager to auto-initialize DB and rehydrate DSA state on startup.
- CORS middleware for frontend communication.
- Modular API routers: Patients, Queue, Doctors, Reports.
- Static file serving of frontend/ at "/".
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.config import FRONTEND_DIR
from backend.database import init_db
from backend.routes.doctors import router as doctors_router
from backend.routes.patients import router as patients_router
from backend.routes.queue import router as queue_router
from backend.routes.reports import router as reports_router
from backend.routes.benchmark import router as benchmark_router
from backend.services.hospital_service import hospital_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context manager.
    Runs on server startup to initialize database schema and rehydrate
    in-memory custom data structures (MinHeap, Queue, HashMap, LinkedList).
    """
    print("[Startup] Initializing Hospital Emergency System...")
    try:
        init_db()
    except Exception as e:
        print(f"[Startup Warning] Database auto-initialization skipped or failed: {e}")
        print("[Startup Info] Verify MySQL is running with valid credentials in .env.")

    try:
        hospital_service.load_from_db()
    except Exception as e:
        print(f"[Startup Warning] Could not load initial state from MySQL into DSA structures: {e}")

    yield

    print("[Shutdown] Cleaning up system resources...")


app = FastAPI(
    title="Hospital Emergency & Patient Priority Management System",
    description="Emergency triage system powered by custom Min-Heap, FIFO Queue, LinkedList, and HashMap.",
    version="1.0.0",
    lifespan=lifespan,
)

# Enable CORS for local development and browser clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(patients_router)
app.include_router(queue_router)
app.include_router(doctors_router)
app.include_router(reports_router)
app.include_router(benchmark_router)


@app.get("/health", tags=["Health"])
def health_check():
    """Health check endpoint to verify backend server status."""
    return {
        "status": "ok",
        "message": "Hospital Emergency System API is running smoothly."
    }


# Mount static files to serve the frontend at the root "/"
# Mounted AFTER API routes so that API routes take precedence
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
