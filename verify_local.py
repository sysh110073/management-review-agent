import requests
import json

def test_local_inference():
    url = "http://127.0.0.1:11434/api/generate"
    
    # 這裡的 model 名稱請換成你實際下載的模型
    payload = {
        "model": "qwen2.5:7b",
        "prompt": "請用一句話解釋『離職率』的定義。",
        "stream": False
    }
    
    print("正在呼叫地端模型，請稍候...")
    try:
        response = requests.post(url, json=payload, timeout=30)
        result = response.json()
        print("\n✅ 成功呼叫！執行端點:", url)
        print("🤖 模型回應:", result['response'])
        print(f"⏱️ 總耗時: {result['total_duration'] / 1e9:.2f} 秒")
    except requests.exceptions.ConnectionError:
        print("\n❌ 連線失敗：請確認 Docker container 是否正常運行。")

if __name__ == "__main__":
    test_local_inference()