"""
Mayz Monitoring Backend - FastAPI Application
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from app.config import APP_NAME, APP_VERSION, CORS_ORIGINS
from app.api.endpoints import auth, dashboard, jobs, export, settings, instagram_accounts, staging

app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description="API Backend for Mayz Instagram Monitoring System"
)

# Middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(jobs.router)
app.include_router(export.router)
app.include_router(settings.router)
app.include_router(instagram_accounts.router)
app.include_router(staging.router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": APP_NAME,
        "version": APP_VERSION,
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    from app.database import test_connection
    db_ok, db_msg = test_connection()
    return {
        "status": "healthy" if db_ok else "degraded",
        "database": db_msg
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
