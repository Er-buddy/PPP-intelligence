import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.ai.service import ask_project
from app.db import SessionLocal

logger = logging.getLogger(__name__)

QUESTIONS = [
    {
        "id": "q1",
        "category": "Economics",
        "question": (
            "Upside & Exposure (The Economics): What are the expected equity IRR, NPV, CAPEX, "
            "and total maximum realistic financial exposure required from us?"
        ),
    },
    {
        "id": "q2",
        "category": "Cashflow",
        "question": (
            "Payer & Security (The Cashflow): Who pays us, and how certain is that revenue "
            "through sovereign guarantees, minimum revenue commitments, or secure offtake agreements?"
        ),
    },
    {
        "id": "q3",
        "category": "Fatal Flaws",
        "question": (
            "The Killers (The Fatal Flaws): What termination clauses, force majeure provisions, "
            "delay penalties, or change-in-law risks can permanently break the project financially?"
        ),
    },
    {
        "id": "q4",
        "category": "Capital",
        "question": (
            "Bankability & Financing (The Capital): Can this project be successfully financed "
            "given the expected debt tenor, interest rates, and required DSCR?"
        ),
    },
    {
        "id": "q5",
        "category": "Win",
        "question": (
            "Competitive Advantage (The Win): Do we possess the specific local partnerships, "
            "experience, and pricing power required to actually win and successfully deliver this?"
        ),
    },
]

_POSITIVE_INDICATORS = [
    "attractive",
    "strong",
    "available",
    "confirmed",
    "adequate",
    "sufficient",
    "favorable",
    "manageable",
    "bankable",
    "experienced",
    "proven",
    "high probability",
    "guaranteed",
    "secured",
    "competitive advantage",
    "clear",
    "robust",
]

_NEGATIVE_INDICATORS = [
    "high risk",
    "not bankable",
    "insufficient",
    "unclear",
    "no guarantee",
    "not recommended",
    "poor",
    "weak",
    "limited",
    "not available",
    "not confirmed",
    "significant risk",
    "unacceptable",
    "not feasible",
    "cannot",
    "unable",
    "difficult",
    "challenging",
]


def _classify_answer(answer: str) -> str:
    lower = answer.lower()

    if "insufficient evidence" in lower:
        return "insufficient"

    positive_hits = sum(1 for indicator in _POSITIVE_INDICATORS if indicator in lower)
    negative_hits = sum(1 for indicator in _NEGATIVE_INDICATORS if indicator in lower)

    if positive_hits > negative_hits:
        return "positive"
    if negative_hits > positive_hits:
        return "negative"
    return "neutral"


def run_evaluation(
    db: Session,
    project_id: str,
) -> dict[str, Any]:
    results = []

    for item in QUESTIONS:
        answer = ask_project(
            db=db,
            project_id=project_id,
            question=item["question"],
        )

        sentiment = _classify_answer(answer.get("answer", ""))

        results.append(
            {
                "id": item["id"],
                "category": item["category"],
                "question": item["question"],
                "answer": answer.get("answer", ""),
                "citations": answer.get("citations", []),
                "sentiment": sentiment,
            }
        )

    positive_count = sum(1 for r in results if r["sentiment"] == "positive")
    negative_count = sum(1 for r in results if r["sentiment"] == "negative")
    neutral_count = sum(1 for r in results if r["sentiment"] == "neutral")
    insufficient_count = sum(1 for r in results if r["sentiment"] == "insufficient")

    if positive_count >= 4 and negative_count == 0 and insufficient_count == 0:
        recommendation = "BID"
        color = "green"
    elif negative_count >= 2 or insufficient_count >= 2:
        recommendation = "NO-BID"
        color = "red"
    else:
        recommendation = "CLARIFY"
        color = "yellow"

    return {
        "project_id": project_id,
        "summary": {
            "positive": positive_count,
            "negative": negative_count,
            "neutral": neutral_count,
            "insufficient": insufficient_count,
            "total": len(results),
            "score": f"{positive_count}/{len(results)}",
            "recommendation": recommendation,
            "color": color,
        },
        "questions": results,
    }


import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.ai.service import ask_project
from app.db import SessionLocal


def _classify_answer(answer: str) -> str:
    lower = answer.lower()

    if "insufficient evidence" in lower:
        return "insufficient"

    positive_hits = sum(1 for indicator in _POSITIVE_INDICATORS if indicator in lower)
    negative_hits = sum(1 for indicator in _NEGATIVE_INDICATORS if indicator in lower)

    if positive_hits > negative_hits:
        return "positive"
    if negative_hits > positive_hits:
        return "negative"
    return "neutral"


def _process_question(project_id: str, item: dict) -> dict:
    logger.info(f"[{project_id}] START question={item['id']} category={item['category']}")
    with SessionLocal() as thread_db:
        try:
            answer = ask_project(
                db=thread_db,
                project_id=project_id,
                question=item["question"],
            )
            logger.info(f"[{project_id}] DONE question={item['id']} answer_len={len(answer.get('answer', ''))}")
        except Exception as exc:
            logger.exception(f"[{project_id}] ERROR question={item['id']} error={exc}")
            answer = {
                "answer": f"Error: {exc}",
                "citations": [],
            }

    sentiment = _classify_answer(answer.get("answer", ""))

    return {
        "id": item["id"],
        "category": item["category"],
        "question": item["question"],
        "answer": answer.get("answer", ""),
        "citations": answer.get("citations", []),
        "sentiment": sentiment,
    }


def run_evaluation_stream(db: Session, project_id: str):
    logger.info(f"[{project_id}] EVALUATION_START total={len(QUESTIONS)}")
    results = []

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {
            executor.submit(_process_question, project_id, item): item
            for item in QUESTIONS
        }
        logger.info(f"[{project_id}] SUBMITTED futures={len(futures)}")

        completed = 0
        for future in as_completed(futures):
            completed += 1
            try:
                result = future.result()
                logger.info(f"[{project_id}] COMPLETED {completed}/{len(QUESTIONS)} question={result['id']} sentiment={result['sentiment']}")
            except Exception as exc:
                logger.exception(f"[{project_id}] FUTURE_ERROR {completed}/{len(QUESTIONS)} error={exc}")
                continue

            results.append(result)

            yield json.dumps({
                "type": "progress",
                "current": completed,
                "total": len(QUESTIONS),
                "question": result["question"],
                "category": result["category"],
            }) + "\n"

            yield json.dumps({
                "type": "result",
                "data": result,
            }) + "\n"

    logger.info(f"[{project_id}] ALL_COMPLETED results={len(results)}")

    positive_count = sum(1 for r in results if r["sentiment"] == "positive")
    negative_count = sum(1 for r in results if r["sentiment"] == "negative")
    neutral_count = sum(1 for r in results if r["sentiment"] == "neutral")
    insufficient_count = sum(1 for r in results if r["sentiment"] == "insufficient")

    if positive_count >= 4 and negative_count == 0 and insufficient_count == 0:
        recommendation = "BID"
        color = "green"
    elif negative_count >= 2 or insufficient_count >= 2:
        recommendation = "NO-BID"
        color = "red"
    else:
        recommendation = "CLARIFY"
        color = "yellow"

    logger.info(f"[{project_id}] SUMMARY recommendation={recommendation} positive={positive_count} negative={negative_count} neutral={neutral_count} insufficient={insufficient_count}")

    yield json.dumps({
        "type": "complete",
        "summary": {
            "positive": positive_count,
            "negative": negative_count,
            "neutral": neutral_count,
            "insufficient": insufficient_count,
            "total": len(results),
            "score": f"{positive_count}/{len(results)}",
            "recommendation": recommendation,
            "color": color,
        },
    }) + "\n"


def stream_evaluation(db: Session, project_id: str) -> StreamingResponse:
    return StreamingResponse(
        run_evaluation_stream(db=db, project_id=project_id),
        media_type="application/x-ndjson",
    )
