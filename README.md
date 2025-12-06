<div align="center">
  <p align="center">
    <img src="docs/images/parallax.png" width="720">
  </p>
</div>

# Parallax

Parallax 是 Gradient 开发的去中心化推理引擎，让你在分布式节点上托管大模型，并内置虚拟小镇（World）模拟模块：可调时间流速、AI 驱动人物、命运事件、持久化与多世界管理。

## 功能亮点
- 分布式推理：节点通过 Lattica P2P 通信，支持流水线并行、KV 缓存管理、动态路由。
- 多后端支持：GPU（SGLang/vLLM）、Mac（MLX-LM）。
- CLI/前端：`parallax run/join/chat`，React 前端可控制时间流、查看事件流与角色。
- 虚拟小镇（World）：
  - 时间控制：start/stop/step/倍速。
  - 事件/Fate：随机相遇、坏运气等规则，可扩展；事件生成情境并调用 LLM 生成对话。
  - 人格漂移与记忆：事件影响关系，自动记录记忆并可合并摘要。
  - 持久化与多世界：`data/worlds/<world_id>/world.json` + `event.log`，支持创建/列出/切换世界。
  - 语言设定：世界默认语言、角色语言/理解力，输出可强制全局语言或按角色语言。
  - 使用文件：[docs/world/README.md](docs/world/README.md)
  - 
  - 

## 快速开始
- 安装指南：[docs/user_guide/install.md](docs/user_guide/install.md)
- 入门指南：[docs/user_guide/quick_start.md](docs/user_guide/quick_start.md)

## 主要后端组件
- `src/parallax/cli.py`：CLI 入口，管理 run/join/chat。
- `src/backend/main.py`：FastAPI 主应用，服务前端与世界接口。
- `src/parallax`、`src/scheduling`：分布式推理、调度与执行。
- `src/world`：虚拟小镇核心（时间、状态、命运、LLM、持久化、多世界）。

## 主要前端页面
- `src/frontend`：React + Vite，`#/world` 提供时间控制、事件流与角色详情。

## 贡献
欢迎 Issue/PR！参考 [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) 获取贡献指南。

## 许可证
[LICENSE](LICENSE)
