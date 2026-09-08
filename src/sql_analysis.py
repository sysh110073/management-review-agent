"""以 SQLite 執行 sql/kpi_queries.sql，供 Python 與 SQL 結果核對。"""

from pathlib import Path
import sqlite3

import pandas as pd


SQL_PATH = Path(__file__).resolve().parents[1] / "sql" / "kpi_queries.sql"


def _load_named_queries(path: str | Path = SQL_PATH) -> dict[str, str]:
    """讀取以 ``-- name:`` 標記的 SQL 查詢區塊。"""
    queries: dict[str, str] = {}
    current_name: str | None = None
    current_lines: list[str] = []

    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.startswith("-- name:"):
            if current_name is not None:
                queries[current_name] = "\n".join(current_lines).strip()
            current_name = line.split(":", maxsplit=1)[1].strip()
            current_lines = []
        else:
            current_lines.append(line)

    if current_name is not None:
        queries[current_name] = "\n".join(current_lines).strip()
    return queries


def execute_kpi_sql(
    df: pd.DataFrame,
    query_name: str,
    period: str,
) -> pd.DataFrame:
    """將 KPI 資料載入暫存 SQLite，執行指定的具名查詢。

    參數：
        df：原始 KPI DataFrame 或已計算 KPI 的 DataFrame。
        query_name：budget_variance、cost_rate_mom 或 cost_rate_yoy。
        period：目標月份，格式為 YYYY-MM。

    回傳：
        SQL 查詢結果 DataFrame。
    """
    queries = _load_named_queries()
    if query_name not in queries:
        raise ValueError(f"找不到 SQL 查詢: {query_name}")

    sqlite_df = df.copy()
    sqlite_df["period"] = pd.to_datetime(sqlite_df["period"]).dt.strftime("%Y-%m")

    with sqlite3.connect(":memory:") as connection:
        sqlite_df.to_sql("monthly_kpi", connection, index=False, if_exists="replace")
        return pd.read_sql_query(
            queries[query_name],
            connection,
            params={"target_period": period},
        )
