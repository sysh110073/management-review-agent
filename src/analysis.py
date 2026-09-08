from pathlib import Path
import pandas as pd

REQUIRED_COLUMNS = [
    "period",
    "plant",
    "department",
    "revenue",
    "cost",
    "budget",
    "material_input",
    "material_loss",
    "headcount_start",
    "headcount_end",
    "leavers",
    "data_status",
    ]

NUMERIC_COLUMNS = [
    "revenue",
    "cost",
    "budget",
    "material_input",
    "material_loss",
    "headcount_start",
    "headcount_end",
    "leavers",
    ]


def load_kpi_data(path:str | Path) -> pd.DataFrame:
    """
    讀取月度 KPI CSV，並將欄位轉成後續分析可使用的類別。

    參數：
    path: monthly_kpi.csv 的檔案路徑。
    　　　可以傳入字串，例如　"data/raw/monthly_kpi.csv",
    　　　也可以傳入 pathlib.Path 物件。

    回傳：
    pd.DataFrame：
    - period 會被轉成每月第一天的 datetime 類別。
    - 金額、人數、材料等欄位會被轉成數值類別。
    - 尚未做資料品質判定，請接著呼叫 validate_kpi_data()。

    使用方式：
    df = load_kpi_data("data/raw/monthly_kpi.csv")
    """
    df = pd.read_csv(path)

    missing_columns = set(REQUIRED_COLUMNS) - set(df.columns)
    if missing_columns:
        raise ValueError(f"CSV 缺少必要的欄位: {sorted(missing_columns)}")

    df["period"] = pd.to_datetime(
        df["period"],
        format="%Y-%m",
        errors="coerce",
        )

    for column in NUMERIC_COLUMNS:
        df[column] = pd.to_numeric(df[column], errors="coerce")
    
    return df

def validate_kpi_data(df: pd.DataFrame) -> None:
    """
    驗證 KPI 原始資料是否符合資料字典與基本商業規則。

    參數：
        df:由 load_kpi_data() 讀取後的 DataFrame。

    回傳：
        無回傳值。
        若資料完全正確，函式正常結束。
        若資料有問題，會拋出 ValueError，並列出所有錯誤原因。

    檢查內容：
        1. 必要欄位是否存在。
        2. period、plant、department 是否缺值。
        3. 數值欄位是否無法轉成數字或為空值。
        4. period + plant + department 是否重複。
        5. 金額、人數、材料數量是否為負數。
        6. material_loss 是否大於 material_input。
        7. leavers 是否大於平均在職人數。
        8. data_status 是否為 closed 或 preliminary。

    使用方式：
        df = load_kpi_data("data/raw/monthly_kpi.csv")
        validate_kpi_data(df)
    """
    errors = []

    missing_columns = set(REQUIRED_COLUMNS) - set(df.columns)
    if missing_columns:
        errors.append(f"CSV 缺少必要的欄位: {sorted(missing_columns)}")

    if df.empty:
        errors.append("資料檔不可為空。")
    
    key_columns = ["period", "plant", "department"]
    if df[key_columns].isna().any().any():
        errors.append("period、plant、department 不可缺值。")

    if df[NUMERIC_COLUMNS].isna().any().any():
        missing_numeric = df[NUMERIC_COLUMNS].isna().any()
        columns = missing_numeric[missing_numeric].index.tolist()
        errors.append(f"數值欄位不可為空或無法轉換: {columns}")
    
    if df.duplicated(subset=key_columns).any():
        duplicated_rows = df.loc[
            df.duplicated(subset=key_columns, keep=False),
            key_columns,
        ]
        errors.append(
            "主鍵重複：period + plant + department 必須唯一。\n" +
            f"{duplicated_rows.to_string(index=False)}"
        )
    if (df[NUMERIC_COLUMNS] < 0).any().any():
        errors.append("金額、人數、材料數量不可為負數。")

    if (df["material_loss"] > df["material_input"]).any():
        errors.append("material_loss 不可大於 material_input。")

    average_headcount = (df["headcount_start"] + df["headcount_end"]) / 2
    if (df["leavers"] > average_headcount).any():
        errors.append("leavers 不可大於平均在職人數。")


    allowed_statuses = {"closed", "preliminary"}
    invalid_status = ~df["data_status"].isin(allowed_statuses)
    if invalid_status.any():
        invalid_values = df.loc[invalid_status, "data_status"].unique().tolist()
        errors.append(
            f"data_status 只能是 {sorted(allowed_statuses)}，"
            f"目前發現：{invalid_values}"
        )

    if errors:
        raise ValueError("資料品質檢查失敗：\n- " + "\n- ".join(errors))

def calculate_kpis(df: pd.DataFrame) -> pd.DataFrame:
    """
    根據 KPI 字典計算衍生指標，並標記零分母情況。

    參數：
        df：已通過 validate_kpi_data() 的原始 KPI DataFrame。

    回傳：
        新的 DataFrame，不會修改原始 df。
        會新增：
        - cost_rate
        - budget_variance
        - budget_variance_pct
        - turnover_rate
        - material_loss_rate
        - calculation_warnings

    零分母規則：
        若分母為 0，對應 KPI 回傳 NaN，
        並在 calculation_warnings 中標示 zero_denominator。

    使用方式：
        metrics_df = calculate_kpis(df)
    """
    result = df.copy()

    result["cost_rate"] = (
        result["cost"]
        .div(result["revenue"])
        .mul(100)
        .where(result["revenue"].ne(0))
    )

    result["budget_variance"] = result["revenue"] - result["budget"]

    result["budget_variance_pct"] = (
        result["budget_variance"]
        .div(result["budget"])
        .mul(100)
        .where(result["budget"].ne(0))
    )

    average_headcount = (
        result["headcount_start"] + result["headcount_end"]
    ) / 2

    result["turnover_rate"] = (
        result["leavers"]
        .div(average_headcount)
        .mul(100)
        .where(average_headcount.ne(0))
    )

    result["material_loss_rate"] = (
        result["material_loss"]
        .div(result["material_input"])
        .mul(100)
        .where(result["material_input"].ne(0))
    )

    warning_masks = {
        "zero_denominator:cost_rate": result["revenue"].eq(0),
        "zero_denominator:budget_variance_pct": result["budget"].eq(0),
        "zero_denominator:turnover_rate": average_headcount.eq(0),
        "zero_denominator:material_loss_rate": result["material_input"].eq(0),
    }

    result["calculation_warnings"] = pd.NA

    for warning, mask in warning_masks.items():
        existing_warning = result.loc[mask, "calculation_warnings"].fillna("")
        result.loc[mask, "calculation_warnings"] = existing_warning.apply(
            lambda value: warning if not value else f"{value},{warning}"
        )

    return result


def compare_to_budget(df: pd.DataFrame, period: str) -> pd.DataFrame:
    """
    依廠別彙總指定月份的營收與預算，計算預算差異。

    參數：
        df：已完成 calculate_kpis() 的 DataFrame。
        period：要查詢的月份，格式必須是 YYYY-MM，例如 "2026-09"。

    回傳：
        每個廠別一列的 DataFrame，包含：
        - revenue
        - budget
        - budget_variance
        - budget_variance_pct
        - source_rows
        - preliminary_rows
        - comparison_allowed
        - warning

    注意：
        若廠別資料中含有 preliminary，仍會保留數字，
        但 comparison_allowed 會是 False，不能直接做正式結論。

    使用方式：
        budget_result = compare_to_budget(metrics_df, "2026-09")
    """
    target_period = pd.to_datetime(period, format="%Y-%m")

    period_df = df.loc[df["period"].eq(target_period)].copy()

    if period_df.empty:
        raise ValueError(f"查無 {period} 的 KPI 資料。")

    result = (
        period_df.groupby("plant", as_index=False)
        .agg(
            revenue=("revenue", "sum"),
            budget=("budget", "sum"),
            source_rows=("department", "size"),
            preliminary_rows=(
                "data_status",
                lambda status: (status != "closed").sum(),
            ),
        )
    )

    result["budget_variance"] = result["revenue"] - result["budget"]
    result["budget_variance_pct"] = (
        result["budget_variance"]
        .div(result["budget"])
        .mul(100)
        .where(result["budget"].ne(0))
    )

    result["comparison_allowed"] = result["preliminary_rows"].eq(0)

    result["warning"] = pd.NA
    result.loc[
        result["budget"].eq(0),
        "warning",
    ] = "zero_denominator:budget_variance_pct"

    result.loc[
        ~result["comparison_allowed"],
        "warning",
    ] = "preliminary_data"

    return result.sort_values("budget_variance_pct").reset_index(drop=True)


def find_anomalies(df: pd.DataFrame, period: str) -> pd.DataFrame:
    """
    依 management_policy.md 的門檻找出指定月份的 KPI 異常。

    參數：
        df：已完成 calculate_kpis() 的 DataFrame。
        period：要分析的月份，格式必須是 YYYY-MM，例如 "2026-09"。

    回傳：
        異常清單 DataFrame，包含：
        - plant
        - department
        - metric_name
        - actual
        - threshold
        - severity
        - source
        - period

    判定門檻：
        - 預算差異率：小於 -5% 為 Warning，小於 -10% 為 Critical。
        - 成本率月增：上升 2 個百分點為 Warning，上升 5 個百分點為 Critical。
        - 離職率：大於 3% 為 Warning，大於 5% 為 Critical。
        - 材料耗損率：大於 3% 為 Warning，大於 5% 為 Critical。

    注意：
        preliminary 資料不納入正式異常結論。

    使用方式：
        anomalies = find_anomalies(metrics_df, "2026-09")
    """
    target_period = pd.to_datetime(period, format="%Y-%m")
    analysis_df = df.copy()

    previous_cost_rate = analysis_df[
        ["period", "plant", "department", "cost_rate"]
    ].copy()

    previous_cost_rate["period"] = (
        previous_cost_rate["period"] + pd.DateOffset(months=1)
    )

    previous_cost_rate = previous_cost_rate.rename(
        columns={"cost_rate": "previous_cost_rate"}
    )

    analysis_df = analysis_df.merge(
        previous_cost_rate,
        on=["period", "plant", "department"],
        how="left",
    )

    analysis_df["cost_rate_change_pp"] = (
        analysis_df["cost_rate"] - analysis_df["previous_cost_rate"]
    )

    scope = analysis_df.loc[
        analysis_df["period"].eq(target_period)
        & analysis_df["data_status"].eq("closed")
    ]

    if scope.empty:
        raise ValueError(f"查無可用於正式判定的 {period} closed 資料。")

    anomalies = []

    for row in scope.itertuples(index=False):
        lower_is_worse = [
            (
                "budget_variance_pct",
                row.budget_variance_pct,
                -5,
                -10,
            ),
        ]

        higher_is_worse = [
            (
                "cost_rate_change_pp",
                row.cost_rate_change_pp,
                2,
                5,
            ),
            (
                "turnover_rate",
                row.turnover_rate,
                3,
                5,
            ),
            (
                "material_loss_rate",
                row.material_loss_rate,
                3,
                5,
            ),
        ]

        for metric_name, actual, warning_threshold, critical_threshold in lower_is_worse:
            if pd.isna(actual):
                continue

            if actual <= critical_threshold:
                severity = "critical"
                threshold = critical_threshold
            elif actual <= warning_threshold:
                severity = "warning"
                threshold = warning_threshold
            else:
                continue

            anomalies.append(
                {
                    "period": period,
                    "plant": row.plant,
                    "department": row.department,
                    "metric_name": metric_name,
                    "actual": round(actual, 2),
                    "threshold": threshold,
                    "severity": severity,
                    "source": "monthly_kpi.csv",
                }
            )

        for metric_name, actual, warning_threshold, critical_threshold in higher_is_worse:
            if pd.isna(actual):
                continue

            if actual > critical_threshold:
                severity = "critical"
                threshold = critical_threshold
            elif actual > warning_threshold:
                severity = "warning"
                threshold = warning_threshold
            else:
                continue

            anomalies.append(
                {
                    "period": period,
                    "plant": row.plant,
                    "department": row.department,
                    "metric_name": metric_name,
                    "actual": round(actual, 2),
                    "threshold": threshold,
                    "severity": severity,
                    "source": "monthly_kpi.csv",
                }
            )

    return pd.DataFrame(anomalies)


if __name__ == "__main__":
    csv_path = Path("../data/raw/monthly_kpi.csv")

    kpi_df = load_kpi_data(csv_path)
    validate_kpi_data(kpi_df)

    metrics_df = calculate_kpis(kpi_df)
    budget_result = compare_to_budget(metrics_df, "2026-09")
    anomalies_result = find_anomalies(metrics_df, "2026-09")

    assert not budget_result.empty
    assert not anomalies_result.empty

    print("\n=== 各廠預算差異 ===")
    print(
        budget_result[
            [
                "plant",
                "revenue",
                "budget",
                "budget_variance",
                "budget_variance_pct",
                "comparison_allowed",
                "warning",
            ]
        ].to_string(index=False)
    )

    print("\n=== 異常 KPI ===")
    print(anomalies_result.to_string(index=False))