# API 계약 초안

상태: draft

## 목적

이 문서는 백엔드와 AI 파트가 어떤 데이터를 주고받을지 합의하기 위한 초안이다.

초기 세팅 단계에서는 실제 schema 코드나 FastAPI route를 만들지 않는다.

## 연결 방향

전체 서비스 연결 방향은 다음과 같다.

```text
Frontend <-> Backend <-> AI
```

AI는 백엔드하고만 통신한다.
프론트엔드 표시, 고객 응답 전송, 문의 저장, 주문/배송 DB 조회, 처리 상태 관리는 백엔드가 담당한다.
정책 문서와 답변 생성 지식은 AI 파트가 관리한다.

## API 계약의 핵심 전제

AI는 문의 데이터를 직접 수집하거나 저장하지 않는다.
AI는 백엔드가 넘겨준 문의 내용과 백엔드 보유 데이터 맥락을 보고, AI가 관리하는 Markdown 정책 문서와 LlamaIndex 검색 결과를 사용해 답변 초안을 생성한다.

따라서 Request는 “고객 문의 생성 요청”이 아니라 “이미 백엔드에 저장된 문의에 대한 답변 초안 생성 요청”이다.

## 역할 분리

| 영역 | 담당 |
| --- | --- |
| Backend | 문의 저장, 주문/배송 DB 조회, 고객/문의 상태 관리, AI 호출, 응답 전송 |
| AI | 정책 문서 관리, Markdown/LlamaIndex 기반 근거 조회, 답변 초안 생성, 검토 필요 여부 반환 |

## 기본 원칙

- AI는 백엔드가 제공한 문의 원문과 운영 데이터 맥락에 의존한다.
- AI는 백엔드 DB를 직접 조회하지 않는다.
- AI는 정책 문서를 자체적으로 관리한다.
- AI는 프론트엔드나 고객 채널을 직접 호출하지 않는다.
- AI는 고객에게 응답을 직접 전송하지 않는다.
- AI는 답변 초안과 최소한의 판단 메타데이터만 반환한다.
- 백엔드 제공 맥락 또는 AI 측 정책 근거가 부족하면 답변을 지어내지 않고 관리자 검토가 필요하다고 반환한다.

## 후보 endpoint

```text
POST /api/v1/answers/draft
```

백엔드가 이미 저장한 문의와 필요한 운영 데이터 맥락을 AI에 전달하면, AI가 자체 Markdown 정책 문서와 LlamaIndex 검색 결과를 참고해 답변 초안과 판단 정보를 반환하는 endpoint다.

## Request 초안

```json
{
  "inquiry_id": "inq_001",
  "message": "제 주문 언제 오나요?",
  "context": {
    "order_status": "배송 중",
    "tracking_number": "1234-5678"
  }
}
```

## Request 필드 설명

| 필드 | 설명 | 필수 여부 | 소유 주체 |
| --- | --- | --- | --- |
| `inquiry_id` | 백엔드에 저장된 문의 고유 ID | 필수 | Backend |
| `message` | 백엔드가 저장한 고객 문의 원문 | 필수 | Backend |
| `context` | 답변 작성에 필요한 주문, 배송, 고객 상태 등 백엔드 제공 운영 데이터 맥락 | 선택 | Backend |

## Request에 넣지 않는 것

초기 AI 계약에서는 다음 정보를 필수로 요구하지 않는다.
필요한 경우 백엔드가 `context` 안에 포함해서 전달한다.

- `customer_id`
- `order_id`
- `channel`
- `created_at`
- 백엔드 내부 DB schema 필드
- 고객 개인정보 원문
- 응답 전송 대상 정보

정책 관련 정보는 백엔드가 넘기지 않는다.
AI 파트가 자체적으로 관리한다.

- `policy_summary`
- 정책 문서 원문
- 정책 문서 검색 결과
- RAG 검색 결과

이유:

- AI는 문의 저장소나 고객 정보를 직접 소유하지 않는다.
- AI는 백엔드의 운영 데이터와 AI 측 정책 지식을 조합해 답변을 작성한다.
- 개인정보와 전송 책임은 백엔드 경계 안에 둔다.
- 정책 문서와 RAG 지식은 AI 파트 경계 안에 둔다.
- API 계약을 작게 유지해야 백엔드 변경의 영향을 줄일 수 있다.

## context 사용 방식

`context`는 백엔드가 AI에게 제공하는 운영 데이터 맥락이다.
정책 정보가 아니라 백엔드 DB 또는 백엔드 상태 관리에서 확인한 사실을 담는다.

예시:

```json
{
  "order_status": "배송 중",
  "tracking_number": "1234-5678",
  "payment_status": "결제 완료"
}
```

초기에는 `context`의 세부 schema를 너무 빨리 확정하지 않는다.
먼저 백엔드가 어떤 운영 데이터를 안정적으로 제공할 수 있는지 확인한 뒤 세부 필드를 확정한다.

## AI 측 정책 문서 사용 방식

정책 문서는 AI 파트에서 관리한다.
초기 구현은 Markdown 정책 문서와 LlamaIndex 기반 검색으로 시작한다.

```text
AI/app/docs/policies/
  shipping.md
  exchange-refund.md
  product.md
  response-tone.md
```

초기 흐름은 다음과 같다.

```text
Markdown 정책 문서
-> LlamaIndex 문서 로딩/검색
-> Pydantic AI 답변 생성 agent
-> 답변 초안과 사용 근거 반환
```

초기에는 별도 VectorDB를 필수로 두지 않는다.
문서 수가 늘어나고 검색 persistence나 metadata filter가 필요해지면 Chroma, Qdrant, pgvector 같은 저장소를 후속 검토한다.

## Response 초안

```json
{
  "inquiry_id": "inq_001",
  "draft_answer": "고객님, 현재 주문은 배송 중이며 송장번호는 1234-5678입니다. 일반 배송은 결제 후 평균 2~3일 소요됩니다.",
  "needs_admin_review": false,
  "reason": "백엔드가 제공한 배송 상태와 AI 측 배송 정책 문서를 근거로 답변 초안을 작성했습니다.",
  "risk_tags": [],
  "used_sources": ["context.order_status", "context.tracking_number", "policy.shipping"],
  "processing_status": "success"
}
```

## Response 필드 설명

| 필드 | 설명 |
| --- | --- |
| `inquiry_id` | 원본 문의 ID |
| `draft_answer` | 백엔드와 관리자 화면이 사용할 답변 초안 |
| `needs_admin_review` | 관리자 검토 필요 여부 |
| `reason` | 답변 생성 또는 관리자 검토 판단 이유 |
| `risk_tags` | 환불, 클레임, 정책 충돌 등 위험 태그 |
| `used_sources` | 답변 초안에 사용한 백엔드 context 또는 AI 측 정책 근거 |
| `processing_status` | 처리 성공, 실패, 보류 상태 |

## Response에서 제외하는 것

초기 AI 응답에서는 다음을 반환하지 않는다.

- 실제 고객 응답 전송 결과
- 백엔드 저장 성공 여부
- 프론트엔드 표시 상태
- 주문/배송 DB 조회 결과 원본
- 고객 개인정보

이유:

- 전송, 저장, 조회, 화면 표시는 백엔드 책임이다.
- AI 응답은 답변 초안 생성 결과에 집중한다.

## 관리자 검토가 필요한 경우

다음 경우에는 `needs_admin_review`를 `true`로 반환한다.

- 백엔드가 제공한 운영 데이터 맥락만으로 답변하기 어려운 경우
- AI 측 정책 문서 검색 결과가 없는 경우
- 교환/환불 최종 판단이 필요한 경우
- 고객 불만 또는 클레임성 문의인 경우
- 문의가 복합적이거나 의도가 불명확한 경우
- 정책 문서 간 내용이 충돌하는 경우
- LLM 또는 외부 시스템 호출이 실패한 경우

## 아직 확정하지 않은 것

- 실제 endpoint URL
- request/response schema의 최종 필드명
- `context`의 세부 schema
- 정책 문서 저장 방식
- VectorDB 도입 여부와 source 표기 형식
- 에러 응답 형식
