"""Generate Methodology Flowchart and Dataset Distribution Figures."""

import os
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import pandas as pd
import numpy as np

from src.utils import get_project_root


def generate_methodology_flowchart(save_path: str):
    """Generate high-resolution architecture diagram of the end-to-end pipeline."""
    fig, ax = plt.subplots(figsize=(14, 7), dpi=300)
    ax.axis("off")

    # Colors
    c_blue = "#1b4f72"
    c_teal = "#117864"
    c_navy = "#154360"
    c_orange = "#d35400"
    c_green = "#1e8449"
    c_bg = "#f8f9f9"

    # Define stage boxes [x, y, w, h, label, color]
    stages = [
        (0.03, 0.55, 0.16, 0.35, "1. PhysioNet Fantasia\n& AidLab Biosignals\n\n• Continuous ECG (250 Hz)\n• Simultaneous Respiration\n• 40 Subjects (Young/Elderly)\n• Autonomic Degradation Proxy", c_blue),
        (0.22, 0.55, 0.16, 0.35, "2. Biosignal Filtering\n& Peak Detection\n\n• Butterworth Bandpass (0.5-45Hz)\n• Resp Lowpass (0.05-0.5Hz)\n• Pan-Tompkins R-peak detector\n• Beat-to-beat RR extraction", c_teal),
        (0.41, 0.55, 0.17, 0.35, "3. Feature Engineering\n(HRV & CPC)\n\n• Time: SDNN, RMSSD, pNN50\n• Poincaré: SD1, SD2, Ratio\n• Freq: VLF, LF, HF, LF/HF\n• CPC: Cross-Corr, RSA, Phase", c_navy),
        (0.61, 0.55, 0.17, 0.35, "4. ML Classification\n& Leakage Control\n\n• Subject-Level Holdout Split\n• Stratified Group 5-Fold CV\n• LogReg, RF, SVM, GB\n• Soft Voting Ensemble", c_orange),
        (0.81, 0.55, 0.16, 0.35, "5. Explainable AI\n& Clinical Insights\n\n• SHAP TreeExplainer\n• Global Feature Ranking\n• Beeswarm Attributions\n• Patient Waterfall Audits", c_green),
    ]

    for x, y, w, h, text, col in stages:
        # Box shadow
        ax.add_patch(patches.FancyBboxPatch(
            (x + 0.005, y - 0.008), w, h,
            boxstyle="round,pad=0.02,rounding_size=0.03",
            facecolor="#bdc3c7", edgecolor="none", alpha=0.4
        ))
        # Main box
        ax.add_patch(patches.FancyBboxPatch(
            (x, y), w, h,
            boxstyle="round,pad=0.02,rounding_size=0.03",
            facecolor=c_bg, edgecolor=col, linewidth=2.5
        ))
        # Title bar
        ax.add_patch(patches.FancyBboxPatch(
            (x, y + h - 0.09), w, 0.09,
            boxstyle="round,pad=0.01,rounding_size=0.02",
            facecolor=col, edgecolor="none"
        ))
        title = text.split("\n\n")[0]
        body = text.split("\n\n")[1] if "\n\n" in text else ""
        ax.text(x + w/2, y + h - 0.045, title, color="white", fontsize=10.5, fontweight="bold", ha="center", va="center")
        ax.text(x + 0.015, y + (h - 0.09)/2, body, color="#2c3e50", fontsize=9, va="center", ha="left")

    # Connective arrows
    arrow_props = dict(facecolor="#34495e", edgecolor="#2c3e50", width=3, headwidth=10, shrink=0.05)
    for i in range(len(stages) - 1):
        x1 = stages[i][0] + stages[i][2]
        x2 = stages[i+1][0]
        y_mid = stages[i][1] + stages[i][3]/2
        ax.annotate("", xy=(x2, y_mid), xytext=(x1, y_mid), arrowprops=arrow_props)

    # Bottom workflow summary banner
    ax.add_patch(patches.FancyBboxPatch(
        (0.03, 0.08), 0.94, 0.36,
        boxstyle="round,pad=0.02,rounding_size=0.03",
        facecolor="#ebf5fb", edgecolor="#2980b9", linewidth=1.5
    ))
    ax.text(0.05, 0.39, "CLINICAL RISK STRATIFICATION & ZERO-LEAKAGE VALIDATION PROTOCOL", color="#1b4f72", fontsize=11, fontweight="bold")
    summary_text = (
        "• Clinical Target: Healthy Controls (Class 0: Young Adult Cohort) vs. Autonomic Cardiac Risk (Class 1: Elderly Cohort with Vagal Blunting).\n"
        "• Strict Leakage Prevention: Split partitioned strictly by subject ID. Zero signal windows from test patients are visible during training or feature scaling.\n"
        "• Cardiopulmonary Coupling (CPC): Captures respiratory sinus arrhythmia (RSA) and phase synchronization between pulmonary respiration and cardiac vagal tone.\n"
        "• Rigorous Explainability: SHAP decomposes black-box ensemble decisions into quantifiable physiological attributions (LF/HF ratio, SDNN, RMSSD, and CPC cross-correlation)."
    )
    ax.text(0.05, 0.22, summary_text, color="#1c2833", fontsize=9.5, va="center", linespacing=1.6)

    plt.tight_layout()
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    plt.savefig(save_path, dpi=300)
    plt.close()
    print(f"Flowchart saved to: {save_path}")


def generate_dataset_distribution_chart(save_path: str):
    """Generate demographic and class distribution figure."""
    train_df = pd.read_csv(os.path.join(get_project_root(), "data", "processed", "train_split.csv"))
    test_df = pd.read_csv(os.path.join(get_project_root(), "data", "processed", "test_split.csv"))
    full_df = pd.concat([train_df, test_df], ignore_index=True)

    # Group by subject to get subject-level demographics
    sub_df = full_df.drop_duplicates(subset=["subject_id"])

    fig, axes = plt.subplots(1, 3, figsize=(15, 5))

    # 1. Subject Count by Class
    class_counts = sub_df["label"].value_counts().sort_index()
    axes[0].bar(["Healthy Young (Class 0)", "Elderly Risk (Class 1)"], class_counts, color=["#1b4f72", "#c0392b"], width=0.55)
    axes[0].set_ylabel("Number of Subjects", fontsize=11, fontweight="bold")
    axes[0].set_title("(a) Cohort Risk Class Distribution", fontsize=12, fontweight="bold")
    axes[0].set_ylim(0, 13)
    for i, v in enumerate(class_counts):
        axes[0].text(i, v + 0.3, str(v), ha="center", fontweight="bold", fontsize=12)

    # 2. Age Distribution
    axes[1].hist([sub_df[sub_df["label"] == 0]["age"], sub_df[sub_df["label"] == 1]["age"]],
                 bins=10, label=["Young Control", "Elderly Risk"], color=["#1b4f72", "#c0392b"])
    axes[1].set_xlabel("Age (years)", fontsize=11, fontweight="bold")
    axes[1].set_ylabel("Subject Count", fontsize=11, fontweight="bold")
    axes[1].set_title("(b) Subject Age Demographics", fontsize=12, fontweight="bold")
    axes[1].legend(frameon=True)

    # 3. Partition Split Windows (Train vs Test)
    split_counts = [len(train_df), len(test_df)]
    axes[2].pie(split_counts, labels=[f"Train ({split_counts[0]} windows, 16 subs)", f"Test ({split_counts[1]} windows, 4 subs)"],
                autopct="%1.1f%%", colors=["#2980b9", "#e67e22"], startangle=140,
                textprops={"fontsize": 11, "weight": "bold"})
    axes[2].set_title("(c) Subject-Level Partitioning Split", fontsize=12, fontweight="bold")

    plt.tight_layout()
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    plt.savefig(save_path, dpi=300)
    plt.close()
    print(f"Dataset distribution saved to: {save_path}")


if __name__ == "__main__":
    root = get_project_root()
    generate_methodology_flowchart(os.path.join(root, "results", "figures", "methodology_flowchart.png"))
    generate_dataset_distribution_chart(os.path.join(root, "results", "figures", "dataset_distribution.png"))
