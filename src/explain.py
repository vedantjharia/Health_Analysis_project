"""Explainable AI (XAI) Module using SHAP (SHapley Additive exPlanations).

Provides model interpretability for biomedical biosignal risk assessment:
Global feature importance, Beeswarm summary plots, Feature dependence plots,
and Local patient-level feature attributions with physiological insights.
"""

import os
import joblib
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import shap
from typing import Dict, List, Any

from src.utils import load_config, setup_logger, save_json, get_project_root
from src.train import PREDICTOR_COLS

logger = setup_logger("explain")

# Readable physiological feature labels
FEATURE_LABELS = {
    "mean_rr": "Mean RR (ms)",
    "sdnn": "SDNN (ms)",
    "rmssd": "RMSSD (Vagal Tone, ms)",
    "pnn50": "pNN50 (%)",
    "sd1": "Poincaré SD1 (Short-term Var)",
    "sd2": "Poincaré SD2 (Long-term Var)",
    "sd1_sd2_ratio": "SD1/SD2 Ratio",
    "vlf_power": "VLF Power (ms²)",
    "lf_power": "LF Power (Sympathovagal, ms²)",
    "hf_power": "HF Power (Parasympathetic, ms²)",
    "total_power": "Total Spectral Power (ms²)",
    "lf_hf_ratio": "LF/HF Ratio (Autonomic Balance)",
    "lf_nu": "Normalized LF (n.u.)",
    "hf_nu": "Normalized HF (n.u.)",
    "mean_resp_rate": "Respiration Rate (breaths/min)",
    "rsa_amplitude": "RSA Amplitude (Peak-Trough, ms)",
    "cpc_cross_corr_max": "CPC Max Cross-Correlation",
    "cpc_phase_coherence": "CPC Phase Coherence Index"
}


def load_model_and_data():
    """Load trained Random Forest pipeline and dataset splits."""
    rf_path = os.path.join(get_project_root(), "results", "models", "random_forest.joblib")
    if not os.path.exists(rf_path):
        raise FileNotFoundError(f"Trained Random Forest model not found at {rf_path}. Run train.py first.")

    pipeline = joblib.load(rf_path)
    scaler = pipeline.named_steps["scaler"]
    rf_clf = pipeline.named_steps["clf"]

    train_df = pd.read_csv(os.path.join(get_project_root(), "data", "processed", "train_split.csv"))
    test_df = pd.read_csv(os.path.join(get_project_root(), "data", "processed", "test_split.csv"))

    X_train_raw = train_df[PREDICTOR_COLS].values
    X_test_raw = test_df[PREDICTOR_COLS].values

    X_train_scaled = scaler.transform(X_train_raw)
    X_test_scaled = scaler.transform(X_test_raw)

    return rf_clf, X_train_scaled, X_test_scaled, test_df, PREDICTOR_COLS


def compute_shap_explanations(rf_clf, X_train_scaled, X_test_scaled, feature_names):
    """Compute SHAP values using TreeExplainer."""
    logger.info("Initializing SHAP TreeExplainer on Random Forest model...")
    explainer = shap.TreeExplainer(rf_clf, X_train_scaled)
    shap_values = explainer(X_test_scaled)

    # For binary classification, slice positive class (Class 1: Risk)
    if len(shap_values.values.shape) == 3 and shap_values.values.shape[2] == 2:
        shap_values_risk = shap.Explanation(
            values=shap_values.values[:, :, 1],
            base_values=shap_values.base_values[:, 1] if len(shap_values.base_values.shape) > 1 else shap_values.base_values,
            data=shap_values.data,
            feature_names=[FEATURE_LABELS.get(f, f) for f in feature_names]
        )
    else:
        shap_values_risk = shap.Explanation(
            values=shap_values.values,
            base_values=shap_values.base_values,
            data=shap_values.data,
            feature_names=[FEATURE_LABELS.get(f, f) for f in feature_names]
        )

    return explainer, shap_values_risk


def generate_shap_visualizations(shap_values_risk, test_df, fig_dir):
    """Generate publication-ready SHAP plots."""
    os.makedirs(fig_dir, exist_ok=True)
    readable_names = [FEATURE_LABELS.get(f, f) for f in PREDICTOR_COLS]

    # 1. SHAP Global Feature Importance Bar Plot
    plt.figure(figsize=(10, 6))
    shap.plots.bar(shap_values_risk, max_display=12, show=False)
    plt.title("Global Feature Importance (Mean |SHAP Value|) — Random Forest", fontsize=12, fontweight="bold", pad=12)
    plt.xlabel("Mean |SHAP Value| (Impact on Autonomic Risk Prediction)", fontsize=11, fontweight="bold")
    plt.tight_layout()
    bar_path = os.path.join(fig_dir, "shap_importance_bar.png")
    plt.savefig(bar_path, dpi=300)
    plt.close()
    logger.info(f"SHAP importance bar plot saved to {bar_path}")

    # 2. SHAP Beeswarm Summary Plot
    plt.figure(figsize=(11, 7))
    shap.plots.beeswarm(shap_values_risk, max_display=12, show=False)
    plt.title("SHAP Beeswarm Summary — Feature Directionality & Clinical Impact", fontsize=12, fontweight="bold", pad=12)
    plt.xlabel("SHAP Value (Log-Odds Impact on Risk State)", fontsize=11, fontweight="bold")
    plt.tight_layout()
    beeswarm_path = os.path.join(fig_dir, "shap_summary_beeswarm.png")
    plt.savefig(beeswarm_path, dpi=300)
    plt.close()
    logger.info(f"SHAP beeswarm summary plot saved to {beeswarm_path}")

    # 3. SHAP Feature Dependence Plot (RMSSD vs. SHAP value)
    rmssd_idx = PREDICTOR_COLS.index("rmssd")
    lf_hf_idx = PREDICTOR_COLS.index("lf_hf_ratio")
    
    plt.figure(figsize=(8, 6))
    plt.scatter(
        shap_values_risk.data[:, rmssd_idx],
        shap_values_risk.values[:, rmssd_idx],
        c=shap_values_risk.data[:, lf_hf_idx],
        cmap="coolwarm",
        s=50,
        alpha=0.8,
        edgecolors="k",
        linewidths=0.5
    )
    cbar = plt.colorbar()
    cbar.set_label("LF/HF Ratio (Standardized)", fontsize=10, fontweight="bold")
    plt.axhline(0, color="gray", linestyle="--", alpha=0.6)
    plt.xlabel("Standardized RMSSD (Vagal Tone)", fontsize=11, fontweight="bold")
    plt.ylabel("SHAP Value for Autonomic Risk", fontsize=11, fontweight="bold")
    plt.title("SHAP Dependence: RMSSD Interaction with LF/HF Ratio", fontsize=12, fontweight="bold", pad=12)
    plt.grid(True, linestyle=":", alpha=0.5)
    plt.tight_layout()
    dep_path = os.path.join(fig_dir, "shap_dependence_rmssd.png")
    plt.savefig(dep_path, dpi=300)
    plt.close()
    logger.info(f"SHAP dependence plot saved to {dep_path}")

    # 4. Local Feature Attribution Waterfall Plots (One Healthy Young vs One Elderly Risk)
    healthy_indices = np.where(test_df["label"].values == 0)[0]
    risk_indices = np.where(test_df["label"].values == 1)[0]

    if len(healthy_indices) > 0 and len(risk_indices) > 0:
        h_idx = healthy_indices[0]
        r_idx = risk_indices[0]

        fig, axes = plt.subplots(1, 2, figsize=(16, 7))

        # Local explanation for Healthy Control
        plt.sca(axes[0])
        shap.plots.waterfall(shap_values_risk[h_idx], max_display=8, show=False)
        axes[0].set_title(f"Patient A: Healthy Young Subject ({test_df.iloc[h_idx]['subject_id']})\nModel Prediction: Low Risk (Label 0)", fontsize=11, fontweight="bold")

        # Local explanation for Autonomic Risk Patient
        plt.sca(axes[1])
        shap.plots.waterfall(shap_values_risk[r_idx], max_display=8, show=False)
        axes[1].set_title(f"Patient B: Elderly Risk Subject ({test_df.iloc[r_idx]['subject_id']})\nModel Prediction: Autonomic Risk (Label 1)", fontsize=11, fontweight="bold")

        plt.tight_layout()
        waterfall_path = os.path.join(fig_dir, "shap_local_waterfall.png")
        plt.savefig(waterfall_path, dpi=300)
        plt.close()
        logger.info(f"Local waterfall comparison saved to {waterfall_path}")


def save_feature_importance_rankings(shap_values_risk, metrics_dir):
    """Save ranked feature importance table with clinical physiological rationale."""
    mean_abs_shap = np.mean(np.abs(shap_values_risk.values), axis=0)
    rankings = []

    clinical_rationales = {
        "rmssd": "Root mean square of successive differences directly indexes parasympathetic vagal tone; depression indicates autonomic blunting.",
        "sdnn": "Overall autonomic variability; reduction reflects cardiac vulnerability and loss of neurocardiac responsiveness.",
        "lf_hf_ratio": "Sympathovagal balance marker; elevation indicates sympathetic hyperactivation or vagal withdrawal.",
        "cpc_cross_corr_max": "Measures cardiorespiratory phase synchronization; uncoupling denotes impaired baroreflex-respiratory coordination.",
        "pnn50": "Fraction of consecutive beats differing >50ms; sensitive barometer of respiratory vagal modulation.",
        "hf_power": "High-frequency spectral band (0.15-0.40 Hz); reflects pure vagal parasympathetic modulation.",
        "rsa_amplitude": "Magnitude of Respiratory Sinus Arrhythmia; collapses during cardiac degradation and autonomic aging.",
        "sd1": "Poincaré short-term beat-to-beat variability, tightly correlated with RMSSD.",
        "sd2": "Poincaré continuous long-term dispersion, reflecting systemic regulatory flexibility.",
        "cpc_phase_coherence": "Phase stability between respiratory oscillations and heart rate rhythms.",
        "mean_resp_rate": "Resting respiratory frequency; tachypnea or irregularity frequently accompanies cardiopulmonary strain.",
        "total_power": "Total autonomic spectral reserve across all regulatory frequency bands."
    }

    for col, score in zip(PREDICTOR_COLS, mean_abs_shap):
        rankings.append({
            "Feature": col,
            "Clinical Label": FEATURE_LABELS.get(col, col),
            "Mean |SHAP Value|": round(float(score), 4),
            "Physiological Mechanism": clinical_rationales.get(col, "Biomarker of autonomic cardiovascular regulation.")
        })

    rank_df = pd.DataFrame(rankings).sort_values("Mean |SHAP Value|", ascending=False).reset_index(drop=True)
    rank_df["Rank"] = range(1, len(rank_df) + 1)

    csv_path = os.path.join(metrics_dir, "shap_feature_importance.csv")
    json_path = os.path.join(metrics_dir, "shap_feature_importance.json")

    rank_df.to_csv(csv_path, index=False)
    save_json(rank_df.to_dict(orient="records"), json_path)
    logger.info(f"SHAP feature importance rankings saved to {csv_path}")
    return rank_df


def main():
    rf_clf, X_train_scaled, X_test_scaled, test_df, feature_names = load_model_and_data()
    explainer, shap_values_risk = compute_shap_explanations(rf_clf, X_train_scaled, X_test_scaled, feature_names)

    fig_dir = os.path.join(get_project_root(), "results", "figures")
    metrics_dir = os.path.join(get_project_root(), "results", "metrics")

    generate_shap_visualizations(shap_values_risk, test_df, fig_dir)
    rank_df = save_feature_importance_rankings(shap_values_risk, metrics_dir)

    print("\n================ TOP 8 SHAP FEATURE IMPORTANCE RANKINGS ================")
    print(rank_df[["Rank", "Clinical Label", "Mean |SHAP Value|"]].head(8).to_string(index=False))
    print("========================================================================\n")


if __name__ == "__main__":
    main()
