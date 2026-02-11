from pathlib import Path

from fastapi import APIRouter, HTTPException

from ..config.logging_config import get_logger
from ..config.settings import settings
from ..models.schemas import APIResponse

logger = get_logger(__name__)

router = APIRouter(prefix="/chat", tags=["media"])


@router.get("/avatar-videos", response_model=APIResponse)
async def get_avatar_videos():
    """Return available avatar videos from web/main/img/lens."""
    try:
        lens_dir = Path(settings.web_main_dir) / "img" / "lens"
        if not lens_dir.exists() or not lens_dir.is_dir():
            return APIResponse(success=True, message="video directory not found", data=[])

        supported_exts = {".mp4", ".webm", ".mov", ".m4v", ".ogg"}
        videos = [
            f"img/lens/{item.name}"
            for item in sorted(lens_dir.iterdir())
            if item.is_file() and item.suffix.lower() in supported_exts
        ]

        return APIResponse(success=True, message="ok", data=videos)
    except Exception as exc:
        logger.error(f"failed to list avatar videos: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))
