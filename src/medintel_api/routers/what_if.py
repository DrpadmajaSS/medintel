"""
Interactive What-If scenario simulation router for MedIntel API.
"""

from fastapi import APIRouter, Depends, HTTPException
from medintel_api.schemas.what_if import WhatIfRequest, WhatIfResponse
from medintel_api.services.data_service import DataService, get_data_service
from medintel_api.services.what_if_service import WhatIfService

router = APIRouter(prefix="/what-if", tags=["What-If Scenario Simulator"])


@router.post("", response_model=WhatIfResponse, summary="Execute Non-Destructive What-If Simulation")
def simulate_what_if(
    request: WhatIfRequest,
    ds: DataService = Depends(get_data_service)
) -> WhatIfResponse:
    """
    Executes a non-destructive What-If scenario simulation.
    
    Accepts operational perturbations (demand surge %, supplier delay days, inventory changes / lateral transfers)
    and returns comparative Baseline vs. Scenario vs. Impact delta analysis.
    """
    service = WhatIfService(ds)
    try:
        response = service.simulate(request)
        return response
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Simulation error: {str(e)}")
