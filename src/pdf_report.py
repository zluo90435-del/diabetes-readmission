from __future__ import annotations

import urllib.request
from datetime import datetime
from io import BytesIO
from pathlib import Path

import img2pdf
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt

from src.config import FEATURE_LABELS, PROJECT_ROOT

FONT_DIR = PROJECT_ROOT / "assets" / "fonts"
FONT_FILE = FONT_DIR / "NotoSansCJKtc-Regular.otf"
FONT_URL = (
    "https://cdn.jsdelivr.net/gh/googlefonts/noto-cjk@main/Sans/OTF/TraditionalChinese/"
    "NotoSansCJKtc-Regular.otf"
)
FONT_CANDIDATES = [
    FONT_FILE,
    Path("C:/Windows/Fonts/msjh.ttc"),
    Path("C:/Windows/Fonts/msyh.ttc"),
    Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
    Path("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc"),
]


def _ensure_font_path() -> Path:
    for candidate in FONT_CANDIDATES:
        if candidate.exists():
            return candidate

    FONT_DIR.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(FONT_URL, FONT_FILE)
    return FONT_FILE


def _font_prop(font_path: Path) -> fm.FontProperties:
    return fm.FontProperties(fname=str(font_path))


def _format_delta_text(delta: float) -> str:
    if delta < 0:
        return f"此介入預估可降低再入院風險 {abs(delta):.2f} 個百分點。"
    if delta > 0:
        return f"此情境下模型預估風險上升 {delta:.2f} 個百分點，請綜合臨床判斷。"
    return "此介入對模型預估風險影響不大。"


def _figure_to_png(fig: plt.Figure) -> bytes:
    buffer = BytesIO()
    fig.savefig(buffer, format="png", dpi=160, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    buffer.seek(0)
    return buffer.getvalue()


def _render_summary_png(
    *,
    font_path: Path,
    baseline_pct: float,
    scenario_pct: float,
    scenario_label: str,
    scenario_hint: str,
    threshold_pct: float,
    delta: float,
    patient_row: dict,
    explanations: list[dict],
    model_name: str | None,
) -> bytes:
    fp = _font_prop(font_path)
    fig = plt.figure(figsize=(8.27, 11.69))
    fig.patch.set_facecolor("white")
    y = 0.94
    line_height = 0.035

    def write_line(text: str, size: int = 11, weight: str = "normal") -> None:
        nonlocal y
        fig.text(
            0.08,
            y,
            text,
            fontsize=size,
            fontweight=weight,
            fontproperties=fp,
            wrap=True,
        )
        y -= line_height

    write_line("糖尿病患 30 天內再入院風險評估報告", size=16, weight="bold")
    write_line(f"報告產生時間：{datetime.now().strftime('%Y-%m-%d %H:%M')}", size=10)
    write_line("What-If 假設分析摘要", size=13, weight="bold")
    y -= 0.01

    write_line(f"模擬情境：{scenario_label}")
    write_line(f"情境說明：{scenario_hint}")
    write_line(f"調藥前風險：{baseline_pct:.2f}%")
    write_line(f"調藥後風險：{scenario_pct:.2f}%")
    write_line(f"風險變化：{delta:+.2f} 個百分點")
    write_line(f"高風險門檻：{threshold_pct:.2f}%")
    write_line(f"分析結論：{_format_delta_text(delta)}")
    if model_name:
        write_line(f"使用模型：{model_name}")

    y -= 0.01
    write_line("患者主要輸入特徵", size=12, weight="bold")
    display_fields = [
        "age",
        "gender",
        "time_in_hospital",
        "number_inpatient",
        "number_emergency",
        "change",
        "metformin",
        "insulin",
        "A1Cresult",
    ]
    for field in display_fields:
        label = FEATURE_LABELS.get(field, field)
        write_line(f"- {label}：{patient_row.get(field, '-')}")

    y -= 0.01
    write_line("SHAP 關鍵風險因子（目前狀態）", size=12, weight="bold")
    for item in explanations:
        sign = "+" if item["contribution"] > 0 else ""
        write_line(
            f"- {item['label']}：{item['direction']}再入院風險 "
            f"(SHAP {sign}{item['contribution']:.4f})"
        )

    y -= 0.01
    write_line(
        "免責聲明：本報告僅供研究與臨床輔助參考，不能取代醫師診斷。"
        "What-If 為情境模擬，非因果推論。",
        size=9,
    )

    return _figure_to_png(fig)


def _render_chart_png(
    *,
    font_path: Path,
    baseline_pct: float,
    scenario_pct: float,
    scenario_label: str,
    threshold_pct: float,
    delta: float,
) -> bytes:
    fp = _font_prop(font_path)
    plt.rcParams["axes.unicode_minus"] = False

    fig, ax = plt.subplots(figsize=(8.27, 6))
    labels = ["調藥前（目前）", f"調藥後（{scenario_label}）"]
    values = [baseline_pct, scenario_pct]
    colors = ["#3498db", "#2ecc71" if scenario_pct < baseline_pct else "#e74c3c"]

    bars = ax.bar(labels, values, color=colors, width=0.55)
    ax.axhline(
        threshold_pct,
        color="#e67e22",
        linestyle="--",
        linewidth=1.5,
        label="高風險門檻",
    )

    ax.set_ylabel("30 天再入院風險 (%)", fontproperties=fp)
    ax.set_title(
        f"What-If 模擬：風險變化 {delta:+.2f} 個百分點",
        fontproperties=fp,
    )
    ax.set_ylim(0, max(values + [threshold_pct]) * 1.25 + 5)
    ax.legend(prop=fp)
    ax.grid(axis="y", alpha=0.25)

    for label in ax.get_xticklabels():
        label.set_fontproperties(fp)
    for label in ax.get_yticklabels():
        label.set_fontproperties(fp)

    for bar, value in zip(bars, values, strict=False):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.8,
            f"{value:.2f}%",
            ha="center",
            va="bottom",
            fontsize=11,
            fontproperties=fp,
        )

    return _figure_to_png(fig)


def generate_what_if_pdf(
    *,
    patient_row: dict,
    baseline_pct: float,
    scenario_pct: float,
    scenario_label: str,
    scenario_hint: str,
    threshold_pct: float,
    explanations: list[dict],
    model_name: str | None = None,
) -> bytes:
    font_path = _ensure_font_path()
    delta = round(scenario_pct - baseline_pct, 2)

    summary_png = _render_summary_png(
        font_path=font_path,
        baseline_pct=baseline_pct,
        scenario_pct=scenario_pct,
        scenario_label=scenario_label,
        scenario_hint=scenario_hint,
        threshold_pct=threshold_pct,
        delta=delta,
        patient_row=patient_row,
        explanations=explanations,
        model_name=model_name,
    )
    chart_png = _render_chart_png(
        font_path=font_path,
        baseline_pct=baseline_pct,
        scenario_pct=scenario_pct,
        scenario_label=scenario_label,
        threshold_pct=threshold_pct,
        delta=delta,
    )

    return img2pdf.convert(summary_png, chart_png)
