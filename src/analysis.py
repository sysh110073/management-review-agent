from pathlib import Path
from html import escape
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


def compare_cost_rate_to_previous_month(
    df: pd.DataFrame,
    period: str,
) -> pd.DataFrame:
    """比較指定月份各廠成本率與真正上個月的差異。

    先將同一廠的成本與營收加總，再計算成本率，避免直接平均部門
    百分比造成加權錯誤。函式會明確以目標月份減一個月取得基準期，
    所以資料缺少某個月時，不會把上一筆資料誤認成「上個月」。

    參數：
        df：已完成 calculate_kpis() 的 DataFrame。
        period：要分析的月份，格式為 YYYY-MM，例如 "2026-09"。

    回傳：
        每個廠別一列，包含本月與上月的成本、營收、成本率、成本率
        差異（百分點）、資料狀態與警告。

    """
    target_period = pd.to_datetime(period, format="%Y-%m")
    previous_period = target_period - pd.DateOffset(months=1)

    scope = df.loc[df["period"].isin([target_period, previous_period])].copy()
    if target_period not in set(scope["period"]):
        raise ValueError(f"查無 {period} 的 KPI 資料。")

    plant_monthly = (
        scope.groupby(["period", "plant"], as_index=False)
        .agg(
            revenue=("revenue", "sum"),
            cost=("cost", "sum"),
            source_rows=("department", "size"),
            preliminary_rows=(
                "data_status",
                lambda status: (status != "closed").sum(),
            ),
        )
    )
    plant_monthly["cost_rate"] = (
        plant_monthly["cost"]
        .div(plant_monthly["revenue"])
        .mul(100)
        .where(plant_monthly["revenue"].ne(0))
    )

    current = plant_monthly.loc[
        plant_monthly["period"].eq(target_period)
    ].copy()
    previous = plant_monthly.loc[
        plant_monthly["period"].eq(previous_period)
    ].copy()

    current = current.rename(
        columns={
            "revenue": "current_revenue",
            "cost": "current_cost",
            "source_rows": "current_source_rows",
            "preliminary_rows": "current_preliminary_rows",
            "cost_rate": "current_cost_rate",
        }
    )
    previous = previous.rename(
        columns={
            "revenue": "previous_revenue",
            "cost": "previous_cost",
            "source_rows": "previous_source_rows",
            "preliminary_rows": "previous_preliminary_rows",
            "cost_rate": "previous_cost_rate",
        }
    ).drop(columns="period")

    result = current.merge(
        previous,
        on="plant",
        how="left",
        validate="one_to_one",
    )
    result["previous_period"] = previous_period.strftime("%Y-%m")
    result["cost_rate_change_pp"] = (
        result["current_cost_rate"] - result["previous_cost_rate"]
    )
    result["comparison_allowed"] = (
        result["current_preliminary_rows"].eq(0)
        & result["previous_preliminary_rows"].eq(0)
        & result["previous_cost_rate"].notna()
    )

    result["warning"] = pd.NA
    result.loc[
        result["previous_cost_rate"].isna(),
        "warning",
    ] = "missing_previous_period"
    result.loc[
        result["current_cost_rate"].isna()
        | (
            result["previous_cost_rate"].isna()
            & result["previous_revenue"].notna()
        ),
        "warning",
    ] = "zero_denominator:cost_rate"
    result.loc[
        result["current_preliminary_rows"].gt(0)
        | result["previous_preliminary_rows"].gt(0),
        "warning",
    ] = "preliminary_data"

    return result.sort_values(
        "cost_rate_change_pp",
        ascending=False,
        na_position="last",
    ).reset_index(drop=True)


def compare_cost_rate_to_previous_year(
    df: pd.DataFrame,
    period: str,
) -> pd.DataFrame:
    """比較指定月份各廠成本率與去年同期的差異。

    去年同期是「相同月、前一年」，例如 2026-09 的基準期是
    2025-09。這和上個月比較不同，不能因為資料缺漏就改用最近
    一筆資料。成本率一律由加總後的成本除以加總後的營收計算。

    """
    target_period = pd.to_datetime(period, format="%Y-%m")
    previous_year_period = target_period - pd.DateOffset(years=1)

    scope = df.loc[
        df["period"].isin([target_period, previous_year_period])
    ].copy()
    if target_period not in set(scope["period"]):
        raise ValueError(f"查無 {period} 的 KPI 資料。")

    plant_monthly = (
        scope.groupby(["period", "plant"], as_index=False)
        .agg(
            revenue=("revenue", "sum"),
            cost=("cost", "sum"),
            source_rows=("department", "size"),
            preliminary_rows=(
                "data_status",
                lambda status: (status != "closed").sum(),
            ),
        )
    )
    plant_monthly["cost_rate"] = (
        plant_monthly["cost"]
        .div(plant_monthly["revenue"])
        .mul(100)
        .where(plant_monthly["revenue"].ne(0)) #當營收不等於 0 時，保留計算結果；如果營收是 0，就把結果變成 NaN
    )

    current = plant_monthly.loc[
        plant_monthly["period"].eq(target_period)
    ].copy()
    previous_year = plant_monthly.loc[
        plant_monthly["period"].eq(previous_year_period)
    ].copy()

    current = current.rename(
        columns={
            "revenue": "current_revenue",
            "cost": "current_cost",
            "source_rows": "current_source_rows",
            "preliminary_rows": "current_preliminary_rows",
            "cost_rate": "current_cost_rate",
        }
    )
    previous_year = previous_year.rename(
        columns={
            "revenue": "previous_year_revenue",
            "cost": "previous_year_cost",
            "source_rows": "previous_year_source_rows",
            "preliminary_rows": "previous_year_preliminary_rows",
            "cost_rate": "previous_year_cost_rate",
        }
    ).drop(columns="period")

    result = current.merge(
        previous_year,
        on="plant",
        how="left",
        validate="one_to_one",
    )
    result["previous_year_period"] = previous_year_period.strftime("%Y-%m")
    result["cost_rate_yoy_change_pp"] = (
        result["current_cost_rate"] - result["previous_year_cost_rate"]
    )
    result["comparison_allowed"] = (
        result["current_preliminary_rows"].eq(0)
        & result["previous_year_preliminary_rows"].eq(0)
        & result["previous_year_cost_rate"].notna()
    )

    # 打上警告標籤
    result["warning"] = pd.NA  #先做初始化(發空白表格)

    # 標記缺少去年的資料 .loc[條件,更新的column] = 新帶入的值
    result.loc[
        result["previous_year_cost_rate"].isna(),
        "warning",
    ] = "missing_previous_year_period"

    # 標記 分母為0 這邊用了 或的條件 |
    # 今年的成本率是空的。去年的成本率是空的，**而且（&）**去年的營收不是空的。
    result.loc[
        result["current_cost_rate"].isna()
        | (
            result["previous_year_cost_rate"].isna()
            & result["previous_year_revenue"].notna()
        ),
        "warning",
    ] = "zero_denominator:cost_rate"

    # 標記 包含暫定/初版資料 (最高優先級)
    # .gt是greater than
    result.loc[
        result["current_preliminary_rows"].gt(0)
        | result["previous_year_preliminary_rows"].gt(0),
        "warning",
    ] = "preliminary_data"

    # 總結warning欄位中會有以下四種結果：
    # pd.NA：完全正常。
    #"missing_previous_year_period"：單純缺去年資料。
    #"zero_denominator:cost_rate"：營收為 0 導致算不出比率。
    #"preliminary_data"：最嚴重的警告，代表資料還不是最終版，看報表的人要注意。

    return result.sort_values(
        "cost_rate_yoy_change_pp",
        ascending=False,
        na_position="last",
    ).reset_index(drop=True)


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

def get_three_month_cost_rate_trend(
    df: pd.DataFrame,
    period: str,
    ) -> pd.DataFrame:
    """
    功能：
        取得目標月份與前兩個月的廠別成本率資料。

    參數：
        df (pd.DataFrame)：
            已經完成 calculate_kpis() 的 KPI 資料。
        period (str)：
            目標月份，格式為 YYYY-MM，例如 "2026-09"。

    回傳：
        pd.DataFrame：
            每個廠別、每個月份一列，包含：
            - period：月份
            - plant：廠別
            - revenue：該廠當月加總營收
            - cost：該廠當月加總成本
            - source_rows：彙總前的部門資料筆數
            - preliminary_rows：尚未關帳的資料筆數
            - cost_rate：成本率，公式為 cost / revenue * 100

    例外／警告：
        若營收為 0，cost_rate 會是 NaN，不會產生無限大數字。

    使用範例：
        three_month_df = get_three_month_cost_rate_trend(
            metrics_df,
            "2026-09",
        )
    """
    target_period = pd.to_datetime(period, format="%Y-%m")
    start_period = target_period - pd.DateOffset(months=2)

    scope = df.loc[
        df["period"].between(start_period, target_period)
    ].copy()


    # 把部門資料彙總成「每廠每月一列」
    plant_monthly = (
        scope.groupby(
            ["period", "plant"],
            as_index=False,
        ).agg(
            revenue = ("revenue", "sum"),
            cost = ("cost", "sum"),
            source_rows = ("department", "size"),
            preliminary_rows = (
                "data_status",
                lambda status: (status != "closed").sum(),
            ),
        )
    )

    plant_monthly["cost_rate"] = (
        plant_monthly["cost"]
        .div(plant_monthly["revenue"])
        .mul(100)
        .where(plant_monthly["revenue"].ne(0))
    )

    return plant_monthly

def summarize_three_month_cost_rate_trend(
    plant_monthly: pd.DataFrame,
    period: str,
) -> pd.DataFrame:
    """
    功能：
        將三個月的廠別成本率明細整理成每廠一列的趨勢摘要。

    參數：
        plant_monthly (pd.DataFrame)：
            get_three_month_cost_rate_trend() 回傳的資料。
        period (str)：
            目標月份，格式為 YYYY-MM，例如 "2026-09"。

    回傳：
        pd.DataFrame：
            每個廠別一列，包含三個月成本率、成本率變化、
            趨勢判定、是否允許比較與警告原因。

    規則：
        - 目標月成本率比第一個月高超過 2 個百分點：
          trend_status 為 "deteriorating"。
        - 低超過 2 個百分點：
          trend_status 為 "improving"。
        - 其餘為 "stable"。
        - 任一月份為 preliminary、缺少月份、營收為 0：
          trend_status 為 "not_assessed"。
    """

    target_period = pd.to_datetime(period, format="%Y-%m")
    start_period = target_period - pd.DateOffset(months=2)

    expected_periods = pd.date_range(
        start = start_period,
        end = target_period,
        freq = "MS",
    )

    # 把「 一廠每月一列 」 轉成 「 一廠一列、每月一欄 」
    rate_wide = (
        plant_monthly.pivot(
            index="plant",
            columns="period",
            values="cost_rate",
        ).reindex(columns=expected_periods)
    )

    # 用來檢查某月是否營收為0
    revenue_wide = (
        plant_monthly.pivot(
            index="plant",
            columns="period",
            values="revenue",
        ).reindex(columns=expected_periods)
    )

    # 用來檢查是否有 preliminary 資料
    preliminary_wide = (
        plant_monthly.pivot(
            index="plant",
            columns="period",
            values="preliminary_rows",
        )
        .reindex(columns=expected_periods)
    )

    result = rate_wide.reset_index()

    result.columns = [
        "plant",
        "cost_rate_month_1",
        "cost_rate_month_2",
        "cost_rate_month_3",
    ]

    result["cost_rate_change_pp"] = (
        result["cost_rate_month_3"]
        - result["cost_rate_month_1"]
    )


    # to_numpy()的用處在於只顯示True或False資訊就好
    # array([True, False, True])
    missing_period = rate_wide.isna().any(axis=1).to_numpy()
    zero_revenue = revenue_wide.eq(0).any(axis=1).to_numpy()
    preliminary_data = preliminary_wide.gt(0).any(axis=1).to_numpy()

    # 沒有任何缺失的資料為主
    result["comparison_allowed"] = (
        ~missing_period
        & ~zero_revenue
        & ~preliminary_data
    )

    result["warning"] = pd.NA

    result.loc[
        missing_period,
        "warning",
    ] = "missing_trend_period"

    result.loc[
        zero_revenue,
        "warning",
    ] = "zero_denominator:cost_rate"

    result.loc[
        preliminary_data,
        "warning",
    ] = "preliminary_data"

    # 先預設為不判定，只有可比較資料才給正式趨勢
    result["trend_status"] = "not_assessed"

    eligible = result["comparison_allowed"]

    result.loc[
        eligible,
        "trend_status",
    ] = "stable"

    result.loc[
        eligible & result["cost_rate_change_pp"].gt(2),
        "trend_status",
    ] = "deteriorating"

    result.loc[
        eligible & result["cost_rate_change_pp"].lt(-2),
        "trend_status",
    ] = "improving"

    return result.sort_values(
        "cost_rate_change_pp",
        ascending=False,
        na_position="last",
    ).reset_index(drop=True)


# 水平比較：同月份各廠排名
def rank_plants_by_metric(
    df: pd.DataFrame,
    period: str,
    metric_name: str,
    ascending: bool = False,
) -> pd.DataFrame:
    """
    功能：
        比較指定月份不同廠別的 KPI，並建立正式排名。

    參數：
        df (pd.DataFrame)：
            已完成 calculate_kpis() 的 KPI 資料。
        period (str)：
            要分析的月份，格式為 YYYY-MM，例如 "2026-09"。
        metric_name (str)：
            欲排名的指標，只能是：
            - "revenue"
            - "cost_rate"
            - "budget_variance_pct"
        ascending (bool)：
            排名方向。
            False 代表數值越大排名越前面。
            True 代表數值越小排名越前面。

    回傳：
        pd.DataFrame：
            每個廠別一列，包含：
            - plant
            - metric_name
            - metric_value
            - metric_rank
            - comparison_allowed
            - warning

    例外／警告：
        - 若沒有指定月份資料，會拋出 ValueError。
        - 含 preliminary 資料的廠別不列入正式排名。
        - 成本率或預算差異率遇到分母為 0 時不列入排名。
    """
    allowed_metrics = {
        "revenue",
        "cost_rate",
        "budget_variance_pct",
    }

    if metric_name not in allowed_metrics:
        raise ValueError(
            f"metric_name 必須是以下其中一種："
            f"{sorted(allowed_metrics)}"
        )

    target_period = pd.to_datetime(period, format="%Y-%m")

    period_df = df.loc[
        df["period"].eq(target_period)
    ].copy()

    if period_df.empty:
        raise ValueError(f"查無 {period} 的 KPI 資料。")

    # 先彙總成「每個廠一列」，避免直接平均部門百分比
    result = (
        period_df.groupby("plant", as_index=False)
        .agg(
            revenue=("revenue", "sum"),
            cost=("cost", "sum"),
            budget=("budget", "sum"),
            source_rows=("department", "size"),
            preliminary_rows=(
                "data_status",
                lambda status: (status != "closed").sum(),
            ),
        )
    )

    result["cost_rate"] = (
        result["cost"]
        .div(result["revenue"])
        .mul(100)
        .where(result["revenue"].ne(0))
    )

    result["budget_variance_pct"] = (
        (result["revenue"] - result["budget"])
        .div(result["budget"])
        .mul(100)
        .where(result["budget"].ne(0))
    )

    # 將使用者指定的 KPI 複製成統一欄位，後面比較方便
    result["metric_name"] = metric_name
    result["metric_value"] = result[metric_name]

    result["comparison_allowed"] = (
        result["preliminary_rows"].eq(0)
        & result["metric_value"].notna()
    )

    result["warning"] = pd.NA

    if metric_name == "cost_rate":
        result.loc[
            result["revenue"].eq(0),
            "warning",
        ] = "zero_denominator:cost_rate"

    if metric_name == "budget_variance_pct":
        result.loc[
            result["budget"].eq(0),
            "warning",
        ] = "zero_denominator:budget_variance_pct"

    # preliminary 的優先度最高，覆蓋前面的 warning
    result.loc[
        result["preliminary_rows"].gt(0),
        "warning",
    ] = "preliminary_data"

    # 只有正式可比較的資料才有排名
    result["metric_rank"] = pd.NA

    eligible = result["comparison_allowed"]

    result.loc[
        eligible,
        "metric_rank",
    ] = (
        result.loc[eligible, "metric_value"]
        .rank(
            method="min",
            ascending=ascending,
        )
        .astype("Int64")
    )

    return result.sort_values(
        "metric_rank",
        na_position="last",
    ).reset_index(drop=True)


def load_incident_data(path: str | Path) -> pd.DataFrame:
    """讀取事件資料並驗證事件明細所需的欄位。

    參數：
        path：incident.csv 的檔案路徑。

    回傳：
        date 已轉為 datetime 的事件 DataFrame。

    例外：
        CSV 缺少必要欄位或日期無法解析時，拋出 ValueError。
    """
    incidents = pd.read_csv(path)
    required_columns = {
        "date", "plant", "incident_type", "severity", "description", "status",
    }
    missing_columns = required_columns - set(incidents.columns)
    if missing_columns:
        raise ValueError(f"事件 CSV 缺少必要欄位: {sorted(missing_columns)}")

    incidents["date"] = pd.to_datetime(
        incidents["date"],
        format="%Y-%m-%d",
        errors="coerce",
    )
    if incidents["date"].isna().any():
        raise ValueError("事件 CSV 含有無法解析的日期。")

    return incidents


def get_incident_details(
    incidents: pd.DataFrame,
    plant: str,
    period: str,
) -> pd.DataFrame:
    """取得指定廠別與月份的事件，作為待查證的異常線索。

    參數：
        incidents：load_incident_data() 回傳的資料。
        plant：廠別名稱。
        period：查詢月份，格式為 YYYY-MM。

    回傳：
        同廠、同月份的事件清單，額外包含 source 與 query_period。

    注意：
        事件是相關線索，不代表已確認的 KPI 異常根因。
    """
    target_period = pd.Period(period, freq="M")
    result = incidents.loc[
        incidents["plant"].eq(plant)
        & incidents["date"].dt.to_period("M").eq(target_period)
    ].copy()
    result["source"] = "incident.csv"
    result["query_period"] = period

    return result.sort_values("date").reset_index(drop=True)


def add_z_score_anomaly(
    df: pd.DataFrame,
    period: str,
    metric_name: str,
    threshold: float = 2.0,
) -> pd.DataFrame:
    """以 z-score 標記指定月份的統計異常，作為業務門檻的輔助。

    參數：
        df：已完成 calculate_kpis() 的 DataFrame。
        period：分析月份，格式為 YYYY-MM。
        metric_name：數值指標欄位，例如 material_loss_rate。
        threshold：z-score 絕對值門檻，預設為 2.0。

    回傳：
        已關帳資料，包含 z_score、statistical_anomaly 與
        statistical_warning。

    例外：
        指標不存在、門檻不正確或無已關帳資料時，拋出 ValueError。
    """
    if metric_name not in df.columns:
        raise ValueError(f"找不到指標欄位: {metric_name}")
    if threshold <= 0:
        raise ValueError("threshold 必須大於 0。")

    target_period = pd.to_datetime(period, format="%Y-%m")
    result = df.loc[
        df["period"].eq(target_period) & df["data_status"].eq("closed")
    ].copy()
    if result.empty:
        raise ValueError(f"查無 {period} 的 closed 資料。")

    standard_deviation = result[metric_name].std(ddof=0)
    result["z_score"] = pd.NA
    result["statistical_warning"] = pd.NA

    if pd.isna(standard_deviation) or standard_deviation == 0:
        result["statistical_warning"] = "insufficient_variation"
    else:
        result["z_score"] = (
            result[metric_name] - result[metric_name].mean()
        ) / standard_deviation

    result["statistical_anomaly"] = (
        result["z_score"].abs().ge(threshold).fillna(False)
    )
    result["statistical_threshold"] = threshold

    return result.sort_values(
        "z_score",
        key=lambda values: values.abs(),
        ascending=False,
        na_position="last",
    ).reset_index(drop=True)


def generate_cost_rate_trend_chart(
    plant_monthly: pd.DataFrame,
    output_path: str | Path,
    data_as_of: str,
) -> Path:
    """產生三個月各廠成本率趨勢 SVG 圖表。

    參數：
        plant_monthly：get_three_month_cost_rate_trend() 的回傳資料。
        output_path：輸出 SVG 檔案位置。
        data_as_of：資料截至日期或時間，顯示於圖表上。

    回傳：
        已建立的 SVG 檔案 Path。
    """
    required_columns = {"period", "plant", "cost_rate"}
    missing_columns = required_columns - set(plant_monthly.columns)
    if missing_columns:
        raise ValueError(f"趨勢資料缺少欄位: {sorted(missing_columns)}")

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    chart_data = plant_monthly.dropna(subset=["cost_rate"]).copy()
    periods = sorted(chart_data["period"].unique())
    plants = sorted(chart_data["plant"].unique())
    if not periods or not plants:
        raise ValueError("沒有可繪製的成本率資料。")

    width, height = 900, 520
    left, right, top, bottom = 90, 40, 90, 90
    values = chart_data["cost_rate"]
    y_min = min(0, float(values.min()) - 5)
    y_max = float(values.max()) + 5
    y_range = y_max - y_min or 1
    x_positions = {
        period: left + index * (width - left - right) / max(1, len(periods) - 1)
        for index, period in enumerate(periods)
    }
    colors = ["#2563eb", "#dc2626", "#16a34a", "#9333ea"]

    def y_position(value: float) -> float:
        return top + (y_max - value) * (height - top - bottom) / y_range

    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        '<text x="450" y="32" text-anchor="middle" font-size="20" font-family="Arial">各廠三個月成本率趨勢</text>',
        f'<text x="450" y="58" text-anchor="middle" font-size="12" font-family="Arial">單位：%　資料截至：{escape(data_as_of)}</text>',
        f'<line x1="{left}" y1="{height-bottom}" x2="{width-right}" y2="{height-bottom}" stroke="#333"/>',
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{height-bottom}" stroke="#333"/>',
    ]
    for index in range(6):
        value = y_min + y_range * index / 5
        y = y_position(value)
        svg.append(f'<line x1="{left}" y1="{y:.1f}" x2="{width-right}" y2="{y:.1f}" stroke="#e5e7eb"/>')
        svg.append(f'<text x="{left-10}" y="{y+4:.1f}" text-anchor="end" font-size="12" font-family="Arial">{value:.1f}</text>')
    for period, x in x_positions.items():
        label = pd.Timestamp(period).strftime("%Y-%m")
        svg.append(f'<text x="{x:.1f}" y="{height-bottom+28}" text-anchor="middle" font-size="12" font-family="Arial">{label}</text>')
    for index, plant in enumerate(plants):
        plant_data = chart_data.loc[chart_data["plant"].eq(plant)].sort_values("period")
        points = " ".join(
            f'{x_positions[row.period]:.1f},{y_position(row.cost_rate):.1f}'
            for row in plant_data.itertuples()
        )
        color = colors[index % len(colors)]
        svg.append(f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="3"/>')
        for row in plant_data.itertuples():
            svg.append(f'<circle cx="{x_positions[row.period]:.1f}" cy="{y_position(row.cost_rate):.1f}" r="4" fill="{color}"/>')
        legend_x = left + index * 175
        svg.append(f'<rect x="{legend_x}" y="{height-35}" width="12" height="12" fill="{color}"/>')
        svg.append(f'<text x="{legend_x+18}" y="{height-24}" font-size="12" font-family="Arial">{escape(plant)}</text>')
    svg.append('</svg>')
    output.write_text("\n".join(svg), encoding="utf-8")
    return output





if __name__ == "__main__":
    # __file__ 是目前這支 Python 程式的實際位置。
    # parents[1] 會從 src/analysis.py 回到專案根目錄，
    # 因此無論從哪個資料夾執行，CSV 路徑都能保持正確。
    project_root = Path(__file__).resolve().parents[1]
    csv_path = project_root / "data" / "raw" / "monthly_kpi.csv"
    incident_path = project_root / "data" / "raw" / "incident.csv"
    report_path = project_root / "reports" / "cost_rate_trend_2026-09.svg"

    kpi_df = load_kpi_data(csv_path)
    validate_kpi_data(kpi_df)

    metrics_df = calculate_kpis(kpi_df)
    budget_result = compare_to_budget(metrics_df, "2026-09")
    cost_rate_result = compare_cost_rate_to_previous_month(
        metrics_df,
        "2026-09",
    )
    cost_rate_yoy_result = compare_cost_rate_to_previous_year(
        metrics_df,
        "2026-09",
    )
    anomalies_result = find_anomalies(metrics_df, "2026-09")

    three_month_scope = get_three_month_cost_rate_trend(
        metrics_df,
        "2026-09",
    )
    trend_summary = summarize_three_month_cost_rate_trend(
        three_month_scope,
        "2026-09",
    )
    revenue_ranking = rank_plants_by_metric(
        metrics_df,
        "2026-09",
        "revenue",
    )
    incidents = load_incident_data(incident_path)
    tainan_incidents = get_incident_details(incidents, "Tainan", "2026-09")
    material_loss_z_scores = add_z_score_anomaly(
        metrics_df,
        "2026-09",
        "material_loss_rate",
        threshold=1.0,
    )
    chart_path = generate_cost_rate_trend_chart(
        three_month_scope,
        report_path,
        data_as_of="2026-09（資料檔未提供更新時間）",
    )
    display = three_month_scope.copy()

    display["period"] = display["period"].dt.strftime("%Y-%m")
    display["cost_rate"] = display["cost_rate"].round(2)

    assert not three_month_scope.empty
    assert not trend_summary.empty
    assert not revenue_ranking.empty
    assert not tainan_incidents.empty
    assert not material_loss_z_scores.empty
    assert chart_path.exists()
    assert not budget_result.empty
    assert not cost_rate_result.empty
    assert not cost_rate_yoy_result.empty
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

    print("\n=== 各廠成本率月增比較 ===")
    print(
        cost_rate_result[
            [
                "plant",
                "previous_period",
                "previous_cost_rate",
                "current_cost_rate",
                "cost_rate_change_pp",
                "comparison_allowed",
                "warning",
            ]
        ].to_string(index=False)
    )

    print("\n=== 各廠成本率去年同期比較 ===")
    print(
        cost_rate_yoy_result[
            [
                "plant",
                "previous_year_period",
                "previous_year_cost_rate",
                "current_cost_rate",
                "cost_rate_yoy_change_pp",
                "comparison_allowed",
                "warning",
            ]
        ].to_string(index=False)
    )


    print("\n=== 最近三個月原始 KPI 範圍 ===")

    print(
        display[
            [
                "period",
                "plant",
                "revenue",
                "cost",
                "cost_rate",
                "source_rows",
                "preliminary_rows",
            ]
        ].sort_values(["plant", "period"]).to_string(index=False)
    )

    print("\n=== 最近三個月成本率趨勢摘要 ===")
    print(
        trend_summary[
            [
                "plant",
                "cost_rate_month_1",
                "cost_rate_month_2",
                "cost_rate_month_3",
                "cost_rate_change_pp",
                "trend_status",
                "comparison_allowed",
                "warning",
            ]
        ].round(2).to_string(index=False)
    )

    print("\n=== 各廠營收正式排名 ===")
    print(
        revenue_ranking[
            ["plant", "metric_value", "metric_rank", "comparison_allowed", "warning"]
        ].to_string(index=False)
    )

    print("\n=== 台南 2026-09 相關事件（待查證線索） ===")
    print(
        tainan_incidents[
            ["date", "incident_type", "severity", "description", "status", "source"]
        ].to_string(index=False)
    )

    print("\n=== 材料耗損率 z-score（輔助訊號） ===")
    print(
        material_loss_z_scores[
            [
                "plant",
                "department",
                "material_loss_rate",
                "z_score",
                "statistical_anomaly",
                "statistical_warning",
            ]
        ].round(2).to_string(index=False)
    )

    print(f"\n成本率圖表已輸出：{chart_path}")

    print("\n=== 異常 KPI ===")
    print(anomalies_result.to_string(index=False))
