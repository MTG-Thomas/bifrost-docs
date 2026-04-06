"""
Health Check Router

Provides health check endpoint for monitoring and load balancers.
"""

from fastapi import APIRouter, Request

from src.core.rate_limiting import RateLimits, limiter
from src.models.contracts.common import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
@limiter.limit(RateLimits.HEALTH)
async def health_check(request: Request) -> HealthResponse:
    """
    Health check endpoint.

    Returns:
        HealthResponse with status and version
    """
    return HealthResponse(status="healthy", version="1.0.0")
