# PentaFlow 五维推演

<div align="center">

![Version](https://img.shields.io/badge/version-2.0.0-blue.svg)
![License](https://img.shields.io/badge/license-AGPL--3.0-green.svg)
![Python](https://img.shields.io/badge/python-3.9+-blue.svg)

**基于多智能体协作的AI事件影响力分析系统**

[✨ 2.0更新](#-20版本更新) • [功能特性](#-功能特性) • [快速开始](#-快速开始) • [使用方法](#-使用方法) • [API消耗说明](#-api消耗说明) • [项目定位](#-项目定位)

</div>

---

## ✨ 2.0版本更新

### 🚀 重大更新内容

#### 1. 界面全面重构
- **技术栈升级**: 从原生 JavaScript 迁移到 **React + Vite** 现代化架构
- **实时交互**: 新增 WebSocket 实时推送，智能体分析过程实时可见
- **极客风格UI**: 全新设计的深色主题界面，矩阵背景动画，更具科技感
- **响应式布局**: 横向双栏布局（输入区+控制台），瀑布流式轮次展示

#### 2. 功能增强
- **事件自动补全**: 输入事件名称后，AI 自动搜索并补全描述和分类
- **五维星图**: 实时雷达图展示技术渗透、经济颠覆、就业波动、流程重构、伦理风险五维指标
- **思维演变线**: 可视化展示多轮推演的综合得分变化趋势
- **Markdown渲染**: 各方观点和总结支持 Markdown 格式，阅读体验更佳
- **推演总结报告**: 多轮推演终止后自动生成 LLM 总结报告，包含时间线和整体趋势分析

#### 3. 性能优化
- **关闭思考模式**: LLM (`qwen3.5-plus`) 启用 `enable_thinking: false`，响应速度提升 50%+
- **API 消耗**: Tokens 消耗并未因关闭思考模式而降低，但获取结果更快
- **前端构建**: 使用 Vite 构建，加载速度更快

#### 4. 安全性提升
- **API Key 管理**: 改为用户手动输入模式，不再预置任何 API Key
- **本地存储**: API Key 仅存储在浏览器 localStorage 中，服务器不保存
- **弹窗配置**: 首次使用需配置 Key，右上角可随时重新配置

#### 5. 移除内容
- **删除 Demo 模式**: 移除了 `demo/simulation.html` 离线演示版本
- 原因：新 React 版本的实时交互效果更好，Demo 版本已过时

---

---

## 📋 系统概述

PentaFlow 五维推演是基于 FastAPI 和现代异步架构的 AI 事件影响力分析系统。通过 7 个不同视角的智能体，对 AI 行业事件进行多维度分析和推演，并且将之前分析的结果带入下一轮的推演，评估事件的影响。

**GitHub仓库**: https://github.com/liu222222222222/PentaFlow

<div align="center">

### 🎬 快速体验演示模式

**[👉 点击此处直接进入演示页面](https://liu222222222222.github.io/PentaFlow/)**

• [🚀 开始使用](#-快速开始)

</div>

### 核心特性

- ⚡ **异步架构** - 基于 FastAPI 和 async/await 的高性能实现
- 🔌 **API 驱动** - 完整的 RESTful API 支持
- 🔍 **智能搜索** - 集成 Tavily 搜索 API
- 🤖 **多智能体** - 7 个不同视角的 AI 智能体协同分析
- 📊 **五维评估** - 技术渗透、经济颠覆、就业波动、流程重构、伦理风险五维指标
- 🎨 **极客风格 UI** - React + Vite 构建的现代化深色主题界面
- 🔄 **多轮推演** - 支持多轮推演，结果带入下一轮
- 📈 **时间线分析** - 自动生成思想演变时间线
- ✨ **实时交互** - WebSocket 实时推送分析进度
- 🤖 **事件补全** - AI 自动搜索补全事件信息
- 📝 **Markdown 渲染** - 支持富文本格式的观点展示

### 7 个智能体角色

| 智能体 | 视角 | 关注维度 |
|--------|------|----------|
| 🏦 **资本代言人** | 投资机构 | 商业价值、ROI、市场份额 |
| 🔧 **技术执行者** | 工程师 | 技术可行性、工程实现 |
| 🎨 **创意指挥官** | 品牌营销 | 品牌认知、传播力 |
| 👁️ **社会观察员** | 公众伦理 | 社会影响、伦理问题 |
| ⚖️ **政策监管者** | 政府监管 | 合规性、安全可控 |
| 👤 **用户代表** | 终端用户 | 易用性、实用价值 |
| 🤔 **旁观者** | 独立观察 | 分析总结、识别冲突/共识 |

---

## 🚀 快速开始

### 前置要求

- Python 3.9+
- 阿里云DashScope API密钥（用于实际推演）
- Tavily搜索API密钥（用于实际推演）

### 快速开始

#### 1. 克隆项目

```bash
git clone https://github.com/liu222222222222/PentaFlow.git
cd PentaFlow
```

#### 2. 安装依赖

```bash
pip install -r requirements.txt
```

#### 3. 配置环境

```bash
# 复制配置文件
cp .env.example .env

# 编辑 .env 文件，填写必需的API keys
# - LLM_API_KEY: 阿里云DashScope API密钥
# - TAVILY_API_KEY: Tavily搜索API密钥
```

获取API密钥：
- **阿里云DashScope**: https://dashscope.console.aliyun.com/apiKey
- **Tavily**: https://tavily.com/

#### 4. 运行Web服务器

```bash
python run_server.py
```

服务器将在 `http://localhost:8000` 启动。

#### 5. 访问Web界面

在浏览器中打开 `http://localhost:8000` 开始使用。

---

## 📖 使用方法

### 第一步：配置API Keys

首次使用时，系统会弹出配置界面，需要填写：

1. **大模型 API Key** - 阿里云DashScope API密钥（必填）
   - 使用模型：`qwen3.5-plus`
   
2. **接口地址** - 默认使用阿里云DashScope接口地址

3. **搜索 API Key** - Tavily搜索API密钥（必填）

### 第二步：输入事件信息

填写以下信息：
- **事件名称** - 如"OpenClaw在中国大陆的爆火"
- **事件描述** - 详细描述事件内容（可选，可自动补全）
- **事件类别** - 选择合适的类别（技术突破、产品发布、政策法规等）

### 第三步：智能补全信息

点击"✨ Enrich Event"按钮，系统会：
- 搜索相关资讯
- 提取关键信息
- 自动补全事件描述和分类

补全完成后，"▶ Start Analysis"按钮才会启用。

### 第四步：开始推演

点击"▶ Start Analysis"按钮，系统将：
- 启动7个智能体并行分析
- 每个智能体从不同视角评估事件
- 实时显示分析进度和日志
- 生成五维影响力雷达图
- 旁观者进行综合总结

### 第五步：多轮推演

每轮推演完成后，可以选择：
- **继续推演** - 将本轮结果带入下一轮，深化分析
- **中止推演** - 停止推演并生成总结报告（2轮及以上）

### 第六步：推演总结报告

如果进行了2轮及以上的推演，点击"终止推演"后，系统会：
- 分析多轮推演数据
- 生成每个智能体的思想演变轨迹
- 提供整体趋势分析
- 展示旁观者的关键洞察
- 以 Markdown 格式呈现完整的推演总结报告

---

## 📊 五维评估指标

1. **技术渗透率** - 技术扩散和采用速度
2. **经济颠覆度** - 对商业模式和市场的影响
3. **就业波动率** - 对就业市场的冲击
4. **流程重构度** - 工作流程和习惯的改变
5. **伦理风险值** - 伦理和社会风险

---

## 🎨 界面展示

### 极客风格设计

PentaFlow 2.0 采用全新的极客风格设计：

- 🌙 **深色主题** - 护眼的深色背景，代码风格配色
- 🎬 **矩阵动画** - 背景动态矩阵雨效果
- 📊 **实时雷达图** - 五维影响力实时可视化
- 🖥️ **双栏布局** - 左侧输入，右侧控制台实时输出
- 📝 **Markdown 渲染** - 观点总结支持富文本格式

### 核心界面

1. **API Key 配置弹窗** - 首次使用引导配置
2. **事件输入面板** - 简洁的表单设计，支持自动补全
3. **实时控制台** - WebSocket 推送的实时日志
4. **智能体面板** - 7个智能体并行展示分析进度
5. **五维星图** - 雷达图展示多维度评分
6. **推演总结弹窗** - 多轮推演后的综合分析报告

---

## 💰 API消耗说明

### 每轮推演消耗

- **阿里云百炼 API**: 约20次请求
  - 7个智能体 × 2-3次请求（搜索+分析）
  
- **Tavily搜索 API**: 约20次请求
  - 7个智能体 × 2-3次搜索请求

### 典型场景总消耗

| 场景 | 阿里云API | TavilyAPI | 总计 |
|------|-----------|-----------|------|
| 2轮推演 + 时间线 | 约60次 | 约60次 | 约120次 |
| 5轮推演 + 时间线 | 约120次 | 约120次 | 约240次 |

### 推演时间估算

- **单轮推演**: 5-10分钟
  - 取决于网络速度和API响应时间
  - 搜索请求：每个智能体2-3秒
  - LLM分析：每个智能体30-60秒
  
- **5轮推演**: 约1小时
  - 推演：5 × 8分钟 = 40分钟
  - 时间线生成：约2-5分钟

### 消耗原因分析

为什么消耗这么多请求？

1. **多智能体并发**: 每轮有7个智能体同时工作
2. **搜索+分析**: 每个智能体需要先搜索，再分析
3. **多轮迭代**: 每轮都要重新搜索和分析
4. **时间线生成**: 需要分析所有轮次数据，生成总结

---

## 🎯 项目定位

### 坦诚说明

PentaFlow 五维推演是一个个人灵光一闪的项目，旨在为开源社区贡献一个实用的AI事件分析工具。

**关于功能的说明**：
- 这个软件的功能对于熟悉Agent运作模式的开发者来说可能显得"有点勉强"，其实用coze等现成工具，也可以实现类似的效果。
- 能搞定API key的一般都晓得agent的运作模式
- 作为一个个人项目，它是一个概念验证和示例

**项目价值**：
- 提供了一个完整的、可运行的多智能体系统示例
- 展示了多智能体协作、多轮推演、实时进度推送等技术的实际应用
- 对于学习和研究AI Agent系统的开发者来说，具有参考价值
- 可以作为基础框架进行扩展和改进
- 可以作为一个简单的项目，来进行简单的语义分析，或者可以做一个简单的产品，短平快的分析一个AI事件
- 2.0版本的 React + Vite 架构为现代 Web 应用开发提供了参考

**开源初衷**：
- 分享想法，交流技术
- 为社区提供一个可扩展的基础框架
- 欢迎大家fork、改进、PR

---

## 📁 项目结构

```
PentaFlow/
├── app/                    # 应用主目录
│   ├── main.py            # FastAPI 应用入口
│   ├── api/               # API 路由
│   │   ├── v1/            # API v1 版本
│   │   │   ├── analysis.py # 分析接口
│   │   │   └── events.py   # 事件接口
│   │   └── ws.py          # WebSocket 接口
│   ├── services/          # 业务逻辑层
│   │   ├── agent_service.py    # 智能体服务
│   │   ├── analysis_service.py  # 分析服务
│   │   ├── llm_service.py      # LLM服务
│   │   ├── search_service.py   # 搜索服务
│   │   └── websocket_service.py # WebSocket服务
│   ├── models/            # 数据模型
│   │   └── metrics.py     # 指标模型
│   └── static/            # 静态文件
│       └── frontend/      # React 构建输出
├── frontend/              # React 前端源码
│   ├── src/               # 源代码
│   │   ├── App.jsx        # 主应用组件
│   │   ├── App.css        # 样式文件
│   │   └── main.jsx       # 入口文件
│   ├── package.json       # 依赖配置
│   └── vite.config.js     # Vite 配置
├── config/                # 配置
│   ├── settings.py        # 配置设置
│   └── .env.example       # 环境变量示例
├── data/                  # 数据目录
├── logs/                  # 日志目录
├── run_server.py          # 服务器启动脚本
├── requirements.txt       # 依赖列表
├── .env.example          # 环境变量示例
└── README.md             # 项目说明
```

---

## ⚙️ 配置选项

在 `.env` 文件中配置：

```env
# 必需配置
LLM_API_KEY=sk-your-dashscope-api-key
TAVILY_API_KEY=tvly-your-tavily-api-key

# 可选配置
LLM_BASE_URL=https://coding.dashscope.aliyuncs.com/v1
LLM_MODEL=qwen3.5-plus
MAX_ROUNDS=5
MIN_ROUNDS=3
TARGET_SCORE_THRESHOLD=0.80
CONVERGENCE_THRESHOLD=0.03
MAX_SEARCH_RESULTS=5
PORT=8000
DEBUG=False
```

---

## 🔧 技术栈

- **后端**: FastAPI, asyncio, Python 3.9+
- **前端**: React 18, Vite, Framer Motion
- **UI组件**: Lucide React, Recharts
- **LLM**: 阿里云DashScope (qwen3.5-plus, enable_thinking: false)
- **搜索**: Tavily API
- **通信**: WebSocket, HTTP
- **数据**: JSON

---

## 📝 开发者信息

- **开发者**: liuyang
- **GitHub**: https://github.com/liu222222222222/
- **版本**: 2.0.0
- **发布日期**: 2026-03-26
  
- 欢迎大家关注我的 杠杆说AI 公众号：
<img width="400" height="400" alt="image" src="https://github.com/user-attachments/assets/8645b2f6-f133-4d81-b47b-da9871cf2099" />

---

## 📄 开源协议

本项目采用 **AGPL-3.0** 协议开源。

AGPL-3.0 是一个 copyleft 协议，要求：
- 如果你修改了代码并分发，必须开源修改后的代码
- 如果你在网络上提供此软件的服务，必须提供源代码
- 用户可以自由使用、修改和分发

选择 AGPL-3.0 的原因：
- 这是一个涉及AI Agent的系统，源代码透明很重要
- 希望促进开源社区对AI Agent技术的探索
- 防止此技术被用于闭源的商业服务而不回馈社区

```
PentaFlow 五维推演
Copyright (C) 2026 liuyang

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published
by the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
```

---

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

### 贡献方式

1. Fork 本项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

### 开发建议

- 保持代码风格一致
- 添加必要的注释
- 更新相关文档
- 确保测试通过

---

## ❓ 常见问题

### Q: API消耗太大怎么办？

A: 可以通过以下方式减少消耗：
- 减少推演轮数
- 使用缓存机制（可自行开发）

### Q: 推演速度慢怎么办？

A: 推演速度主要受限于：
- API响应速度
- 网络延迟
- 每个智能体的分析时间

建议：
- 确保网络稳定
- 使用高质量的API服务
- 考虑并发优化（可自行开发），但是不建议，最好是逐个推演，最终等待旁观者汇总，然后带入下一轮。

### Q: 搜索API不可用怎么办？

A: 目前使用Tavily API，如果不可用：
- 检查API key是否正确
- 检查网络连接
- 考虑添加其他搜索服务（可自行开发）

### Q: 可以使用其他LLM吗？

A: 可以，但需要修改配置：
- 修改 `.env` 中的 `LLM_BASE_URL`
- 确保新的API兼容OpenAI接口协议

---

## 📄 许可证

```
Copyright (C) 2026 liuyang

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published
by the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
```

---

## 🙏 致谢

感谢以下开源项目和服务：

- FastAPI - 现代化的Python Web框架
- 阿里云DashScope - 提供强大的LLM服务
- Tavily - 提供高质量的搜索API
- 所有开源贡献者

---

<div align="center">

**Made with ❤️ by liuyang**

[⬆ 回到顶部](#pentaflow-五维推演)

</div>
