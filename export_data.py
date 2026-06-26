"""將 SQL Server 資料匯出為 CSV，供本機訓練或線上部署使用。"""

from pathlib import Path

import pandas as pd
import pyodbc

from src.config import DATA_CSV_PATH, PROJECT_ROOT
from src.data import _all_feature_columns, _prepare_features, build_connection_string
from src.config import READMITTED_COLUMN, TARGET_COLUMN


def export_to_csv(output_path: Path = DATA_CSV_PATH) -> Path:
    columns = _all_feature_columns() + [READMITTED_COLUMN]
    query = f"SELECT {', '.join(columns)} FROM diabetic_data"

    with pyodbc.connect(build_connection_string()) as conn:
        df = pd.read_sql(query, conn)

    df[TARGET_COLUMN] = (df[READMITTED_COLUMN] == "<30").astype(int)
    df = _prepare_features(df)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False, encoding="utf-8-sig")

    size_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"已匯出 {len(df):,} 筆 -> {output_path}")
    print(f"檔案大小：{size_mb:.2f} MB")
    return output_path


if __name__ == "__main__":
    export_to_csv()
