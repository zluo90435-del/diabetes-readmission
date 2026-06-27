WHAT_IF_SCENARIOS = [
    {
        "id": "adjust_diabetes_meds",
        "label": "💊 調整糖尿病用藥",
        "hint": "將用藥狀態改為「本次住院有調藥」",
        "overrides": {"change": "Ch"},
    },
    {
        "id": "start_insulin",
        "label": "💉 啟用 Insulin",
        "hint": "新增 Insulin 並維持劑量",
        "overrides": {"insulin": "Steady", "diabetesMed": "Yes"},
    },
    {
        "id": "metformin_up",
        "label": "📈 Metformin 加量",
        "hint": "Metformin 調升劑量",
        "overrides": {"metformin": "Up", "diabetesMed": "Yes"},
    },
    {
        "id": "a1c_norm",
        "label": "🩸 A1C 改善為正常",
        "hint": "糖化血色素由異常/未檢測改為正常",
        "overrides": {"A1Cresult": "Norm"},
    },
    {
        "id": "comprehensive",
        "label": "✨ 綜合出院優化",
        "hint": "調藥 + Insulin + A1C 改善（綜合介入）",
        "overrides": {
            "change": "Ch",
            "insulin": "Steady",
            "metformin": "Up",
            "diabetesMed": "Yes",
            "A1Cresult": "Norm",
        },
    },
]


def apply_what_if_overrides(patient_row: dict, overrides: dict) -> dict:
    return {**patient_row, **overrides}


def find_scenario(scenario_id: str) -> dict | None:
    for scenario in WHAT_IF_SCENARIOS:
        if scenario["id"] == scenario_id:
            return scenario
    return None
