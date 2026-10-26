"""Tests for HRV feature calculation and evaluation metrics."""

import numpy as np
import pandas as pd
import pytest
from src.feature_extraction import BiosignalFeatureExtractor
from src.train import split_by_subject


def test_time_domain_hrv_calculation():
    """Verify standard formulas for SDNN, RMSSD, and pNN50."""
    extractor = BiosignalFeatureExtractor()
    # Constant RR intervals of 800 ms
    rr_constant = np.array([800.0, 800.0, 800.0, 800.0, 800.0])
    feats_const = extractor.compute_time_domain_features(rr_constant)
    assert feats_const["mean_rr"] == 800.0
    assert feats_const["sdnn"] == 0.0
    assert feats_const["rmssd"] == 0.0
    assert feats_const["pnn50"] == 0.0

    # Alternating RR intervals [800, 900, 800, 900, 800] -> diffs are 100 ms
    rr_alt = np.array([800.0, 900.0, 800.0, 900.0, 800.0])
    feats_alt = extractor.compute_time_domain_features(rr_alt)
    assert feats_alt["mean_rr"] == 840.0
    assert feats_alt["rmssd"] == 100.0
    assert feats_alt["pnn50"] == 100.0


def test_subject_level_split_leakage_prevention():
    """Verify that test subjects have ZERO window segments in training partition."""
    dummy_data = {
        "subject_id": ["s01", "s01", "s02", "s02", "s03", "s03", "s04", "s04"],
        "window_id": [f"w_{i}" for i in range(8)],
        "label": [0, 0, 0, 0, 1, 1, 1, 1],
        "mean_rr": [800 + i*10 for i in range(8)]
    }
    df = pd.DataFrame(dummy_data)
    test_subjects = ["s02", "s04"]

    train_df, test_df = split_by_subject(df, test_subjects)

    train_subs = set(train_df["subject_id"].unique())
    test_subs = set(test_df["subject_id"].unique())

    # Strict disjunction
    assert len(train_subs.intersection(test_subs)) == 0
    assert test_subs == {"s02", "s04"}
    assert train_subs == {"s01", "s03"}
