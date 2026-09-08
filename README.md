# Management Review Agent

以虛構資料實作的營運管理會議 AI 助理。

## 專案目標

協助主管分析營收、成本率、離職率與材料耗損率，
提供異常、證據、可能原因與待查證事項。

## 技術原則

- 數字由 Python 或 SQL 計算。
- 模型只負責理解問題、選擇 Tool 與組織文字。
- 所有 Tool 預設唯讀。
- 使用虛構資料，不使用真實公司資料。
- 回答必須區分事實、規則判定與可能原因。

## 本地模型

- 服務：Ollama Docker
- Endpoint：`http://127.0.0.1:11434`
- 模型：`qwen2.5:7b`
- GPU：NVIDIA GeForce RTX 3060 Ti

## 啟動服務

```bash
docker compose up -d
docker compose ps