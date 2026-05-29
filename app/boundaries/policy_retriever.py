import os
from pathlib import Path
from typing import Any

from app.boundaries import document_loader
from app.boundaries.llm_client import generate_structured
from schemas.rag_draft import RagDraftAnswer

# 0.4는 경험적 시작점. 최적값은 evals(AGENTS.md 기준 80%)로 결정한다.
# 낮추면: 무관한 문서까지 포함 → 잘못된 초안 생성 위험
# 높이면: 정상 문의도 needs_review로 빠지는 hit rate 저하
# 조정 방법: RAG_RELEVANCE_THRESHOLD=0.3 python scripts/check_retriever.py
RELEVANCE_THRESHOLD = float(os.getenv("RAG_RELEVANCE_THRESHOLD", "0.4"))


def retrieve_and_generate(
    query: str,
    inquiry_context: dict[str, Any] | None,
) -> RagDraftAnswer | None:
    """
    정책 문서 검색 후 Pydantic AI로 답변 합성.
    threshold 미달 시 None 반환 → process_inquiry가 needs_review 처리.
    used_sources는 반환된 RagDraftAnswer에 포함된다.
    """
    inquiry_context = inquiry_context or {}

    index = document_loader.get_index()
    nodes = index.as_retriever(similarity_top_k=3).retrieve(query)
    relevant = [n for n in nodes if (n.score or 0.0) >= RELEVANCE_THRESHOLD]
    if not relevant:
        return None

    policy_sources = list(
        dict.fromkeys(_node_to_source_id(n) for n in relevant)  # 중복 제거, 순서 유지
    )
    context_sources = [f"context.{k}" for k in inquiry_context.keys()]
    used_sources = context_sources + policy_sources

    context_text = "\n\n---\n\n".join(n.get_content() for n in relevant)
    rag_answer = _generate_answer(query, context_text, inquiry_context)

    return rag_answer.model_copy(update={"used_sources": used_sources})


def _node_to_source_id(node: Any) -> str:
    """file_name 메타데이터 → policy.{stem} 변환 (api-contract-v2.md 접두사 규칙)."""
    stem = Path(node.metadata.get("file_name", "unknown")).stem
    return f"policy.{stem}"


def _generate_answer(
    query: str,
    policy_context: str,
    inquiry_context: dict[str, Any],
) -> RagDraftAnswer:
    return generate_structured(
        _build_prompt(query, policy_context, inquiry_context), RagDraftAnswer
    )


def _build_prompt(
    query: str,
    policy_context: str,
    inquiry_context: dict[str, Any],
) -> str:
    ctx_str = (
        "\n".join(f"- {k}: {v}" for k, v in inquiry_context.items()) or "(없음)"
    )
    return f"""
            다음 정책 문서와 운영 데이터를 바탕으로 고객 문의에 대한 답변 초안을 작성하세요.

            [고객 문의]
            {query}

            [백엔드 운영 데이터 (context)]
            {ctx_str}

            [정책 문서]
            {policy_context}

            Return JSON only. All keys must be in camelCase.
            답변은 한국어로 작성합니다.
            정책 문서와 운영 데이터에 명시된 내용만 사용하고, 없는 내용은 추측하지 않습니다.
            """
