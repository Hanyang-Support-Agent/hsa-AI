# AI 문서 안내

이 `docs/` 폴더는 HSA AI 파트의 개발 방향을 팀원들이 같은 기준으로 이해하기 위한 작은 프로젝트 기준 문서 모음이다.

초기 세팅 단계에서는 코드 구현보다 다음 내용을 먼저 맞춘다.

1. 무엇을 만드는가
2. 이번 PoC에서 어디까지 하는가
3. 어떤 구조로 나눌 것인가
4. 백엔드와 어떤 계약으로 연결할 것인가
5. 팀원이 어떻게 로컬 개발을 시작할 것인가

## 문서 목록

| 문서 | 목적 |
| --- | --- |
| `project-overview.md` | 프로젝트 목적, AI 파트 책임, PoC 범위 정리 |
| `architecture.md` | Lightweight Layered Architecture와 AI 파트 계층 구조 정리 |
| `api-contract.md` | 백엔드와 AI 파트 사이의 API 계약 초안 |
| `framework-decision.md` | AI 파트에서 사용할 프레임워크와 후속 검토 도구 정리 |
| `policy-rag-strategy.md` | 정책 문서 사용 기준과 답변 생성 원칙 정리 |
| `development-guide.md` | 브랜치, 커밋, PR, secret 관리 규칙 |
| `local-setup.md` | 로컬 환경 세팅과 실행 전 준비 사항 |

## 문서 상태 기준

- `draft`: 논의 중인 초안
- `decision`: 현재 팀 기준으로 채택한 결정
- `guide`: 팀원이 따라야 하는 개발 가이드

현재 문서들은 초기 PoC 기준이며, 실제 구현이 시작되면 API 계약과 실행 방법은 변경될 수 있다.
