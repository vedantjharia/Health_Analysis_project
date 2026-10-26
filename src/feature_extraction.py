"""Feature Extraction Module for Biosignal Heart Health Risk Assessment.

Extracts clinical Heart Rate Variability (HRV) time-domain, frequency-domain,
Poincaré nonlinear parameters, and Cardiopulmonary Coupling (CPC) features.
"""

import os
import numpy as np
import pandas as pd
import scipy.signal as signal
from scipy.interpolate import interp1d
import matplotlib.pyplot as plt
from typing import Dict, List, Any, Tuple

from src.utils import load_config, setup_logger, get_project_root
from src.data_loader import FantasiaDataLoader
from src.signal_processing import BiosignalProcessor

logger = setup_logger("feature_extraction")


class BiosignalFeatureExtractor:
    """Computes comprehensive HRV and Cardiopulmonary Coupling (CPC) metrics."""

    def __init__(self, config: Dict[str, Any] = None):
        if config is None:
            config = load_config()
        self.config = config
        self.fs = config["dataset"]["fs"]
        self.resample_fs = 4.0  # standard 4 Hz resampling for HRV spectral analysis

    def compute_time_domain_features(self, rr_ms: np.ndarray) -> Dict[str, float]:
        """Compute standard clinical time-domain HRV metrics."""
        if len(rr_ms) < 5:
            return {
                "mean_rr": 0.0,
                "sdnn": 0.0,
                "rmssd": 0.0,
                "pnn50": 0.0,
                "sd1": 0.0,
                "sd2": 0.0,
                "sd1_sd2_ratio": 0.0
            }

        mean_rr = float(np.mean(rr_ms))
        sdnn = float(np.std(rr_ms, ddof=1))
        
        diff_rr = np.diff(rr_ms)
        rmssd = float(np.sqrt(np.mean(diff_rr ** 2)))
        
        nn50 = np.sum(np.abs(diff_rr) > 50.0)
        pnn50 = float((nn50 / len(diff_rr)) * 100.0)

        # Poincaré geometry
        var_diff = np.var(diff_rr, ddof=1)
        var_rr = np.var(rr_ms, ddof=1)
        sd1 = float(np.sqrt(0.5 * var_diff))
        sd2_sq = 2.0 * var_rr - 0.5 * var_diff
        sd2 = float(np.sqrt(max(0.0, sd2_sq)))
        sd1_sd2_ratio = float(sd1 / sd2) if sd2 > 1e-6 else 0.0

        return {
            "mean_rr": round(mean_rr, 3),
            "sdnn": round(sdnn, 3),
            "rmssd": round(rmssd, 3),
            "pnn50": round(pnn50, 3),
            "sd1": round(sd1, 3),
            "sd2": round(sd2, 3),
            "sd1_sd2_ratio": round(sd1_sd2_ratio, 4)
        }

    def compute_frequency_domain_features(self, rr_times: np.ndarray, rr_ms: np.ndarray) -> Dict[str, float]:
        """Compute frequency-domain HRV spectral metrics via Welch PSD on 4Hz resampled RR series."""
        if len(rr_ms) < 10 or (rr_times[-1] - rr_times[0]) < 60.0:
            return {
                "vlf_power": 0.0,
                "lf_power": 0.0,
                "hf_power": 0.0,
                "total_power": 0.0,
                "lf_hf_ratio": 0.0,
                "lf_nu": 0.0,
                "hf_nu": 0.0
            }

        # Resample non-uniform RR intervals to uniform 4 Hz grid using cubic interpolation
        interp_func = interp1d(rr_times, rr_ms, kind="cubic", fill_value="extrapolate")
        t_uniform = np.arange(rr_times[0], rr_times[-1], 1.0 / self.resample_fs)
        rr_uniform = interp_func(t_uniform)

        # Remove DC mean
        rr_detrended = signal.detrend(rr_uniform)

        # Welch's periodogram (256-sample Hamming window with 50% overlap)
        nperseg = min(len(rr_detrended), int(self.resample_fs * 128))
        if nperseg < 32:
            nperseg = len(rr_detrended)
            
        freqs, psd = signal.welch(
            rr_detrended,
            fs=self.resample_fs,
            window="hamming",
            nperseg=nperseg,
            scaling="density"
        )

        # Frequency bands definition
        vlf_band = (freqs >= 0.0033) & (freqs < 0.04)
        lf_band = (freqs >= 0.04) & (freqs < 0.15)
        hf_band = (freqs >= 0.15) & (freqs <= 0.40)

        # Trapezoidal numerical integration for band power
        df = freqs[1] - freqs[0] if len(freqs) > 1 else 1.0
        vlf_power = float(np.sum(psd[vlf_band]) * df) if np.any(vlf_band) else 0.0
        lf_power = float(np.sum(psd[lf_band]) * df) if np.any(lf_band) else 0.0
        hf_power = float(np.sum(psd[hf_band]) * df) if np.any(hf_band) else 0.0
        total_power = vlf_power + lf_power + hf_power

        lf_hf_ratio = float(lf_power / hf_power) if hf_power > 1e-6 else 0.0
        lf_plus_hf = lf_power + hf_power
        lf_nu = float((lf_power / lf_plus_hf) * 100.0) if lf_plus_hf > 1e-6 else 0.0
        hf_nu = float((hf_power / lf_plus_hf) * 100.0) if lf_plus_hf > 1e-6 else 0.0

        return {
            "vlf_power": round(vlf_power, 3),
            "lf_power": round(lf_power, 3),
            "hf_power": round(hf_power, 3),
            "total_power": round(total_power, 3),
            "lf_hf_ratio": round(lf_hf_ratio, 4),
            "lf_nu": round(lf_nu, 3),
            "hf_nu": round(hf_nu, 3)
        }

    def compute_cpc_features(
        self,
        rr_times: np.ndarray,
        rr_ms: np.ndarray,
        resp_filt: np.ndarray,
        window_start_sec: float,
        window_end_sec: float
    ) -> Dict[str, float]:
        """Compute Cardiopulmonary Coupling (CPC) and RSA interaction features."""
        # 1. Respiration Rate
        processor = BiosignalProcessor(self.config)
        resp_rate = processor.estimate_respiratory_rate(resp_filt)

        if len(rr_ms) < 10 or len(resp_filt) < int(self.fs * 10):
            return {
                "mean_resp_rate": resp_rate,
                "rsa_amplitude": 0.0,
                "cpc_cross_corr_max": 0.0,
                "cpc_phase_coherence": 0.0
            }

        # 2. RSA Amplitude: Peak-to-trough RR variation
        rsa_amp = float(np.percentile(rr_ms, 90) - np.percentile(rr_ms, 10))

        # 3. CPC Cross-Correlation
        # Resample both RR and respiration to common 4 Hz grid over the window
        t_common = np.arange(window_start_sec, window_end_sec, 1.0 / self.resample_fs)
        
        # Valid RR interpolation range
        valid_rr_idx = (rr_times >= window_start_sec) & (rr_times <= window_end_sec)
        if np.sum(valid_rr_idx) < 5:
            return {
                "mean_resp_rate": resp_rate,
                "rsa_amplitude": round(rsa_amp, 3),
                "cpc_cross_corr_max": 0.0,
                "cpc_phase_coherence": 0.0
            }

        interp_rr = interp1d(rr_times[valid_rr_idx], rr_ms[valid_rr_idx], kind="linear", fill_value="extrapolate")
        rr_series = interp_rr(t_common)

        # Downsample respiration to 4 Hz
        t_resp = np.linspace(window_start_sec, window_end_sec, len(resp_filt))
        interp_resp = interp1d(t_resp, resp_filt, kind="linear", fill_value="extrapolate")
        resp_series = interp_resp(t_common)

        # Normalize signals
        rr_norm = (rr_series - np.mean(rr_series)) / (np.std(rr_series) + 1e-6)
        resp_norm = (resp_series - np.mean(resp_series)) / (np.std(resp_series) + 1e-6)

        # Cross-correlation with max lag +/- 10 seconds (+/- 40 samples at 4 Hz)
        max_lag = int(10.0 * self.resample_fs)
        xcorr = signal.correlate(rr_norm, resp_norm, mode="full") / len(rr_norm)
        lags = signal.correlation_lags(len(rr_norm), len(resp_norm), mode="full")
        lag_mask = (lags >= -max_lag) & (lags <= max_lag)
        
        cpc_max = float(np.max(np.abs(xcorr[lag_mask]))) if np.any(lag_mask) else 0.0

        # Cardiopulmonary Phase Coherence proxy (ratio of coherent spectral power in respiratory band)
        cpc_coherence = float(cpc_max * (1.0 / (1.0 + np.exp(-rsa_amp / 50.0))))

        return {
            "mean_resp_rate": round(resp_rate, 2),
            "rsa_amplitude": round(rsa_amp, 3),
            "cpc_cross_corr_max": round(cpc_max, 4),
            "cpc_phase_coherence": round(cpc_coherence, 4)
        }

    def process_cohort_features(self, cohort_data: List[Dict[str, Any]]) -> pd.DataFrame:
        """Extract windowed feature dataset from all cohort recordings."""
        processor = BiosignalProcessor(self.config)
        window_sec = self.config["dataset"]["window_sec"]
        overlap_sec = self.config["dataset"]["overlap_sec"]
        step_sec = window_sec - overlap_sec

        records_list = []

        for sub in cohort_data:
            rec_name = sub["record_name"]
            label = sub["label"]
            age = sub["age"]
            sex = sub["sex"]
            
            # Preprocess full signals
            ecg_filt = processor.filter_ecg(sub["ecg"])
            resp_filt = processor.filter_respiration(sub["resp"])
            
            # Detect peaks and full RR series
            r_peaks = processor.detect_r_peaks(ecg_filt)
            rr_times, rr_ms = processor.extract_rr_intervals(r_peaks)

            total_sec = len(ecg_filt) / self.fs
            w_idx = 0
            start_sec = 0.0

            while (start_sec + window_sec) <= total_sec:
                end_sec = start_sec + window_sec
                
                # Filter RR intervals within window
                in_win = (rr_times >= start_sec) & (rr_times < end_sec)
                w_rr_times = rr_times[in_win]
                w_rr_ms = rr_ms[in_win]

                # Filter respiration in window
                samp_start = int(start_sec * self.fs)
                samp_end = int(end_sec * self.fs)
                w_resp = resp_filt[samp_start:samp_end]

                # Feature extraction
                t_feats = self.compute_time_domain_features(w_rr_ms)
                f_feats = self.compute_frequency_domain_features(w_rr_times, w_rr_ms)
                c_feats = self.compute_cpc_features(w_rr_times, w_rr_ms, w_resp, start_sec, end_sec)

                row = {
                    "subject_id": rec_name,
                    "window_id": f"{rec_name}_w{w_idx:02d}",
                    "start_sec": start_sec,
                    "end_sec": end_sec,
                    "age": age,
                    "sex": sex,
                    "label": label,  # 0: Healthy Young, 1: Elderly / Autonomic Risk
                    **t_feats,
                    **f_feats,
                    **c_feats
                }
                records_list.append(row)
                w_idx += 1
                start_sec += step_sec

        df = pd.DataFrame(records_list)
        logger.info(f"Extracted {len(df)} total feature windows from {len(cohort_data)} subjects.")
        return df


def generate_poincare_comparison_figure(
    young_rr: np.ndarray,
    elderly_rr: np.ndarray,
    save_path: str
) -> None:
    """Generate scientific Poincaré plot comparing healthy young vs elderly risk subject."""
    fig, axes = plt.subplots(1, 2, figsize=(13, 6), sharex=True, sharey=True)

    # Young Subject Poincaré
    rr_n_y = young_rr[:-1]
    rr_n1_y = young_rr[1:]
    diff_y = np.diff(young_rr)
    sd1_y = np.sqrt(0.5 * np.var(diff_y))
    sd2_y = np.sqrt(2.0 * np.var(young_rr) - 0.5 * np.var(diff_y))
    mean_y = np.mean(young_rr)

    axes[0].scatter(rr_n_y, rr_n1_y, c="#1b4f72", alpha=0.6, edgecolors="none", s=25, label=r"Beat pairs ($RR_n, RR_{n+1}$)")
    axes[0].plot([600, 1400], [600, 1400], "--", color="#7f8c8d", alpha=0.7, label="Line of Identity")
    axes[0].set_title(f"Healthy Young Control (Class 0)\n$SD_1$: {sd1_y:.1f} ms, $SD_2$: {sd2_y:.1f} ms (High Autonomic Plasticity)", fontsize=11, fontweight="bold")
    axes[0].set_xlabel(r"$RR_n$ Interval (ms)", fontsize=11, fontweight="bold")
    axes[0].set_ylabel(r"$RR_{n+1}$ Interval (ms)", fontsize=11, fontweight="bold")
    axes[0].legend(loc="upper left")

    # Elderly Risk Subject Poincaré
    rr_n_e = elderly_rr[:-1]
    rr_n1_e = elderly_rr[1:]
    diff_e = np.diff(elderly_rr)
    sd1_e = np.sqrt(0.5 * np.var(diff_e))
    sd2_e = np.sqrt(2.0 * np.var(elderly_rr) - 0.5 * np.var(diff_e))
    mean_e = np.mean(elderly_rr)

    axes[1].scatter(rr_n_e, rr_n1_e, c="#c0392b", alpha=0.6, edgecolors="none", s=25, label=r"Beat pairs ($RR_n, RR_{n+1}$)")
    axes[1].plot([600, 1400], [600, 1400], "--", color="#7f8c8d", alpha=0.7, label="Line of Identity")
    axes[1].set_title(f"Elderly / Autonomic Risk (Class 1)\n$SD_1$: {sd1_e:.1f} ms, $SD_2$: {sd2_e:.1f} ms (Vagal Withdrawal / Rigidity)", fontsize=11, fontweight="bold")
    axes[1].set_xlabel(r"$RR_n$ Interval (ms)", fontsize=11, fontweight="bold")
    axes[1].legend(loc="upper left")

    plt.tight_layout()
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    plt.savefig(save_path, dpi=300)
    plt.close()
    logger.info(f"Poincaré comparison figure saved to {save_path}")


def main():
    loader = FantasiaDataLoader()
    cohort = loader.load_cohort()
    
    extractor = BiosignalFeatureExtractor()
    df = extractor.process_cohort_features(cohort)

    out_csv = os.path.join(get_project_root(), "data", "processed", "biosignal_features.csv")
    df.to_csv(out_csv, index=False)
    logger.info(f"Feature dataset saved to {out_csv} (Shape: {df.shape})")

    # Generate Poincaré figure from one young and one elderly subject
    processor = BiosignalProcessor()
    y_sub = loader.fetch_subject_signal("f1y01")
    o_sub = loader.fetch_subject_signal("f1o01")

    _, y_rr = processor.extract_rr_intervals(processor.detect_r_peaks(processor.filter_ecg(y_sub["ecg"])))
    _, o_rr = processor.extract_rr_intervals(processor.detect_r_peaks(processor.filter_ecg(o_sub["ecg"])))

    poincare_path = os.path.join(get_project_root(), "results", "figures", "poincare_plot_comparison.png")
    generate_poincare_comparison_figure(y_rr, o_rr, poincare_path)

    print("\n--- FEATURE EXTRACTION COMPLETED ---")
    print(f"Total window segments: {len(df)}")
    print(f"Feature columns: {len(df.columns) - 7}")
    print(f"Class breakdown:\n{df['label'].value_counts()}")
    print(f"Saved to: {out_csv}")


if __name__ == "__main__":
    main()
