# 로컬 세팅 가이드

상태: guide

## 목적

이 문서는 팀원이 HSA AI 폴더를 clone 받은 뒤 로컬 개발을 시작하기 위해 필요한 준비 사항을 정리한다.

현재 단계에서는 코드 구현이 없으므로 서버 실행 방법보다 프로젝트 설정과 환경변수 준비를 우선한다.

## 요구 사항

- Python 3.10 이상
- Git
- pip

## 가상환경 생성

macOS 또는 Linux 기준:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Windows 기준:

```bash
python -m venv .venv
.venv\Scripts\activate
```

## 의존성 설치

기본 의존성만 설치:

```bash
python -m pip install --upgrade pip
python -m pip install -e .
```

개발 도구까지 설치:

```bash
python -m pip install -e ".[dev]"
```

## 환경변수 파일 준비

`.env.example`을 복사해서 `.env`를 만든다.

```bash
cp .env.example .env
```

`.env`에는 실제 로컬 값만 넣는다.

현재 확정된 LLM 연동은 OpenAI API 기준으로 둔다.
실제 OpenAI 키는 `.env`에만 입력하고, `.env.example`에는 예시 또는 빈 값만 둔다.

서버 실행 설정은 로컬 기본값으로 다음을 사용한다.
Docker 컨테이너 안에서 실행할 경우 `HOST=0.0.0.0`을 사용하고, 로컬 PC에서만 접근하게 하려면 `HOST=127.0.0.1`로 바꿔도 된다.

```text
HOST=0.0.0.0
PORT=8000
```

주의:

- `.env`는 git에 올리지 않는다.
- `.env.example`에는 실제 secret 값을 넣지 않는다.
- OpenAI API key는 톡방에 평문으로 공유하지 않는다.
- 백엔드 API 직접 호출이 확정되기 전까지 DB 접속정보는 AI `.env`에 넣지 않는다.

## 문제 발생 시 확인할 것

- Python 버전이 3.10 이상인지 확인한다.
- 가상환경이 활성화되어 있는지 확인한다.
- `.env`가 git에 올라가지 않았는지 확인한다.
- 의존성 설치 중 실패하면 pip 버전을 먼저 업데이트한다.
