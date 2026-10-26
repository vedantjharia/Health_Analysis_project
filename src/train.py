"""Model Training and Subject-Level Cross-Validation Module.

Implements strict subject-level holdout partitioning to prevent signal window leakage,
trains benchmark classifiers (Logistic Regression, Random Forest, SVM, Gradient Boosting,
and Soft Voting Ensemble), fits standard scalers on training subjects only, and saves models.
"""

import os
import joblib
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Any

from sklearn.dummy import DummyClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier, VotingClassifier
from sklearn.svm import SVC
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import StratifiedGroupKFold, cross_validate
from sklearn.pipeline import Pipeline

from src.utils import load_config, setup_logger, save_json, get_project_root

logger = setup_logger("train")

# Define exact feature predictor columns (Strictly excluding identifiers and clinical age/sex metadata)
PREDICTOR_COLS = [
    "mean_rr",
    "sdnn",
    "rmssd",
    "pnn50",
    "sd1",
    "sd2",
    "sd1_sd2_ratio",
    "vlf_power",
    "lf_power",
    "hf_power",
    "total_power",
    "lf_hf_ratio",
    "lf_nu",
    "hf_nu",
    "mean_resp_rate",
    "rsa_amplitude",
    "cpc_cross_corr_max",
    "cpc_phase_coherence"
]


def load_dataset(csv_path: str = None) -> pd.DataFrame:
    """Load the extracted biosignal features dataset."""
    if csv_path is None:
        csv_path = os.path.join(get_project_root(), "data", "processed", "biosignal_features.csv")
    
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Feature dataset not found at {csv_path}. Run feature_extraction first.")
    
    df = pd.read_csv(csv_path)
    return df


def split_by_subject(
    df: pd.DataFrame,
    test_subjects: List[str]
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Perform strict subject-level holdout split.
    
    Ensures zero window segments from test subjects appear in the training partition.
    """
    test_mask = df["subject_id"].isin(test_subjects)
    train_df = df[~test_mask].copy().reset_index(drop=True)
    test_df = df[test_mask].copy().reset_index(drop=True)

    logger.info(
        f"Subject-level Split -> Train: {train_df['subject_id'].nunique()} subjects ({len(train_df)} windows) | "
        f"Test: {test_df['subject_id'].nunique()} subjects ({len(test_df)} windows)"
    )
    return train_df, test_df


def build_models(config: Dict[str, Any]) -> Dict[str, Pipeline]:
    """Construct benchmark model pipelines with StandardScaler fitted inside CV/Pipeline."""
    seed = config["evaluation"]["random_seed"]
    
    lr_cfg = config["models"]["logistic_regression"]
    rf_cfg = config["models"]["random_forest"]
    svm_cfg = config["models"]["svm"]
    gb_cfg = config["models"]["gradient_boosting"]

    # 1. Baseline Dummy
    dummy = Pipeline([
        ("scaler", StandardScaler()),
        ("clf", DummyClassifier(strategy="stratified", random_state=seed))
    ])

    # 2. Logistic Regression
    lr = Pipeline([
        ("scaler", StandardScaler()),
        ("clf", LogisticRegression(
            C=lr_cfg["C"],
            solver=lr_cfg["solver"],
            max_iter=lr_cfg["max_iter"],
            random_state=seed
        ))
    ])

    # 3. Random Forest
    rf = Pipeline([
        ("scaler", StandardScaler()),
        ("clf", RandomForestClassifier(
            n_estimators=rf_cfg["n_estimators"],
            max_depth=rf_cfg["max_depth"],
            random_state=seed
        ))
    ])

    # 4. Support Vector Machine
    svm = Pipeline([
        ("scaler", StandardScaler()),
        ("clf", SVC(
            C=svm_cfg["C"],
            kernel=svm_cfg["kernel"],
            probability=svm_cfg["probability"],
            random_state=seed
        ))
    ])

    # 5. Gradient Boosting
    gb = Pipeline([
        ("scaler", StandardScaler()),
        ("clf", GradientBoostingClassifier(
            n_estimators=gb_cfg["n_estimators"],
            learning_rate=gb_cfg["learning_rate"],
            max_depth=gb_cfg["max_depth"],
            random_state=seed
        ))
    ])

    # 6. Soft Voting Ensemble
    voting = Pipeline([
        ("scaler", StandardScaler()),
        ("clf", VotingClassifier(
            estimators=[
                ("lr", LogisticRegression(C=1.0, solver="lbfgs", max_iter=1000, random_state=seed)),
                ("rf", RandomForestClassifier(n_estimators=100, max_depth=5, random_state=seed)),
                ("gb", GradientBoostingClassifier(n_estimators=100, learning_rate=0.08, max_depth=3, random_state=seed))
            ],
            voting="soft"
        ))
    ])

    return {
        "Dummy Baseline": dummy,
        "Logistic Regression": lr,
        "Random Forest": rf,
        "Support Vector Machine": svm,
        "Gradient Boosting": gb,
        "Soft Voting Ensemble": voting
    }


def train_and_cross_validate(
    train_df: pd.DataFrame,
    models: Dict[str, Pipeline],
    seed: int = 42
) -> Dict[str, Any]:
    """Perform 5-fold Stratified Group Cross-Validation on training subjects."""
    X = train_df[PREDICTOR_COLS].values
    y = train_df["label"].values
    groups = train_df["subject_id"].values

    sgkf = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=seed)
    cv_results = {}

    for name, pipe in models.items():
        logger.info(f"Running 5-fold Stratified Group-CV for: {name}...")
        scores = cross_validate(
            pipe,
            X,
            y,
            groups=groups,
            cv=sgkf,
            scoring=["accuracy", "f1", "roc_auc"],
            return_train_score=False
        )
        cv_results[name] = {
            "cv_accuracy_mean": float(np.mean(scores["test_accuracy"])),
            "cv_accuracy_std": float(np.std(scores["test_accuracy"])),
            "cv_f1_mean": float(np.mean(scores["test_f1"])),
            "cv_f1_std": float(np.std(scores["test_f1"])),
            "cv_roc_auc_mean": float(np.mean(scores["test_roc_auc"])),
            "cv_roc_auc_std": float(np.std(scores["test_roc_auc"]))
        }

    return cv_results


def fit_and_save_final_models(
    train_df: pd.DataFrame,
    models: Dict[str, Pipeline],
    save_dir: str
) -> None:
    """Fit all model pipelines on the full training partition and serialize them."""
    os.makedirs(save_dir, exist_ok=True)
    X_train = train_df[PREDICTOR_COLS].values
    y_train = train_df["label"].values

    for name, pipe in models.items():
        logger.info(f"Fitting final pipeline on {len(train_df)} training samples: {name}")
        pipe.fit(X_train, y_train)
        slug = name.lower().replace(" ", "_")
        model_path = os.path.join(save_dir, f"{slug}.joblib")
        joblib.dump(pipe, model_path)
        logger.info(f"Saved model pipeline to {model_path}")


def main():
    config = load_config()
    df = load_dataset()
    
    test_subjects = config["evaluation"]["test_subjects"]
    train_df, test_df = split_by_subject(df, test_subjects)

    # Save partitioned splits
    splits_dir = os.path.join(get_project_root(), "data", "processed")
    train_df.to_csv(os.path.join(splits_dir, "train_split.csv"), index=False)
    test_df.to_csv(os.path.join(splits_dir, "test_split.csv"), index=False)

    models = build_models(config)
    cv_summary = train_and_cross_validate(train_df, models, seed=config["evaluation"]["random_seed"])

    models_dir = os.path.join(get_project_root(), "results", "models")
    fit_and_save_final_models(train_df, models, models_dir)

    summary_path = os.path.join(get_project_root(), "results", "metrics", "training_summary.json")
    save_json({
        "predictor_columns": PREDICTOR_COLS,
        "train_subjects": list(train_df["subject_id"].unique()),
        "test_subjects": list(test_df["subject_id"].unique()),
        "train_samples": len(train_df),
        "test_samples": len(test_df),
        "cv_performance": cv_summary
    }, summary_path)
    
    print("\n--- MODEL TRAINING & GROUP-CV SUMMARY ---")
    for m_name, m_res in cv_summary.items():
        print(f"{m_name:25s} | Acc: {m_res['cv_accuracy_mean']:.3f} +/- {m_res['cv_accuracy_std']:.3f} | "
              f"F1: {m_res['cv_f1_mean']:.3f} | AUC: {m_res['cv_roc_auc_mean']:.3f}")


if __name__ == "__main__":
    main()
