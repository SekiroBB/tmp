# VoiceAgent - 实时语音智能助手

VoiceAgent 是一个基于 LiveKit 的实时语音智能助手系统，支持用户与 AI 助手进行自然语音对话。

## 🚀 项目特性

- **实时语音交互**: 基于 LiveKit 实现低延迟的实时语音通话
- **智能对话**: 集成多种 AI 模型，支持自然语言理解和生成
- **多知识库支持**: 支持教师信息、新闻等多种知识库查询
- **Web 界面**: 现代化的 Vue.js 前端界面
- **容器化部署**: 完整的 Docker 部署方案

## 📁 项目结构

```
voiceagent/
├── frontend/          # Vue.js 前端应用
├── backend/           # Python 后端服务
│   ├── main.py       # FastAPI 服务入口
│   └── simple-agent.py # LiveKit Agent 入口
├── build/            # 部署配置
│   └── docker-compose.yml
└── readme.md
```

## 🛠️ 技术栈

### 前端
- **Vue 3** - 现代化前端框架
- **TypeScript** - 类型安全的 JavaScript
- **LiveKit Client** - 实时音视频通信
- **Vite** - 快速构建工具

### 后端
- **FastAPI** - 高性能 Python Web 框架
- **LiveKit Agents** - AI 语音助手框架
- **LangGraph** - 对话流程管理
- **LangChain** - LLM 应用开发框架

### 部署
- **Docker** - 容器化部署
- **Docker Compose** - 多服务编排
- **LiveKit Server** - 实时通信服务器

## 🚀 快速开始

### 使用 Docker 部署

1. 克隆项目
```bash
git clone <repository-url>
cd voiceagent
```

2. 启动服务
```bash
cd build
docker-compose up -d
```

3. 访问应用
```
http://localhost:28010
```

### 开发环境

详细开发指南请参考 [dev.md](./dev.md)

## 📋 功能特性

### 实时语音通话
- 支持多人语音通话
- 实时音频流处理
- 自动语音活动检测

### 智能对话
- 自然语言理解
- 上下文感知对话
- 多轮对话支持

### 知识库查询
- 教师信息查询
- 新闻资讯查询
- 智能路由选择

## 🔧 配置说明

### AI 模型配置
- STT: FunASR 语音识别
- LLM: RAG Studio 大语言模型
- TTS: Kokoro 语音合成
