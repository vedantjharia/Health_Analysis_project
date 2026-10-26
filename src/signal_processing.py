"""Biosignal Preprocessing and Peak Detection Module.

Implements Butterworth bandpass filtering for ECG, lowpass filtering for Respiration,
and Pan-Tompkins R-peak detection for accurate RR interval extraction.
"""

import os
import numpy as np
import scipy.signal as signal
import matplotlib.pyplot as plt
from typing import Tuple, Dict, Any, List

from src.utils import load_config, setup_logger, get_project_root

logger = setup_logger("signal_processing")


class BiosignalProcessor:
    """Processes raw ECG and Respiration biosignals into clean waveforms and RR intervals."""

    def __init__(self, config: Dict[str, Any] = None):
        if config is None:
            config = load_config()
        self.config = config
        self.fs = config["dataset"]["fs"]

        # ECG filter parameters
        self.ecg_low = config["signal_processing"]["ecg"]["lowcut"]
        self.ecg_high = config["signal_processing"]["ecg"]["highcut"]
        self.ecg_order = config["signal_processing"]["ecg"]["order"]

        # Respiration filter parameters
        self.resp_low = config["signal_processing"]["respiration"]["lowcut"]
        self.resp_high = config["signal_processing"]["respiration"]["highcut"]
        self.resp_order = config["signal_processing"]["respiration"]["order"]

    def filter_ecg(self, ecg_raw: np.ndarray) -> np.ndarray:
        """Apply 4th-order zero-phase Butterworth bandpass filter (0.5 - 45 Hz) to ECG."""
        nyq = 0.5 * self.fs
        low = self.ecg_low / nyq
        high = self.ecg_high / nyq
        b, a = signal.butter(self.ecg_order, [low, high], btype="bandpass")
        filtered = signal.filtfilt(b, a, ecg_raw)
        return filtered.astype(np.float32)

    def filter_respiration(self, resp_raw: np.ndarray) -> np.ndarray:
        """Apply 3rd-order zero-phase Butterworth bandpass filter (0.05 - 0.5 Hz) to Respiration."""
        nyq = 0.5 * self.fs
        low = self.resp_low / nyq
        high = self.resp_high / nyq
        b, a = signal.butter(self.resp_order, [low, high], btype="bandpass")
        filtered = signal.filtfilt(b, a, resp_raw)
        return filtered.astype(np.float32)

    def detect_r_peaks(self, ecg_filtered: np.ndarray) -> np.ndarray:
        """Detect R-peaks using Pan-Tompkins inspired derivative-squaring-integration approach."""
        # 1. Differentiation
        diff = np.diff(ecg_filtered)
        diff = np.pad(diff, (1, 0), mode="edge")

        # 2. Squaring
        squared = diff ** 2

        # 3. Moving-window integration (150 ms window)
        window_len = int(0.150 * self.fs)
        kernel = np.ones(window_len) / window_len
        integrated = np.convolve(squared, kernel, mode="same")

        # 4. Adaptive thresholding and peak prominence detection
        min_distance = int(0.25 * self.fs)  # min 250 ms refractory period (~240 bpm max)
        threshold = np.mean(integrated) + 0.5 * np.std(integrated)
        
        peaks, _ = signal.find_peaks(
            integrated,
            height=threshold,
            distance=min_distance
        )

        # 5. Local peak refinement on filtered ECG (search window +/- 40 ms around detected integrated peak)
        search_radius = int(0.040 * self.fs)
        refined_peaks = []
        for p in peaks:
            start = max(0, p - search_radius)
            end = min(len(ecg_filtered), p + search_radius + 1)
            local_max = start + np.argmax(ecg_filtered[start:end])
            refined_peaks.append(local_max)

        refined_peaks = np.unique(refined_peaks)
        return np.array(refined_peaks, dtype=int)

    def extract_rr_intervals(self, r_peaks: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Convert R-peak indices into beat-to-beat RR intervals (in milliseconds).
        
        Returns:
            rr_times: timestamps of the R-peaks in seconds (for interval end)
            rr_intervals: RR intervals in milliseconds
        """
        if len(r_peaks) < 2:
            return np.array([]), np.array([])

        rr_samples = np.diff(r_peaks)
        rr_ms = (rr_samples / self.fs) * 1000.0
        rr_times = r_peaks[1:] / self.fs

        # Physiological validation: 300 ms <= RR <= 2000 ms (30 bpm to 200 bpm)
        valid_mask = (rr_ms >= 300.0) & (rr_ms <= 2000.0)
        
        # Relative jump rejection: reject changes > 35% from running median
        if np.sum(valid_mask) > 5:
            med_rr = np.median(rr_ms[valid_mask])
            rel_mask = np.abs(rr_ms - med_rr) <= 0.40 * med_rr
            valid_mask = valid_mask & rel_mask

        return rr_times[valid_mask], rr_ms[valid_mask]

    def estimate_respiratory_rate(self, resp_filtered: np.ndarray) -> float:
        """Estimate mean respiration rate (breaths per minute) from filtered signal."""
        # Detect breath inhalation peaks
        min_breath_dist = int(1.2 * self.fs)  # Max 50 breaths/min
        peaks, _ = signal.find_peaks(resp_filtered, distance=min_breath_dist)
        
        if len(peaks) < 2:
            return 14.0  # standard baseline
        
        intervals_sec = np.diff(peaks) / self.fs
        mean_breath_dur = np.mean(intervals_sec)
        if mean_breath_dur > 0:
            bpm = 60.0 / mean_breath_dur
            return float(np.clip(bpm, 6.0, 40.0))
        return 14.0


def generate_filtering_comparison_figure(
    time_vec: np.ndarray,
    ecg_raw: np.ndarray,
    ecg_filt: np.ndarray,
    resp_raw: np.ndarray,
    resp_filt: np.ndarray,
    r_peaks: np.ndarray,
    save_path: str
) -> None:
    """Generate high-resolution scientific figure comparing raw and filtered signals."""
    plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
    fig, axes = plt.subplots(4, 1, figsize=(12, 10), sharex=True)

    # 1. Raw ECG
    axes[0].plot(time_vec, ecg_raw, color="#7f8c8d", linewidth=0.9, label="Raw ECG (Lead II)")
    axes[0].set_ylabel("Voltage (mV)", fontsize=11, fontweight="bold")
    axes[0].set_title("(a) Raw Continuous ECG Signal with Baseline Drift", fontsize=12, fontweight="bold", loc="left")
    axes[0].legend(loc="upper right", frameon=True)

    # 2. Filtered ECG with detected R-peaks
    axes[1].plot(time_vec, ecg_filt, color="#1b4f72", linewidth=1.0, label="Filtered ECG (0.5–45 Hz Butterworth)")
    peak_mask = (r_peaks < len(time_vec))
    axes[1].scatter(
        time_vec[r_peaks[peak_mask]],
        ecg_filt[r_peaks[peak_mask]],
        color="#c0392b",
        s=40,
        zorder=5,
        label="Detected R-peaks"
    )
    axes[1].set_ylabel("Voltage (mV)", fontsize=11, fontweight="bold")
    axes[1].set_title("(b) Filtered ECG with Pan-Tompkins Peak Detection", fontsize=12, fontweight="bold", loc="left")
    axes[1].legend(loc="upper right", frameon=True)

    # 3. Raw Respiration
    axes[2].plot(time_vec, resp_raw, color="#95a5a6", linewidth=0.9, label="Raw Respiration (Plethysmograph Bellows)")
    axes[2].set_ylabel("Amplitude (V)", fontsize=11, fontweight="bold")
    axes[2].set_title("(c) Raw Continuous Respiratory Signal", fontsize=12, fontweight="bold", loc="left")
    axes[2].legend(loc="upper right", frameon=True)

    # 4. Filtered Respiration
    axes[3].plot(time_vec, resp_filt, color="#117864", linewidth=1.2, label="Filtered Respiration (0.05–0.5 Hz)")
    axes[3].set_ylabel("Amplitude (V)", fontsize=11, fontweight="bold")
    axes[3].set_xlabel("Time (seconds)", fontsize=11, fontweight="bold")
    axes[3].set_title("(d) Filtered Respiratory Rhythm for Cardiopulmonary Coupling", fontsize=12, fontweight="bold", loc="left")
    axes[3].legend(loc="upper right", frameon=True)

    plt.tight_layout()
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    plt.savefig(save_path, dpi=300)
    plt.close()
    logger.info(f"Filtering comparison figure saved to {save_path}")


def main():
    from src.data_loader import FantasiaDataLoader
    loader = FantasiaDataLoader()
    record = loader.fetch_subject_signal("f1y01")

    processor = BiosignalProcessor()
    
    # Process first 15 seconds for clean visual demonstration
    demo_sec = 15
    demo_samples = int(demo_sec * processor.fs)
    time_vec = np.arange(demo_samples) / processor.fs
    
    ecg_filt = processor.filter_ecg(record["ecg"])
    resp_filt = processor.filter_respiration(record["resp"])
    r_peaks = processor.detect_r_peaks(ecg_filt[:demo_samples])
    
    rr_times, rr_ms = processor.extract_rr_intervals(processor.detect_r_peaks(ecg_filt))
    resp_rate = processor.estimate_respiratory_rate(resp_filt)

    logger.info(f"Validation on {record['record_name']}: Detected {len(r_peaks)} peaks in first {demo_sec}s.")
    logger.info(f"Full segment: {len(rr_ms)} RR intervals extracted. Mean RR: {np.mean(rr_ms):.1f} ms, Resp Rate: {resp_rate:.1f} bpm.")

    fig_path = os.path.join(get_project_root(), "results", "figures", "raw_vs_filtered_biosignals.png")
    generate_filtering_comparison_figure(
        time_vec,
        record["ecg"][:demo_samples],
        ecg_filt[:demo_samples],
        record["resp"][:demo_samples],
        resp_filt[:demo_samples],
        r_peaks,
        fig_path
    )
    print("\n--- SIGNAL PROCESSING VALIDATION ---")
    print(f"R-peaks detected: {len(r_peaks)} in 15s")
    print(f"Mean RR interval: {np.mean(rr_ms):.2f} ms ({60000.0/np.mean(rr_ms):.1f} bpm)")
    print(f"Estimated Respiratory Rate: {resp_rate:.2f} breaths/min")
    print(f"Figure saved to: {fig_path}")


if __name__ == "__main__":
    main()
