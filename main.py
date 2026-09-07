from fastapi import FastAPI, HTTPException, Response, Depends, status
from pydantic import BaseModel, Field
from google import genai
from google.genai import errors
from config import settings
from cache import response_cache
from limiter import check_rate_limit

app = FastAPI(
    title="Observable Gemini Proxy",
    description="Production-ready rate-limited proxy for Gemini API",
    version="0.1.0"
)

# Initialize the official Gemini Client once at application startup
# Reusing the client pool avoids TCP handshake overhead on every request
client = genai.Client(api_key=settings.GEMINI_API_KEY)


class GenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=1, description="Text prompt sent to Gemini")
    model: str | None = Field(default=None, description="Optional override for model ID")


class GenerateResponse(BaseModel):
    text: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cached: bool = False


@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    """
    Evaluates proxy health and readiness state.
    """
    # Check if critical secrets and configurations are present
    has_api_key = bool(settings.GEMINI_API_KEY and len(settings.GEMINI_API_KEY) > 10)
    
    if not has_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "unhealthy", "reason": "Missing or invalid API key configuration"}
        )

    return {
        "status": "healthy",
        "model": settings.DEFAULT_MODEL,
        "environment": "configured",
        "cached_entries": response_cache.size()
    }

@app.post(
        "/generate",
        response_model=GenerateResponse,
        status_code=status.HTTP_200_OK,
        dependencies=[Depends(check_rate_limit)],
)
async def generate_text(request: GenerateRequest, response: Response):
    """
    Proxy endpoint forwarding text prompts to Google Gemini API with SHA-256 caching and sliding-window rate limiting.
    Captures raw output and usage metadata.
    """
    target_model = request.model or settings.DEFAULT_MODEL

    # 1. Check cache first
    cached_payload = response_cache.get(model=target_model, prompt=request.prompt)
    if cached_payload:
        # Cache HIT: Set header and return instantly without touching Gemini
        response.headers["X-Cache"] = "HIT"
        return GenerateResponse(**cached_payload, cached=True)

    # Cache MISS: Prepare to make the actual API call
    response.headers["X-Cache"] = "MISS"


    try:
        # client.aio provides the asynchronous implementation
        # Awaiting this prevents blocking the ASGI event loop
        api_response = await client.aio.models.generate_content(
            model=target_model,
            contents=request.prompt
        )

        # Extract token usage metadata safely (defaults to 0 if not returned)
        usage = api_response.usage_metadata
        prompt_tokens = usage.prompt_token_count if usage else 0
        completion_tokens = usage.candidates_token_count if usage else 0
        total_tokens = usage.total_token_count if usage else 0

        payload = {
            "text": api_response.text or "",
            "model": target_model,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens
        }

        # 2. Save fresh result in cache for future identical requests
        response_cache.set(model=target_model, prompt=request.prompt, data=payload)

        return GenerateResponse(**payload, cached=False)

    except errors.APIError as e:
        # Catches upstream Google API failures (auth errors, quota exceeded, invalid model)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Upstream Gemini API error: {e.message}"
        )
    except Exception as e:
        # Catch unexpected server errors
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal proxy error: {str(e)}"
        )