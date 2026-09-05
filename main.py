from fastapi import FastAPI
from config import settings

app = FastAPI(
    title="Observable Gemini Proxy",
    description="Production-ready rate-limited proxy for Gemini API",
    version="0.1.0"
)

@app.get("/health", status_code=200)
async def health_check():
    """
    Liveness probe endpoint.
    Used by Docker HEALTHCHECK and load balancers to verify service availability.
    """
    return {
        "status": "healthy",
        "model": settings.DEFAULT_MODEL
    }