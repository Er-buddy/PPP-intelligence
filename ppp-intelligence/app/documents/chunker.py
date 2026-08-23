from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import get_settings


def chunk_document(pages: list[dict]) -> list[dict]:
    settings = get_settings()

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    chunks = []

    for page in pages:
        text = page["text"].strip()

        if not text:
            continue

        for part in splitter.split_text(text):
            chunks.append(
                {
                    "page": page.get("page"),
                    "section": page.get("metadata", {}).get("section"),
                    "content": part,
                    "metadata": page.get("metadata", {}),
                }
            )

    return chunks
