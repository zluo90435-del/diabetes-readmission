# 資料說明

此資料夾存放從 SQL Server 匯出的 CSV，供線上部署或無資料庫環境使用。

## 產生方式（在本機，需能連 SQL Server）

```bash
python export_data.py
```

會產生 `diabetic_data.csv`（約 8 MB，101,766 筆）。

## 線上部署

將此 CSV 與程式一起 push 到 GitHub，並在 Streamlit Cloud 設定：

```
DATA_SOURCE=csv
```

詳細步驟見 [`docs/DEPLOY.md`](../docs/DEPLOY.md)。
