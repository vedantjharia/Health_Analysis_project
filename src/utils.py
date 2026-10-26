"""Utility functions for biosignal pipeline: configuration, logging, and I/O."""

import os
import json
import logging
import yaml
from pathlib import Path
from typing import Any, Dict


def get_project_root() -> Path:
    """Return project root directory."""
    return Path(__file__).resolve().parent.parent


def load_config(config_path: str = None) -> Dict[str, Any]:
    """Load YAML experiment configuration file."""
    if config_path is None:
        config_path = os.path.join(get_project_root(), "config", "experiment_config.yaml")
    
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    return config


def setup_logger(name: str = "biosignal_pipeline", log_file: str = None) -> logging.Logger:
    """Setup standard console and file logger."""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    if not logger.handlers:
        formatter = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        ch = logging.StreamHandler()
        ch.setFormatter(formatter)
        logger.addHandler(ch)

        if log_file:
            os.makedirs(os.path.dirname(log_file), exist_ok=True)
            fh = logging.FileHandler(log_file, encoding="utf-8")
            fh.setFormatter(formatter)
            logger.addHandler(fh)

    return logger


def save_json(data: Any, filepath: str) -> None:
    """Save python dictionary or list to JSON file with indentation."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


def load_json(filepath: str) -> Any:
    """Load JSON file."""
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)
