"""File reader tool — reads local text or PDF files from the data/ directory."""

from pathlib import Path

from langchain_core.tools import tool

from app.core.logging import get_logger

logger = get_logger(__name__)

# Restrict to a safe data directory to prevent path traversal
_DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"
_MAX_CHARS = 10_000


@tool
def file_reader(filename: str) -> dict:
    """Read a local file from the data/ directory.

    Supports .txt and .pdf files. The file must be inside the data/ directory.

    Args:
        filename: Filename relative to the data/ directory, e.g. "report.txt".

    Returns:
        Dict with keys: filename, text (up to 10 000 chars), error (str or None).
    """
    try:
        # Resolve and validate — no path traversal
        target = (_DATA_DIR / filename).resolve()
        if not str(target).startswith(str(_DATA_DIR.resolve())):
            return {"filename": filename, "text": "", "error": "Path traversal denied"}

        if not target.exists():
            return {"filename": filename, "text": "", "error": f"File not found: {filename}"}

        suffix = target.suffix.lower()

        if suffix == ".txt":
            text = target.read_text(encoding="utf-8", errors="replace")
        elif suffix == ".pdf":
            try:
                from pypdf import PdfReader  # noqa: PLC0415

                reader = PdfReader(str(target))
                text = "\n".join(page.extract_text() or "" for page in reader.pages)
            except ImportError:
                return {"filename": filename, "text": "", "error": "pypdf not installed"}
        else:
            return {
                "filename": filename,
                "text": "",
                "error": f"Unsupported file type: {suffix}",
            }

        text = " ".join(text.split())  # normalize whitespace
        logger.debug("file_reader_ok", filename=filename, chars=len(text))
        return {"filename": filename, "text": text[:_MAX_CHARS], "error": None}

    except Exception as exc:
        logger.warning("file_reader_failed", filename=filename, error=str(exc))
        return {"filename": filename, "text": "", "error": str(exc)}
