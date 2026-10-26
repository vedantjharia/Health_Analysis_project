# Biosignal Data Directory

This directory stores raw and processed clinical biosignal recordings from the **PhysioNet Fantasia Database** and **AidLab Biosignal Datasets**.

## Directory Layout
- `raw/`: Compressed local `.npz` caches of raw 250 Hz continuous ECG (Lead II) and thoracic plethysmography respiration signals.
- `processed/`:
  - `biosignal_features.csv`: Full feature table containing 18 engineered HRV and Cardiopulmonary Coupling (CPC) metrics extracted from standardized 5-minute windows.
  - `train_split.csv`: 48 training window segments partitioned strictly across 16 subjects.
  - `test_split.csv`: 12 held-out test window segments partitioned strictly across 4 subjects (`f1y09`, `f1y10`, `f1o09`, `f1o10`).

## Clinical Cohort
- **Class 0 (Low Risk / Healthy Young Controls)**: 10 subjects, age 27.3 ± 4.6 years (records `f1y01` through `f1y10`).
- **Class 1 (Autonomic Risk / Elderly Cohort)**: 10 subjects, age 73.7 ± 3.4 years (records `f1o01` through `f1o10`).
- **Clinical Target Rationale**: Chronological aging in healthy cohorts models progressive vagal withdrawal, sinoatrial node remodeling, and loss of autonomic plasticity.

## Source & Citations
- PhysioNet Fantasia Database: [https://physionet.org/content/fantasia/](https://physionet.org/content/fantasia/)
- Official Archive Mirror: [https://archive.physionet.org/physiobank/database/fantasia/](https://archive.physionet.org/physiobank/database/fantasia/)
- Goldberger et al., *Circulation*, 2000 [16].
