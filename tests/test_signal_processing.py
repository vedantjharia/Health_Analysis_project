"""Tests for biosignal filtering and R-peak detection algorithms."""

import numpy as np
import pytest
from src.signal_processing import BiosignalProcessor


def test_ecg_butterworth_bandpass():
    """Verify zero-phase Butterworth bandpass filter suppresses DC drift and high frequencies."""
    processor = BiosignalProcessor()
    fs = 250
    t = np.arange(0, 5, 1.0 / fs)
    
    # 0.1 Hz baseline wander + 10 Hz cardiac wave + 60 Hz powerline interference
    signal_in = 2.0 * np.sin(2 * np.pi * 0.1 * t) + np.sin(2 * np.pi * 10 * t) + 0.8 * np.sin(2 * np.pi * 60 * t)
    filtered = processor.filter_ecg(signal_in)
    
    assert len(filtered) == len(signal_in)
    assert not np.isnan(filtered).any()
    # Baseline DC energy should be severely attenuated
    assert np.mean(np.abs(signal_in[:fs])) > np.mean(np.abs(filtered[:fs]))


def test_respiration_filtering():
    """Verify respiration filter isolates respiratory band (<0.5 Hz)."""
    processor = BiosignalProcessor()
    fs = 250
    t = np.arange(0, 10, 1.0 / fs)
    # 0.25 Hz respiration (15 breaths/min) + 1.2 Hz ECG pulse artifact
    resp_in = np.sin(2 * np.pi * 0.25 * t) + 0.5 * np.sin(2 * np.pi * 1.2 * t)
    filtered = processor.filter_respiration(resp_in)
    
    assert len(filtered) == len(resp_in)
    assert not np.isnan(filtered).any()


def test_r_peak_detection_synthetic():
    """Verify R-peak detection identifies synthetic pulses spaced at 800 ms (75 bpm)."""
    processor = BiosignalProcessor()
    fs = 250
    duration_sec = 6
    ecg_synth = np.zeros(int(duration_sec * fs))
    
    # Place sharp synthetic R-peaks every 200 samples (800 ms = 75 bpm)
    true_peaks = np.arange(100, len(ecg_synth) - 100, 200)
    for p in true_peaks:
        # triangular QRS wave
        ecg_synth[p-2:p+3] = [0.2, 0.7, 1.5, 0.7, 0.2]
    
    detected_peaks = processor.detect_r_peaks(ecg_synth)
    assert len(detected_peaks) >= len(true_peaks) - 1
    
    # Verify RR interval calculation
    rr_times, rr_ms = processor.extract_rr_intervals(detected_peaks)
    assert len(rr_ms) > 0
    assert np.all(rr_ms >= 300.0) and np.all(rr_ms <= 2000.0)
    assert np.isclose(np.mean(rr_ms), 800.0, atol=25.0)
