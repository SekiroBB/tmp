import requests

# 接口地址
url = 'http://192.168.103.21:11090/ai-supremegpt/api/kb/kb_search'

# 请求体（字典形式，requests 会自动转换为 JSON）
payload = {
    "kb_args_config": {
        "rerank": True,
        "lowest_relevance": 0.4,
        "max_quotation": 24000,
        "empty_search_enabled": False,
        "empty_search_response": "知识库中无相关内容，请尝试提问其他问题。",
        "problem_completion": False,
        "completion_model_id": "",
        "completion_context": "",
        "retrieval_top_n": 20,
        "retrieval_type": "embedding",
        "file_quote_max_length": 80000
    },
    "kb_id": "ad3b36335ac94a13aeb597dbd9c09ab5",
    "query": "班会",
    "top_n": 5,
    "retrieval_number": 10
}

# 发送 POST 请求
response = requests.post(url, json=payload)

# 获取响应体内容（假设响应为 JSON 格式）
if response.status_code == 200:
    data = response.json()
    print("响应内容：", data)
else:
    print("请求失败，状态码：", response.status_code)
    print("响应内容：", response.text)