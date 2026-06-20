"""
읽기 전용 RDS(PostgreSQL) 클라이언트.
현재 stub 상태 — DB 스키마 및 접근 권한 확정 후 구현.

실제 구현 시 교체할 항목:
- RDS_READ_URL 환경변수로 연결 문자열 관리
- psycopg2 또는 asyncpg 사용
- 반환 딕셔너리 키는 api-contract-v2.md context 필드 규칙(camelCase) 준수
"""
from typing import Any


def lookup_order_context(inquiry_id: str) -> dict[str, Any] | None:
    """
    inquiry_id로 주문/배송 정보를 RDS에서 조회한다.
    반환 딕셔너리는 inquiry.context 형식과 동일하게 camelCase 키를 사용한다.

    stub: 항상 None 반환 → 상위 로직이 RAG 경로로 진행됨 (현재 동작 유지).

    실제 구현 예시:
        row = db.execute(
            "SELECT delivery_status, carrier, tracking_number, current_location ..."
            " FROM orders WHERE inquiry_id = %s",
            (inquiry_id,)
        ).fetchone()
        if not row:
            return None
        return {
            "deliveryStatus": row.delivery_status,
            "carrier": row.carrier,
            "trackingNumber": row.tracking_number,
            "currentLocation": row.current_location,
        }
    """
    return None  # stub
