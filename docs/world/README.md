# World 模块说明

这是虚拟小镇/World 子系统的文档目录。暂存架构、协议和设计草稿，后续可以拆分为更细的指南（API、前端、事件规则等）。

## 事件类型与频率配置（FateRule）
- 事件由 `FateRule` 生成：包含 `id`, `trigger`（如 tick）、`condition`（触发条件）、`factory`（产出事件列表），以及 `weight`（用于概率或排序）。
- 添加事件类型：
  1. 在 `world.fate.engine.build_default_rules` 里新增规则，或写新的规则列表并注册：`engine.register_rule(FateRule(...))`。
  2. 在 `factory` 函数中创建 `Event(type="your_type", ...)`；可按需要传入 actors/location/payload。
- 控制频率的做法：
  - 基于时间：在 `condition` 中使用 `store.world.epoch % N == 0` 控制每 N tick 触发。
  - 基于概率：在 `factory` 前加随机判断 `if random.random() > p: return []`，或使用 `weight` 作为概率阈值。
  - 基于背景/标签：`condition` 检查 `store.world.background` 或自定义的 `env_state`、地点/角色标签。
- 示例（伪代码）：
  ```python
  def factory(store, tick):
      if random.random() > 0.3:  # 30% 概率
          return []
      actors = pick_two(store)
      return [Event(id=..., type="festival", scheduled_for=tick, location_id="square", actors=actors)]

  rule = FateRule(
      id="festival",
      trigger="tick",
      condition=lambda s: s.world.epoch % 24 == 0,  # 每 24 tick 检查一次
      factory=factory,
      weight=0.3,
  )
  engine.register_rule(rule)
  ```
- 调整频率：通过修改 `condition` 的周期、`weight`、`random` 概率，或在 `factory` 中根据 `store` 状态返回空列表。

## 日志（NDJSON）
- 位置：`data/world/event.log`（自动创建目录），每条事件/对话以一行 JSON 追加写入。
- 追加：`WorldStore.append_log` 会同步写入内存与文件（最佳努力）。
- 查询：`GET /world/logs/tail?limit=10&kind=event|dialogue` 返回尾部日志（优先读取文件，便于跨进程/重启后查看）。

## 地图/坐标
- 规划见 `docs/world/map_spec.md`，地图存放 `data/worlds/<world_id>/map.json`。
- 采用平面 XY 坐标，支持单点地点 `locations` 与范围场景 `zones`。
- 后续会提供地点/移动/距离筛选 API。

## 基础 API（前端可用）
- GET `/world/world`：世界快照（含 time_scale、locations、characters 概要等）。
- POST `/world/world/time-scale`：设定 time_scale。
- POST `/world/characters`：创建角色。
- GET `/world/characters`：角色列表；GET `/world/characters/{id}`：角色详情。
- GET `/world/characters/{id}/memories?limit=`：角色记忆列表。
- POST `/world/characters/{id}/memories/summarize?limit=`：手动合并摘要记忆（默认合并 recent，保留 summary，供 prompt 使用）。
- GET `/world/events?status=&limit=`：事件列表（可筛 status、限制数量）。
- POST `/world/events`：创建事件。
- POST `/world/simulate/step`：推进一 tick。
- POST `/world/simulate/start`：后台连续运行。
- POST `/world/simulate/stop`：暂停循环。
- GET `/world/logs/tail?limit=&kind=`：尾部日志，可筛类型。
- 世界管理：
  - GET `/world/worlds`：列出世界，返回当前 world_id。
  - POST `/world/worlds`：创建世界，body 需包含 `id`，可选 `name`、`background`、`default_language`、`force_default_language`。
  - POST `/world/worlds/select`：切换世界，body `{ "id": "<world_id>" }`。
- 自定义事件：
  - POST `/world/events` 注入任意事件，设置 `type/actors/payload/effects/scheduled_for`。`scheduled_for=0` 即刻处理；`effects` 可直接修改关系/状态/属性（如 `{"target":"c1","field":"rel:c2","delta":1.0}`）。

### 添加人物
- 使用 `POST /world/characters` 创建：
  ```json
  {
    "id": "char-1",
    "name": "Alice",
    "age": 20,
    "role": "villager",
    "attributes": {"empathy": 0.7, "curiosity": 0.6},
    "traits": {"kind": 0.6, "brave": 0.4},
    "states": {"mood": 0.5},
    "flags": {"alive": true},
    "location_id": "loc-1"
  }
  ```
- 查询：`GET /world/characters` 列表，`GET /world/characters/{id}` 详情。

## LLM 配置
- 环境变量：
  - `WORLD_LLM_ENDPOINT`：默认 `http://localhost:3001/v1/chat/completions`
  - `WORLD_LLM_MODEL`：可选，显式指定模型名称
  - `WORLD_LLM_TEMPERATURE`：默认 `0.7`
  - `WORLD_LLM_SYSTEM_PROMPT`：默认 “You are narrating a small town simulation. Be concise.”
  - `WORLD_LLM_TIMEOUT`：请求超时秒数，默认 15
  - `WORLD_LLM_STOP`：stop tokens，默认 `<think>,</think>`（逗号分隔）
  - `WORLD_LLM_MAX_TOKENS`：每次生成的最大 token 数，默认 256
- 代码默认：缺省值同上；可在 `HttpLLMClient` 初始化时覆盖。
- 可选：在项目根目录放置 `.env`，内容为以上键值，后端启动时会自动加载：
  ```
  WORLD_LLM_ENDPOINT=http://localhost:3001/v1/chat/completions
  WORLD_LLM_MODEL=Qwen/Qwen3-1.8B-Instruct
  WORLD_LLM_TEMPERATURE=0.4
  WORLD_LLM_SYSTEM_PROMPT=请用简体中文回答，简洁，无思维链。
  WORLD_LLM_MAX_TOKENS=256
  ```
***

## 多世界管理与持久化
- 世界文件路径：`data/worlds/<world_id>/world.json`；日志：`data/worlds/<world_id>/event.log`。
- API：
- `GET /world/worlds`：列出世界，返回当前 world_id。
- `POST /world/worlds`：创建世界，body 需包含 `id`，可选 `name`、`background`、`default_language`、`force_default_language`。
- `POST /world/worlds/select`：切换世界，body `{ "id": "<world_id>" }`。
- 世界/角色变更会写入对应 world.json；日志按世界分目录。
***
## 启动与测试
1) 启动后端（复用 Parallax FastAPI）  
   ```bash
   # 在仓库根目录
   python -m parallax.cli run  # 或按你的启动方式启动 backend/main.py
   ```
   确保 `WORLD_LLM_ENDPOINT` 可访问（默认 http://localhost:3001/v1/chat/completions）。

2) 调用世界接口（示例）  
   ```bash
   # 单步前进一个 tick
   curl -X POST http://localhost:3001/world/simulate/step

   # 启动连续运行
   curl -X POST http://localhost:3001/world/simulate/start

   # 停止连续运行
   curl -X POST http://localhost:3001/world/simulate/stop

   # 查看世界状态
   curl http://localhost:3001/world/world

   # 创建角色
   curl -X POST http://localhost:3001/world/characters \
     -H 'Content-Type: application/json' \
     -d '{"id":"char-1","name":"Alice","age":20,"role":"villager","location_id":"loc-1"}'

   # 查看日志尾部
   curl http://localhost:3001/world/logs/tail?limit=10

   # 切换到 myworld（若不存在可先创建）
   curl -X POST http://localhost:3001/world/worlds/select \
     -H 'Content-Type: application/json' \
     -d '{"id":"myworld"}'

   # 创建两个角色
   curl -X POST http://localhost:3001/world/characters \
     -H 'Content-Type: application/json' \
     -d '{"id":"c1","name":"Alice","age":20,"role":"villager","location_id":"loc-1"}'
   curl -X POST http://localhost:3001/world/characters \
     -H 'Content-Type: application/json' \
     -d '{"id":"c2","name":"Bob","age":22,"role":"villager","location_id":"loc-1"}'

   # 再推进一次 tick 并查看事件
   curl -X POST http://localhost:3001/world/simulate/step
   curl http://localhost:3001/world/events?limit=10
   ```

## 其他功能速览
- 语言设定：世界默认语言、角色语言/理解力；可强制全局语言输出或按角色语言输出。
- 人格漂移：事件类型对角色关系做小幅正/负调整。
- 记忆与摘要：事件自动生成记忆，按次数触发 LLM 摘要，`/characters/{id}/memories` 可查。
- 持久化与多世界：世界/角色存储于 `data/worlds/<world_id>/world.json`，日志同目录，支持多世界切换。***

3) 前端页面  
   - 路由 `#/world`：时间控制（start/stop/step）、事件流、角色列表+详情。  
   - 需先在 `src/frontend` 目录执行 `pnpm install && pnpm run dev`（或现有构建流程），并确保 API 路径 `/world/*` 可访问。
