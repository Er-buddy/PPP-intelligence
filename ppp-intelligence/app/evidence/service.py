from sqlalchemy.orm import Session

from app.documents.models import DocumentChunk


def get_chunks_by_ids(
    db: Session,
    chunk_ids: list[str],
) -> list[DocumentChunk]:
    if not chunk_ids:
        return []

    rows = (
        db.query(DocumentChunk)
        .filter(DocumentChunk.id.in_(chunk_ids))
        .all()
    )

    order = {chunk_id: i for i, chunk_id in enumerate(chunk_ids)}

    return sorted(
        rows,
        key=lambda row: order.get(row.id, 999999),
    )
