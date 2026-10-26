"""Generate the 4 interactive demonstration notebooks."""

import os
import json
from pathlib import Path


def create_notebook(cells, filepath):
    nb = {
        "cells": cells,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3"
            },
            "language_info": {
                "name": "python",
                "version": "3.13"
            }
        },
        "nbformat": 4,
        "nbformat_minor": 5
    }
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(nb, f, indent=2)
    print(f"Notebook created: {filepath}")


def md_cell(text):
    return {
        "cell_type": "markdown",
        "metadata": {},
        "source": [line + "\n" for line in text.strip().split("\n")]
    }


def code_cell(code):
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [line + "\n" for line in code.strip().split("\n")]
    }


def main():
    root = Path(__file__).resolve().parent.parent
    nb_dir = root / "notebooks"

    # Notebook 1: 01_data_audit.ipynb
    nb1_cells = [
        md_cell("# Notebook 01: PhysioNet Fantasia Dataset Audit & Inspection\n\nThis notebook demonstrates downloading, caching, and auditing the continuous ECG and Respiration signals from the PhysioNet Fantasia database."),
        code_cell("import sys\nsys.path.append('..')\n\nfrom src.data_loader import FantasiaDataLoader\nfrom src.utils import load_config\nimport pandas as pd"),
        code_cell("loader = FantasiaDataLoader()\ncohort = loader.load_cohort()\naudit = loader.audit_dataset(cohort)\n\nfor k, v in audit.items():\n    print(f'{k}: {v}')"),
        code_cell("import matplotlib.pyplot as plt\n\ny_sub = loader.fetch_subject_signal('f1y01')\no_sub = loader.fetch_subject_signal('f1o01')\n\nfig, axes = plt.subplots(2, 1, figsize=(12, 6))\naxes[0].plot(y_sub['ecg'][:1250], color='#1b4f72')\naxes[0].set_title(f\"Healthy Young Subject ({y_sub['record_name']}, Age: {y_sub['age']})\")\naxes[1].plot(o_sub['ecg'][:1250], color='#c0392b')\naxes[1].set_title(f\"Elderly Risk Subject ({o_sub['record_name']}, Age: {o_sub['age']})\")\nplt.tight_layout()\nplt.show()")
    ]
    create_notebook(nb1_cells, str(nb_dir / "01_data_audit.ipynb"))

    # Notebook 2: 02_signal_preprocessing.ipynb
    nb2_cells = [
        md_cell("# Notebook 02: Biosignal Filtering & R-Peak Detection\n\nDemonstration of 4th-order Butterworth bandpass filtering (0.5-45 Hz), Pan-Tompkins R-peak detection, and respiratory rhythm extraction."),
        code_cell("import sys\nsys.path.append('..')\n\nimport numpy as np\nimport matplotlib.pyplot as plt\nfrom src.data_loader import FantasiaDataLoader\nfrom src.signal_processing import BiosignalProcessor"),
        code_cell("loader = FantasiaDataLoader()\nprocessor = BiosignalProcessor()\n\nsub = loader.fetch_subject_signal('f1y01')\necg_filt = processor.filter_ecg(sub['ecg'])\nresp_filt = processor.filter_respiration(sub['resp'])\nr_peaks = processor.detect_r_peaks(ecg_filt)\nrr_times, rr_ms = processor.extract_rr_intervals(r_peaks)\n\nprint(f'Detected {len(r_peaks)} R-peaks. Mean RR: {np.mean(rr_ms):.1f} ms')"),
        code_cell("plt.figure(figsize=(12, 4))\nplt.plot(ecg_filt[:2500], color='#1b4f72', label='Filtered ECG (0.5-45 Hz)')\np_mask = r_peaks < 2500\nplt.scatter(r_peaks[p_mask], ecg_filt[r_peaks[p_mask]], color='#c0392b', s=50, label='Pan-Tompkins R-peaks')\nplt.legend()\nplt.title('Pan-Tompkins Peak Detection on Cleaned ECG')\nplt.show()")
    ]
    create_notebook(nb2_cells, str(nb_dir / "02_signal_preprocessing.ipynb"))

    # Notebook 3: 03_model_training.ipynb
    nb3_cells = [
        md_cell("# Notebook 03: Subject-Level Holdout Training & Evaluation\n\nTrains benchmark models with strict Subject-Level Holdout partitioning to eliminate signal window data leakage."),
        code_cell("import sys\nsys.path.append('..')\n\nimport pandas as pd\nfrom src.train import load_dataset, split_by_subject, build_models, train_and_cross_validate\nfrom src.utils import load_config"),
        code_cell("config = load_config()\ndf = load_dataset()\ntest_subjects = config['evaluation']['test_subjects']\ntrain_df, test_df = split_by_subject(df, test_subjects)\n\nprint(f'Training windows: {len(train_df)}, Testing windows: {len(test_df)}')"),
        code_cell("models = build_models(config)\ncv_res = train_and_cross_validate(train_df, models)\n\npd.DataFrame(cv_res).T[['cv_accuracy_mean', 'cv_f1_mean', 'cv_roc_auc_mean']]")
    ]
    create_notebook(nb3_cells, str(nb_dir / "03_model_training.ipynb"))

    # Notebook 4: 04_explainability.ipynb
    nb4_cells = [
        md_cell("# Notebook 04: Explainable AI with SHAP\n\nComputes TreeSHAP explanations on the trained Random Forest model to generate global feature importance hierarchies and local patient waterfall explanations."),
        code_cell("import sys\nsys.path.append('..')\n\nimport shap\nimport pandas as pd\nfrom src.explain import load_model_and_data, compute_shap_explanations"),
        code_cell("rf_clf, X_train, X_test, test_df, feature_names = load_model_and_data()\nexplainer, shap_risk = compute_shap_explanations(rf_clf, X_train, X_test, feature_names)\n\nshap.plots.bar(shap_risk, max_display=10)"),
        code_cell("shap.plots.beeswarm(shap_risk, max_display=10)")
    ]
    create_notebook(nb4_cells, str(nb_dir / "04_explainability.ipynb"))


if __name__ == "__main__":
    main()
