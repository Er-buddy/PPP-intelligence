from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.ai.service import ask_project
from app.db import get_db
from app.documents.service import ingest_document
from app.projects.models import Project


router = APIRouter()


class ProjectCreate(BaseModel):
    name: str


class AskRequest(BaseModel):
    question: str


@router.post("/projects")
def create_project(
    payload: ProjectCreate,
    db: Session = Depends(get_db),
):
    project = Project(
        id=str(uuid4()),
        name=payload.name,
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    return {
        "id": project.id,
        "name": project.name,
    }


@router.post("/projects/{project_id}/documents")
async def upload_document(
    project_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    project = db.get(Project, project_id)

    if project is None:
        raise HTTPException(404, "Project not found")

    extension = Path(file.filename or "").suffix.lower()

    if extension not in {".pdf", ".docx", ".xlsx"}:
        raise HTTPException(
            400,
            "Supported formats: PDF, DOCX, XLSX",
        )

    storage_dir = Path("storage/uploads") / project_id
    storage_dir.mkdir(parents=True, exist_ok=True)

    destination = storage_dir / f"{uuid4()}{extension}"

    content = await file.read()
    destination.write_bytes(content)

    try:
        document = ingest_document(
            db=db,
            project_id=project_id,
            filename=file.filename or destination.name,
            file_path=destination,
        )
    except Exception as exc:
        raise HTTPException(
            500,
            f"Document processing failed: {exc}",
        ) from exc

    return {
        "document_id": document.id,
        "filename": document.filename,
        "chunks": document.chunk_count,
        "status": document.status,
    }


@router.post("/projects/{project_id}/ask")
def ask(
    project_id: str,
    payload: AskRequest,
    db: Session = Depends(get_db),
):
    try:
        return ask_project(
            db=db,
            project_id=project_id,
            question=payload.question,
        )
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(500, str(exc)) from exc
