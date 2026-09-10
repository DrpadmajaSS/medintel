"""
Pydantic schemas for MedIntel API.
"""

from medintel_api.schemas.common import HealthResponse, ErrorResponse, MetadataResponse
from medintel_api.schemas.medication import MedicationItem, MedicationListResponse
from medintel_api.schemas.location import LocationItem, LocationListResponse
from medintel_api.schemas.risk import RiskAssessmentItem, RiskDetailResponse, RiskListResponse
from medintel_api.schemas.inventory import InventoryItem, InventoryListResponse
from medintel_api.schemas.utilization import UtilizationPoint, UtilizationHistoryResponse
from medintel_api.schemas.supplier import SupplierItem, SupplierListResponse
from medintel_api.schemas.intelligence import DailyIntelligenceBrief, BriefItem
from medintel_api.schemas.opportunities import (
    RedistributionOpportunity,
    ExpiryOpportunity,
    OpportunitiesResponse
)
from medintel_api.schemas.what_if import (
    WhatIfRequest,
    WhatIfBaseline,
    WhatIfScenario,
    WhatIfImpact,
    WhatIfResponse
)
from medintel_api.schemas.metrics import DashboardMetricsResponse
from medintel_api.schemas.chat import ChatRequest, ChatResponse, ChatMessage

__all__ = [
    "HealthResponse",
    "ErrorResponse",
    "MetadataResponse",
    "MedicationItem",
    "MedicationListResponse",
    "LocationItem",
    "LocationListResponse",
    "RiskAssessmentItem",
    "RiskDetailResponse",
    "RiskListResponse",
    "InventoryItem",
    "InventoryListResponse",
    "UtilizationPoint",
    "UtilizationHistoryResponse",
    "SupplierItem",
    "SupplierListResponse",
    "DailyIntelligenceBrief",
    "BriefItem",
    "RedistributionOpportunity",
    "ExpiryOpportunity",
    "OpportunitiesResponse",
    "WhatIfRequest",
    "WhatIfBaseline",
    "WhatIfScenario",
    "WhatIfImpact",
    "WhatIfResponse",
    "DashboardMetricsResponse",
    "ChatRequest",
    "ChatResponse",
    "ChatMessage"
]
