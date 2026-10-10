from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import Base, engine, SessionLocal
from app.seed.seed_data import seed_demo_database

# Import routers
from app.api.endpoints import (
    health,
    dashboard,
    returns,
    recovery,
    suppliers,
    actions,
    copilot,
    data,
    settings as settings_router
)

# Initialize tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    description="What Came Back: AI-Powered Returns Recovery and Supplier Intelligence Platform for Gadgetbay."
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(health.router, prefix="/api", tags=["Health"])
app.include_router(dashboard.router, prefix="/api", tags=["Dashboard"])
app.include_router(returns.router, prefix="/api", tags=["Returns"])
app.include_router(recovery.router, prefix="/api", tags=["Recovery Engine"])
app.include_router(suppliers.router, prefix="/api", tags=["Supplier Intelligence"])
app.include_router(actions.router, prefix="/api", tags=["Actions & Approvals"])
app.include_router(copilot.router, prefix="/api", tags=["Copilot Assistant"])
app.include_router(data.router, prefix="/api", tags=["Data & Ingestion"])
app.include_router(settings_router.router, prefix="/api", tags=["Settings"])

@app.on_event("startup")
def on_startup():
    db = SessionLocal()
    try:
        # Seed demo data if database is fresh
        seed_demo_database(db)
    finally:
        db.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
