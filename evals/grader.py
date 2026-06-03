"""채점과 AGENTS.md 임계값 강제를 담당하는 grader.

TaskResult 목록을 받아 케이스별 pass/fail과 지표별 집계를 계산한다.
임계값 미달 시 GradeReport.threshold_passed = False를 반환한다.

AGENTS.md 기준 임계값:
  - Pydantic 검증 통과율 (전체 pass율로 측정)  ≥ 95%
  - 자동응답 분기 정확도                         ≥ 85%
  - RAG 근거 일치율                              ≥ 80%

분류 정확도(≥ 80%)는 tasks.json에 category 골든 라벨이 추가되면 별도 집계한다.
현재는 GradeReport.metrics에 항목만 포함하고 측정 대상 없음으로 표기한다.
"""

from dataclasses import dataclass, field
from typing import Any

from runner import TaskResult

# AGENTS.md 임계값
THRESHOLDS: dict[str, float] = {
    "pydantic_pass_rate": 0.95,
    "auto_reply_accuracy": 0.85,
    "rag_source_match_rate": 0.80,
}


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


@dataclass
class GradeReport:
    cases: list[CaseGrade]
    metrics: list[MetricResult]
    threshold_passed: bool  # 모든 임계값 통과 여부
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

    # data 필드 비교
    actual_data = actual.get("data") or {}
    expected_data = expected.get("data") or {}

    if expected_data:
        core_fields = ["autoReplyAvailable", "needsAdminReview", "riskTags", "usedSources"]
        for field_name in core_fields:
            actual_val = actual_data.get(field_name)
            expected_val = expected_data.get(field_name)

            if isinstance(expected_val, list):
                if sorted(actual_val or []) != sorted(expected_val or []):
                    errors.append(
                        f"data.{field_name} 불일치 (기대: {expected_val}, 실제: {actual_val})"
                    )
            else:
                if actual_val != expected_val:
                    errors.append(
                        f"data.{field_name} 불일치 (기대: {expected_val}, 실제: {actual_val})"
                    )

    # error 필드 비교
    expected_error = expected.get("error")
    if expected_error:
        actual_error = actual.get("error") or {}
        if actual_error.get("code") != expected_error.get("code"):
            errors.append(
                f"error.code 불일치 (기대: {expected_error.get('code')}, 실제: {actual_error.get('code')})"
            )

    # forbidden_sources 검증 — injection 케이스에서 정책 혼합 여부 확인
    # tasks.json의 forbidden_sources 필드에 나열된 소스가 실제 usedSources에 없어야 한다.
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


def _compute_metrics(
    cases: list[CaseGrade],
    results: list[TaskResult],
) -> list[MetricResult]:
    """지표별 점수를 계산하고 임계값과 비교한다."""
    metrics: list[MetricResult] = []

    # 1. Pydantic 검증 통과율 — 전체 pass율로 측정
    total = len(cases)
    pass_rate = sum(1 for c in cases if c.passed) / total if total else 0.0
    threshold = THRESHOLDS["pydantic_pass_rate"]
    metrics.append(MetricResult(
        name="Pydantic 검증 통과율",
        score=pass_rate,
        threshold=threshold,
        passed=pass_rate >= threshold,
    ))

    # 2. 자동응답 분기 정확도 — autoReplyAvailable 비교 대상 케이스만
    auto_reply_cases = [
        (c, r) for c, r in zip(cases, results)
        if (r.expected.get("data") or {}).get("autoReplyAvailable") is not None
        and r.runner_error is None
    ]
    if auto_reply_cases:
        correct = sum(
            1 for c, r in auto_reply_cases
            if (c.actual or {}).get("data", {}).get("autoReplyAvailable")
            == (r.expected.get("data") or {}).get("autoReplyAvailable")
        )
        score = correct / len(auto_reply_cases)
    else:
        score = None
    threshold = THRESHOLDS["auto_reply_accuracy"]
    metrics.append(MetricResult(
        name="자동응답 분기 정확도",
        score=score,
        threshold=threshold,
        passed=score is None or score >= threshold,
    ))

    # 3. RAG 근거 일치율 — expected.data.usedSources가 있는 케이스만
    rag_cases = [
        (c, r) for c, r in zip(cases, results)
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
                # 기대 소스가 있으면 실제 소스에 모두 포함되는지 확인
                if expected_sources.issubset(actual_sources):
                    matched += 1
            else:
                # 기대 소스가 빈 배열이면 실제도 비어야 함 (무관 문의, injection 차단 등)
                if not actual_sources:
                    matched += 1
        score = matched / len(rag_cases)
    else:
        score = None
    threshold = THRESHOLDS["rag_source_match_rate"]
    metrics.append(MetricResult(
        name="RAG 근거 일치율",
        score=score,
        threshold=threshold,
        passed=score is None or score >= threshold,
    ))

    # 4. 분류 정확도 — tasks.json에 category 골든 라벨 추가 후 측정
    metrics.append(MetricResult(
        name="분류 정확도",
        score=None,
        threshold=THRESHOLDS.get("classification_accuracy", 0.80),
        passed=True,  # 측정 대상 없으면 통과로 처리
    ))

    return metrics


def grade_results(results: list[TaskResult]) -> GradeReport:
    """TaskResult 목록 전체를 채점하고 GradeReport를 반환한다."""
    cases = [_grade_case(r) for r in results]
    metrics = _compute_metrics(cases, results)
    threshold_passed = all(m.passed for m in metrics)

    return GradeReport(
        cases=cases,
        metrics=metrics,
        threshold_passed=threshold_passed,
    )
