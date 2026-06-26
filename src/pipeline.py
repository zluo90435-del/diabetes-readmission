import json
from pathlib import Path

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shap
from lightgbm import LGBMClassifier
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    ConfusionMatrixDisplay,
    classification_report,
    roc_auc_score,
    roc_curve,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from xgboost import XGBClassifier

from src.config import (
    BASELINE_CATEGORICAL_FEATURES,
    BASELINE_NUMERIC_FEATURES,
    CATEGORICAL_FEATURES,
    COMPARISON_PATH,
    FEATURE_LABELS,
    METRICS_PATH,
    MODEL_CHOICES,
    MODEL_PATH,
    NUMERIC_FEATURES,
    REPORTS_DIR,
)


def build_preprocessor(
    numeric_features: list[str],
    categorical_features: list[str],
) -> ColumnTransformer:
    return ColumnTransformer(
        transformers=[
            ("num", "passthrough", numeric_features),
            (
                "cat",
                OneHotEncoder(drop="first", handle_unknown="ignore", sparse_output=False),
                categorical_features,
            ),
        ]
    )


def _build_estimator(model_name: str, y_train: pd.Series):
    if model_name == "random_forest":
        return RandomForestClassifier(
            n_estimators=200,
            class_weight="balanced",
            random_state=42,
            n_jobs=-1,
        )

    scale_pos_weight = float((y_train == 0).sum() / max((y_train == 1).sum(), 1))

    if model_name == "xgboost":
        return XGBClassifier(
            n_estimators=300,
            max_depth=6,
            learning_rate=0.05,
            subsample=0.9,
            colsample_bytree=0.9,
            scale_pos_weight=scale_pos_weight,
            random_state=42,
            eval_metric="logloss",
            n_jobs=-1,
        )

    if model_name == "lightgbm":
        return LGBMClassifier(
            n_estimators=300,
            max_depth=-1,
            learning_rate=0.05,
            class_weight="balanced",
            random_state=42,
            verbose=-1,
            n_jobs=-1,
        )

    raise ValueError(f"Unsupported model: {model_name}")


def build_pipeline(
    model_name: str = "xgboost",
    numeric_features: list[str] | None = None,
    categorical_features: list[str] | None = None,
    y_train: pd.Series | None = None,
) -> Pipeline:
    numeric = numeric_features or NUMERIC_FEATURES
    categorical = categorical_features or CATEGORICAL_FEATURES

    if y_train is None:
        y_train = pd.Series([0, 1])

    return Pipeline(
        steps=[
            ("preprocess", build_preprocessor(numeric, categorical)),
            ("model", _build_estimator(model_name, y_train)),
        ]
    )


def get_feature_names(pipeline: Pipeline) -> list[str]:
    return pipeline.named_steps["preprocess"].get_feature_names_out().tolist()


def _humanize_feature_name(feature_name: str) -> str:
    if feature_name in FEATURE_LABELS:
        return FEATURE_LABELS[feature_name]

    for prefix, label_prefix in [
        ("cat__change_", "用藥調整"),
        ("cat__A1Cresult_", "A1C 結果"),
        ("cat__age_", "年齡"),
        ("cat__gender_", "性別"),
        ("cat__race_", "種族"),
        ("cat__max_glu_serum_", "血糖"),
        ("cat__diabetesMed_", "糖尿病用藥"),
        ("cat__metformin_", "Metformin"),
        ("cat__insulin_", "Insulin"),
    ]:
        if feature_name.startswith(prefix):
            return f"{label_prefix}：{feature_name.replace(prefix, '')}"

    if feature_name.startswith("num__"):
        raw_name = feature_name.replace("num__", "")
        return FEATURE_LABELS.get(raw_name, raw_name)
    return feature_name


def _evaluate_split(
    pipeline: Pipeline,
    X_test: pd.DataFrame,
    y_test: pd.Series,
) -> dict:
    y_proba = pipeline.predict_proba(X_test)[:, 1]
    y_pred = (y_proba >= 0.5).astype(int)

    fpr, tpr, thresholds = roc_curve(y_test, y_proba)
    youden_idx = int(np.argmax(tpr - fpr))
    optimal_threshold = float(thresholds[youden_idx])

    return {
        "roc_auc": float(roc_auc_score(y_test, y_proba)),
        "optimal_threshold": optimal_threshold,
        "default_threshold": 0.5,
        "test_size": len(y_test),
        "classification_report": classification_report(
            y_test,
            y_pred,
            target_names=["未再入院", "30天內再入院"],
            output_dict=True,
        ),
    }


def compare_models(
    X: pd.DataFrame,
    y: pd.Series,
    numeric_features: list[str],
    categorical_features: list[str],
    model_names: tuple[str, ...] = MODEL_CHOICES,
) -> tuple[dict, Pipeline, dict]:
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42,
        stratify=y,
    )

    comparison = {
        "feature_count": len(numeric_features) + len(categorical_features),
        "numeric_features": numeric_features,
        "categorical_features": categorical_features,
        "results": [],
    }

    best_pipeline = None
    best_metrics = None
    best_auc = -1.0
    best_model_name = None

    for model_name in model_names:
        pipeline = build_pipeline(
            model_name=model_name,
            numeric_features=numeric_features,
            categorical_features=categorical_features,
            y_train=y_train,
        )
        pipeline.fit(X_train, y_train)
        metrics = _evaluate_split(pipeline, X_test, y_test)
        metrics["model_name"] = model_name
        comparison["results"].append(metrics)

        if metrics["roc_auc"] > best_auc:
            best_auc = metrics["roc_auc"]
            best_pipeline = pipeline
            best_metrics = metrics
            best_model_name = model_name

    comparison["best_model"] = best_model_name
    comparison["best_roc_auc"] = best_auc
    return comparison, best_pipeline, best_metrics


def train_and_evaluate(
    X: pd.DataFrame,
    y: pd.Series,
    X_baseline: pd.DataFrame | None = None,
    model_path: Path = MODEL_PATH,
    metrics_path: Path = METRICS_PATH,
    comparison_path: Path = COMPARISON_PATH,
    reports_dir: Path = REPORTS_DIR,
) -> tuple[Pipeline, dict]:
    baseline_auc = None
    if X_baseline is not None:
        baseline_pipeline = build_pipeline(
            model_name="random_forest",
            numeric_features=BASELINE_NUMERIC_FEATURES,
            categorical_features=BASELINE_CATEGORICAL_FEATURES,
            y_train=y,
        )
        X_train, X_test, y_train, y_test = train_test_split(
            X_baseline,
            y,
            test_size=0.2,
            random_state=42,
            stratify=y,
        )
        baseline_pipeline.fit(X_train, y_train)
        baseline_auc = _evaluate_split(baseline_pipeline, X_test, y_test)["roc_auc"]

    comparison, best_pipeline, best_metrics = compare_models(
        X,
        y,
        NUMERIC_FEATURES,
        CATEGORICAL_FEATURES,
    )

    reports_dir.mkdir(parents=True, exist_ok=True)
    model_path.parent.mkdir(parents=True, exist_ok=True)

    joblib.dump(best_pipeline, model_path)

    metrics = {
        **best_metrics,
        "model_name": comparison["best_model"],
        "feature_version": "v2",
        "feature_count": comparison["feature_count"],
        "positive_rate": float(y.mean()),
        "baseline_roc_auc": baseline_auc,
        "improvement": None if baseline_auc is None else float(best_metrics["roc_auc"] - baseline_auc),
    }

    with metrics_path.open("w", encoding="utf-8") as file:
        json.dump(metrics, file, ensure_ascii=False, indent=2)

    with comparison_path.open("w", encoding="utf-8") as file:
        json.dump(comparison, file, ensure_ascii=False, indent=2)

    _, X_test, _, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    y_pred = (best_pipeline.predict_proba(X_test)[:, 1] >= 0.5).astype(int)

    ConfusionMatrixDisplay.from_predictions(
        y_test,
        y_pred,
        display_labels=["No readmission", "Readmission <30d"],
        cmap="Blues",
    )
    plt.title(f"Confusion Matrix ({comparison['best_model']})")
    plt.tight_layout()
    plt.savefig(reports_dir / "confusion_matrix.png", dpi=150)
    plt.close()

    return best_pipeline, metrics


def load_pipeline(model_path: Path = MODEL_PATH) -> Pipeline:
    return joblib.load(model_path)


def load_metrics(metrics_path: Path = METRICS_PATH) -> dict | None:
    if not metrics_path.exists():
        return None
    with metrics_path.open(encoding="utf-8") as file:
        return json.load(file)


def predict_readmission_proba(pipeline: Pipeline, patient_data: pd.DataFrame) -> float:
    return float(pipeline.predict_proba(patient_data)[0][1])


def explain_prediction(pipeline: Pipeline, patient_data: pd.DataFrame, top_k: int = 3) -> list[dict]:
    preprocess = pipeline.named_steps["preprocess"]
    model = pipeline.named_steps["model"]

    processed = preprocess.transform(patient_data)
    feature_names = get_feature_names(pipeline)
    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(processed)

    if isinstance(shap_values, list):
        values = np.asarray(shap_values[1 if len(shap_values) > 1 else 0])
    else:
        values = np.asarray(shap_values)

    if values.ndim == 3:
        values = values[0, :, 1]
    elif values.ndim == 2:
        values = values[0]

    ranked = sorted(
        zip(feature_names, values),
        key=lambda item: abs(item[1]),
        reverse=True,
    )[:top_k]

    explanations = []
    for feature_name, contribution in ranked:
        direction = "提高" if contribution > 0 else "降低"
        explanations.append(
            {
                "feature": feature_name,
                "label": _humanize_feature_name(feature_name),
                "contribution": float(contribution),
                "direction": direction,
            }
        )
    return explanations
