from __future__ import annotations
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from configs.settings import settings

router = APIRouter(prefix="/export", tags=["Export"])


@router.get("/{report_id}")
async def download_report(report_id: str, format: str = "pdf") -> FileResponse:
    allowed = {"pdf", "docx", "md"}
    if format not in allowed:
        raise HTTPException(400, f"Format must be one of {allowed}")

    ext_map = {"pdf": ".pdf", "docx": ".docx", "md": ".md"}
    file_path = Path(settings.EXPORT_DIR) / f"report_{report_id}{ext_map[format]}"

    if not file_path.exists():
        raise HTTPException(404, "Report file not found. Generate it first.")

    media_types = {
        "pdf":  "application/pdf",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "md":   "text/markdown",
    }
    return FileResponse(
        path=str(file_path),
        media_type=media_types[format],
        filename=file_path.name,
    )
