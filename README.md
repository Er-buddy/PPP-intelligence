# PPP Intelligence MVP

Evidence-first PPP Bid Intelligence MVP.

## Current milestone

The first implementation milestone is:

PDF / DOCX / XLSX
→ text extraction
→ evidence-aware chunking
→ SQLite storage
→ SQLite FTS5 retrieval
→ LangChain
→ OpenRouter
→ cited answer

OCR is intentionally not included.

## Run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Set:

```env
OPENROUTER_API_KEY=your_key
OPENROUTER_MODEL=your_model
```

Start:

```bash
uvicorn app.main:app --reload
```

API:

- GET `/health`
- POST `/projects`
- POST `/projects/{project_id}/documents`
- POST `/projects/{project_id}/ask`

## Example

Create project:

```bash
curl -X POST http://127.0.0.1:8000/projects \
  -H "Content-Type: application/json" \
  -d '{"name":"GCC Water PPP"}'
```

Upload:

```bash
curl -X POST \
  -F "file=@/path/to/tender.pdf" \
  http://127.0.0.1:8000/projects/PROJECT_ID/documents
```

Ask:

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"question":"What are the main commercial risks?"}' \
  http://127.0.0.1:8000/projects/PROJECT_ID/ask
```
