from src.config import COMPARISON_PATH, METRICS_PATH, MODEL_PATH, REPORTS_DIR
from src.data import load_diabetic_data, split_baseline_features_target, split_features_target
from src.pipeline import train_and_evaluate


def main() -> None:
    print("正在從資料庫載入資料...")
    df = load_diabetic_data()
    X, y = split_features_target(df)
    X_baseline, _ = split_baseline_features_target(df)

    print(f"資料筆數：{len(df)}，30 天內再入院比例：{y.mean():.2%}")
    print(f"v2 特徵數：{X.shape[1]}（v1 基線：{X_baseline.shape[1]}）")
    print("開始比較 Random Forest / XGBoost / LightGBM...\n")

    _, metrics = train_and_evaluate(X, y, X_baseline=X_baseline)

    print("訓練完成！")
    print(f"最佳模型：{metrics['model_name']}")
    print(f"模型已儲存：{MODEL_PATH}")
    print(f"評估指標已儲存：{METRICS_PATH}")
    print(f"模型比較已儲存：{COMPARISON_PATH}")
    print(f"混淆矩陣圖已儲存：{REPORTS_DIR / 'confusion_matrix.png'}")
    print("\n--- 成效對照 ---")
    if metrics.get("baseline_roc_auc") is not None:
        print(f"v1 基線 ROC-AUC：{metrics['baseline_roc_auc']:.4f}")
    print(f"v2 最佳 ROC-AUC：{metrics['roc_auc']:.4f}")
    if metrics.get("improvement") is not None:
        print(f"提升幅度：{metrics['improvement']:+.4f}")
    print(f"建議風險門檻 (Youden index)：{metrics['optimal_threshold']:.4f}")


if __name__ == "__main__":
    main()
