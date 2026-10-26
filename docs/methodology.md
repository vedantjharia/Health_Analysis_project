# Signal Processing and Classification Methodology

This document outlines the biophysical principles, mathematical formulations, and validation protocols implemented in the biosignal risk assessment framework.

## 1. Dual-Channel Biosignal Conditioning
Continuous ECG and thoracic respiratory signals operate in distinct frequency bands:
- **ECG Preprocessing**: A 4th-order zero-phase Butterworth bandpass filter ($0.5\text{ Hz} - 45.0\text{ Hz}$) eliminates low-frequency baseline wander and high-frequency EMG muscle interference.
- **R-Peak Localization**: A Pan-Tompkins derivative-integration pipeline isolates QRS complexes:
  $$y[n] = \frac{1}{8}\left(2x[n] + x[n-1] - x[n-3] - 2x[n-4]\right)$$
  Followed by non-linear squaring, 150 ms moving integration, and 250 ms refractory period thresholding.
- **Respiration Preprocessing**: A 3rd-order Butterworth bandpass filter ($0.05\text{ Hz} - 0.50\text{ Hz}$) isolates breathing excursions while suppressing cardiac pulsation artifacts.

## 2. Feature Engineering
From each standardized 5-minute window, 18 features are extracted across 4 physiological domains:
- **Time-Domain HRV**: Mean RR, SDNN, RMSSD, pNN50.
- **Poincaré Geometry**: SD1 (transverse short-term variability), SD2 (longitudinal continuous dispersion), SD1/SD2 ratio.
- **Frequency-Domain HRV**: 4 Hz cubic spline interpolated Welch PSD for VLF, LF (0.04–0.15 Hz), HF (0.15–0.40 Hz), and LF/HF ratio.
- **Cardiopulmonary Coupling (CPC)**: Maximum normalized cross-correlation $\rho_{\max}$ across lags of $[-10\text{s}, +10\text{s}]$, peak-to-trough RSA amplitude, and phase coherence index.

## 3. Strict Subject-Level Holdout Protocol
Signal windowing creates multiple 5-minute segments per recording. To prevent severe data leakage:
- Slicing and splitting are strictly segregated by participant ID.
- Subjects `f1y09`, `f1y10`, `f1o09`, `f1o10` are held out exclusively for final testing (12 segments, 20% holdout).
- Training features are scaled using `StandardScaler` fitted only on training subjects.

## 4. Explainable AI with SHAP
TreeSHAP computes exact Shapley attributions:
$$f(x) = \phi_0 + \sum_{i=1}^M \phi_i(x)$$
Decomposing ensemble decisions into positive risk vs. negative protective physiological factors.
