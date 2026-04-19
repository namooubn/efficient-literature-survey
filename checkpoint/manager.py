"""Workflow checkpoint persistence for multi-turn Claude conversations.

Stage 1 (batch extraction) writes a checkpoint file that Claude can read
on subsequent turns to resume the workflow without re-running the script.
"""

import json
import logging
from datetime import datetime
from pathlib import Path

from core.helpers import file_sha256

CHECKPOINT_FILENAME = "_els_stage.json"
CURRENT_CHECKPOINT_VERSION = 1


def save_checkpoint(
    output_dir: Path,
    stage: int,
    lit_dir: Path,
    results_count: int = 0,
    config: dict | None = None,
) -> Path:
    """Persist the current workflow stage and metadata.

    Args:
        output_dir: Directory where checkpoint and outputs live.
        stage: Current workflow stage (0-4).
        lit_dir: Root literature folder path.
        results_count: Number of extracted results so far.
        config: Optional Stage 0 config dict.

    Returns:
        Path to the written checkpoint file.
    """
    payload = {
        "version": CURRENT_CHECKPOINT_VERSION,
        "generated_at": datetime.now().isoformat(),
        "stage": stage,
        "lit_dir": str(lit_dir),
        "results_count": results_count,
        "config": config or {},
    }
    cp_path = output_dir / CHECKPOINT_FILENAME
    try:
        with open(cp_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logging.warning("Checkpoint save failed: %s", e)
    return cp_path


def load_checkpoint(output_dir: Path) -> dict:
    """Load the latest checkpoint if it exists and is valid.

    Returns an empty dict if no checkpoint or version mismatch.
    """
    cp_path = output_dir / CHECKPOINT_FILENAME
    if not cp_path.exists():
        return {}
    try:
        with open(cp_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if data.get("version") != CURRENT_CHECKPOINT_VERSION:
            logging.info("Checkpoint version mismatch, ignoring.")
            return {}
        return data
    except Exception:
        return {}


def update_checkpoint_config(output_dir: Path, **kwargs) -> None:
    """Merge new key/value pairs into the existing checkpoint config."""
    cp = load_checkpoint(output_dir)
    if not cp:
        return
    cp["config"] = cp.get("config", {})
    cp["config"].update(kwargs)
    cp_path = output_dir / CHECKPOINT_FILENAME
    try:
        with open(cp_path, "w", encoding="utf-8") as f:
            json.dump(cp, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logging.warning("Checkpoint update failed: %s", e)


def is_checkpoint_valid(
    output_dir: Path, lit_dir: Path, expected_stage: int | None = None
) -> bool:
    """Quick validity check: stage matches and literature dir is unchanged."""
    cp = load_checkpoint(output_dir)
    if not cp:
        return False
    if expected_stage is not None and cp.get("stage") != expected_stage:
        return False
    if str(cp.get("lit_dir")) != str(lit_dir):
        return False
    return True
