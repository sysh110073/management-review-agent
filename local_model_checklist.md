# Local Model Checklist

## 執行紀錄
- 日期：2026/09/07
- 驗證人：Steven

## 模型
- 模型名稱：qwen2.5:7b
- 完整 digest：845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e
- 模型大小：約 4.7 GB

## 推論服務
- Endpoint：http://127.0.0.1:11434
- 實際服務：Docker container `local-ollama`
- Python 推論：成功
- 使用 GPU：是
- GPU：NVIDIA GeForce RTX 3060 Ti，8 GB VRAM

## Docker
- Compose 服務：ollama
- Container：local-ollama
- Port：127.0.0.1:11434:11434
- Volume：ollama_data → /root/.ollama
- Restart policy：unless-stopped

## 網路與安全
- OLLAMA_NO_CLOUD：true
- 服務僅綁定 localhost：是
- 完全斷網驗證：尚未執行，Day 7 驗收

## 驗收結果
- [x] Python 可呼叫本地模型
- [x] 模型可回傳可解析回應
- [x] GPU 實際參與推論
- [x] 容器重啟後模型仍可用
- [ ] 斷外網下可完成推論