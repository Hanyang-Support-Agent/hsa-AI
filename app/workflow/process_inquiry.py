# TODO: 테스트용 임시 stub — workflow 구현 후 삭제
from schemas import CustomerInquiry, InquiryProcessResult
from schemas.process_result import InquiryProcessData, ProcessStatus


# FastAPI 엔드포인트 테스팅 및 API 계약 검증을 위해 process_inquiry 함수의 임시 stub 구현.
def process_inquiry(inquiry: CustomerInquiry) -> InquiryProcessResult:
    return InquiryProcessResult(
        status=ProcessStatus.SUCCESS,
        data=InquiryProcessData(
            inquiry_id=inquiry.inquiry_id,
            auto_reply_available=False,
            draft_answer="[stub] 아직 구현되지 않은 응답입니다.",
            needs_admin_review=True,
            reason="[stub] workflow 미구현 상태",
            risk_tags=[],
            used_sources=[],
        ),
        error=None,
    )
