# 線上部署指南（Streamlit Cloud + CSV 資料）

本專案支援**不依賴 SQL Server** 的線上部署：  
把資料匯成 CSV、模型檔一起放進 GitHub，再用 [Streamlit Community Cloud](https://streamlit.io/cloud) 免費部署。

---

## 架構說明

| 元件 | 本機開發 | 線上部署 |
|------|----------|----------|
| 資料 | SQL Server | `data/diabetic_data.csv` |
| 模型 | `models/diabetes_pipeline.pkl` | 同上（約 1 MB） |
| 評估指標 | `models/metrics.json` | 同上 |
| Web 介面 | Streamlit | Streamlit Cloud |

> **重點**：訪客使用 Web 介面做預測時，**不需要連資料庫**，只要模型檔即可。  
> CSV 主要用於**重新訓練**（`python train.py`）。

---

## 第一步：在本機匯出資料

確認 SQL Server 可連線後：

```bash
python export_data.py
```

會產生：`data/diabetic_data.csv`（約 8 MB）

---

## 第二步：確認必要檔案齊全

部署前請確認 repo 內有：

```
diabetic/
├── app.py
├── requirements.txt
├── data/diabetic_data.csv          ← 匯出的資料
├── models/diabetes_pipeline.pkl    ← 訓練好的模型（約 1 MB）
├── models/metrics.json             ← 評估指標
├── src/
└── .streamlit/config.toml
```

若還沒訓練模型：

```bash
python train.py
```

---

## 第三步：推上 GitHub

1. 建立 GitHub 新 repository（例如 `diabetes-readmission`）
2. 在專案資料夾：

```bash
git init
git add .
git commit -m "Add diabetes readmission prediction app"
git branch -M main
git remote add origin https://github.com/你的帳號/diabetes-readmission.git
git push -u origin main
```

> 注意：`.env` 不要 push（已在 `.gitignore`）。  
> CSV 與模型檔**需要** push 才能線上運作。

---

## 第四步：部署到 Streamlit Cloud

1. 前往 https://share.streamlit.io
2. 用 GitHub 登入
3. **New app** → 選你的 repo
4. 設定：
   - **Main file path**：`app.py`
   - **Branch**：`main`
5. **Advanced settings → Secrets**（可選，建議設定）：

```toml
DATA_SOURCE = "csv"
```

6. 按 **Deploy**

數分鐘後會得到公開網址，例如：  
`https://diabetes-readmission-xxxxx.streamlit.app`

---

## 環境變數說明

| 變數 | 本機建議 | 線上建議 |
|------|----------|----------|
| `DATA_SOURCE` | `sql` | `csv` |
| `DATA_CSV_PATH` | `data/diabetic_data.csv` | 預設即可 |
| `MODEL_PATH` | `models/diabetes_pipeline.pkl` | 預設即可 |

---

## 常見問題

### Q：一定要匯 CSV 嗎？

線上主機通常**無法連你的本機 SQL Server**，所以要把資料匯出成 CSV 一起放上去。  
若只用 Web 預測、不重新訓練，理論上只 push 模型檔也行，但保留 CSV 較完整。

### Q：資料會不會太大？

目前 CSV 約 **8 MB**、模型約 **1 MB**，GitHub 免費方案可接受。

### Q：CSV 含不含個資？

此資料集為研究用去識別化資料，但仍請勿公開可識別個資；對外展示時說明為研究/作品集用途。

### Q：之後資料更新了？

在本機重新執行：

```bash
python export_data.py
python train.py
git add data/diabetic_data.csv models/
git commit -m "Update data and model"
git push
```

Streamlit Cloud 會自動重新部署。

---

## 免責聲明

線上版本同樣僅供**研究與作品集展示**，不能取代醫師診斷。
