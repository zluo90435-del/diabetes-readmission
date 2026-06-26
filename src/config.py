import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")


def _resolve_path(env_key: str, default: Path) -> Path:
    value = os.getenv(env_key)
    path = Path(value) if value else default
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path


MODEL_PATH = _resolve_path("MODEL_PATH", PROJECT_ROOT / "models" / "diabetes_pipeline.pkl")
METRICS_PATH = _resolve_path("METRICS_PATH", PROJECT_ROOT / "models" / "metrics.json")
COMPARISON_PATH = _resolve_path("COMPARISON_PATH", PROJECT_ROOT / "models" / "model_comparison.json")
REPORTS_DIR = _resolve_path("REPORTS_DIR", PROJECT_ROOT / "models" / "reports")
DATA_CSV_PATH = _resolve_path("DATA_CSV_PATH", PROJECT_ROOT / "data" / "diabetic_data.csv")


def _default_data_source() -> str:
    explicit = os.getenv("DATA_SOURCE")
    if explicit:
        return explicit.lower()
    if DATA_CSV_PATH.exists() and not os.getenv("DB_SERVER"):
        return "csv"
    return "sql"


DATA_SOURCE = _default_data_source()

DB_DRIVER = os.getenv("DB_DRIVER", "{SQL Server}")
DB_SERVER = os.getenv("DB_SERVER", "DESKTOP-TF0HMPQ")
DB_DATABASE = os.getenv("DB_DATABASE", "diabetic_data")
DB_TRUSTED_CONNECTION = os.getenv("DB_TRUSTED_CONNECTION", "yes")

# v1 原始特徵（用於 before/after 對照）
BASELINE_NUMERIC_FEATURES = [
    "time_in_hospital",
    "num_lab_procedures",
    "num_medications",
    "number_inpatient",
    "number_emergency",
]
BASELINE_CATEGORICAL_FEATURES = ["change", "A1Cresult"]

# v2 擴充特徵
NUMERIC_FEATURES = [
    "time_in_hospital",
    "num_lab_procedures",
    "num_procedures",
    "num_medications",
    "number_outpatient",
    "number_emergency",
    "number_inpatient",
    "number_diagnoses",
    "admission_type_id",
    "discharge_disposition_id",
    "admission_source_id",
]
CATEGORICAL_FEATURES = [
    "age",
    "gender",
    "race",
    "max_glu_serum",
    "A1Cresult",
    "change",
    "diabetesMed",
    "metformin",
    "insulin",
]

TARGET_COLUMN = "target"
READMITTED_COLUMN = "readmitted"

MODEL_CHOICES = ("random_forest", "xgboost", "lightgbm")

FEATURE_LABELS = {
    "time_in_hospital": "住院天數",
    "num_lab_procedures": "實驗室檢查次數",
    "num_procedures": "非實驗室處置次數",
    "num_medications": "本次住院開立藥物數量",
    "number_outpatient": "過去一年門診次數",
    "number_emergency": "過去一年看急診次數",
    "number_inpatient": "過去一年住院次數",
    "number_diagnoses": "診斷數量",
    "admission_type_id": "入院類型",
    "discharge_disposition_id": "出院去向",
    "admission_source_id": "入院來源",
    "age": "年齡區間",
    "gender": "性別",
    "race": "種族",
    "max_glu_serum": "最高血糖檢驗",
    "A1Cresult": "糖化血色素 (A1C)",
    "change": "糖尿病用藥調整",
    "diabetesMed": "是否使用糖尿病藥物",
    "metformin": "Metformin 用藥狀態",
    "insulin": "Insulin 用藥狀態",
}
