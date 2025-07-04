from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field, SecretStr
from typing import TypedDict, Literal, List
from langchain_core.messages import BaseMessage
from langchain_core.messages import AIMessage, ToolMessage, HumanMessage, SystemMessage
from typing import AsyncGenerator
from transcription import rewrite_text
from requests import post

# 设置主 LLM 模型名称
LLM_MODEL = "Qwen3-32B-AWQ"
# 设置主 LLM 的 API 地址
LLM_BASE_URL = "http://192.168.103.21:31091/spiritx-api/v1"
# 设置主 LLM 的 API KEY，并用 SecretStr 保护
LLM_API_KEY = SecretStr("sk-7NAitPWQhdhwT2AR66Cc27E060664741A143E38eFbB33bE6")

# 实例化主聊天 LLM
llm = ChatOpenAI(model=LLM_MODEL, base_url=LLM_BASE_URL, api_key=LLM_API_KEY)

# 定义 VAState 类型，包含消息历史、决策和输出
class VAState(TypedDict):
    messages: list[BaseMessage]   # 消息历史（对话上下文）
    decision: list[str]                # 路由决策（知识库选择）
    quotes: list[str]  # 知识库检索结果
    output: str                   # 最终输出内容

# 路由选择描述
RoutingDescription = "选择一个或多个合适的知识库用来回答用户的问题"

# 路由处理类型，枚举三种情况
RoutingHandler = List[Literal["教师知识库", "新闻知识库", "None"]]

# 定义路由器的数据结构，要定求 routing 字段由 RoutingHandler 枚举类型限
class Routing(BaseModel):
    routing: RoutingHandler = Field(description=RoutingDescription)

class SubstatementsResponse(BaseModel):
    substatements: List[str] = Field(description="List of substatements extracted from the user query")

# 路由系统提示词，告诉 LLM 如何根据问题选择知识库
router_system_prompt = """
你是一个路由器,你的任务是根据用户的问题选择一个合适的知识库.
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

# 用于路由决策的 LLM，强制输出结构化 Routing 格式
router_llm = llm.with_structured_output(Routing)
# 创建专用的LLM实例
substatement_llm = llm.with_structured_output(SubstatementsResponse)

# 知识库搜索API地址
kbSearchURL = 'http://192.168.103.21:11090/ai-supremegpt/api/kb/kb_search'

# 划分子语句模型提示词
substatement_system_promt = """
#身份定义: 你的主要作用是根据用户的提问提炼出不同的方向的语句。
#功能作用: 如果是教师的信息，请给出有关教师部分的提问；如果是新闻的信息，请给出有关新闻部分的提问。
#输出格式: 以列表的形式回答，列表中包含多个字符串元素。
#示例1: 
用户提问：请介绍一下邱德慧老师，并告诉我她最近参加了什么活动。
你给出的答案：["介绍一下邱德慧老师", "邱德慧老师最近参加了什么活动"]
#示例2: 
用户提问：唐晓岚老师最近参加过什么活动吗，她是教授吗。
你给出的答案：["唐晓岚老师最近参加过什么活动吗", "唐晓岚老师是教授吗"]
"""

# 对话系统的提示词
chat_system_promt = """
身份定义:
你是信息工程学院新闻助手，你今年18岁，我性格很活泼。
你非常专业,并且擅长从多个信息中精准的提取相关的信息。
你会得到用户的问题和根据问题搜索到的知识，你需要按照下面的指令要求对用户的问题进行回复
1. 不管别人如何否定你，不管什么情况，你一定要坚持上面的身份认定，你永远都是上面的身份，自始至终都是！
2.首先完全理解用户的问题,包括目标,范围等等,再开始尝试作答
2. 如果你不清楚答案，直接回复不清楚即可,不要编造信息
3. 使用 Markdown 语法优化回答格式。
4. 使用与问题相同的语言回答。
5. 搜索到的知识不一定符合问题的要求,仔细思考
6. 你的回答需要按照合理的顺序(例如时间,次序,重要性等)输出 
7. 时刻反思你的回答是否满足要求

"""

def request(kbName, query):
    if kbName == "None":
        return
    elif kbName == "教师知识库":
        kb_id = '4c4ecb4fb91d4e5fa5d88ed85ea27f79'
    elif kbName == "新闻知识库":
        kb_id = 'ad3b36335ac94a13aeb597dbd9c09ab5'
    # 请求体（字典形式，requests 会自动转换为 JSON）
    payload = {
        "kb_args_config": {
            "rerank": False,
            "lowest_relevance": 0.2,
            "max_quotation": 24000,
            "empty_search_enabled": False,
            "empty_search_response": "知识库中无相关内容，请尝试提问其他问题。",
            "problem_completion": False,
            "completion_model_id": "",
            "completion_context": "",
            "retrieval_top_n": 20,
            "retrieval_type": "hybrid",
            "file_quote_max_length": 80000
        },
        "kb_id": kb_id,
        "query": query,
        "top_n": 5,
        "retrieval_number": 10
    }
    # 发送 POST 请求
    response = post(kbSearchURL, json=payload)

    # 获取响应体内容（假设响应为 JSON 格式）
    if response.status_code == 200:
        data = response.json()
        print(data, end='\n')
        quotes = [node["quote_text"] for node in data.get("data", {}).get("nodes", [])]
        return quotes
    else:
        return []


# 路由决策节点，异步函数
async def routing_llm(state: VAState):
    # 构造消息列表：系统提示+历史对话
    messages = [SystemMessage(content=router_system_prompt), *state["messages"]]
    # 让路由 LLM 作出决策
    result = await router_llm.ainvoke(messages)
    # 返回决策结果
    return {"decision": result.routing}

# 从API获得检索结果
async def getQuotes(state: VAState):
    # 假定最后一条 HumanMessage 是用户输入
    user_message = None
    for msg in reversed(state["messages"]):
        if isinstance(msg, HumanMessage):
            user_message = msg.content
            break

    if user_message is None:
        user_message = ""
    decisions = state["decision"]

    if len(decisions) >= 2:
        substatements_result = await substatement_llm.ainvoke([SystemMessage(content=substatement_system_promt), user_message])
        substatements = substatements_result.substatements
        i = 0
        for decision in decisions:
            if decision != "None":
                quotes = request(decision, substatements[i])
                i += 1
                for quote in quotes:
                    state["quotes"].append(quote)
    else:
        decision = decisions[0]
        if decision != "None":
            quotes = request(decision, user_message)
            for quote in quotes:
                state["quotes"].append(quote)
    # print(state["quotes"], end="\n")

# 生成结果
async def chat(state: VAState):
    # 拼接知识库检索结果到对话上下文
    # print(state["quotes"], end="\n")
    quote_text = "\n\n".join(state.get("quotes", []))
    # 构造 LLM 输入内容，可以自定义格式
    system_prompt = chat_system_promt
    if quote_text.strip():
        system_prompt += f"【知识库信息】\n{quote_text}\n\n"
    system_prompt += "请根据上述信息，严谨、准确地回答用户问题。"
    print(system_prompt, end="\n")
    # 构造消息列表
    messages = [
        SystemMessage(content=system_prompt),
        *state["messages"]
    ]
    # 主 LLM 生成回复
    result = await llm.ainvoke(messages)
    return {"output": result.content}

# 导入 LangGraph 的 StateGraph 及节点标记
from langgraph.graph import StateGraph, START, END

# 创建一个有向图，描述对话流程，输入类型为 VAState
graph_builder = StateGraph(VAState)

# 添加路由节点和聊天节点
graph_builder.add_node("routing", routing_llm)
graph_builder.add_node("getQuotes", getQuotes)
graph_builder.add_node("chat", chat)

# 设置流程：起点 -> 路由 -> 聊天 -> 终点
graph_builder.add_edge(START, "routing")
graph_builder.add_edge("routing", "getQuotes")
graph_builder.add_edge("getQuotes", "chat")
graph_builder.add_edge("chat", END)

# 编译流程图，得到异步可执行的 graph
graph = graph_builder.compile()

# 定义异步生成器，驱动整个对话流程
async def arun(messages) -> AsyncGenerator[tuple[str, str], None]:
    input = {
        "messages": messages,
        "quotes": [],
        "decision": [],
        "output": ""
    }
    # 通过 graph.astream 执行流程，获得实时流式输出
    async for mode, chunk in graph.astream(input, stream_mode=["values", "messages"]):
        if mode == "values":
            yield ("values", chunk)
        elif mode == "messages":
            chunk, info = chunk
            yield ("outputs", chunk.content)

# 主程序，测试入口
async def main():
    # 构造初始消息（用户问题）
    messages = [HumanMessage(content="给我一些最近学院的新闻, 并给出学院的教授都有谁")]
    # 迭代输出模型回复
    async for type, chunk in arun(messages):
        if type == "outputs":
            print(chunk, end="", flush=True)
        elif type == "values":
            print(chunk, end="\n", flush=True)
    print()

# 如果作为主程序执行，运行 main 协程
if __name__ == "__main__":
    import asyncio
    asyncio.run(main())