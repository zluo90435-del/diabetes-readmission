AGE_OPTIONS = [
    "[0-10)",
    "[10-20)",
    "[20-30)",
    "[30-40)",
    "[40-50)",
    "[50-60)",
    "[60-70)",
    "[70-80)",
    "[80-90)",
    "[90-100)",
]

CHANGE_OPTIONS = {
    "有變動 (Ch)": "Ch",
    "無變動 (No)": "No",
}

A1C_OPTIONS = {
    "未檢測 (None)": "None",
    "正常 (Norm)": "Norm",
    "大於 7% (>7)": ">7",
    "大於 8% (>8)": ">8",
}

GENDER_OPTIONS = {
    "女性 (Female)": "Female",
    "男性 (Male)": "Male",
}

RACE_OPTIONS = {
    "白人 (Caucasian)": "Caucasian",
    "非裔 (AfricanAmerican)": "AfricanAmerican",
    "Hispanic": "Hispanic",
    "亞裔 (Asian)": "Asian",
    "其他 (Other)": "Other",
    "未知 (?)": "?",
}

MAX_GLU_OPTIONS = {
    "未檢測 (None)": "None",
    "正常 (Norm)": "Norm",
    "大於 200 (>200)": ">200",
    "大於 300 (>300)": ">300",
}

MEDICATION_OPTIONS = {
    "未使用 (No)": "No",
    "維持 (Steady)": "Steady",
    "加量 (Up)": "Up",
    "減量 (Down)": "Down",
}

ADMISSION_TYPE_OPTIONS = {
    "急診 (1)": 1,
    "緊急 (2)": 2,
    "排程/擇期 (3)": 3,
    "新borns (4)": 4,
    "其他 (5)": 5,
    "NULL (6)": 6,
    "外傷中心 (7)": 7,
}

DISCHARGE_DISPOSITION_OPTIONS = {
    "回家/自癒 (1)": 1,
    "轉院 (2)": 2,
    "轉 SNF (3)": 3,
    "臨終關懷 (6)": 6,
    "其他 (18)": 18,
    "過世 (11)": 11,
    "長期照護 (4)": 4,
}

ADMISSION_SOURCE_OPTIONS = {
    "轉診/醫師 (1)": 1,
    "診所 (2)": 2,
    "轉院 (4)": 4,
    "急診 (7)": 7,
    "其他 (17)": 17,
}
