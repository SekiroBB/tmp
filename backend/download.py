from livekit.plugins import openai, deepgram, silero

import logging
import json
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


logger = logging.getLogger("basic-agent")

API_KEY = "sk-7NAitPWQhdhwT2AR66Cc27E060664741A143E38eFbB33bE6"

stt = openai.STT(
    model="funasr",
    base_url= "http://192.168.103.21:31091/inference/ins-3ovzko3o1i.spiritx-model/v1",
    api_key=API_KEY
)

llm = openai.LLM(
    model="Qwen2.5-32B-Instruct-GPTQ-Int4",
    base_url="http://192.168.103.21:31091/spiritx-api/v1",
    api_key=API_KEY
)

tts= openai.TTS(
    model="Kokoro-82M-v1.1-zh",
    base_url="http://192.168.103.21:31091/spiritx-api/v1",
    api_key=API_KEY
)

INSTRUCTIONS = "你是一个语音助手,你可以用声音和用户交流,你很耐心,友好,并且有一些幽默感"
TURN_FAST_REPLY = """根据用户的输入,从下面的文本中选择一个最合适的回答用户
1. 好的,正在处理中
2. 好的,请稍等
3. 好的,请稍候
"""



class SimpleAgent(Agent):
    def __init__(self):
        super().__init__(
            instructions=INSTRUCTIONS,
        )
        
    async def on_enter(self):
        # 使用asyncio.gather同时执行两个异步任务
        await asyncio.gather(
            self.session.say('你好,我是新智智能体,期待与你对话'),
            self._create_ragflow_session()
        )
    
    async def _create_ragflow_session(self):
        sessionId = await ragflow_chat_new_session(RAGFLOW_CHAT_ID)
        print(f"ragflow_chat_new_session: {sessionId}")
        self.session.userdata.ragFlowSessionId = sessionId
        
        
    async def on_user_turn_completed(
        self, turn_ctx: ChatContext, new_message: ChatMessage,
    ) -> None:
        await self.session.say('好的,请稍等')
        pass
        
    async def llm_node(self, 
                       chat_ctx: ChatContext,
                       tools: list[FunctionTool], 
                       model_settings: ModelSettings) -> AsyncIterable[ChatChunk | str]:
        user_input = chat_ctx.items[-1].text_content
        chat_id = RAGFLOW_CHAT_ID
        session_id = self.session.userdata.ragFlowSessionId
        print(f"ragflow_chat_completion: {user_input}, {chat_id}, {session_id}")
        
        async for chunk in ragflow_chat_completion(user_input,chat_id,session_id):
            yield chunk
        
            
    async def tts_node(self,text:AsyncIterable[str],
                       model_settings: ModelSettings):
        print("enter tts_node")
        print(text)
        return Agent.default.tts_node(
            self, text,model_settings
        )
        
        

def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()
    
    
async def entrypoint(ctx: JobContext):
    # each log entry will include these fields
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }

    session = AgentSession[MySessionInfo](
        userdata=MySessionInfo(),
        llm=llm,
            stt=stt,
            tts=tts,
        vad=ctx.proc.userdata["vad"],
        # any combination of STT, LLM, TTS, or realtime API can be used
        # use LiveKit's turn detection model
        turn_detection=MultilingualModel(),
        min_interruption_duration= 2,
    )

    # log metrics as they are emitted, and total usage after session is over
    usage_collector = metrics.UsageCollector()

    @session.on("metrics_collected")
    def _on_metrics_collected(ev: MetricsCollectedEvent):
        metrics.log_metrics(ev.metrics)
        usage_collector.collect(ev.metrics)

    async def log_usage():
        summary = usage_collector.get_summary()
        logger.info(f"Usage: {summary}")

    # shutdown callbacks are triggered when the session is over
    ctx.add_shutdown_callback(log_usage)

    await session.start(
        agent=SimpleAgent(),
        room=ctx.room,
        room_input_options=RoomInputOptions(
        ),
        room_output_options=RoomOutputOptions(transcription_enabled=True),
    )

    # join the room when agent is ready
    await ctx.connect()


if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            prewarm_fnc=prewarm,
        ),
    )