# Intelligent Preprocessing Module
# This module will handle code/data preprocessing for uploaded projects.
# It will support cleaning, feature extraction, and transformation for code analysis.

import os
import zipfile
import tempfile
import shutil
from typing import List

SUPPORTED_EXTENSIONS = ['.py', '.js', '.ts', '.java', '.cpp', '.c', '.md']


from typing import Optional

class PreprocessingResult:
    def __init__(self, files: List[str], errors: List[str], repo_type: Optional[str] = None, entry_points: Optional[List[str]] = None, config_files: Optional[List[str]] = None, important_files: Optional[List[str]] = None, code_chunks: Optional[list] = None):
        self.files = files
        self.errors = errors
        self.repo_type = repo_type
        self.entry_points = entry_points or []
        self.config_files = config_files or []
        self.important_files = important_files or []
        self.code_chunks = code_chunks or []


def extract_and_clean_zip(zip_path: str, extract_dir: str) -> PreprocessingResult:
    """
    Extracts a ZIP file, filters supported files, and returns their paths.
    """
    files = []
    errors = []
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
        for root, _, filenames in os.walk(extract_dir):
            for fname in filenames:
                ext = os.path.splitext(fname)[1].lower()
                if ext in SUPPORTED_EXTENSIONS:
                    files.append(os.path.join(root, fname))
    except Exception as e:
        errors.append(str(e))
    return PreprocessingResult(files, errors)


def clean_code_file(file_path: str) -> str:
    """
    Reads a code file and removes empty lines and trailing whitespace.
    Returns cleaned code as a string.
    """
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        cleaned = [line.rstrip() for line in lines if line.strip()]
        return '\n'.join(cleaned)
    except Exception as e:
        return f"ERROR: {e}"


def preprocess_project_zip(zip_path: str) -> PreprocessingResult:
    """
    Full pipeline: extract, clean, detect repo type/structure, and return cleaned code for all supported files.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        result = extract_and_clean_zip(zip_path, tmpdir)
        cleaned_files = []
        for f in result.files:
            cleaned_code = clean_code_file(f)
            cleaned_files.append({'path': f, 'cleaned_code': cleaned_code})
        # Detect repo type and structure
        repo_type = None
        entry_points = []
        config_files = []
        important_files = []
        code_chunks = []
        exts = set(os.path.splitext(f['path'])[1].lower() for f in cleaned_files)
        if '.py' in exts:
            repo_type = 'Python'
            import ast
            for f in cleaned_files:
                if os.path.basename(f['path']) == 'main.py':
                    entry_points.append(f['path'])
                if 'fastapi' in f['cleaned_code'].lower():
                    repo_type = 'Python FastAPI'
                if 'streamlit' in f['cleaned_code'].lower():
                    repo_type = 'Python Streamlit'
                # Extract code chunks (functions/classes)
                try:
                    tree = ast.parse(f['cleaned_code'])
                    for node in ast.walk(tree):
                        if isinstance(node, ast.FunctionDef):
                            code_chunks.append({
                                'file': f['path'],
                                'type': 'function',
                                'name': node.name,
                                'lineno': node.lineno,
                                'end_lineno': getattr(node, 'end_lineno', node.lineno),
                            })
                        elif isinstance(node, ast.ClassDef):
                            code_chunks.append({
                                'file': f['path'],
                                'type': 'class',
                                'name': node.name,
                                'lineno': node.lineno,
                                'end_lineno': getattr(node, 'end_lineno', node.lineno),
                            })
                except Exception:
                    pass
            for f in cleaned_files:
                if os.path.basename(f['path']) in ['requirements.txt', 'pyproject.toml', 'setup.py']:
                    config_files.append(f['path'])
        elif '.js' in exts or '.ts' in exts:
            repo_type = 'JavaScript/TypeScript'
            for f in cleaned_files:
                if os.path.basename(f['path']) in ['index.js', 'index.ts', 'main.js', 'main.ts']:
                    entry_points.append(f['path'])
                if 'react' in f['cleaned_code'].lower():
                    repo_type = 'React'
                if 'next' in f['cleaned_code'].lower():
                    repo_type = 'Next.js'
            for f in cleaned_files:
                if os.path.basename(f['path']) in ['package.json', 'tsconfig.json']:
                    config_files.append(f['path'])
        for f in cleaned_files:
            if os.path.basename(f['path']).lower() in ['readme.md', 'license', 'contributing.md']:
                important_files.append(f['path'])
        result.files = cleaned_files
        result.repo_type = repo_type
        result.entry_points = entry_points
        result.config_files = config_files
        result.important_files = important_files
        result.code_chunks = code_chunks
        return result
