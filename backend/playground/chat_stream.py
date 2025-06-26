from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage,AIMessage

from pydantic import SecretStr

LLM_MODEL = "Qwen3-32B-AWQ"
LLM_BASE_URL = "http://192.168.103.21:31091/spiritx-api/v1"
LLM_API_KEY = SecretStr("sk-7NAitPWQhdhwT2AR66Cc27E060664741A143E38eFbB33bE6")

llm = ChatOpenAI(model=LLM_MODEL, base_url=LLM_BASE_URL, api_key=LLM_API_KEY)

messages = [
    SystemMessage(content="你是一个聊天机器人，请根据用户的问题回答"),
    HumanMessage(content="你好，我是小明，请问你是谁？"),
]

# 流式输出第一个响应
print("第一个对话:")
full_response = ""
for chunk in llm.stream(messages):
    if chunk.content:
        if not isinstance(chunk.content, str):
            continue
        print(chunk.content, end="", flush=True)
        full_response += chunk.content
print()  # 换行

# 将响应添加到消息历史
messages.append(AIMessage(content=full_response))
messages.append(HumanMessage(content="我想写一个python 程序调用 openai 接口"))

# 流式输出第二个响应
print("\n第二个对话:")
full_response = ""
for chunk in llm.stream(messages):
    if chunk.content:
        if not isinstance(chunk.content, str):
            continue
        print(chunk.content, end="", flush=True)
        full_response += chunk.content
print()  # 换行