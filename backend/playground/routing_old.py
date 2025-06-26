from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage,AIMessage

from pydantic import SecretStr

LLM_MODEL = "Qwen3-32B-AWQ"
LLM_BASE_URL = "http://192.168.103.21:31091/spiritx-api/v1"
LLM_API_KEY = SecretStr("sk-7NAitPWQhdhwT2AR66Cc27E060664741A143E38eFbB33bE6")

llm = ChatOpenAI(model=LLM_MODEL, base_url=LLM_BASE_URL, api_key=LLM_API_KEY)

system_prompt = """你是一个路由器,你的任务是根据用户的问题选择一个合适的知识库.
如果用户的问题不需要知识库,则选择None.

教师知识库: 获取关于学院中教师信息和介绍的知识库,主要是一些固定的信息

新闻知识库: 获取关于学院中新闻的知识库,包含学院的新闻,学院某个教师的新闻等等
"""

def routing(message: str):
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=message),
    ]
    response = llm.invoke(messages)
    print(f"message: {message}, response: {response.content}")

test_messages = [
    "学院最近有什么新闻",
    "学院的教师有哪些",
    "张教授的信息",
    "张教授最近有哪些活动",
    "如何计算阶乘"
]

for message in test_messages:
    routing(message)
