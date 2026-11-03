import requests
import time
import json

print("Testing Ollama...", flush=True)

start = time.perf_counter()

response = requests.post(
    "http://localhost:11434/api/generate",
    json={
        "model": "qwen3-vl:4b-instruct",
        "prompt": "Return JSON only: " + json.dumps({"status": "ok"}),
        "stream": False,
        "format": "json",
        "options": {"num_predict": 30}
    },
    timeout=120
)

elapsed = time.perf_counter() - start
data = response.json()

print("HTTP status:", response.status_code)
print("Elapsed:", round(elapsed, 2), "seconds")
print("Prompt tokens:", data.get("prompt_eval_count"))
print("Output tokens:", data.get("eval_count"))
print("Load duration:", round(data.get("load_duration", 0) / 1e9, 2), "seconds")
print("Prompt evaluation:", round(data.get("prompt_eval_duration", 0) / 1e9, 2), "seconds")
print("Generation:", round(data.get("eval_duration", 0) / 1e9, 2), "seconds")
print("Response:", data.get("response"))
