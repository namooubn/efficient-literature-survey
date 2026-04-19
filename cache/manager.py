"""Cache helpers keyed by file relative path and SHA-256 hash."""

import json
import logging
from datetime import datetime
from pathlib import Path

from core.helpers import file_sha256 as _file_sha256


file_sha256 = _file_sha256


def load_cache(cache_path: Path) -> dict:
    """Load cached extraction results keyed by relative path -> {sha256, result}."""
    if not cache_path.exists():
        return {}
    try:
        with open(cache_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and "files" in data:
            return data["files"]
    except Exception:
        pass
    return {}


def save_cache(cache_path: Path, cache_data: dict) -> None:
    """Save cache with version and timestamp metadata."""
    payload = {
        "version": 2,
        "generated_at": datetime.now().isoformat(),
        "files": cache_data,
    }
    try:
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logging.warning("缓存保存失败：%s", e)
