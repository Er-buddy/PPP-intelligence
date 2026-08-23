import re

from sqlalchemy import text
from sqlalchemy.orm import Session

_FTS5_METACHARACTERS = re.compile(r'[\"*^()~?,\-]')
_FTS5_KEYWORDS = {"and", "or", "not"}


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

    safe_tokens = [
        _FTS5_METACHARACTERS.sub("", token)
        for token in query.split()
    ]

    safe_tokens = [
        token.lower()
        for token in safe_tokens
        if len(token) > 2
        and token.lower() not in _FTS5_KEYWORDS
        and token.strip()
    ]

    if not safe_tokens:
        return []

    fts_query = " OR ".join(safe_tokens)

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
