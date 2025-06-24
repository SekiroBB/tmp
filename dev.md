# VoiceAgent 开发指南

本文档为 VoiceAgent 项目的开发指南，详细介绍了如何搭建开发环境、理解项目架构以及进行开发工作。

## 📋 目录

- [项目概述](#项目概述)
- [开发环境搭建](#开发环境搭建)
- [项目架构详解](#项目架构详解)
- [后端开发](#后端开发)
- [前端开发](#前端开发)
- [调试指南](#调试指南)
- [部署指南](#部署指南)

## 🎯 项目概述

VoiceAgent 是一个实时语音智能助手系统，包含三个主要组件：

1. **FastAPI 后端服务** (`main.py`) - 提供 Web API 接口
2. **LiveKit Agent 服务** (`simple-agent.py`) - 处理语音对话逻辑
3. **Vue.js 前端应用** - 用户界面

## 🛠️ 开发环境搭建

### 系统要求

- Python 3.8+
- Node.js 18+
- Git

### 1. 克隆项目

```bash
git clone <repository-url>
cd voiceagent
```

### 2. 后端环境搭建

```bash
cd backend

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate     # Windows

# 安装依赖
pip install -r requirements.in
```

### 3. 前端环境搭建

```bash
cd frontend

# 安装依赖
pnpm install

# 启动开发服务器
pnpm dev
```

## 🏗️ 项目架构详解
项目基于 LiveKit Server基础设施运行.  
通过 Api 控制 LiveKit Server 创建房间后  
用户和 LiveKit Agent 进入同一个房间后进行语音交互


### 后端架构

```
backend/
├── main.py              # FastAPI 服务入口
├── simple-agent.py      # LiveKit Agent 入口
├── graph.py            # LangGraph 对话流程
├── transcription.py    # 文本处理工具
├── requirements.in     # Python 依赖
└── Dockerfile         # 容器化配置
```

### 前端架构

```
frontend/
├── src/
│   ├── components/
│   │   ├── AudioCall.vue    # 主要通话组件
│   │   ├── AudioPicker.vue  # 音频设备选择
│   │   └── HelloWorld.vue   # 示例组件
│   ├── App.vue              # 根组件
│   └── main.ts              # 应用入口
├── package.json             # 项目配置
└── vite.config.ts          # Vite 配置
```

## 🔧 后端开发

### 1. LiveKit Server
使用 [Locally](https://docs.livekit.io/home/self-hosting/local/) 方式启动本地 LiveKit Server 服务

### 2. FastAPI 服务 (`main.py`)

**功能**: 提供 Web API 接口，主要处理房间创建和令牌生成。

**主要接口**:
- `GET /api/createRoom` - 创建新的语音房间

**启动方式**:
```bash
cd backend
python main.py --host ws://localhost:7880 \
               --api-key devkey \
               --api-secret secret
```

**开发要点**:
- 集成 LiveKit API 进行房间管理
- 支持命令行参数配置

### 3. LiveKit Agent 服务 (`simple-agent.py`)
使用 [LiveKit Agent](https://docs.livekit.io/agents/) 框架进行开发

**功能**: 处理实时语音对话，集成 STT、LLM、TTS 模型。

**核心组件**:
- **STT (Speech-to-Text)**: FunASR 语音识别
- **LLM (Large Language Model)**: RAG Studio 大语言模型
- **TTS (Text-to-Speech)**: Kokoro 语音合成
- **VAD (Voice Activity Detection)**: Silero VAD

**启动方式**:
```bash
cd backend
python simple-agent.py download-files # 只需要执行一次,目的下载一些vad之类的模型
python simple-agent.py start \
    --url ws://localhost:7880 \
    --api-key devkey \
    --api-secret secret
```

**开发要点**:
- 继承 `Agent` 类实现自定义逻辑
- 使用 `on_user_turn_completed` 处理用户输入
- 集成 LangGraph 进行对话流程管理

### 4. 对话流程管理 (`graph.py`)

**功能**: 使用 LangGraph 管理复杂的对话流程。

**主要特性**:
- 智能路由选择知识库
- 支持教师信息、新闻等多种知识库
- 流式响应处理

**核心流程**:
```
用户输入 → 路由选择 → 知识库查询 → 响应生成
```

## 🎨 前端开发

### 1. 技术栈

- **Vue 3** - 组合式 API
- **TypeScript** - 类型安全
- **LiveKit Client** - 实时音视频
- **Vite** - 构建工具

### 2. 主要组件

#### AudioCall.vue
**功能**: 主要的语音通话组件

**核心特性**:
- 房间连接管理
- 音频流处理
- 实时转录显示
- 音量可视化

**关键方法**:
```typescript
// 创建房间
const createRoom = async () => {
    const response = await fetch(`/api/createRoom`)
    return await response.json()
}

// 连接房间
const connectToRoom = async () => {
    room.value = new Room({
        adaptiveStream: true,
        dynacast: true,
        publishDefaults: {
            audioPreset: { maxBitrate: 64000 }
        }
    })
    // ... 事件监听
}
```

#### AudioPicker.vue
**功能**: 音频可视化组件

### 3. 开发命令

```bash
# 启动开发服务器
pnpm dev

# 构建生产版本
pnpm build

# 预览构建结果
pnpm preview
```

## 常见问题
### 1. 录音权限问题
浏览器为了安全考虑，只允许在以下情况下访问麦克风：
- 在 localhost 等本地开发环境中可以通过 HTTP 访问麦克风
- 在生产环境中必须使用 HTTPS 协议才能获取麦克风权限
- 如果使用 HTTP 协议访问非本地环境，浏览器将拒绝麦克风访问请求
所以本地开发调试可以使用 http , 部署到其他环境上使用时需要 SSL 证书

### 2. 基础镜像问题
项目中的 docker-compose.yml 和 Dockerfile 中使用的镜像都是
harbor.xz.com:8448/spiritx-platform 下的镜像,如果需要使用其他镜像,请自行调整

### 3. docker 部署问题
LiveKit Server 作为 WebRtc 的基础设施服务,需要的端口和权限比较多,所以需要使用 network: host 方式进行部署

## 📚 开发资源

### 文档链接
- [LiveKit 官方文档](https://docs.livekit.io/)
- [LiveKit Agent官方文档](https://docs.livekit.io/agents/)
- [Vue 3 官方文档](https://vuejs.org/)
- [FastAPI 官方文档](https://fastapi.tiangolo.com/)
- [LangGraph 文档](https://langchain-ai.github.io/langgraph/)
