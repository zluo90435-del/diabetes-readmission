import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from src.config import METRICS_PATH, MODEL_PATH
from src.ui_options import (
    ADMISSION_SOURCE_OPTIONS,
    ADMISSION_TYPE_OPTIONS,
    A1C_OPTIONS,
    CHANGE_OPTIONS,
    DISCHARGE_DISPOSITION_OPTIONS,
    GENDER_OPTIONS,
    MAX_GLU_OPTIONS,
    MEDICATION_OPTIONS,
    RACE_OPTIONS,
    AGE_OPTIONS,
)
from src.pipeline import (
    explain_prediction,
    load_metrics,
    load_pipeline,
    predict_readmission_proba,
)


st.set_page_config(page_title="糖尿病患再入院風險預測系統", layout="wide")
st.title("🏥 糖尿病患 30 天內再入院風險評估系統")
st.write("請輸入患者的臨床指標，系統將即時計算出院後的再入院機率。")

st.info(
    "⚠️ **免責聲明**：本系統僅供研究與臨床輔助參考，不能取代醫師診斷。"
    "實際治療決策請由合格醫療人員綜合判斷。"
)


@st.cache_resource
def get_pipeline():
    if not MODEL_PATH.exists():
        return None
    return load_pipeline(MODEL_PATH)


@st.cache_resource
def get_metrics():
    return load_metrics(METRICS_PATH)


with st.spinner("正在載入 AI 模型，首次約需 10–30 秒，請稍候..."):
    pipeline = get_pipeline()
    metrics = get_metrics()

if pipeline is None:
    st.error(
        f"找不到模型檔案 `{MODEL_PATH}`。"
        "請先執行 `python train.py` 完成訓練後再啟動此頁面。"
    )
    st.stop()

risk_threshold = metrics["optimal_threshold"] if metrics else 0.5

st.divider()
st.subheader("📋 患者臨床資料輸入")

tab_basic, tab_care, tab_meds = st.tabs(["基本資料", "就醫紀錄", "用藥與檢驗"])

with tab_basic:
    col1, col2, col3 = st.columns(3)
    with col1:
        age = st.selectbox("年齡區間", AGE_OPTIONS, index=AGE_OPTIONS.index("[60-70)"))
        gender = st.selectbox("性別", list(GENDER_OPTIONS.keys()))
        race = st.selectbox("種族", list(RACE_OPTIONS.keys()))
    with col2:
        time_in_hospital = st.slider("住院天數 (天)", min_value=1, max_value=14, value=3)
        num_diagnoses = st.number_input("診斷數量", min_value=1, max_value=16, value=9)
        admission_type = st.selectbox("入院類型", list(ADMISSION_TYPE_OPTIONS.keys()))
    with col3:
        discharge_disposition = st.selectbox("出院去向", list(DISCHARGE_DISPOSITION_OPTIONS.keys()))
        admission_source = st.selectbox("入院來源", list(ADMISSION_SOURCE_OPTIONS.keys()))

with tab_care:
    col1, col2 = st.columns(2)
    with col1:
        num_lab_procedures = st.number_input("實驗室檢查次數", min_value=0, max_value=150, value=40)
        num_procedures = st.number_input("非實驗室處置次數", min_value=0, max_value=10, value=0)
        num_medications = st.number_input("本次住院開立藥物數量", min_value=0, max_value=100, value=15)
    with col2:
        number_outpatient = st.number_input("過去一年門診次數", min_value=0, max_value=50, value=0)
        number_emergency = st.number_input("過去一年看急診次數", min_value=0, max_value=30, value=0)
        number_inpatient = st.number_input("過去一年住院次數", min_value=0, max_value=30, value=0)

with tab_meds:
    col1, col2 = st.columns(2)
    with col1:
        diabetes_med = st.checkbox("有使用糖尿病藥物", value=True)
        change_status = st.selectbox("本次住院是否有調整糖尿病藥物？", list(CHANGE_OPTIONS.keys()))
        metformin = st.selectbox("Metformin 用藥狀態", list(MEDICATION_OPTIONS.keys()))
        insulin = st.selectbox("Insulin 用藥狀態", list(MEDICATION_OPTIONS.keys()))
    with col2:
        a1c_status = st.selectbox("糖化血色素 (A1C) 檢查結果", list(A1C_OPTIONS.keys()))
        max_glu = st.selectbox("最高血糖檢驗", list(MAX_GLU_OPTIONS.keys()))

st.divider()

if st.button("🔮 開始評估再入院風險", type="primary"):
    patient_data = pd.DataFrame(
        [
            {
                "time_in_hospital": time_in_hospital,
                "num_lab_procedures": num_lab_procedures,
                "num_procedures": num_procedures,
                "num_medications": num_medications,
                "number_outpatient": number_outpatient,
                "number_emergency": number_emergency,
                "number_inpatient": number_inpatient,
                "number_diagnoses": num_diagnoses,
                "admission_type_id": ADMISSION_TYPE_OPTIONS[admission_type],
                "discharge_disposition_id": DISCHARGE_DISPOSITION_OPTIONS[discharge_disposition],
                "admission_source_id": ADMISSION_SOURCE_OPTIONS[admission_source],
                "age": age,
                "gender": GENDER_OPTIONS[gender],
                "race": RACE_OPTIONS[race],
                "max_glu_serum": MAX_GLU_OPTIONS[max_glu],
                "A1Cresult": A1C_OPTIONS[a1c_status],
                "change": CHANGE_OPTIONS[change_status],
                "diabetesMed": "Yes" if diabetes_med else "No",
                "metformin": MEDICATION_OPTIONS[metformin],
                "insulin": MEDICATION_OPTIONS[insulin],
            }
        ]
    )

    try:
        risk_proba = predict_readmission_proba(pipeline, patient_data)
        explanations = explain_prediction(pipeline, patient_data, top_k=3)
    except Exception as exc:
        st.error(f"預測失敗：{exc}")
        st.stop()

    risk_percentage = round(risk_proba * 100, 2)
    threshold_percentage = round(risk_threshold * 100, 2)

    st.subheader("📊 AI 風險評估報告")

    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=risk_percentage,
            domain={"x": [0, 1], "y": [0, 1]},
            title={"text": "30 天內再入院風險機率 (%)", "font": {"size": 18}},
            gauge={
                "axis": {"range": [None, 100], "tickwidth": 1, "tickcolor": "darkblue"},
                "bar": {"color": "black"},
                "bgcolor": "white",
                "borderwidth": 2,
                "bordercolor": "gray",
                "steps": [
                    {"range": [0, threshold_percentage * 0.7], "color": "#2ecc71"},
                    {"range": [threshold_percentage * 0.7, threshold_percentage * 1.3], "color": "#f1c40f"},
                    {"range": [threshold_percentage * 1.3, 100], "color": "#e74c3c"},
                ],
            },
        )
    )
    st.plotly_chart(fig, use_container_width=True)

    if risk_proba >= risk_threshold:
        st.error(f"⚠️ **高風險警示（機率：{risk_percentage}%）**")
        st.warning(
            "【優化建議】該病患再入院風險偏高。"
            "建議個案管理師在出院後第 3 天與第 14 天安排電話追蹤，"
            "並確認其出院後的用藥順從性。"
        )
    else:
        st.success(f"✅ **低風險通過（機率：{risk_percentage}%）**")
        st.info(
            "【優化建議】該病患再入院風險較低，"
            "請維持常規出院衛教與常規回診預約即可。"
        )

    st.caption(f"高風險門檻依驗證集 Youden index 設定為 {threshold_percentage}%")

    st.divider()
    st.subheader("🔍 關鍵風險因子分析")
    st.write("以下為 SHAP 分析後，對本次預測影響最大的臨床特徵：")

    for item in explanations:
        sign = "+" if item["contribution"] > 0 else ""
        st.write(
            f"- **{item['label']}**：{item['direction']}再入院風險 "
            f"（SHAP 貢獻：{sign}{item['contribution']:.4f}）"
        )

if metrics:
    with st.expander("📈 模型評估摘要（測試集）"):
        if metrics.get("model_name"):
            st.write(f"- 最佳模型：`{metrics['model_name']}`")
        if metrics.get("feature_count"):
            st.write(f"- 特徵數量：`{metrics['feature_count']}`")
        st.write(f"- ROC-AUC：`{metrics['roc_auc']:.4f}`")
        if metrics.get("baseline_roc_auc") is not None:
            st.write(f"- v1 基線 ROC-AUC：`{metrics['baseline_roc_auc']:.4f}`")
        if metrics.get("improvement") is not None:
            st.write(f"- 提升幅度：`{metrics['improvement']:+.4f}`")
        st.write(f"- 建議風險門檻：`{metrics['optimal_threshold']:.4f}`")
        st.write(f"- 測試集樣本數：`{metrics['test_size']}`")
        report = metrics["classification_report"]
        st.write(
            f"- 30 天內再入院 — precision: `{report['30天內再入院']['precision']:.3f}`, "
            f"recall: `{report['30天內再入院']['recall']:.3f}`, "
            f"f1: `{report['30天內再入院']['f1-score']:.3f}`"
        )
