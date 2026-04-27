# 아키텍처 문서

상태: decision

## 전체 연결 방향

HSA 서비스의 기본 연결 방향은 다음과 같다.

```text
Frontend <-> Backend <-> AI
```

AI 파트는 백엔드 뒤에 있는 보조 서비스다.
프론트엔드, 고객 채널, 실제 응답 전송은 AI가 직접 처리하지 않는다. 정책 문서와 답변 생성 지식은 AI 파트가 관리한다.

## 아키텍처 결정

HSA AI 파트는 초기 PoC에서 `Lightweight Layered Architecture`를 사용한다.

쉽게 말하면, 하나의 FastAPI 서비스 안에서 다음 계층만 가볍게 분리한다.

```text
api -> schemas -> workflow -> services -> boundaries
```

이 방식은 작은 프로젝트에서 과한 Clean Architecture나 Microservice 구조를 피하면서도, 백엔드와의 API 계약과 AI 내부 책임을 명확히 나누기 위한 선택이다.

## 아키텍처 방향

HSA AI 파트는 초기 PoC에서 Workflow-first 구조를 사용한다.

즉, 여러 agent를 먼저 나누는 방식이 아니라 백엔드가 전달한 고객 문의 1건과 운영 데이터 맥락, AI 파트가 관리하는 Markdown 정책 문서 및 LlamaIndex 검색 결과를 바탕으로 답변 초안을 생성하는 명시적인 workflow를 먼저 만든다.

## 기본 의존성 방향

AI 내부의 권장 의존성 방향은 다음과 같다.

```text
api
-> schemas
-> workflow
-> services
-> boundaries/adapters
```

의존성은 위에서 아래로만 흐르게 한다.
`external systems`는 코드 폴더가 아니라 boundaries/adapters 바깥에 있는 실제 연동 대상이므로, 초기 폴더 구조에는 포함하지 않는다.
service가 FastAPI route를 직접 호출하거나, LLM SDK와 VectorDB client를 직접 호출하지 않도록 한다.

전체 시스템 관점에서는 다음 경계를 지킨다.

```text
Frontend -> Backend -> AI
AI -> Backend
Backend -> Frontend
Backend -> 고객 응답 전송 채널
AI -> AI-managed Markdown policy documents / LlamaIndex retriever
```

AI는 Frontend 또는 고객 응답 전송 채널을 직접 호출하지 않는다.

## api

역할:

- 백엔드에서 들어온 요청 수신
- request/response schema 검증 연결
- workflow 호출
- 결과 반환

포함하지 않는 것:

- 프론트엔드 직접 연결
- 고객 응답 직접 전송
- 백엔드 DB 직접 소유
- 복잡한 판단 로직

## workflow

역할:

- 백엔드가 넘긴 문의 처리 순서 관리
- 분기 처리
- service 호출 순서 결정
- 최종 결과 조립

초기 workflow는 다음 흐름을 가진다.

```text
1. 요청 검증
2. 백엔드 제공 문의 원문과 운영 데이터 맥락 확인
3. AI 측 Markdown 정책 문서를 LlamaIndex로 검색
4. 운영 데이터와 정책 근거 기반 답변 초안 생성
5. 관리자 검토 필요 여부 판단
6. 답변 초안과 최소 메타데이터 반환
```

## services

역할:

- 답변 초안 생성
- AI 측 정책 문서 검색 결과 참조
- 관리자 검토 정책 판단
- 위험 태그 판단
- 판단 이유 생성

포함하지 않는 것:

- FastAPI route 직접 호출
- 프론트엔드 직접 호출
- 고객 응답 직접 전송
- 백엔드 DB 직접 소유
- VectorDB client 직접 호출

## boundaries/adapters

역할:

- 외부 시스템 연결부를 감싼다.
- 외부 시스템이 바뀌어도 service 로직 변경을 줄인다.

후보:

- LLM client
- LlamaIndex 기반 정책 문서 retriever
- prompt store
- backend-provided context adapter
- policy document loader

## 초기 폴더 구조 후보

아래 구조는 구현 시작 시점의 후보이며, 초기 세팅 단계에서는 코드 파일을 만들지 않는다.

```text
AI/
  app/
    main.py
    api/
      routes.py
    schemas/
      inquiry.py
      answer.py
    workflow/
      answer_workflow.py
    services/
      answer_generator.py
      review_policy.py
    boundaries/
      llm_client.py
      policy_loader.py
      document_retriever.py
    docs/
      policies/
    tests/
    evals/
```