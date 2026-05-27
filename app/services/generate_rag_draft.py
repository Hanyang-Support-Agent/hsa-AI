from app.boundaries import policy_retriever
from schemas.inquiry import CustomerInquiry
from schemas.rag_draft import RagDraftAnswer


def generate_rag_draft(
    inquiry: CustomerInquiry,
) -> tuple[RagDraftAnswer, list[str]] | None:
    """정책 문서 기반 답변 초안 생성. 근거 없으면 None 반환."""
    result = policy_retriever.retrieve_and_generate(inquiry.message, inquiry.context)
    if result is None:
        return None
    return RagDraftAnswer(
        draft_answer=result.draft_answer,
        reason=result.reason,
    ), result.used_sources
