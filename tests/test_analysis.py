from src.analysis import(
    load_kpi_data,
    validate_kpi_data,
    calculate_kpis,
    compare_cost_rate_to_previous_year,
    get_three_month_cost_rate_trend,
    summarize_three_month_cost_rate_trend,
    rank_plants_by_metric,
    load_incident_data,
    get_incident_details,
    add_z_score_anomaly,
    generate_cost_rate_trend_chart,
)

import pandas as pd
import pytest

def test_tainan_cost_rate_yoy_change():
    df = load_kpi_data("data/raw/monthly_kpi.csv")
    validate_kpi_data(df)
    metrics_df = calculate_kpis(df)


    result = compare_cost_rate_to_previous_year(
        metrics_df,
        "2026-09"
    )

    tainan = result.loc[result["plant"] == "Tainan"].iloc[0]
    
    # assert主要是檢查程式寫出來的內容是否跟我們預期的一致
    # 它就像是自動化品管（QC）。你給程式輸入一組資料，assert 會在最後幫你比對：
    #「程式算出來的答案，跟我想像的是否一模一樣？
    # 如果一樣（True）：測試通過（Pass），什麼事都不會發生。
    #如果不同（False）：測試失敗（Fail），程式會立刻報錯中斷，並告訴你哪裡算錯了。
    assert round(tainan["cost_rate_yoy_change_pp"], 2) == 8.38
    assert tainan["comparison_allowed"]

def test_preliminary_data_cannot_be_compared():
    # 查 2026-09
    # 找 Taichung
    # 驗證 comparison_allowed 是 False
    # 驗證 warning 是 "preliminary_data"
    
    # 讀取資料
    df = load_kpi_data("data/raw/monthly_kpi.csv")
    # 確認原始資料品質正確
    validate_kpi_data(df)

    # 算出成本率等 KPI
    result = compare_cost_rate_to_previous_year(
        df,
        "2026-09"
    )

    # 從結果中擷取出台中廠那一列
    taichung = result.loc[
        result["plant"] == "Taichung"
        ].iloc[0]

    # 台中九月資料尚未關帳，因此不能正式比較
    assert not taichung["comparison_allowed"]

    # 警告標示必須正確
    assert taichung["warning"] == "preliminary_data"

def test_missing_previous_year_period_has_warning():
    # 查 2026-08
    # 資料沒有 2025-08
    # 驗證每個廠 comparison_allowed 都是 False
    # 驗證 warning 都是 "missing_previous_year_period"

    # 讀取資料
    df = load_kpi_data("data/raw/monthly_kpi.csv")
    # 確認原始資料品質正確
    validate_kpi_data(df)

    # 算出成本率等 KPI
    result = compare_cost_rate_to_previous_year(
        df,
        "2026-08"
    )

    # 所有廠別都不能比較
    assert not result["comparison_allowed"].any()

    # 所有警告都應該是缺少去年同期
    assert set(result["warning"]) == {
        "missing_previous_year_period"
    }


def test_tainan_three_month_cost_rate_is_deteriorating():
    df = load_kpi_data("data/raw/monthly_kpi.csv")
    validate_kpi_data(df)

    metrics_df = calculate_kpis(df)

    monthly = get_three_month_cost_rate_trend(
        metrics_df,
        "2026-09",
    )

    result = summarize_three_month_cost_rate_trend(
        monthly,
        "2026-09",
    )

    tainan = result.loc[
        result["plant"] == "Tainan"
    ].iloc[0]

    assert tainan["trend_status"] == "deteriorating"
    assert round(tainan["cost_rate_change_pp"], 2) == 8.43
    assert tainan["comparison_allowed"]

def test_taichung_preliminary_data_is_not_assessed():
    df = load_kpi_data("data/raw/monthly_kpi.csv")
    validate_kpi_data(df)

    metrics_df = calculate_kpis(df)

    monthly = get_three_month_cost_rate_trend(
        metrics_df,
        "2026-09",
    )

    result = summarize_three_month_cost_rate_trend(
        monthly,
        "2026-09",
    )

    taichung = result.loc[
        result["plant"] == "Taichung"
    ].iloc[0]

    assert not taichung["comparison_allowed"]
    assert taichung["warning"] == "preliminary_data"
    assert taichung["trend_status"] == "not_assessed"


def test_tainan_revenue_rank_is_second():
    df = load_kpi_data("data/raw/monthly_kpi.csv")
    validate_kpi_data(df)

    metrics_df = calculate_kpis(df)

    result = rank_plants_by_metric(
        metrics_df,
        "2026-09",
        "revenue",
    )

    tainan = result.loc[
        result["plant"] == "Tainan"
    ].iloc[0]

    assert tainan["comparison_allowed"]
    assert tainan["metric_rank"] == 2

def test_preliminary_plant_is_excluded_from_ranking():
    df = load_kpi_data("data/raw/monthly_kpi.csv")
    validate_kpi_data(df)

    metrics_df = calculate_kpis(df)

    result = rank_plants_by_metric(
        metrics_df,
        "2026-09",
        "revenue",
    )

    taichung = result.loc[
        result["plant"] == "Taichung"
    ].iloc[0]

    assert not taichung["comparison_allowed"]
    assert taichung["warning"] == "preliminary_data"
    assert pd.isna(taichung["metric_rank"])


def test_tainan_incidents_are_retrieved_for_september():
    incidents = load_incident_data("data/raw/incident.csv")
    result = get_incident_details(incidents, "Tainan", "2026-09")

    assert len(result) == 3
    assert set(result["incident_type"]) == {"equipment", "material", "hr"}
    assert set(result["source"]) == {"incident.csv"}


def test_z_score_returns_a_statistical_signal():
    df = load_kpi_data("data/raw/monthly_kpi.csv")
    validate_kpi_data(df)
    metrics_df = calculate_kpis(df)

    result = add_z_score_anomaly(
        metrics_df,
        "2026-09",
        "material_loss_rate",
        threshold=1.0,
    )

    first_row = result.iloc[0]
    assert first_row["plant"] == "Tainan"
    assert first_row["department"] == "Manufacturing"
    assert first_row["statistical_anomaly"]


def test_cost_rate_chart_is_created(tmp_path):
    df = load_kpi_data("data/raw/monthly_kpi.csv")
    metrics_df = calculate_kpis(df)
    trend_data = get_three_month_cost_rate_trend(metrics_df, "2026-09")

    output = generate_cost_rate_trend_chart(
        trend_data,
        tmp_path / "cost_rate_trend.svg",
        "2026-09-30",
    )

    assert output.exists()
    assert "資料截至：2026-09-30" in output.read_text(encoding="utf-8")


def test_validation_rejects_missing_numeric_value():
    df = load_kpi_data("data/raw/monthly_kpi.csv")
    df.loc[0, "revenue"] = pd.NA

    with pytest.raises(ValueError, match="數值欄位不可為空"):
        validate_kpi_data(df)


def test_validation_rejects_duplicate_primary_key():
    df = load_kpi_data("data/raw/monthly_kpi.csv")
    duplicate = df.iloc[[0]].copy()
    corrupted = pd.concat([df, duplicate], ignore_index=True)

    with pytest.raises(ValueError, match="主鍵重複"):
        validate_kpi_data(corrupted)


def test_validation_rejects_negative_value():
    df = load_kpi_data("data/raw/monthly_kpi.csv")
    df.loc[0, "cost"] = -1

    with pytest.raises(ValueError, match="不可為負數"):
        validate_kpi_data(df)


def test_validation_rejects_material_loss_above_input():
    df = load_kpi_data("data/raw/monthly_kpi.csv")
    df.loc[0, "material_loss"] = df.loc[0, "material_input"] + 1

    with pytest.raises(ValueError, match="material_loss 不可大於"):
        validate_kpi_data(df)


def test_validation_rejects_invalid_data_status():
    df = load_kpi_data("data/raw/monthly_kpi.csv")
    df.loc[0, "data_status"] = "draft"

    with pytest.raises(ValueError, match="data_status 只能是"):
        validate_kpi_data(df)
