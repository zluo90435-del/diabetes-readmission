# 糖尿病患 30 天內再入院風險評估系統

從 MS SQL Server 讀取資料、訓練隨機森林模型，並以 Streamlit 提供即時風險預測與 SHAP 解釋。

## 專案結構

```
diabetic/
├── app.py              # Streamlit 推論介面
├── train.py            # 訓練與評估入口
├── src/
│   ├── config.py       # 設定與特徵定義
│   ├── data.py         # 資料庫讀取
│   └── pipeline.py     # 前處理 + 模型 + 評估
├── models/             # 訓練產物（.pkl、metrics.json、報告圖）
├── requirements.txt
├── .env.example
└── README.md
```

## 環境設定

1. 安裝依賴：

```bash
pip install -r requirements.txt
```

2. 複製環境變數範例並修改資料庫連線：

```bash
copy .env.example .env
```

`.env` 中請依你的 SQL Server 設定修改 `DB_SERVER`、`DB_DATABASE` 等欄位。

## 訓練模型

```bash
python train.py
```

訓練完成後會產生：

- `models/diabetes_pipeline.pkl` — 含前處理與模型的完整 Pipeline
- `models/metrics.json` — ROC-AUC、分類報告、Youden 門檻
- `models/reports/confusion_matrix.png` — 混淆矩陣圖

## 啟動 Web 介面

**方式一（最簡單）**：雙擊 `run_app.bat`

**方式二（終端機）**：

```bash
python -m streamlit run app.py
```

> 若出現「無法辨識 streamlit」錯誤，請用 `python -m streamlit`，不要直接打 `streamlit`。

啟動後在瀏覽器開啟：**http://localhost:8501**

## 主要改善

- 訓練與推論共用同一套 `sklearn.Pipeline`，避免手動 One-Hot 欄位不一致
- 分層切分、`class_weight='balanced'`、ROC-AUC 與混淆矩陣評估
- 高風險門檻由驗證集 Youden index 自動計算
- SHAP 解釋本次預測的關鍵因子
- 環境變數管理資料庫連線，免硬編碼

## 免責聲明

本系統僅供研究與臨床輔助參考，不能取代醫師診斷。

## 匯出資料（線上部署用）

```bash
python export_data.py
```

會產生 `data/diabetic_data.csv`，可與程式一起 push 到 GitHub，**不需在雲端連 SQL Server**。

完整部署步驟見 [`docs/DEPLOY.md`](docs/DEPLOY.md)。

## 作品集說明書

申請在職專班或整理作品集時，請參考：

- [`docs/PORTFOLIO_REPORT.md`](docs/PORTFOLIO_REPORT.md) — 完整專案報告（含背景、方法、結果、面試稿）

### 匯出 PDF

1. 用 VS Code 開啟 `docs/PORTFOLIO_REPORT.md`
2. 安裝「Markdown PDF」延伸套件後右鍵 Export
3. 或貼到 Word / Google Docs 再另存 PDF
4. 補上 `docs/images/` 內的 Streamlit 截圖後更完整
