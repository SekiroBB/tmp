from pydantic import SecretStr
from langchain_openai import ChatOpenAI
from typing import TypedDict
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph,START,END

LLM_MODEL = "Qwen3-32B-AWQ"
LLM_BASE_URL = "http://192.168.103.21:31091/spiritx-api/v1"
LLM_API_KEY = SecretStr("sk-7NAitPWQhdhwT2AR66Cc27E060664741A143E38eFbB33bE6")

llm = ChatOpenAI(model=LLM_MODEL, base_url=LLM_BASE_URL, api_key=LLM_API_KEY)


class IState(TypedDict):
    topic: str
    introduction: str 
    translation: str 
    

def generate_brief(state: IState):
    messages = [
        SystemMessage(content="根据主题生成一段简单的介绍"),
        HumanMessage(content=state["topic"]),
    ]
    response = llm.invoke(messages)
    return {"introduction": response.content}

def translate_joke(state: IState):
    messages = [
        SystemMessage(content="你是一个翻译大师,请将文本翻译成英文,注意直接输出翻译结果,不要有任何解释"),
        HumanMessage(content=state["introduction"]),
    ]
    response = llm.invoke(messages)
    return {"translation": response.content}



graph_builder = StateGraph(IState)

graph_builder.add_node("generate_brief", generate_brief)
graph_builder.add_node("translate_joke", translate_joke)

graph_builder.add_edge(START, "generate_brief")
graph_builder.add_edge("generate_brief", "translate_joke")
graph_builder.add_edge("translate_joke", END)

graph = graph_builder.compile()

input_data = {"topic": "tom和jerry"}
print(f"input_data: {input_data}")
result = graph.invoke(input_data)
print(f"result:")
print(f"introduction: {result['introduction']}")
print(f"translation: {result['translation']}")




