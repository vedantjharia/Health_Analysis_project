"""Model Evaluation and Metric Computation Module.

Computes genuine classification metrics on strictly held-out subjects:
Accuracy, Precision, Recall, Specificity, F1-Score, ROC-AUC, Balanced Accuracy,
and Confusion Matrices. Generates publication-grade scientific figures.
"""

import os
import joblib
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, List, Any, Tuple
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, confusion_matrix, balanced_accuracy_score, roc_curve
)

from src.utils import load_config, setup_logger, save_json, get_project_root
from src.train import PREDICTOR_COLS

logger = setup_logger("evaluate")


def load_test_data() -> Tuple[np.ndarray, np.ndarray, pd.DataFrame]:
    """Load test dataset split."""
    test_path = os.path.join(get_project_root(), "data", "processed", "test_split.csv")
    if not os.path.exists(test_path):
        raise FileNotFoundError(f"Test split not found at {test_path}. Run train.py first.")
    
    test_df = pd.read_csv(test_path)
    X_test = test_df[PREDICTOR_COLS].values
    y_test = test_df["label"].values
    return X_test, y_test, test_df


def evaluate_all_models(
    models_dir: str,
    X_test: np.ndarray,
    y_test: np.ndarray
) -> Tuple[pd.DataFrame, Dict[str, Any], Dict[str, Any]]:
    """Evaluate all serialized models on held-out test data."""
    model_files = [f for f in os.listdir(models_dir) if f.endswith(".joblib")]
    results = []
    curves_data = {}
    cm_dict = {}

    model_display_names = {
        "dummy_baseline.joblib": "Dummy Baseline",
        "logistic_regression.joblib": "Logistic Regression",
        "random_forest.joblib": "Random Forest",
        "support_vector_machine.joblib": "Support Vector Machine",
        "gradient_boosting.joblib": "Gradient Boosting",
        "soft_voting_ensemble.joblib": "Soft Voting Ensemble"
    }

    for f in sorted(model_files):
        display_name = model_display_names.get(f, f.replace(".joblib", "").replace("_", " ").title())
        pipe = joblib.load(os.path.join(models_dir, f))
        
        y_pred = pipe.predict(X_test)
        
        if hasattr(pipe, "predict_proba"):
            y_proba = pipe.predict_proba(X_test)[:, 1]
        else:
            y_proba = y_pred

        cm = confusion_matrix(y_test, y_pred, labels=[0, 1])
        tn, fp, fn, tp = cm.ravel()

        acc = float(accuracy_score(y_test, y_pred))
        prec = float(precision_score(y_test, y_pred, zero_division=0))
        rec = float(recall_score(y_test, y_pred, zero_division=0))
        spec = float(tn / (tn + fp)) if (tn + fp) > 0 else 0.0
        f1 = float(f1_score(y_test, y_pred, zero_division=0))
        b_acc = float(balanced_accuracy_score(y_test, y_pred))
        
        try:
            auc = float(roc_auc_score(y_test, y_proba))
            fpr, tpr, _ = roc_curve(y_test, y_proba)
        except Exception:
            auc = 0.5
            fpr, tpr = np.array([0, 1]), np.array([0, 1])

        curves_data[display_name] = {
            "fpr": fpr.tolist(),
            "tpr": tpr.tolist(),
            "auc": auc
        }
        cm_dict[display_name] = cm

        results.append({
            "Model": display_name,
            "Accuracy": round(acc, 4),
            "Precision": round(prec, 4),
            "Recall (Sensitivity)": round(rec, 4),
            "Specificity": round(spec, 4),
            "F1-Score": round(f1, 4),
            "Balanced Accuracy": round(b_acc, 4),
            "ROC-AUC": round(auc, 4),
            "TP": int(tp),
            "FP": int(fp),
            "TN": int(tn),
            "FN": int(fn)
        })

    res_df = pd.DataFrame(results)
    return res_df, curves_data, cm_dict


def plot_roc_curves(curves_data: Dict[str, Any], save_path: str) -> None:
    """Generate scientific ROC curves comparison figure."""
    plt.figure(figsize=(8, 7))
    palette = ["#7f8c8d", "#2980b9", "#27ae60", "#8e44ad", "#d35400", "#c0392b"]

    for idx, (model_name, data) in enumerate(curves_data.items()):
        color = palette[idx % len(palette)]
        linestyle = "--" if "Dummy" in model_name else "-"
        linewidth = 2.4 if "Ensemble" in model_name or "Random Forest" in model_name else 1.8
        plt.plot(
            data["fpr"], data["tpr"],
            label=f"{model_name} (AUC = {data['auc']:.3f})",
            color=color,
            linestyle=linestyle,
            linewidth=linewidth
        )

    plt.plot([0, 1], [0, 1], color="#bdc3c7", linestyle=":", label="Chance Baseline (AUC = 0.500)")
    plt.xlim([-0.02, 1.02])
    plt.ylim([-0.02, 1.05])
    plt.xlabel("False Positive Rate (1 - Specificity)", fontsize=11, fontweight="bold")
    plt.ylabel("True Positive Rate (Sensitivity)", fontsize=11, fontweight="bold")
    plt.title("Receiver Operating Characteristic (ROC) — Subject-Level Holdout", fontsize=12, fontweight="bold", pad=12)
    plt.legend(loc="lower right", frameon=True, fontsize=10)
    plt.grid(True, linestyle="--", alpha=0.5)

    plt.tight_layout()
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    plt.savefig(save_path, dpi=300)
    plt.close()
    logger.info(f"ROC comparison figure saved to {save_path}")


def plot_confusion_matrices(cm_dict: Dict[str, Any], save_path: str) -> None:
    """Generate subplots of confusion matrices for all evaluated models."""
    n_models = len(cm_dict)
    fig, axes = plt.subplots(2, 3, figsize=(14, 9))
    axes = axes.flatten()

    for idx, (model_name, cm) in enumerate(cm_dict.items()):
        ax = axes[idx]
        sns.heatmap(
            cm, annot=True, fmt="d", cmap="Blues", cbar=False, ax=ax,
            xticklabels=["Healthy (0)", "Risk (1)"],
            yticklabels=["Healthy (0)", "Risk (1)"],
            annot_kws={"size": 14, "weight": "bold"}
        )
        ax.set_title(model_name, fontsize=11, fontweight="bold")
        ax.set_ylabel("True Diagnosis", fontsize=10)
        ax.set_xlabel("Predicted Diagnosis", fontsize=10)

    plt.tight_layout()
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    plt.savefig(save_path, dpi=300)
    plt.close()
    logger.info(f"Confusion matrices figure saved to {save_path}")


def plot_metrics_barchart(res_df: pd.DataFrame, save_path: str) -> None:
    """Generate comparative metric bar charts."""
    metrics_to_plot = ["Accuracy", "Precision", "Recall (Sensitivity)", "Specificity", "F1-Score"]
    
    # Filter non-dummy models for clean comparison or include all
    melted = res_df.melt(
        id_vars=["Model"],
        value_vars=metrics_to_plot,
        var_name="Metric",
        value_name="Score"
    )

    plt.figure(figsize=(12, 6))
    palette = ["#34495e", "#2980b9", "#27ae60", "#8e44ad", "#e67e22", "#c0392b"]
    
    sns.barplot(
        data=melted,
        x="Metric",
        y="Score",
        hue="Model",
        palette=palette
    )
    plt.ylim(0, 1.15)
    plt.ylabel("Performance Score (0.0 - 1.0)", fontsize=11, fontweight="bold")
    plt.xlabel("Diagnostic Evaluation Metric", fontsize=11, fontweight="bold")
    plt.title("Comparative Model Performance on Held-Out Test Subjects", fontsize=13, fontweight="bold", pad=12)
    plt.legend(bbox_to_anchor=(1.02, 1), loc="upper left", frameon=True)
    plt.grid(axis="y", linestyle="--", alpha=0.5)

    plt.tight_layout()
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    plt.savefig(save_path, dpi=300)
    plt.close()
    logger.info(f"Metrics barchart figure saved to {save_path}")


def main():
    X_test, y_test, test_df = load_test_data()
    models_dir = os.path.join(get_project_root(), "results", "models")

    res_df, curves_data, cm_dict = evaluate_all_models(models_dir, X_test, y_test)

    # Save CSV and JSON
    metrics_dir = os.path.join(get_project_root(), "results", "metrics")
    csv_path = os.path.join(metrics_dir, "model_comparison.csv")
    json_path = os.path.join(metrics_dir, "model_comparison.json")
    
    res_df.to_csv(csv_path, index=False)
    save_json({
        "metrics_table": res_df.to_dict(orient="records"),
        "roc_curves": curves_data
    }, json_path)
    logger.info(f"Model comparison saved to {csv_path} and {json_path}")

    # Generate Figures
    fig_dir = os.path.join(get_project_root(), "results", "figures")
    plot_roc_curves(curves_data, os.path.join(fig_dir, "roc_curves_comparison.png"))
    plot_confusion_matrices(cm_dict, os.path.join(fig_dir, "confusion_matrices.png"))
    plot_metrics_barchart(res_df, os.path.join(fig_dir, "metrics_barchart.png"))

    print("\n================== HELD-OUT TEST EVALUATION RESULTS ==================")
    print(res_df[["Model", "Accuracy", "Recall (Sensitivity)", "Specificity", "F1-Score", "ROC-AUC"]].to_string(index=False))
    print("======================================================================\n")


if __name__ == "__main__":
    main()
