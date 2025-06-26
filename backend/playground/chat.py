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

response = llm.invoke(messages)
print(response)

messages.append(AIMessage(content=response.content))
messages.append(HumanMessage(content="请问我是谁"))

response = llm.invoke(messages)
print(response)