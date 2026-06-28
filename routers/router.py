from fastapi import APIRouter

from routers import health_router

common_router = APIRouter()
common_router.include_router(health_router.router)
