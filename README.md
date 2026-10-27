# TalentSphere AI — HR Portal with RAG

TalentSphere AI is a Streamlit HR portal using Python, SQLite, and Google's Gemini API. This updated version adds a **Retrieval-Augmented Generation (RAG) HR Policy Knowledge Assistant** while retaining the existing HR, Employee, and Graduate workflows.

## AI architecture

### Gemini LLM

The existing `app.py` uses the Google Gen AI SDK (`google-genai`) and `client.models.generate\_content(...)`. The model is configured through `GEMINI\_MODEL` and defaults to `gemini-2.5-flash`.

Gemini is used for:

* Preliminary resume evaluation (existing workflow).
* Technical interview question generation (existing workflow).
* Candidate interview-answer evaluation (existing workflow).
* Answer generation for the new RAG HR policy assistant.

### RAG pipeline added

The new `rag/rag\_pipeline.py` implements:

1. **Chunking:** splits policy text into 220-word chunks with 40-word overlap.
2. **Embeddings:** `sentence-transformers/all-MiniLM-L6-v2` generates normalized vectors locally.
3. **Vector store:** ChromaDB persists chunk text, vectors, and metadata under `data/vector\_db/`.
4. **Semantic retrieval:** the user's question is embedded and the top relevant policy chunks are retrieved from the `hr\_policy` document type.
5. **Grounded generation:** the retrieved chunks and question are passed to Gemini. The prompt asks it not to invent policy details and to include source filenames/chunk numbers.

The RAG Knowledge Assistant is added as an HR-only tab. Upload approved HR policy PDFs, DOCX, or TXT files, index them, and then ask policy questions. Resume screening and interview features remain their existing Gemini-assisted workflows; they are not automatically converted into RAG by this change.

## Technology stack

* Python 3.10+
* Streamlit
* SQLite
* Google Gen AI SDK / Gemini
* ChromaDB
* Sentence Transformers (`all-MiniLM-L6-v2`)
* PyMuPDF for PDF text extraction
* python-docx for DOCX text extraction
* python-dotenv
* SMTP email using Python's `smtplib` (existing workflow)

## Project structure

```text
HR Portal/
├── app.py
├── rag/
│   ├── \_\_init\_\_.py
│   └── rag\_pipeline.py
├── check\_db.py
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
└── data/
    └── vector\_db/       # Created/used by ChromaDB at runtime
```

Runtime data such as the SQLite database, uploaded resumes, policy documents, vector database, logs, and exports is intentionally not included in this source ZIP.

## Run on Windows PowerShell

```powershell
cd "D:\\HR Portal"
python -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and set your Gemini API key. Then run:

```powershell
Copy-Item .env.example .env
# Edit .env and add your Gemini API key before starting the app.
python -m streamlit run app.py
```

Open the local URL printed by Streamlit, normally `http://localhost:8501`.

### Environment variables

* `GEMINI\_API\_KEY` — required for Gemini-powered features.
* `GEMINI\_MODEL` — optional; defaults to `gemini-2.5-flash`.
* `SMTP\_HOST`, `SMTP\_PORT`, `SMTP\_USERNAME`, `SMTP\_PASSWORD`, `SMTP\_FROM\_EMAIL`, `SMTP\_USE\_TLS` — for email notifications if used.
* `BOOTSTRAP\_ADMIN\_EMAIL`, `BOOTSTRAP\_ADMIN\_PASSWORD` — for the existing bootstrap HR-account flow, if enabled by the app's validation rules.

Never commit `.env`, API keys, SMTP credentials, database files, resumes, or confidential policy documents.

## Using the RAG assistant

1. Sign in with an HR account.
2. Open **RAG Knowledge Assistant**.
3. Upload approved HR policy documents in PDF, DOCX, or TXT format.
4. Select **Index Policy Documents** and wait for indexing to complete. The first run may download the embedding model from Hugging Face and requires network access.
5. Enter a policy question and select **Search Policies \& Ask Gemini**.
6. Review the generated answer and its source references. Expand **Retrieved passages** to inspect the context that was supplied to Gemini.

Scanned PDFs without an extractable text layer are not OCR-processed. Use text-based PDFs or DOCX/TXT files for now.

## Notes and limitations

* The embedding model runs locally, but RAG answers send retrieved policy text to Gemini's API. Ensure your organization's privacy rules allow this.
* Only upload approved HR policy documents to this HR-only knowledge assistant. The new UI is not a general employee-facing policy chat.
* The application asks Gemini to ground answers in retrieved context, but this is not a guarantee of correctness. Verify policy answers against the source document.
* The current implementation stores chunks with filename and chunk-index metadata. Re-indexing a same-named document replaces the existing indexed version for that document type.
* ChromaDB data is local under `data/vector\_db/`. Back it up as appropriate, and delete it when you need to purge indexed policy content.
* Existing resume-screening scores and AI interview assessments remain advisory; human review is required.
* This project has not been security-audited or production-hardened. Review authentication, authorization, retention, backups, dependency security, and deployment settings before production use.

## Dependencies

Install the packages listed in `requirements.txt`. ChromaDB and Sentence Transformers are used by the new RAG module. If a dependency fails to install on your Python version, use a supported Python version and install the requirements in a clean virtual environment.
