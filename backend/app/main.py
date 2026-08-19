from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="ClinicFlow AOPI",
    version="1.0.0",
    description="Patient appointment managemenrt API",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health", tags=["health"])
def health_check() -> dict[str, str]:
    return {"status": "healthy", "service": "clinicflow-api"}