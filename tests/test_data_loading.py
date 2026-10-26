"""Tests for data loader and dataset configuration."""

import os
import pytest
from src.utils import load_config, get_project_root
from src.data_loader import FantasiaDataLoader


def test_config_loading():
    """Verify experiment configuration loads properly with required keys."""
    config = load_config()
    assert "dataset" in config
    assert "signal_processing" in config
    assert "features" in config
    assert "evaluation" in config
    assert config["dataset"]["fs"] == 250
    assert len(config["dataset"]["cohort"]["young_records"]) >= 10
    assert len(config["dataset"]["cohort"]["elderly_records"]) >= 10


def test_data_loader_initialization():
    """Verify data loader directory initialization."""
    loader = FantasiaDataLoader()
    assert os.path.exists(loader.raw_dir)
    assert os.path.exists(loader.proc_dir)
    assert loader.fs == 250
    assert loader.duration_sec > 0


def test_dataset_audit_schema():
    """Verify audit dictionary conforms to scientific reporting requirements."""
    loader = FantasiaDataLoader()
    dummy_cohort = [
        {"record_name": "f1y01", "ecg": [0.1, 0.2], "resp": [0.0, 0.1], "fs": 250, "age": 22, "sex": "F", "label": 0},
        {"record_name": "f1o01", "ecg": [0.1, 0.2], "resp": [0.0, 0.1], "fs": 250, "age": 72, "sex": "M", "label": 1}
    ]
    audit = loader.audit_dataset(dummy_cohort)
    assert audit["total_subjects"] == 2
    assert audit["young_control_count"] == 1
    assert audit["elderly_risk_count"] == 1
    assert audit["sampling_frequency_hz"] == 250
    assert "clinical_proxy_rationale" in audit
