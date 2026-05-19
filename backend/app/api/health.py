from fastapi import APIRouter

from app import __version__
from app.config import get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check():
    settings = get_settings()
    kb_exists = (settings.kb_active_path / "manifest.json").is_file()
    return {
        "status": "ok",
        "version": __version__,
        "kb_loaded": kb_exists,
        "kb_path": str(settings.kb_active_path),
    }
