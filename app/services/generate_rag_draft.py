from app.boundaries import policy_retriever
from schemas.inquiry import CustomerInquiry
from schemas.rag_draft import RagDraftAnswer


def generate_rag_draft(
    inquiry: CustomerInquiry,
) -> RagDraftAnswer | None:
    """정책 문서 기반 답변 초안 생성. 근거 없으면 None 반환."""
    return policy_retriever.retrieve_and_generate(inquiry.message, inquiry.context)
