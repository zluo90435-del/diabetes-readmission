import base64

import streamlit as st
import streamlit.components.v1 as components
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
from src.what_if import WHAT_IF_SCENARIOS, apply_what_if_overrides, find_scenario
from src.pdf_report import generate_what_if_pdf


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


def build_patient_row(
    *,
    time_in_hospital,
    num_lab_procedures,
    num_procedures,
    num_medications,
    number_outpatient,
    number_emergency,
    number_inpatient,
    number_diagnoses,
    admission_type,
    discharge_disposition,
    admission_source,
    age,
    gender,
    race,
    max_glu,
    a1c_status,
    change_status,
    diabetes_med,
    metformin,
    insulin,
) -> dict:
    return {
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


def render_gauge(risk_percentage: float, threshold_percentage: float) -> go.Figure:
    return go.Figure(
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


def render_what_if_chart(
    baseline_pct: float,
    scenario_pct: float,
    scenario_label: str,
    threshold_pct: float,
) -> go.Figure:
    delta = round(scenario_pct - baseline_pct, 2)
    colors = ["#3498db", "#2ecc71" if scenario_pct < baseline_pct else "#e74c3c"]

    fig = go.Figure(
        data=[
            go.Bar(
                name="調藥前（目前）",
                x=["30 天再入院風險 (%)"],
                y=[baseline_pct],
                marker_color=colors[0],
                text=[f"{baseline_pct}%"],
                textposition="outside",
            ),
            go.Bar(
                name=f"調藥後（{scenario_label}）",
                x=["30 天再入院風險 (%)"],
                y=[scenario_pct],
                marker_color=colors[1],
                text=[f"{scenario_pct}%"],
                textposition="outside",
            ),
        ]
    )
    fig.add_hline(
        y=threshold_pct,
        line_dash="dash",
        line_color="#e67e22",
        annotation_text=f"高風險門檻 {threshold_pct}%",
    )
    fig.update_layout(
        title=f"What-If 模擬：風險變化 {delta:+.2f} 個百分點",
        barmode="group",
        yaxis={"range": [0, max(baseline_pct, scenario_pct, threshold_pct) * 1.25 + 5]},
        showlegend=True,
        height=420,
    )
    return fig


def _what_if_pdf_cache_key(
    scenario_id: str,
    patient_row: dict,
    baseline_pct: float,
    scenario_pct: float,
) -> tuple:
    return (
        scenario_id,
        baseline_pct,
        scenario_pct,
        tuple(sorted(patient_row.items())),
    )


def _clear_what_if_pdf_cache() -> None:
    st.session_state.pop("what_if_pdf_key", None)
    st.session_state.pop("what_if_pdf_bytes", None)


def render_pdf_download_link(pdf_bytes: bytes, filename: str) -> None:
    b64 = base64.b64encode(pdf_bytes).decode()
    components.html(
        f"""
        <a href="data:application/pdf;base64,{b64}" download="{filename}"
           style="display:inline-block;padding:0.45rem 1rem;background:#f0f2f6;
                  border:1px solid rgba(49,51,63,0.2);border-radius:0.5rem;
                  text-decoration:none;color:#31333f;font-family:sans-serif;
                  font-size:0.875rem;">
          📄 下載 PDF 報告
        </a>
        """,
        height=48,
    )


def render_risk_summary(risk_proba: float, risk_threshold: float) -> None:
    risk_percentage = round(risk_proba * 100, 2)
    threshold_percentage = round(risk_threshold * 100, 2)

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
threshold_percentage = round(risk_threshold * 100, 2)

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
    st.session_state.patient_row = build_patient_row(
        time_in_hospital=time_in_hospital,
        num_lab_procedures=num_lab_procedures,
        num_procedures=num_procedures,
        num_medications=num_medications,
        number_outpatient=number_outpatient,
        number_emergency=number_emergency,
        number_inpatient=number_inpatient,
        number_diagnoses=num_diagnoses,
        admission_type=admission_type,
        discharge_disposition=discharge_disposition,
        admission_source=admission_source,
        age=age,
        gender=gender,
        race=race,
        max_glu=max_glu,
        a1c_status=a1c_status,
        change_status=change_status,
        diabetes_med=diabetes_med,
        metformin=metformin,
        insulin=insulin,
    )
    st.session_state.selected_scenario_id = None
    _clear_what_if_pdf_cache()

if "patient_row" in st.session_state:
    patient_data = pd.DataFrame([st.session_state.patient_row])

    try:
        baseline_proba = predict_readmission_proba(pipeline, patient_data)
        explanations = explain_prediction(pipeline, patient_data, top_k=3)
    except Exception as exc:
        st.error(f"預測失敗：{exc}")
        st.stop()

    baseline_pct = round(baseline_proba * 100, 2)

    st.subheader("📊 AI 風險評估報告")
    st.plotly_chart(render_gauge(baseline_pct, threshold_percentage), use_container_width=True)
    render_risk_summary(baseline_proba, risk_threshold)

    st.divider()
    st.subheader("🔬 What-If 假設分析（調藥前 vs 調藥後）")
    st.write(
        "模擬「若採取以下醫療介入，30 天再入院風險可能如何變化」。"
        "點選快捷情境即可在同一圖表上對比調藥前後機率。"
    )

    scenario_cols = st.columns(len(WHAT_IF_SCENARIOS))
    for index, scenario in enumerate(WHAT_IF_SCENARIOS):
        with scenario_cols[index]:
            if st.button(scenario["label"], key=f"what_if_{scenario['id']}", use_container_width=True):
                st.session_state.selected_scenario_id = scenario["id"]
                _clear_what_if_pdf_cache()

    selected = find_scenario(st.session_state.get("selected_scenario_id", ""))
    if selected:
        scenario_row = apply_what_if_overrides(st.session_state.patient_row, selected["overrides"])
        scenario_data = pd.DataFrame([scenario_row])
        scenario_proba = predict_readmission_proba(pipeline, scenario_data)
        scenario_pct = round(scenario_proba * 100, 2)
        delta = round(scenario_pct - baseline_pct, 2)

        st.caption(selected["hint"])
        st.plotly_chart(
            render_what_if_chart(
                baseline_pct,
                scenario_pct,
                selected["label"],
                threshold_percentage,
            ),
            use_container_width=True,
        )

        if delta < 0:
            st.success(f"✅ 此介入預估可降低再入院風險 **{abs(delta):.2f}** 個百分點。")
        elif delta > 0:
            st.warning(f"⚠️ 此情境下模型預估風險上升 **{delta:.2f}** 個百分點，請綜合臨床判斷。")
        else:
            st.info("ℹ️ 此介入對模型預估風險影響不大。")

        pdf_cache_key = _what_if_pdf_cache_key(
            selected["id"],
            st.session_state.patient_row,
            baseline_pct,
            scenario_pct,
        )
        pdf_ready = (
            st.session_state.get("what_if_pdf_key") == pdf_cache_key
            and st.session_state.get("what_if_pdf_bytes")
        )

        st.caption("PDF 報告匯出")
        gen_col, dl_col = st.columns([1, 1])
        with gen_col:
            if st.button("📄 產生 PDF 報告", key="generate_what_if_pdf", type="secondary"):
                try:
                    with st.spinner("正在產生 PDF 報告..."):
                        st.session_state.what_if_pdf_bytes = generate_what_if_pdf(
                            patient_row=st.session_state.patient_row,
                            baseline_pct=baseline_pct,
                            scenario_pct=scenario_pct,
                            scenario_label=selected["label"],
                            scenario_hint=selected["hint"],
                            threshold_pct=threshold_percentage,
                            explanations=explanations,
                            model_name=metrics.get("model_name") if metrics else None,
                        )
                    st.session_state.what_if_pdf_key = pdf_cache_key
                    pdf_ready = True
                except Exception as exc:
                    _clear_what_if_pdf_cache()
                    st.error(f"PDF 產生失敗：{exc}")

        with dl_col:
            if pdf_ready:
                render_pdf_download_link(
                    st.session_state.what_if_pdf_bytes,
                    f"what_if_report_{selected['id']}.pdf",
                )
            else:
                st.caption("請先按「產生 PDF 報告」，完成後再下載。")
    else:
        st.info("👆 請點選上方快捷鍵，查看調藥前後的風險對比。")

    st.divider()
    st.subheader("🔍 關鍵風險因子分析（目前狀態）")
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
