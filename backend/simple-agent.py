from livekit.plugins import openai, deepgram, silero

import logging
import json
from livekit import rtc
from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    JobProcess,
    RoomInputOptions,
    RoomOutputOptions,
    RunContext,
    WorkerOptions,
    cli,
    metrics,
    ModelSettings,
    llm,
    FunctionTool
)
from livekit.agents.llm import ChatChunk,ChoiceDelta,ChatRole
from livekit.plugins import deepgram, openai, silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel
from livekit.agents.voice import MetricsCollectedEvent
from livekit.agents import ChatContext, ChatMessage
import asyncio
from typing import AsyncIterable,AsyncGenerator
import uuid
import aiohttp
from dataclasses import dataclass
from graph import arun
from transcription import rewrite_text
from langchain_core.messages import AIMessage,ToolMessage,HumanMessage,SystemMessage


# 设置日志记录器，名为 basic-agent
logger = logging.getLogger("basic-agent")

# OpenAI API 密钥
API_KEY = "sk-7NAitPWQhdhwT2AR66Cc27E060664741A143E38eFbB33bE6"

# 配置语音转文本（STT）模块
stt = openai.STT(
    model="funasr",
    base_url= "http://192.168.103.21:31091/inference/ins-3ovzko3o1i.spiritx-model/v1",
    api_key=API_KEY
)

# 配置大预言模型（LLM）模块
llm = openai.LLM(
    model="rag-studio",
    base_url="http://192.168.103.21:11090/ai-supremegpt/api/v1",
    api_key="xzinfra-927be4d7a53e439cb4da8bfec56c31ac"
)

# 配置文本转语音（TTS）模块
tts= openai.TTS(
    model="Kokoro-82M-v1.1-zh",
    base_url="http://192.168.103.21:31091/spiritx-api/v1",
    api_key=API_KEY
)

# 设置系统指令和快速回复
INSTRUCTIONS = "你是一个语音助手,你可以用声音和用户交流,你很耐心,友好,并且有一些幽默感"
TURN_FAST_REPLY = """根据用户的输入,从下面的文本中选择一个最合适的回答用户
1. 好的,正在处理中
2. 好的,请稍等
3. 好的,请稍候
"""



# 定义 SimpleAgent 智能体类（继承自 Agent）
class SimpleAgent(Agent):
    # 构造函数
    def __init__(self):
        super().__init__(
            instructions=INSTRUCTIONS,
        )
        self.messages = []

    # async：异步函数
    # 进入会话时发出自我介绍
    async def on_enter(self):
        # 使用asyncio.gather同时执行两个异步任务
        self_introduce = "你好,我是新智智能体,期待与你对话"
        self.messages.append(AIMessage(content=self_introduce))
        await asyncio.gather(
            self.session.say(self_introduce),
        )

    # 用户话轮结束，将内容存入历史，并回复“好的，请稍等”
    async def on_user_turn_completed(
        self, turn_ctx: ChatContext, new_message: ChatMessage,
    ) -> None:
        user_input = new_message.text_content
        self.messages.append(HumanMessage(content=user_input))
        await self.session.say('好的,请稍等')

    # LLM 节点
    async def llm_node(self, chat_ctx, tools, model_settings):
        async for (type,text) in arun(self.messages):
            if type == "text":
                yield text
            elif type == "message":
                self.messages.append(AIMessage(content=text))

    # TTS 节点，对文本先 rewrite_text，再调用默认 TTS 节点合成音频
    async def tts_node(self, text: AsyncIterable[str], model_settings: ModelSettings) -> AsyncIterable[rtc.AudioFrame]:
        # Insert custom text processing here
        async def process_text():
            async for t in text:
                result = rewrite_text(t)
                yield result

        async for frame in Agent.default.tts_node(self, process_text(), model_settings):
            yield frame
        

# 预热函数，启动时预加载 VAD 模型，防止后续加载耗时
def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()
    

# 会话主入口
# 向日志中增加房间信息
async def entrypoint(ctx: JobContext):
    # each log entry will include these fields
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }

    # 新建会话，绑定 STT，LMM，TTS，turn detection 等模块，设置最小中断时长
    session = AgentSession(
        userdata={},
        llm=llm,
            stt=stt,
            tts=tts,
        vad=ctx.proc.userdata["vad"],
        # any combination of STT, LLM, TTS, or realtime API can be used
        # use LiveKit's turn detection model
        turn_detection=MultilingualModel(),
        min_interruption_duration= 2,
    )

    # 实例化指标采集器
    # log metrics as they are emitted, and total usage after session is over
    usage_collector = metrics.UsageCollector()


    # 注册事件回调，每当收集到指标时记录日志并累计数据
    @session.on("metrics_collected")
    def _on_metrics_collected(ev: MetricsCollectedEvent):
        metrics.log_metrics(ev.metrics)
        usage_collector.collect(ev.metrics)

    # 定义会话结束时的日志回调，输出使用统计
    async def log_usage():
        summary = usage_collector.get_summary()
        logger.info(f"Usage: {summary}")

    # shutdown callbacks are triggered when the session is over
    ctx.add_shutdown_callback(log_usage)

    # 启动会话，传入自定义智能体，设置输入输出选项，启用实时转录；然后连接房间
    await session.start(
        agent=SimpleAgent(),
        room=ctx.room,
        room_input_options=RoomInputOptions(
        ),
        room_output_options=RoomOutputOptions(transcription_enabled=True),
    )

    # join the room when agent is ready
    await ctx.connect()

# 主程序入口
if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            prewarm_fnc=prewarm,
        ),
    )