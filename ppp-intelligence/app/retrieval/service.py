import re

from sqlalchemy import text
from sqlalchemy.orm import Session

# Characters that have special meaning in FTS5 MATCH syntax or break the
# unicode61 tokenizer when left in raw form. We strip them defensively
# from each token before quoting, and then wrap the token in double
# quotes so any remaining special character is treated as a literal.
# See: https://www.sqlite.org/fts5.html#fts5_strings
_FTS5_METACHARACTERS = re.compile(r'[^\w\s]', flags=re.UNICODE)
_FTS5_KEYWORDS = {"and", "or", "not"}
_FTS5_STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "of", "in", "on", "at", "to", "for", "with", "by", "from", "as",
    "this", "that", "these", "those", "it", "its", "and", "or", "not",
    "what", "which", "who", "whom", "whose", "do", "does", "did",
    "have", "has", "had", "will", "would", "should", "could", "can",
    "may", "might", "must", "shall",
}


def _sanitize_token(token: str) -> str:
    """Strip FTS5-special chars and any embedded double quotes, return lowercase."""
    cleaned = _FTS5_METACHARACTERS.sub(" ", token)
    # Split on whitespace introduced by stripping punctuation
    parts = [p for p in cleaned.split() if p]
    return " ".join(parts).lower()


def search_evidence(
    db: Session,
    project_id: str,
    query: str,
    limit: int = 8,
) -> list[dict]:
    """
    SQLite FTS5 retrieval.

    This intentionally uses keyword retrieval for the first MVP.
    Semantic/vector retrieval can be added later without changing
    the evidence contract.
    """

    raw_tokens = query.split()
    safe_tokens: list[str] = []

    for token in raw_tokens:
        cleaned = _sanitize_token(token)
        if not cleaned:
            continue
        if cleaned in _FTS5_KEYWORDS or cleaned in _FTS5_STOPWORDS:
            continue
        # Drop any individual word shorter than 2 chars after cleaning
        words = [w for w in cleaned.split() if len(w) >= 2]
        safe_tokens.extend(words)

    # De-duplicate while preserving order to keep the MATCH expression compact
    seen = set()
    deduped: list[str] = []
    for tok in safe_tokens:
        if tok in seen:
            continue
        seen.add(tok)
        deduped.append(tok)

    if not deduped:
        return []

    # Quote each token so any residual special character is treated as a
    # literal string in the FTS5 MATCH expression.
    fts_query = " OR ".join(f'"{tok}"' for tok in deduped)

    rows = db.execute(
        text(
            """
            SELECT
                f.chunk_id,
                f.content,
                c.page,
                c.section,
                c.document_id,
                d.filename,
                bm25(chunk_fts) AS score
            FROM chunk_fts AS f
            JOIN document_chunks AS c
              ON c.id = f.chunk_id
            JOIN documents AS d
              ON d.id = c.document_id
            WHERE f.project_id = :project_id
              AND chunk_fts MATCH :query
            ORDER BY bm25(chunk_fts)
            LIMIT :limit
            """
        ),
        {
            "project_id": project_id,
            "query": fts_query,
            "limit": limit,
        },
    ).mappings().all()

    return [dict(row) for row in rows]
