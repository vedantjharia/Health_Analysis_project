# Experimental Results Directory

This directory archives genuine numerical metrics, scientific figures, serialized machine learning models, and execution logs.

## Subdirectories
- `figures/`: High-resolution (300 DPI) scientific visualizations generated directly from empirical outputs:
  - `methodology_flowchart.png`: End-to-end multi-modal architecture.
  - `raw_vs_filtered_biosignals.png`: ECG and respiration before and after Butterworth filtering and R-peak detection.
  - `poincare_plot_comparison.png`: Poincaré geometry contrasting young autonomic plasticity with elderly rigidity.
  - `roc_curves_comparison.png`: ROC comparison across all 6 models on held-out test subjects.
  - `confusion_matrices.png`: Confusion matrices demonstrating 100% specificity for Random Forest and SVM.
  - `metrics_barchart.png`: Performance scores across Accuracy, Recall, Specificity, and F1.
  - `shap_importance_bar.png`: Global mean |SHAP| feature ranking.
  - `shap_summary_beeswarm.png`: Beeswarm plot revealing biomarker directional impact.
  - `shap_dependence_rmssd.png`: Feature interaction between RMSSD and LF/HF ratio.
  - `shap_local_waterfall.png`: Patient-level waterfall attributions contrasting low vs. high risk.
  - `dataset_distribution.png`: Cohort demographic breakdown.
- `metrics/`: Genuine serialized data:
  - `dataset_audit.json`: Clinical audit parameters.
  - `model_comparison.csv` / `.json`: Benchmark evaluation on held-out test subjects.
  - `shap_feature_importance.csv` / `.json`: Ranked physiological SHAP attributions.
  - `training_summary.json`: 5-fold Stratified Group Cross-Validation performance.
- `models/`: Serialized scikit-learn pipelines with fitted scalers (`.joblib`).
- `logs/`: Execution logs from data loading, signal processing, and training.
