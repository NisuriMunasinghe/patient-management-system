from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import appointments, auth, doctors


app = FastAPI(
    title="ClinicFlow API",
    version="1.0.0",
    description="Patient appointment management API",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(doctors.router, prefix="/api")
app.include_router(appointments.router, prefix="/api")


@app.get("/api/health", tags=["health"])
def health_check() -> dict[str, str]:
    return {
        "status": "healthy",
        "service": "clinicflow-api",
    }