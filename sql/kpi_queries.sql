-- name: budget_variance
WITH plant_month AS (
    SELECT
        plant,
        SUM(revenue) AS revenue,
        SUM(budget) AS budget,
        SUM(CASE WHEN data_status <> 'closed' THEN 1 ELSE 0 END) AS preliminary_rows
    FROM monthly_kpi
    WHERE period = :target_period
    GROUP BY plant
)
SELECT
    plant,
    revenue,
    budget,
    revenue - budget AS budget_variance,
    CASE
        WHEN budget = 0 THEN NULL
        ELSE (revenue - budget) * 100.0 / budget
    END AS budget_variance_pct,
    CASE WHEN preliminary_rows = 0 THEN 1 ELSE 0 END AS comparison_allowed,
    CASE
        WHEN preliminary_rows > 0 THEN 'preliminary_data'
        WHEN budget = 0 THEN 'zero_denominator:budget_variance_pct'
        ELSE NULL
    END AS warning
FROM plant_month
ORDER BY budget_variance_pct;

-- name: cost_rate_mom
WITH plant_month AS (
    SELECT
        period,
        plant,
        SUM(revenue) AS revenue,
        SUM(cost) AS cost,
        SUM(CASE WHEN data_status <> 'closed' THEN 1 ELSE 0 END) AS preliminary_rows
    FROM monthly_kpi
    WHERE period IN (
        :target_period,
        strftime('%Y-%m', date(:target_period || '-01', '-1 month'))
    )
    GROUP BY period, plant
),
current_month AS (
    SELECT *
    FROM plant_month
    WHERE period = :target_period
),
previous_month AS (
    SELECT *
    FROM plant_month
    WHERE period = strftime('%Y-%m', date(:target_period || '-01', '-1 month'))
)
SELECT
    current_month.plant,
    current_month.cost * 100.0 / NULLIF(current_month.revenue, 0) AS current_cost_rate,
    previous_month.cost * 100.0 / NULLIF(previous_month.revenue, 0) AS previous_cost_rate,
    current_month.cost * 100.0 / NULLIF(current_month.revenue, 0)
        - previous_month.cost * 100.0 / NULLIF(previous_month.revenue, 0)
        AS cost_rate_change_pp,
    CASE
        WHEN current_month.preliminary_rows = 0
         AND COALESCE(previous_month.preliminary_rows, 0) = 0
         AND previous_month.plant IS NOT NULL
         AND current_month.revenue <> 0
         AND previous_month.revenue <> 0
        THEN 1 ELSE 0
    END AS comparison_allowed
FROM current_month
LEFT JOIN previous_month ON current_month.plant = previous_month.plant
ORDER BY cost_rate_change_pp DESC;

-- name: cost_rate_mom_window
WITH plant_month AS (
    SELECT
        period,
        plant,
        SUM(revenue) AS revenue,
        SUM(cost) AS cost,
        SUM(CASE WHEN data_status <> 'closed' THEN 1 ELSE 0 END) AS preliminary_rows
    FROM monthly_kpi
    GROUP BY period, plant
),
monthly_with_previous AS (
    SELECT
        period,
        plant,
        revenue,
        cost,
        preliminary_rows,
        LAG(period) OVER (PARTITION BY plant ORDER BY period) AS previous_period,
        LAG(revenue) OVER (PARTITION BY plant ORDER BY period) AS previous_revenue,
        LAG(cost) OVER (PARTITION BY plant ORDER BY period) AS previous_cost,
        LAG(preliminary_rows) OVER (PARTITION BY plant ORDER BY period)
            AS previous_preliminary_rows
    FROM plant_month
)
SELECT
    plant,
    cost * 100.0 / NULLIF(revenue, 0) AS current_cost_rate,
    previous_cost * 100.0 / NULLIF(previous_revenue, 0) AS previous_cost_rate,
    cost * 100.0 / NULLIF(revenue, 0)
        - previous_cost * 100.0 / NULLIF(previous_revenue, 0)
        AS cost_rate_change_pp,
    CASE
        WHEN previous_period = strftime('%Y-%m', date(:target_period || '-01', '-1 month'))
         AND preliminary_rows = 0
         AND previous_preliminary_rows = 0
         AND revenue <> 0
         AND previous_revenue <> 0
        THEN 1 ELSE 0
    END AS comparison_allowed
FROM monthly_with_previous
WHERE period = :target_period
ORDER BY cost_rate_change_pp DESC;

-- name: cost_rate_yoy
WITH plant_month AS (
    SELECT
        period,
        plant,
        SUM(revenue) AS revenue,
        SUM(cost) AS cost,
        SUM(CASE WHEN data_status <> 'closed' THEN 1 ELSE 0 END) AS preliminary_rows
    FROM monthly_kpi
    WHERE period IN (
        :target_period,
        strftime('%Y-%m', date(:target_period || '-01', '-1 year'))
    )
    GROUP BY period, plant
),
current_month AS (
    SELECT * FROM plant_month WHERE period = :target_period
),
previous_year AS (
    SELECT *
    FROM plant_month
    WHERE period = strftime('%Y-%m', date(:target_period || '-01', '-1 year'))
)
SELECT
    current_month.plant,
    current_month.cost * 100.0 / NULLIF(current_month.revenue, 0) AS current_cost_rate,
    previous_year.cost * 100.0 / NULLIF(previous_year.revenue, 0) AS previous_year_cost_rate,
    current_month.cost * 100.0 / NULLIF(current_month.revenue, 0)
        - previous_year.cost * 100.0 / NULLIF(previous_year.revenue, 0)
        AS cost_rate_yoy_change_pp,
    CASE
        WHEN current_month.preliminary_rows = 0
         AND COALESCE(previous_year.preliminary_rows, 0) = 0
         AND previous_year.plant IS NOT NULL
         AND current_month.revenue <> 0
         AND previous_year.revenue <> 0
        THEN 1 ELSE 0
    END AS comparison_allowed
FROM current_month
LEFT JOIN previous_year ON current_month.plant = previous_year.plant
ORDER BY cost_rate_yoy_change_pp DESC;
