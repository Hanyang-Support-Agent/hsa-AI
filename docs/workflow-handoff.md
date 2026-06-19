# Workflow 담당자 인계 문서

상태: handoff

## 목적

RAG reranker 도입에 따라 workflow와 배포 설정에서 반영해야 할 작업을 정리한다.
특히 Backend의 AI 호출 timeout과 ECS 환경변수는 RAG 초안 경로의 성공 여부를
직접 결정한다. RAG public interface는 변경되지 않았다.

```python
def generate_rag_draft(inquiry: CustomerInquiry) -> RagDraftAnswer | None:
    ...
```

## 필수 작업

| 우선순위 | 작업 | 권장 기준 |
| --- | --- | --- |
| P1 | BE → AI HTTP timeout 반영 | `AiInquiryClient`의 `RestTemplate` `readTimeout=60s` 필수 |
| P1 | ECS 환경변수 반영 | `RAG_RELEVANCE_THRESHOLD=0.40` 명시 설정 권장 |
| P1 | RDS 책임 경계 문서 갱신 | AI ECS가 private subnet RDS에 read-only로 접근하는 팀 결정 반영 |
| P2 | `usedSources` 소유권 문서 정리 | RAG boundary가 실제 검색 source를 계산하고 workflow가 외부 응답으로 집약 |
| P2 | RAG `None` 경로 유지 | 검색 근거 없음 또는 reranker 선택 없음 → `needs_review` |
| P2 | 오류 매핑 확인 | embedding, reranker, 답변 생성 provider 실패 → `EXTERNAL_SYSTEM_ERROR` 또는 합의한 세부 코드 |

## Timeout 권장값

2026-05-31 반복 라이브 측정에서 검색 + rerank 최대 지연은 `18.88s`였다.
답변 생성까지 포함한 RAG boundary 최대 관측 지연은 `28.66s`였다.
이 값에는 workflow의 분류 LLM 시간이 포함되지 않는다.

현재 Backend의 AI 호출 `readTimeout`이 `5s`이면 RAG 초안 경로는 정상 완료 전에
끊긴다. RAG 초안 p95는 약 `24s`이고, 현재 측정 최대값도 `28.66s`라서 `5s` 설정에서는
RAG draft가 `EXTERNAL_SYSTEM_ERROR`로 매핑되고 Backend 처리는 `FAILED`가 된다.
자동응답 템플릿 경로는 보통 `1s` 미만이라 영향이 작지만, RAG 기능은 timeout
상향 없이는 운영 성공 경로가 없다.

Backend 저장소에서 적용할 계약:

```java
// AiInquiryClient 전용 RestTemplate 설정 예시
builder
    .setConnectTimeout(Duration.ofSeconds(5))
    .setReadTimeout(Duration.ofSeconds(60));
```

AI 저장소에는 `AiInquiryClient` 구현이 없으므로 이 파일은 Backend 구현자가 적용할
timeout 계약과 운영 검증 기준을 명시한다.

초기 운영값:

| 항목 | 권장값 | 이유 |
| --- | --- | --- |
| BE → AI 전체 요청 timeout | `60s` | RAG boundary 최대 `28.66s`에 분류, 네트워크 변동 여유 포함 |
| 모니터링 경고 기준 | `30s` | 정상 요청 지연 증가를 timeout 전에 감지 |
| 재조정 시점 | 운영 요청 `p95`, `p99` 수집 후 | `p99 + 20%`를 기준으로 timeout 재검토 |

timeout이 지나치게 길면 BE 재시도가 늦어지고, 지나치게 짧으면 정상 RAG 요청이 실패한다.
초기에는 `60s`로 시작하고 운영 로그를 기반으로 조정한다.

## ECS RAG 환경변수

현재 `development` 기준 ECS task definition에는 `RAG_RELEVANCE_THRESHOLD=0.40`만
명시 설정하는 것을 권장한다. 아래 Phase 2/4 값은 해당 RAG 구현이 포함된 배포
브랜치에서 기본값 `0.05`가 적용될 때의 운영 기준이다. 이 브랜치에는 두 환경변수를
읽는 코드가 아직 없으므로 현재 ECS에는 추가하지 않는다.

| 환경변수 | 권장값 | ECS 설정 |
| --- | --- | --- |
| `RAG_RELEVANCE_THRESHOLD` | `0.40` | 명시 설정 권장 |
| `RAG_CONFLICT_SCORE_EPSILON` | `0.05` | Phase 2 코드 배포 후 기본값 확인, 현재 ECS 미설정 |
| `RAG_RERANK_SKIP_MARGIN` | `0.05` | Phase 4 코드 배포 후 기본값 확인, 현재 ECS 미설정 |

`RAG_CONFLICT_SCORE_EPSILON`은 Phase 2 정책 충돌 감지 민감도이고,
`RAG_RERANK_SKIP_MARGIN`은 Phase 4 조건부 rerank skip 마진이다. 두 값은 해당
구현이 배포 대상에 포함됐는지 확인한 뒤 운영 로그 기준으로만 명시 설정한다.

## RDS 문서 갱신 대상

현재 아래 문서는 여전히 Backend가 주문/배송 DB 조회를 담당한다고 설명한다.
팀 결정에 맞게 AI ECS의 read-only RDS 접근을 반영한다.

- `docs/api-contract-v2.md`
- `docs/project-overview.md`
- `docs/policy-rag-strategy.md`
- `docs/development-guide.md`

실제 SQL 구현은 DB schema와 읽기 전용 계정 확정 후 별도 이슈로 진행한다.

## Workflow 검증 체크리스트

- [ ] RAG가 `None`을 반환하면 `status="needs_review"`와 `[No_Context]` reason을 반환한다.
- [ ] RAG 성공 시 `RagDraftAnswer.used_sources`가 외부 `usedSources`에 포함된다.
- [ ] reranker provider 실패가 성공 응답으로 처리되지 않는다.
- [ ] Backend `AiInquiryClient`의 AI 호출용 `RestTemplate readTimeout`이 `60s`인지 확인한다.
- [ ] ECS task definition에 `RAG_RELEVANCE_THRESHOLD=0.40`만 명시하고, `RAG_CONFLICT_SCORE_EPSILON`/`RAG_RERANK_SKIP_MARGIN`은 해당 구현 배포 전까지 추가하지 않는다.
