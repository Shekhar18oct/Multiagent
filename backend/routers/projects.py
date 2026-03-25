import os
import uuid
import ast
import tempfile

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Body
from pydantic import BaseModel
from typing import List, Optional

from backend.preprocessing import extract_and_clean_zip, clean_code_file, PreprocessingResult
from backend.semantic_search import search_code_chunks
from backend.orchestration import orchestrate_agents
from backend.progress import progress_tracker
from backend.analysis_state import analysis_state

router = APIRouter(prefix="/projects", tags=["projects"])

PROJECTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../docs/projects"))
os.makedirs(PROJECTS_DIR, exist_ok=True)

# In-memory project code chunk index (backed by ChromaDB in production)
project_chunks_index: dict = {}

# ── Models ────────────────────────────────────────────────────────────────────

class ProjectResponse(BaseModel):
    project_id: str
    status: str
    message: str
    repo_type: Optional[str] = None
    entry_points: Optional[List[str]] = None
    config_files: Optional[List[str]] = None
    important_files: Optional[List[str]] = None
    code_chunks: Optional[list] = None
    agent_outputs: Optional[dict] = None
    agent_activity: Optional[list] = None


class CodeSearchRequest(BaseModel):
    project_id: str
    query: str
    max_results: int = 10


class CodeSearchResponse(BaseModel):
    matches: list


class QARequest(BaseModel):
    project_id: str
    question: str
    context: Optional[str] = None


class QAResponse(BaseModel):
    answer: str


# ── Preprocessing helper ──────────────────────────────────────────────────────

def _run_preprocessing(zip_path: str, project_id: str) -> PreprocessingResult:
    with tempfile.TemporaryDirectory() as tmpdir:
        result = extract_and_clean_zip(zip_path, tmpdir)
        total_files = len(result.files)
        progress_tracker.start(project_id, total_files)

        cleaned_files = []
        for f in result.files:
            progress_tracker.update(project_id, os.path.basename(f), "Cleaning")
            cleaned_code = clean_code_file(f)
            cleaned_files.append({"path": f, "cleaned_code": cleaned_code})

        repo_type: Optional[str] = None
        entry_points: List[str] = []
        config_files: List[str] = []
        important_files: List[str] = []
        code_chunks: list = []

        exts = {os.path.splitext(f["path"])[1].lower() for f in cleaned_files}

        if ".py" in exts:
            repo_type = "Python"
            for f in cleaned_files:
                name = os.path.basename(f["path"])
                code_lower = f["cleaned_code"].lower()
                if name == "main.py":
                    entry_points.append(f["path"])
                if "fastapi" in code_lower:
                    repo_type = "Python FastAPI"
                if "streamlit" in code_lower:
                    repo_type = "Python Streamlit"
                if name in ("requirements.txt", "pyproject.toml", "setup.py"):
                    config_files.append(f["path"])
                try:
                    tree = ast.parse(f["cleaned_code"])
                    for node in ast.walk(tree):
                        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            code_chunks.append({
                                "file": f["path"], "type": "function",
                                "name": node.name,
                                "lineno": node.lineno,
                                "end_lineno": getattr(node, "end_lineno", node.lineno),
                                "code": ast.get_source_segment(f["cleaned_code"], node) or "",
                            })
                        elif isinstance(node, ast.ClassDef):
                            code_chunks.append({
                                "file": f["path"], "type": "class",
                                "name": node.name,
                                "lineno": node.lineno,
                                "end_lineno": getattr(node, "end_lineno", node.lineno),
                                "code": ast.get_source_segment(f["cleaned_code"], node) or "",
                            })
                except Exception:
                    pass

        elif ".js" in exts or ".ts" in exts:
            repo_type = "JavaScript/TypeScript"
            for f in cleaned_files:
                name = os.path.basename(f["path"])
                code_lower = f["cleaned_code"].lower()
                if name in ("index.js", "index.ts", "main.js", "main.ts"):
                    entry_points.append(f["path"])
                if "react" in code_lower:
                    repo_type = "React"
                if "next" in code_lower:
                    repo_type = "Next.js"
                if name in ("package.json", "tsconfig.json"):
                    config_files.append(f["path"])

        for f in cleaned_files:
            if os.path.basename(f["path"]).lower() in ("readme.md", "license", "contributing.md"):
                important_files.append(f["path"])

        progress_tracker.complete(project_id)

        return PreprocessingResult(
            files=cleaned_files,
            errors=result.errors,
            repo_type=repo_type,
            entry_points=entry_points,
            config_files=config_files,
            important_files=important_files,
            code_chunks=code_chunks,
        )


# ── Upload endpoint ────────────────────────────────────────────────────────────

@router.post("/upload", response_model=ProjectResponse)
def upload_project(
    personas: List[str] = Form(...),
    file: Optional[UploadFile] = File(None),
    github_url: Optional[str] = Form(None),
    analysis_depth: str = Form("Standard"),
    verbosity: str = Form("Medium"),
    enable_diagrams: str = Form("True"),
    enable_feature_analysis: str = Form("True"),
):
    agent_config = {
        "analysis_depth": analysis_depth,
        "verbosity": verbosity,
        "enable_diagrams": enable_diagrams == "True",
        "enable_feature_analysis": enable_feature_analysis == "True",
    }

    if not file and not github_url:
        raise HTTPException(status_code=400, detail="Must provide a ZIP file or GitHub URL.")

    project_id = str(uuid.uuid4())
    project_path = os.path.join(PROJECTS_DIR, project_id)
    os.makedirs(project_path, exist_ok=True)
    analysis_state.start(project_id)

    # ── ZIP upload path ──
    if file:
        if not file.filename or not file.filename.endswith(".zip"):
            raise HTTPException(
                status_code=400,
                detail="Only ZIP files are supported. Please upload a .zip archive.",
            )
        file_bytes = file.file.read()
        if len(file_bytes) > 100 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File too large (max 100MB).")

        zip_path = os.path.join(project_path, file.filename)
        with open(zip_path, "wb") as fh:
            fh.write(file_bytes)

        try:
            preprocess_result = _run_preprocessing(zip_path, project_id)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Corrupted or invalid ZIP file: {e}")

        if preprocess_result.errors:
            raise HTTPException(
                status_code=400,
                detail=f"Preprocessing error: {preprocess_result.errors}",
            )
        if not preprocess_result.files:
            raise HTTPException(
                status_code=400,
                detail="No valid code files found. Please upload a code repository.",
            )

        # Index chunks in memory and persist to ChromaDB
        project_chunks_index[project_id] = preprocess_result.code_chunks
        try:
            from db.chroma import store_project_metadata, store_code_chunks
            store_project_metadata(project_id, {
                "repo_type": preprocess_result.repo_type or "Unknown",
                "file_count": str(len(preprocess_result.files)),
                "personas": ",".join(personas),
            })
            store_code_chunks(project_id, preprocess_result.code_chunks)
        except Exception:
            pass  # ChromaDB errors must not fail the upload

        orchestration_result = orchestrate_agents(
            project_id, agent_config, personas, preprocess_result.code_chunks
        )

        return ProjectResponse(
            project_id=project_id,
            status="preprocessed",
            message=f"Project uploaded and preprocessed. {len(preprocess_result.files)} files processed.",
            repo_type=preprocess_result.repo_type,
            entry_points=preprocess_result.entry_points,
            config_files=preprocess_result.config_files,
            important_files=preprocess_result.important_files,
            code_chunks=preprocess_result.code_chunks,
            agent_outputs=orchestration_result.get("outputs"),
            agent_activity=orchestration_result.get("activity"),
        )

    # ── GitHub URL path ──
    return ProjectResponse(
        project_id=project_id,
        status="cloned",
        message="GitHub repository registered (full clone coming in Milestone 4).",
    )


# ── Progress / State ──────────────────────────────────────────────────────────

@router.get("/progress/{project_id}")
def get_project_progress(project_id: str):
    prog = progress_tracker.get(project_id)
    if not prog:
        raise HTTPException(status_code=404, detail="No progress found for this project.")
    return prog


@router.post("/pause/{project_id}")
def pause_analysis(project_id: str):
    analysis_state.pause(project_id)
    return {"status": "paused"}


@router.post("/resume/{project_id}")
def resume_analysis(project_id: str):
    analysis_state.resume(project_id)
    return {"status": "resumed"}


@router.get("/state/{project_id}")
def get_analysis_state(project_id: str):
    state = analysis_state.get(project_id)
    if not state:
        raise HTTPException(status_code=404, detail="No analysis state found for this project.")
    return state


# ── Search & Q&A ──────────────────────────────────────────────────────────────

@router.post("/search", response_model=CodeSearchResponse)
def search_project_code(request: CodeSearchRequest = Body(...)):
    chunks = project_chunks_index.get(request.project_id)
    if chunks is None:
        raise HTTPException(status_code=404, detail="Project not found or not indexed.")
    matches = search_code_chunks(chunks, request.query, request.max_results)
    return CodeSearchResponse(matches=matches)


@router.post("/qa", response_model=QAResponse)
def project_qa(request: QARequest = Body(...)):
    """Answer a question about the project using indexed code chunks."""
    chunks = project_chunks_index.get(request.project_id)
    if not chunks:
        raise HTTPException(status_code=404, detail="Project not found or not indexed.")
    relevant = search_code_chunks(chunks, request.question, max_results=5)
    if relevant:
        names = ", ".join(c["name"] for c in relevant)
        answer = (
            f"Based on the codebase, relevant code found: {names}. "
            "(Full LLM-powered Q&A coming in Milestone 6.)"
        )
    else:
        answer = "No directly relevant code found for your question. (Full LLM Q&A in Milestone 6.)"
    return QAResponse(answer=answer)


# ── List projects (for Projects page) ────────────────────────────────────────

@router.get("/list")
def list_projects():
    """Return all indexed project IDs and their metadata."""
    try:
        from db.chroma import list_all_projects
        return {"projects": list_all_projects()}
    except Exception:
        return {"projects": list(project_chunks_index.keys())}
