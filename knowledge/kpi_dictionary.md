# KPI Dictionary

## 文件資訊

- 版本：0.1.0
- 生效日：2026-09-07
- 資料範圍：虛構的營運管理練習資料
- 幣別：新台幣（TWD）
- 金額單位：百萬元
- 更新頻率：每月
- 資料狀態：月度資料可能存在未關帳、缺值或延遲情況，系統必須標示警告。

---

## 1. 營收（Revenue）

| 欄位 | 定義 |
| --- | --- |
| KPI 名稱 | 營收 |
| 英文名稱 | revenue |
| 定義 | 指指定月份、廠別與部門的實際營收。 |
| 公式 | `revenue` |
| 單位 | 百萬元 |
| 時間粒度 | 月 |
| 組織粒度 | 廠別、部門 |
| 資料來源 | `monthly_kpi.csv` 的 `revenue` 欄位 |
| 資料 owner | 財務部 |
| 注意事項 | 不可將不同幣別或不同時間粒度的資料直接加總。 |

---

## 2. 預算差異（Budget Variance）

| 欄位 | 定義 |
| --- | --- |
| KPI 名稱 | 預算差異 |
| 英文名稱 | budget_variance |
| 定義 | 實際營收與預算營收之間的金額差異。 |
| 公式 | `revenue - budget` |
| 單位 | 百萬元 |
| 時間粒度 | 月 |
| 組織粒度 | 廠別、部門 |
| 資料來源 | `monthly_kpi.csv` 的 `revenue` 與 `budget` 欄位 |
| 資料 owner | 財務部 |
| 注意事項 | 預算必須與實際營收使用相同月份、組織粒度與預算版本。 |

---

## 3. 預算差異率（Budget Variance Rate）

| 欄位 | 定義 |
| --- | --- |
| KPI 名稱 | 預算差異率 |
| 英文名稱 | budget_variance_pct |
| 定義 | 實際營收相對於預算營收的差異比例。 |
| 公式 | `(revenue - budget) / budget * 100` |
| 單位 | 百分比（%） |
| 時間粒度 | 月 |
| 組織粒度 | 廠別、部門 |
| 資料來源 | `monthly_kpi.csv` 的 `revenue` 與 `budget` 欄位 |
| 資料 owner | 財務部 |
| 注意事項 | 當 `budget = 0` 時，不計算差異率；回傳空值並標記 `zero_denominator`。 |

---

## 4. 成本率（Cost Rate）

| 欄位 | 定義 |
| --- | --- |
| KPI 名稱 | 成本率 |
| 英文名稱 | cost_rate |
| 定義 | 成本占營收的比例，用於觀察獲利結構與成本控制狀況。 |
| 公式 | `cost / revenue * 100` |
| 單位 | 百分比（%） |
| 時間粒度 | 月 |
| 組織粒度 | 廠別、部門 |
| 資料來源 | `monthly_kpi.csv` 的 `cost` 與 `revenue` 欄位 |
| 資料 owner | 財務部 |
| 注意事項 | 當 `revenue = 0` 時，不計算成本率；回傳空值並標記 `zero_denominator`。成本與營收必須先彙總至相同粒度再計算。 |

---

## 5. 離職率（Turnover Rate）

| 欄位 | 定義 |
| --- | --- |
| KPI 名稱 | 離職率 |
| 英文名稱 | turnover_rate |
| 定義 | 指定期間內離職人數占平均在職人數的比例。 |
| 公式 | `leavers / ((headcount_start + headcount_end) / 2) * 100` |
| 單位 | 百分比（%） |
| 時間粒度 | 月 |
| 組織粒度 | 廠別、部門 |
| 資料來源 | `monthly_kpi.csv` 的 `headcount_start`、`headcount_end`、`leavers` 欄位 |
| 資料 owner | 人資部 |
| 注意事項 | 期初與期末人數不可缺漏；平均在職人數為 0 時，不計算離職率並標記 `zero_denominator`。 |

---

## 6. 材料耗損率（Material Loss Rate）

| 欄位 | 定義 |
| --- | --- |
| KPI 名稱 | 材料耗損率 |
| 英文名稱 | material_loss_rate |
| 定義 | 材料耗損量占材料投入量的比例，用於觀察材料使用效率。 |
| 公式 | `material_loss / material_input * 100` |
| 單位 | 百分比（%） |
| 時間粒度 | 月 |
| 組織粒度 | 廠別、部門 |
| 資料來源 | `monthly_kpi.csv` 的 `material_input` 與 `material_loss` 欄位 |
| 資料 owner | 製造部 |
| 注意事項 | 材料投入量為 0 時，不計算耗損率並標記 `zero_denominator`。材料單位必須一致。 |

---

## 資料品質規則

1. `period` 必須使用 `YYYY-MM` 格式。
2. 同一筆月度 KPI 的唯一鍵為：`period + plant + department`。
3. 金額欄位不可為負數。
4. 人數與材料數量不可為負數。
5. `material_loss` 不可大於 `material_input`。
6. `leavers` 不可大於期初與期末平均人數。
7. 未關帳資料必須標示 `data_status = preliminary`，不可直接與正式關帳資料做結論性比較。