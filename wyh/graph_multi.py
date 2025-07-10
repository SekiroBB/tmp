from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field, SecretStr
from typing import TypedDict, Literal
from langchain_core.messages import BaseMessage
from langchain_core.messages import AIMessage, ToolMessage, HumanMessage, SystemMessage
from typing import AsyncGenerator
from typing import Literal, List
from transcription import rewrite_text

# 设置主 LLM 模型名称
LLM_MODEL = "Qwen3-32B-AWQ"
# 设置主 LLM 的 API 地址
LLM_BASE_URL = "http://192.168.103.21:31091/spiritx-api/v1"
# 设置主 LLM 的 API KEY，并用 SecretStr 保护
LLM_API_KEY = SecretStr("sk-7NAitPWQhdhwT2AR66Cc27E060664741A143E38eFbB33bE6")

# 实例化主聊天 LLM
llm = ChatOpenAI(model=LLM_MODEL, base_url=LLM_BASE_URL, api_key=LLM_API_KEY)
#123
# 定义 VAState 类型，包含消息历史、决策和输出
class VAState(TypedDict):
    messages: list[BaseMessage]   # 消息历史（对话上下文）
    decision: list[str]                 # 路由决策（知识库选择）
    sum: str                 # 多个知识库总结
    output: str                   # 最终输出内容

# 路由选择描述
RoutingDescription = "选择一个或多个合适的知识库用来回答用户的问题"

# 路由处理类型，枚举三种情况
RoutingHandler = List[Literal["教师知识库", "新闻知识库", "None"]]

# 知识库 LLM 模型及 API 地址
knowledge_model = "rag-studio"
knowledge_base_url = "http://192.168.103.21:11090/ai-supremegpt/api/v1"

# 实例化教师知识库的 LLM
teacher_llm = ChatOpenAI(model=knowledge_model, base_url=knowledge_base_url, api_key=SecretStr("xzinfra-ae1b0913ca844e05babd60ee851a7d8e"))
# 实例化新闻知识库的 LLM
news_llm = ChatOpenAI(model=knowledge_model, base_url=knowledge_base_url, api_key=SecretStr("xzinfra-e83e3e1ee18e4126bda9545214a576db"))

# 定义路由器的数据结构，要求 routing 字段由 RoutingHandler 类型限定
class Routing(BaseModel):
    routing: RoutingHandler = Field(description=RoutingDescription)

# 路由系统提示词，告诉 LLM 如何根据问题选择知识库
router_system_prompt = """
你是一个路由器,你的任务是根据用户的问题选择一个或多个合适的知识库
如果用户的问题不需要知识库,则选择None.

教师知识库: 获取关于学院中教师信息和介绍的知识库,主要是一些固定的信息
例子: 
1. 用户的问题是: 介绍陈文龙教授
2. 用户的问题是: 陈文龙教授在2025年的活动?

新闻知识库: 获取关于学院中新闻的知识库,包含学院的新闻,学院某个教师的新闻等等
例子:
1. 用户的问题是: 学院最近的新闻
2. 用户的问题是: 陈文龙教授最近的新闻

"""

# 总结模型提示词
sum_model_prompt = """
你是一个总结模型，你的任务是根据用户的问题从知识库里检索信息。

"""

# 用于路由决策的 LLM，强制输出结构化 Routing 格式
router_llm = llm.with_structured_output(Routing)

# 路由决策节点，异步函数
async def routing_llm(state: VAState):
    # 构造消息列表：系统提示+历史对话
    messages = [SystemMessage(content=router_system_prompt), *state["messages"]]
    # 让路由 LLM 作出决策
    result = await router_llm.ainvoke(messages)
    # 返回决策结果
    return {"decision": result.routing}

async def sum(state: VAState):
    messages = [SystemMessage(content=sum_model_prompt), *state["messages"]]
    decisions = state["decision"]
    # # 允许 decision 是字符串或列表
    # if isinstance(decisions, str):
    #     decisions = [decisions]

    results = "知识库提供的信息如下："

    for decision in decisions:
        if decision == "教师知识库":
            res = await teacher_llm.ainvoke(messages)
            results += res.content + "|||||"
        elif decision == "新闻知识库":
            res = await news_llm.ainvoke(messages)
            results += res.content
        # 其他知识库可扩展

    return {"sum": results}

async def chat(state: VAState):

    messages = [*state["messages"], *state["sum"]]

    result = await llm.ainvoke(messages)

    return {"output": result.content}

# 导入 LangGraph 的 StateGraph 及节点标记
from langgraph.graph import StateGraph, START, END

# 创建一个有向图，描述对话流程，输入类型为 VAState
graph_builder = StateGraph(VAState)

# 添加路由节点和聊天节点
graph_builder.add_node("routing", routing_llm)
graph_builder.add_node("sum", sum)
graph_builder.add_node("chat", chat)

# 设置流程：起点 -> 路由 -> 聊天 -> 终点
graph_builder.add_edge(START, "routing")
graph_builder.add_edge("routing", "sum")
graph_builder.add_edge("sum", "chat")
graph_builder.add_edge("chat", END)

# 编译流程图，得到异步可执行的 graph
graph = graph_builder.compile()

# 定义异步生成器，驱动整个对话流程
async def arun(messages) -> AsyncGenerator[tuple[str, str], None]:
    input = {"messages": messages}
    # 通过 graph.astream 执行流程，获得实时流式输出
    async for mode, chunk in graph.astream(input, stream_mode=["updates", "messages"]):
        # 如果是消息流，且到达 chat 节点，输出文本内容
        if mode == "messages":
            chunk, info = chunk
            if info["langgraph_node"] == "chat":
                yield ("text", chunk.content)
        # 如果是状态更新流，且有 chat 输出，输出消息内容
        elif mode == "updates":
            if "chat" in chunk:
                yield ("message", chunk["chat"]["output"])

async def arun_test(messages) -> AsyncGenerator[tuple[str, str], None]:
    input = {"messages": messages}
    # 通过 graph.astream 执行流程，获得实时流式输出
    async for mode, chunk in graph.astream(input, stream_mode=["values"]):
        yield ("values", chunk)

async def main():
    # 构造初始消息（用户问题）
    messages = [HumanMessage(content="学院最近的新闻，以及学院的教授有谁")]
    # 迭代输出模型回复
    async for type, chunk in arun(messages):
        if type == "messages":
            print(chunk, end="", flush=True)
    print()

async def main_test():
    # 构造初始消息（用户问题）
    messages = [HumanMessage(content="学院的教授都有谁，以及学院最近的新闻")]
    # 迭代输出模型回复
    async for type, chunk in arun_test(messages):
        print(chunk, end="", flush=True)

# 如果作为主程序执行，运行 main 协程
if __name__ == "__main__":
    import asyncio
    asyncio.run(main_test())