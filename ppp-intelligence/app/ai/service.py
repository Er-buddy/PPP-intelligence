import logging

from sqlalchemy.orm import Session

import httpx

from app.ai.prompts import QUESTION_PROMPT, SYSTEM_PROMPT
from app.config import get_settings
from app.retrieval.service import search_evidence

logger = logging.getLogger(__name__)


def _build_evidence_context(results: list[dict]) -> str:
    blocks = []

    for index, item in enumerate(results, start=1):
        evidence_id = f"E{index}"

        blocks.append(
            "\n".join(
                [
                    f"[{evidence_id}]",
                    f"Document: {item['filename']}",
                    f"Page: {item['page']}",
                    f"Section: {item['section']}",
                    f"Chunk ID: {item['chunk_id']}",
                    f"Content:\n{item['content']}",
                ]
            )
        )

    return "\n\n".join(blocks)


def ask_project(
    db: Session,
    project_id: str,
    question: str,
) -> dict:
    settings = get_settings()

    if not settings.openrouter_api_key:
        raise RuntimeError(
            "OPENROUTER_API_KEY is not configured."
        )

    results = search_evidence(
        db=db,
        project_id=project_id,
        query=question,
        limit=settings.max_retrieval_chunks,
    )

    if not results:
        return {
            "answer": (
                "I could not find relevant evidence in the "
                "uploaded project documents."
            ),
            "citations": [],
        }

    context = _build_evidence_context(results)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": QUESTION_PROMPT.format(
                question=question,
                evidence=context,
            ),
        },
    ]

    logger.info(f"LLM_CALL_START model={settings.openrouter_model} question_len={len(question)}")

    with httpx.Client(timeout=120.0) as client:
        response = client.post(
            settings.openrouter_base_url + "/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.openrouter_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.openrouter_model,
                "messages": messages,
                "temperature": 0,
            },
        )

    logger.info(f"LLM_CALL_DONE status={response.status_code}")

    response.raise_for_status()
    payload = response.json()

    answer = payload["choices"][0]["message"]["content"]

    citations = [
        {
            "evidence_id": f"E{index}",
            "document_id": item["document_id"],
            "filename": item["filename"],
            "page": item["page"],
            "section": item["section"],
            "chunk_id": item["chunk_id"],
        }
        for index, item in enumerate(results, start=1)
    ]

    return {
        "answer": answer,
        "citations": citations,
    }
