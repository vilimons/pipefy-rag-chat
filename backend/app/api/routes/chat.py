from fastapi import APIRouter

from app.models.schemas import ChatRequest, ChatResponse

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    # Temporary placeholder. Real RAG pipeline will be implemented next.
    return ChatResponse(
        answer=(
            "RAG pipeline is not implemented yet. "
            "This placeholder confirms that the chat contract is working."
        ),
        sources=[],
        session_id=request.session_id,
    )
