"""
Router package for MedIntel API.
"""

from medintel_api.routers.health import router as health_router
from medintel_api.routers.medications import router as medications_router
from medintel_api.routers.locations import router as locations_router
from medintel_api.routers.risks import router as risks_router
from medintel_api.routers.inventory import router as inventory_router
from medintel_api.routers.utilization import router as utilization_router
from medintel_api.routers.suppliers import router as suppliers_router
from medintel_api.routers.intelligence import router as intelligence_router
from medintel_api.routers.what_if import router as what_if_router
from medintel_api.routers.opportunities import router as opportunities_router
from medintel_api.routers.metrics import router as metrics_router
from medintel_api.routers.chat import router as chat_router

__all__ = [
    "health_router",
    "medications_router",
    "locations_router",
    "risks_router",
    "inventory_router",
    "utilization_router",
    "suppliers_router",
    "intelligence_router",
    "what_if_router",
    "opportunities_router",
    "metrics_router",
    "chat_router"
]
