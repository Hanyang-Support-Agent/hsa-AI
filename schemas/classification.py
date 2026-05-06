"""
schemas/classification.py

문의 유형 분류 결과 모델.
classify_inquiry 함수의 반환 타입.
"""

from enum import Enum

from pydantic import Field

from schemas.base import BaseHsaModel


class InquiryCategory(str, Enum):
    DELIVERY = "배송 문의"
    REFUND_EXCHANGE = "교환/환불 문의"
    PRODUCT = "상품 문의"
    ETC = "기타 문의"


class ClassificationResult(BaseHsaModel):
    """
    문의 분류 결과.

    PoC에서는 confidence를 hard threshold로 사용하지 않는다.
    LLM의 self-reported confidence이며, evals에서 calibration을 측정한 뒤
    v2에서 임계값 도입을 재검토한다.
    """

    category: InquiryCategory = Field(..., description="분류된 문의 유형")
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="LLM 자가 보고 신뢰도. PoC에서는 참고용",
    )
    reason: str = Field(..., min_length=1, description="분류 근거")
