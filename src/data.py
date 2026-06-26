import pandas as pd

from src.config import (
    BASELINE_CATEGORICAL_FEATURES,
    BASELINE_NUMERIC_FEATURES,
    CATEGORICAL_FEATURES,
    DATA_CSV_PATH,
    DATA_SOURCE,
    DB_DATABASE,
    DB_DRIVER,
    DB_SERVER,
    DB_TRUSTED_CONNECTION,
    NUMERIC_FEATURES,
    READMITTED_COLUMN,
    TARGET_COLUMN,
)


def build_connection_string() -> str:
    return (
        f"Driver={DB_DRIVER};"
        f"Server={DB_SERVER};"
        f"Database={DB_DATABASE};"
        f"Trusted_Connection={DB_TRUSTED_CONNECTION};"
    )


def _all_feature_columns() -> list[str]:
    return NUMERIC_FEATURES + CATEGORICAL_FEATURES


def _baseline_feature_columns() -> list[str]:
    return BASELINE_NUMERIC_FEATURES + BASELINE_CATEGORICAL_FEATURES


def _prepare_features(df: pd.DataFrame) -> pd.DataFrame:
    prepared = df.copy()

    if "diabetesMed" in prepared.columns:
        prepared["diabetesMed"] = prepared["diabetesMed"].map(
            {True: "Yes", False: "No", "True": "Yes", "False": "No"}
        ).fillna("No")

    for column in CATEGORICAL_FEATURES:
        if column in prepared.columns:
            prepared[column] = prepared[column].astype(str).replace({"nan": "Unknown"}).fillna("Unknown")

    for column in NUMERIC_FEATURES:
        if column in prepared.columns:
            prepared[column] = pd.to_numeric(prepared[column], errors="coerce").fillna(0)

    return prepared


def _load_from_csv() -> pd.DataFrame:
    if not DATA_CSV_PATH.exists():
        raise FileNotFoundError(
            f"找不到資料檔 `{DATA_CSV_PATH}`。"
            "請先在本機執行 `python export_data.py` 匯出 CSV。"
        )
    df = pd.read_csv(DATA_CSV_PATH)
    if TARGET_COLUMN not in df.columns:
        df[TARGET_COLUMN] = (df[READMITTED_COLUMN] == "<30").astype(int)
    return _prepare_features(df)


def _load_from_sql(connection_string: str | None = None) -> pd.DataFrame:
    import pyodbc

    conn_str = connection_string or build_connection_string()
    query = f"""
    SELECT
        {", ".join(_all_feature_columns())},
        {READMITTED_COLUMN}
    FROM diabetic_data
    """
    with pyodbc.connect(conn_str) as conn:
        df = pd.read_sql(query, conn)

    df[TARGET_COLUMN] = (df[READMITTED_COLUMN] == "<30").astype(int)
    return _prepare_features(df)


def load_diabetic_data(connection_string: str | None = None) -> pd.DataFrame:
    if DATA_SOURCE == "csv":
        return _load_from_csv()

    try:
        import pyodbc

        return _load_from_sql(connection_string)
    except Exception as exc:
        if DATA_CSV_PATH.exists():
            print(f"SQL 連線失敗（{exc}），改用 CSV 資料。")
            return _load_from_csv()
        raise


def split_features_target(
    df: pd.DataFrame,
    feature_columns: list[str] | None = None,
) -> tuple[pd.DataFrame, pd.Series]:
    columns = feature_columns or _all_feature_columns()
    X = df[columns].copy()
    y = df[TARGET_COLUMN].copy()
    return X, y


def split_baseline_features_target(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    return split_features_target(df, _baseline_feature_columns())
