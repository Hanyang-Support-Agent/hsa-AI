"""채점과 AGENTS.md 임계값 강제를 담당하는 grader.

TaskResult 목록을 받아 케이스별 pass/fail과 지표별 집계를 계산한다.

AGENTS.md PR 통과 조건:
  - 4개 지표 모두 목표치 이상
  - 실패 태스크가 1개라도 있으면 PR 금지

AGENTS.md 기준 임계값:
  - Pydantic 검증 통과율  ≥ 95%  — api-contract 필수 필드 전체 보유율
  - 자동응답 분기 정확도  ≥ 85%
  - RAG 근거 일치율       ≥ 80%
  - p95 latency          < 30s  (quality-handoff gate)

분류 정확도(≥ 80%)는 현재 API 응답에 분류 결과가 포함되지 않아 측정 불가.
측정 불가 = 미충족 상태로 처리해 PR 통과 조건에서 블로킹한다.
"""

from dataclasses import dataclass, field
from typing import Any

from runner import TaskResult

# AGENTS.md 임계값
THRESHOLDS: dict[str, float] = {
    "pydantic_pass_rate": 0.95,
    "auto_reply_accuracy": 0.85,
    "rag_source_match_rate": 0.80,
    "p95_latency_seconds": 30.0,
}

# api-contract-v2.md 기준 필수 필드
_REQUIRED_TOP_FIELDS = {"status", "data", "error"}
_REQUIRED_DATA_FIELDS = {
    "inquiryId", "autoReplyAvailable", "needsAdminReview",
    "reason", "riskTags", "usedSources",
}
_REQUIRED_ERROR_FIELDS = {"code", "message"}


@dataclass
class CaseGrade:
    task_id: str
    passed: bool
    errors: list[str]
    latency: float
    actual: dict[str, Any] | None
    runner_error: str | None


@dataclass
class MetricResult:
    name: str
    score: float | None  # 측정 대상 케이스가 없으면 None
    threshold: float
    passed: bool
    note: str = ""  # 측정 불가 등 부가 설명


@dataclass
class GradeReport:
    cases: list[CaseGrade]
    metrics: list[MetricResult]
    threshold_passed: bool  # 지표 임계값 + 케이스 전원 통과 여부
    total: int = field(init=False)
    pass_count: int = field(init=False)
    fail_count: int = field(init=False)

    def __post_init__(self) -> None:
        self.total = len(self.cases)
        self.pass_count = sum(1 for c in self.cases if c.passed)
        self.fail_count = self.total - self.pass_count


# ---------------------------------------------------------------------------
# 내부 채점 함수
# ---------------------------------------------------------------------------

def _grade_case(result: TaskResult) -> CaseGrade:
    """단일 TaskResult를 채점해 CaseGrade를 반환한다."""
    errors: list[str] = []

    if result.runner_error:
        errors.append(f"Runner 오류: {result.runner_error}")
        return CaseGrade(
            task_id=result.task_id,
            passed=False,
            errors=errors,
            latency=result.latency,
            actual=None,
            runner_error=result.runner_error,
        )

    actual = result.actual or {}
    expected = result.expected

    # 최상위 status 비교
    if actual.get("status") != expected.get("status"):
        errors.append(
            f"status 불일치 (기대: {expected.get('status')}, 실제: {actual.get('status')})"
        )

    # data 필드 비교 — status=error 응답은 data=null이므로 or {} 처리
    actual_data = (actual.get("data") or {})
    expected_data = (expected.get("data") or {})

    if expected_data:
        core_fields = ["autoReplyAvailable", "needsAdminReview", "riskTags", "usedSources"]
        for field_name in core_fields:
            actual_val = actual_data.get(field_name)
            expected_val = expected_data.get(field_name)

            if isinstance(expected_val, list):
                if field_name == "usedSources":
                    # 기대 소스가 실제 소스에 포함되는지 확인 (실제가 더 많아도 통과)
                    if not set(expected_val).issubset(set(actual_val or [])):
                        errors.append(
                            f"data.{field_name} 불일치 (기대: {expected_val}, 실제: {actual_val})"
                        )
                elif sorted(actual_val or []) != sorted(expected_val or []):
                    errors.append(
                        f"data.{field_name} 불일치 (기대: {expected_val}, 실제: {actual_val})"
                    )
            else:
                if actual_val != expected_val:
                    errors.append(
                        f"data.{field_name} 불일치 (기대: {expected_val}, 실제: {actual_val})"
                    )

    # error 필드 비교
    expected_error = (expected.get("error") or {})
    if expected_error:
        actual_error = (actual.get("error") or {})
        if actual_error.get("code") != expected_error.get("code"):
            errors.append(
                f"error.code 불일치 (기대: {expected_error.get('code')}, "
                f"실제: {actual_error.get('code')})"
            )

    # forbidden_sources 검증 — injection 케이스에서 정책 혼합 여부 확인
    forbidden = result.task.get("forbidden_sources", [])
    if forbidden:
        actual_sources = set(actual_data.get("usedSources") or [])
        mixed = actual_sources & set(forbidden)
        if mixed:
            errors.append(
                f"정책 혼합 감지 — usedSources에 허용되지 않는 소스 포함: {sorted(mixed)}"
            )

    return CaseGrade(
        task_id=result.task_id,
        passed=len(errors) == 0,
        errors=errors,
        latency=result.latency,
        actual=actual if actual else None,
        runner_error=None,
    )


def _is_schema_valid(actual: dict[str, Any] | None) -> bool:
    """api-contract-v2.md 기준 필수 필드를 모두 보유하는지 검사한다."""
    if actual is None:
        return False
    if not _REQUIRED_TOP_FIELDS.issubset(actual.keys()):
        return False
    status = actual.get("status")
    if status == "error":
        return _REQUIRED_ERROR_FIELDS.issubset((actual.get("error") or {}).keys())
    return _REQUIRED_DATA_FIELDS.issubset((actual.get("data") or {}).keys())


def _compute_metrics(
    cases: list[CaseGrade],
    results: list[TaskResult],
) -> list[MetricResult]:
    """지표별 점수를 계산하고 임계값과 비교한다."""
    metrics: list[MetricResult] = []

    # 1. Pydantic 검증 통과율
    # 응답 수신 케이스 중 api-contract 필수 필드 전체 보유율.
    # runner_error 케이스는 네트워크 문제로 제외.
    received = [c for c in cases if c.runner_error is None and c.actual is not None]
    if received:
        schema_valid = sum(1 for c in received if _is_schema_valid(c.actual))
        pydantic_score: float | None = schema_valid / len(received)
    else:
        pydantic_score = None
    threshold = THRESHOLDS["pydantic_pass_rate"]
    metrics.append(MetricResult(
        name="Pydantic 검증 통과율",
        score=pydantic_score,
        threshold=threshold,
        passed=pydantic_score is None or pydantic_score >= threshold,
    ))

    # 2. 자동응답 분기 정확도 — autoReplyAvailable 비교 대상 케이스만
    auto_reply_cases = [
        (c, r) for c, r in zip(cases, results, strict=True)
        if (r.expected.get("data") or {}).get("autoReplyAvailable") is not None
        and r.runner_error is None
    ]
    if auto_reply_cases:
        correct = sum(
            1 for c, r in auto_reply_cases
            if ((c.actual or {}).get("data") or {}).get("autoReplyAvailable")
            == (r.expected.get("data") or {}).get("autoReplyAvailable")
        )
        auto_score: float | None = correct / len(auto_reply_cases)
    else:
        auto_score = None
    threshold = THRESHOLDS["auto_reply_accuracy"]
    metrics.append(MetricResult(
        name="자동응답 분기 정확도",
        score=auto_score,
        threshold=threshold,
        passed=auto_score is None or auto_score >= threshold,
    ))

    # 3. RAG 근거 일치율 — expected.data.usedSources가 있는 케이스만
    rag_cases = [
        (c, r) for c, r in zip(cases, results, strict=True)
        if (r.expected.get("data") or {}).get("usedSources") is not None
        and r.runner_error is None
    ]
    if rag_cases:
        matched = 0
        for c, r in rag_cases:
            expected_sources = set((r.expected.get("data") or {}).get("usedSources") or [])
            actual_sources = set(
                ((c.actual or {}).get("data") or {}).get("usedSources") or []
            )
            if expected_sources:
                if expected_sources.issubset(actual_sources):
                    matched += 1
            else:
                # 기대 소스가 빈 배열이면 실제도 비어야 함 (무관 문의, injection 차단 등)
                if not actual_sources:
                    matched += 1
        rag_score: float | None = matched / len(rag_cases)
    else:
        rag_score = None
    threshold = THRESHOLDS["rag_source_match_rate"]
    metrics.append(MetricResult(
        name="RAG 근거 일치율",
        score=rag_score,
        threshold=threshold,
        passed=rag_score is None or rag_score >= threshold,
    ))

    # 4. p95 latency — quality-handoff gate (< 30s)
    latencies = sorted(c.latency for c in cases if c.runner_error is None)
    if latencies:
        p95_idx = max(0, int(len(latencies) * 0.95) - 1)
        p95 = latencies[p95_idx]
        p95_threshold = THRESHOLDS["p95_latency_seconds"]
        metrics.append(MetricResult(
            name="p95 latency",
            score=p95,
            threshold=p95_threshold,
            passed=p95 < p95_threshold,
        ))
    else:
        metrics.append(MetricResult(
            name="p95 latency",
            score=None,
            threshold=THRESHOLDS["p95_latency_seconds"],
            passed=True,
        ))

    # 5. 분류 정확도 — 현재 API 응답에 분류 결과 미포함, 측정 불가
    # 측정 불가 = 미충족으로 처리해 PR 통과를 블로킹한다.
    # 해소 방법: API 응답에 inquiryType 추가 또는 classify_inquiry 단위 eval 별도 구현.
    metrics.append(MetricResult(
        name="분류 정확도",
        score=None,
        threshold=0.80,
        passed=False,
        note="API 응답에 분류 결과 미포함 — inquiryType 노출 또는 단위 eval 추가 필요",
    ))

    return metrics


def grade_results(results: list[TaskResult]) -> GradeReport:
    """TaskResult 목록 전체를 채점하고 GradeReport를 반환한다.

    AGENTS.md PR 통과 조건:
    - 4개 지표 모두 목표치 이상
    - 실패 태스크가 1개라도 있으면 PR 금지
    """
    cases = [_grade_case(r) for r in results]
    metrics = _compute_metrics(cases, results)
    fail_count = sum(1 for c in cases if not c.passed)
    metrics_passed = all(m.passed for m in metrics)
    threshold_passed = metrics_passed and fail_count == 0

    return GradeReport(
        cases=cases,
        metrics=metrics,
        threshold_passed=threshold_passed,
    )
