"""
Custom exception handlers for MedIntel API.
"""

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse


async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "error_code": f"HTTP_{exc.status_code}"}
    )


async def generic_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc), "error_code": "INTERNAL_SERVER_ERROR"}
    )
