"""
Security Headers Middleware

Adds important security headers to all HTTP responses.
Based on OWASP Secure Headers Project recommendations.
"""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from src.config import get_settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to all responses.

    Headers added:
    - X-Content-Type-Options: nosniff
    - X-Frame-Options: DENY
    - X-XSS-Protection: 1; mode=block (legacy browsers)
    - Strict-Transport-Security (HSTS)
    - Content-Security-Policy
    - Referrer-Policy
    - Permissions-Policy
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        response = await call_next(request)
        settings = get_settings()

        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"

        # Legacy XSS protection for older browsers
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Referrer policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions policy (formerly Feature-Policy)
        response.headers["Permissions-Policy"] = (
            "accelerometer=(), "
            "camera=(), "
            "geolocation=(), "
            "gyroscope=(), "
            "magnetometer=(), "
            "microphone=(), "
            "payment=(), "
            "usb=()"
        )

        # HSTS (only in production and if using HTTPS)
        if settings.environment == "production":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )

        # Content Security Policy
        # More restrictive in production, more permissive in development
        if settings.environment == "production":
            # Strict CSP for production
            csp_directives = [
                "default-src 'self'",
                "script-src 'self'",
                "style-src 'self' 'unsafe-inline'",  # Allow inline styles (needed for many UI frameworks)
                "img-src 'self' data: blob:",
                "font-src 'self'",
                "connect-src 'self'",
                "media-src 'self'",
                "object-src 'none'",
                "frame-ancestors 'none'",
                "base-uri 'self'",
                "form-action 'self'",
            ]
        else:
            # More permissive CSP for development (allows eval, inline scripts)
            csp_directives = [
                "default-src 'self'",
                "script-src 'self' 'unsafe-inline' 'unsafe-eval'",  # Needed for Vite HMR
                "style-src 'self' 'unsafe-inline'",
                "img-src 'self' data: blob: https:",
                "font-src 'self' data:",
                "connect-src 'self' ws: wss:",  # Allow WebSocket for HMR
                "media-src 'self'",
                "object-src 'none'",
                "frame-ancestors 'none'",
            ]

        response.headers["Content-Security-Policy"] = "; ".join(csp_directives)

        return response


def add_security_headers(app):
    """
    Add security headers middleware to FastAPI app.

    Usage:
        from src.core.security_headers import add_security_headers
        add_security_headers(app)
    """
    app.add_middleware(SecurityHeadersMiddleware)
