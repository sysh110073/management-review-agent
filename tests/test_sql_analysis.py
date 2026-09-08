import pytest

from src.analysis import (
    calculate_kpis,
    compare_cost_rate_to_previous_month,
    compare_cost_rate_to_previous_year,
    compare_to_budget,
    load_kpi_data,
)
from src.sql_analysis import execute_kpi_sql


@pytest.fixture
def raw_kpi_df():
    return load_kpi_data("data/raw/monthly_kpi.csv")


def test_sql_budget_variance_matches_python(raw_kpi_df):
    python_result = compare_to_budget(calculate_kpis(raw_kpi_df), "2026-09")
    sql_result = execute_kpi_sql(raw_kpi_df, "budget_variance", "2026-09")

    python_tainan = python_result.loc[python_result["plant"].eq("Tainan")].iloc[0]
    sql_tainan = sql_result.loc[sql_result["plant"].eq("Tainan")].iloc[0]

    assert sql_tainan["budget_variance"] == python_tainan["budget_variance"]
    assert sql_tainan["budget_variance_pct"] == pytest.approx(
        python_tainan["budget_variance_pct"]
    )


def test_sql_cost_rate_mom_matches_python(raw_kpi_df):
    python_result = compare_cost_rate_to_previous_month(
        calculate_kpis(raw_kpi_df),
        "2026-09",
    )
    sql_result = execute_kpi_sql(raw_kpi_df, "cost_rate_mom", "2026-09")

    python_tainan = python_result.loc[python_result["plant"].eq("Tainan")].iloc[0]
    sql_tainan = sql_result.loc[sql_result["plant"].eq("Tainan")].iloc[0]

    assert sql_tainan["cost_rate_change_pp"] == pytest.approx(
        python_tainan["cost_rate_change_pp"]
    )


def test_sql_window_function_keeps_the_true_previous_month(raw_kpi_df):
    sql_result = execute_kpi_sql(raw_kpi_df, "cost_rate_mom_window", "2026-09")
    tainan = sql_result.loc[sql_result["plant"].eq("Tainan")].iloc[0]

    assert tainan["comparison_allowed"] == 1
    assert tainan["cost_rate_change_pp"] == pytest.approx(8.4523809524)


def test_sql_cost_rate_yoy_matches_python(raw_kpi_df):
    python_result = compare_cost_rate_to_previous_year(
        calculate_kpis(raw_kpi_df),
        "2026-09",
    )
    sql_result = execute_kpi_sql(raw_kpi_df, "cost_rate_yoy", "2026-09")

    python_tainan = python_result.loc[python_result["plant"].eq("Tainan")].iloc[0]
    sql_tainan = sql_result.loc[sql_result["plant"].eq("Tainan")].iloc[0]

    assert sql_tainan["cost_rate_yoy_change_pp"] == pytest.approx(
        python_tainan["cost_rate_yoy_change_pp"]
    )
