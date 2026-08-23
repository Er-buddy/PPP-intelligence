from pathlib import Path

from app.config import get_settings
from app.db import SessionLocal, init_db


def inspect_database() -> None:
    init_db()

    with SessionLocal() as db:
        from sqlalchemy import text

        project_count = db.execute(text("SELECT COUNT(*) FROM projects")).scalar_one()
        document_count = db.execute(text("SELECT COUNT(*) FROM documents")).scalar_one()
        chunk_count = db.execute(text("SELECT COUNT(*) FROM document_chunks")).scalar_one()
        fts_count = db.execute(text("SELECT COUNT(*) FROM chunk_fts")).scalar_one()

        print(f"Projects:    {project_count}")
        print(f"Documents:   {document_count}")
        print(f"Chunks:      {chunk_count}")
        print(f"FTS rows:    {fts_count}")

        print("\n=== PROJECTS ===")
        projects = db.execute(
            text("SELECT id, name, created_at FROM projects")
        ).mappings().all()
        for project in projects:
            print(dict(project))

        print("\n=== DOCUMENTS ===")
        documents = db.execute(
            text("SELECT id, project_id, filename, status, chunk_count, created_at FROM documents")
        ).mappings().all()
        for document in documents:
            print(dict(document))

        print("\n=== FIRST 5 CHUNKS ===")
        chunks = db.execute(
            text("SELECT id, document_id, project_id, page, section, chunk_index, content FROM document_chunks LIMIT 5")
        ).mappings().all()
        for chunk in chunks:
            row = dict(chunk)
            content = row.get("content", "")
            print(f"  [{row['id']}] doc={row['document_id']} page={row['page']} section={row['section']}")
            print(f"    {content[:200]}...")

        print("\n=== FTS5 CONTENT ===")
        fts_rows = db.execute(
            text("SELECT chunk_id, project_id, content FROM chunk_fts LIMIT 5")
        ).mappings().all()
        for fts_row in fts_rows:
            row = dict(fts_row)
            print(f"  [{row['chunk_id']}] project={row['project_id']}")
            print(f"    {row['content'][:200]}...")


if __name__ == "__main__":
    inspect_database()
