from pathlib import Path
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.documents.chunker import chunk_document
from app.documents.models import Document, DocumentChunk
from app.documents.parser import parse_document


SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".xlsx"}


def ingest_document(
    db: Session,
    project_id: str,
    filename: str,
    file_path: Path,
) -> Document:
    extension = file_path.suffix.lower()

    if extension not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported file type: {extension}")

    document = Document(
        id=str(uuid4()),
        project_id=project_id,
        filename=filename,
        file_path=str(file_path),
        status="processing",
    )

    db.add(document)
    db.flush()

    pages = parse_document(file_path)
    chunks = chunk_document(pages)

    for index, chunk in enumerate(chunks):
        chunk_id = str(uuid4())

        record = DocumentChunk(
            id=chunk_id,
            document_id=document.id,
            project_id=project_id,
            page=chunk.get("page"),
            section=chunk.get("section"),
            chunk_index=index,
            content=chunk["content"],
        )

        db.add(record)

        db.flush()

        db.execute(
            text(
                """
                INSERT INTO chunk_fts (
                    chunk_id,
                    project_id,
                    content
                )
                VALUES (
                    :chunk_id,
                    :project_id,
                    :content
                )
                """
            ),
            {
                "chunk_id": chunk_id,
                "project_id": project_id,
                "content": chunk["content"],
            },
        )

    document.chunk_count = len(chunks)
    document.status = "ready"

    db.commit()
    db.refresh(document)

    return document
