from langchain_openai import ChatOpenAI
from pydantic import BaseModel,Field
from typing import TypedDict,Literal
from langchain_core.messages import BaseMessage
from langchain_core.messages import AIMessage,ToolMessage,HumanMessage,SystemMessage
from typing import AsyncGenerator

LLM_MODEL = "Qwen3-32B-AWQ"
LLM_BASE_URL = "http://192.168.103.21:31091/spiritx-api/v1"
LLM_API_KEY = "sk-7NAitPWQhdhwT2AR66Cc27E060664741A143E38eFbB33bE6"

llm = ChatOpenAI(model=LLM_MODEL, base_url=LLM_BASE_URL, api_key=LLM_API_KEY)


class VAState(TypedDict):
    messages: list[BaseMessage]
    decision: str
    output: str


RoutingDescription = "选择一个合适的知识库用来回答用户的问题"

type RoutingHandler = Literal["教师知识库","新闻知识库","None"]

knowledge_model = "rag-studio"
knowledge_base_url = "http://192.168.103.21:11090/ai-supremegpt/api/v1"

teacher_llm = ChatOpenAI(model=knowledge_model, base_url=knowledge_base_url, api_key="xzinfra-ae1b0913ca844e05babd60ee851a7d8e")
news_llm = ChatOpenAI(model=knowledge_model, base_url=knowledge_base_url, api_key="xzinfra-e83e3e1ee18e4126bda9545214a576db")


class Routing(BaseModel):
    routing: RoutingHandler = Field(None,description=RoutingDescription)

router_system_prompt = """
你是一个路由器,你的任务是根据用户的问题选择一个合适的知识库.
如果用户的问题不需要知识库,则选择None.

教师知识库: 获取关于学院中教师信息和介绍的知识库,主要是一些固定的信息

新闻知识库: 获取关于学院中新闻的知识库,包含学院的新闻,学院某个教师的新闻等等
"""

router_llm = llm.with_structured_output(Routing)
# Node
async def routing_llm(state: VAState):
    messages=[SystemMessage(content=router_system_prompt),*state["messages"]]
    result = await router_llm.ainvoke(messages)
    return {"decision": result.routing}


async def chat(state: VAState):
    if state["decision"] == "教师知识库":
        result = await teacher_llm.ainvoke(state["messages"])
    elif state["decision"] == "新闻知识库":
        result = await news_llm.ainvoke(state["messages"])
    else:
        result = await llm.ainvoke(state["messages"])
    return {"output": result.content}
    
from langgraph.graph import StateGraph,START,END

graph_builder = StateGraph(VAState)

graph_builder.add_node("routing",routing_llm)
graph_builder.add_node("chat",chat)

graph_builder.add_edge(START, "routing")
graph_builder.add_edge("routing", "chat")
graph_builder.add_edge("chat", END)

graph = graph_builder.compile()

async def arun(messages) -> AsyncGenerator[tuple[str,str],None]:
    input = {"messages":messages}
    async for mode,chunk in graph.astream(input,stream_mode=["updates","messages"]):
        if mode == "messages":
            chunk,info = chunk
            if info["langgraph_node"] == "chat":
                yield ("text",chunk.content)
        elif mode == "updates":
            if "chat" in chunk:
                yield ("message",chunk["chat"]["output"])


async def main():
    
    messages = [HumanMessage(content="陈文龙教授在2025年的活动?")]
    async for type,chunk in arun(messages):
        print(type,chunk)
        

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

