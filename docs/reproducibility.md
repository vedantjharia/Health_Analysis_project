# Reproducibility Guide & Verification Protocol

This guide provides step-by-step instructions for reproducing all experimental figures, metrics, paper deliverables, and test suites.

## System Prerequisites
- Operating System: Windows, Linux, or macOS
- Python Version: Python 3.10 to 3.13
- Core Dependencies: `numpy`, `pandas`, `scipy`, `scikit-learn`, `matplotlib`, `seaborn`, `wfdb`, `shap`, `python-docx`, `python-pptx`, `reportlab`, `pytest`, `pyyaml`.

## Installation
```bash
# 1. Clone repository
git clone https://github.com/vedant-jharia/biosignal-heart-risk-ml.git
cd biosignal-heart-risk-ml

# 2. Create virtual environment
python -m venv .venv
# On Windows PowerShell:
.venv\Scripts\Activate.ps1
# On Linux/macOS:
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt
```

## Step-by-Step Execution Pipeline
Execute each modular stage in sequence:

```bash
# Stage 1: Data Acquisition & Audit
python -m src.data_loader

# Stage 2: Biosignal Filtering & R-Peak Detection
python -m src.signal_processing

# Stage 3: Multi-Domain HRV & CPC Feature Extraction
python -m src.feature_extraction

# Stage 4: Subject-Level Holdout Training & Group-CV
python -m src.train

# Stage 5: Evaluation & Metric Computation
python -m src.evaluate

# Stage 6: Explainable AI with SHAP
python -m src.explain

# Stage 7: Supplementary Flowcharts & Demographic Figures
python -m src.generate_supplementary_figures

# Stage 8: Document Compilation (IEEE Paper & Presentation)
python paper/generate_ieee_paper.py
python paper/generate_ieee_pdf.py
python presentation/generate_presentation.py

# Stage 9: Unit Test Suite
pytest -v tests/
```

## Verification Checklist
- [x] All 8 unit tests in `tests/` pass with zero failures.
- [x] Zero data leakage: Subject-level holdout strictly partitions 16 training subjects and 4 testing subjects.
- [x] Figures are generated at 300 DPI directly from genuine data.
- [x] Paper compiled to `paper/report.docx` and `paper/report.pdf`.
- [x] Presentation compiled to `presentation/presentation.pptx` (14 slides).
