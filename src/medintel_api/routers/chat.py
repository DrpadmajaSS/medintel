"""
Gemini Copilot chat router for MedIntel API.
"""

from fastapi import APIRouter, Depends
from medintel_api.schemas.chat import ChatRequest, ChatResponse
from medintel_api.services.data_service import DataService, get_data_service
from medintel_api.services.gemini_service import GeminiCopilotService

router = APIRouter(prefix="/chat", tags=["Gemini Copilot (Ask MedIntel)"])


@router.post("", response_model=ChatResponse, summary="Ask MedIntel Gemini Copilot")
def chat_copilot(
    request: ChatRequest,
    ds: DataService = Depends(get_data_service)
) -> ChatResponse:
    """
    Submits a natural-language query to the MedIntel Copilot.
    
    The copilot reasons with access to application data and tools (risks, inventory, suppliers, opportunities, what-if)
    and produces grounded, explainable clinical intelligence answers.
    """
    service = GeminiCopilotService(ds)
    return service.answer_query(request)
