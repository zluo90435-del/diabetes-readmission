@echo off
cd /d "%~dp0"
echo ========================================
echo  糖尿病再入院風險評估系統
echo ========================================
echo.
echo 正在啟動，請稍候...
echo 若瀏覽器未自動開啟，請手動前往: http://localhost:8501
echo.
python -m streamlit run app.py
pause
