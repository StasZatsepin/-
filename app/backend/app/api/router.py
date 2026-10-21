"""Сборка маршрутов API."""

from fastapi import APIRouter

from app.api.routes import analysis, auth, findings, products, reports, sources, stats

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(products.router)
api_router.include_router(sources.router)
api_router.include_router(analysis.router)
api_router.include_router(findings.router)
api_router.include_router(reports.router)
api_router.include_router(stats.router)

__all__ = ["api_router"]
