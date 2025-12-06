# 世界设定档案格式说明

世界与角色的设定存放在 `data/worlds/<world_id>/world.json`，启动时会自动读取；事件日志在同目录 `event.log`。以下描述 `world.json` 的主要结构。

## world.json 顶层字段
- `id`: 世界 ID。
- `name`: 世界名称。
- `background`: 世界背景描述。
- `epoch`: 当前时间步（tick）。
- `time_scale`: 时间倍率。
- `default_language`: 世界默认语言（如 `zh-CN`）。
- `force_default_language`: 是否强制输出使用默认语言（true/false）。
- `env_state`: 环境状态（自由扩展的键值）。
- `locations`: 地点集合（字典，key 为 location_id）。
- `characters`: 角色集合（字典，key 为 character_id）。
- `memories`: 记忆集合（字典，key 为 memory_id）。
- `events`: 事件集合（字典，key 为 event_id；多用于队列/缓存）。
- `logs`: 运行时日志（不持久化到文件，世界快照会忽略）。

## locations[location_id]
```json
{
  "id": "loc-1",
  "name": "Square",
  "kind": "center",
  "connections": ["loc-2"],
  "tags": ["public"]
}
```

## characters[character_id]
```json
{
  "id": "c1",
  "name": "Alice",
  "age": 20,
  "role": "villager",
  "language": "zh-CN",
  "comprehension": {"en-US": 0.6},
  "attributes": {"empathy": 0.7},
  "traits": {"kind": 0.6},
  "states": {"mood": 0.5},
  "relationships": {"c2": 0.8},
  "memory_ids": ["mem-123"],
  "goals": [],
  "flags": {"alive": true},
  "location_id": "loc-1"
}
```

## memories[memory_id]
```json
{
  "id": "mem-123",
  "owner_id": "c1",
  "summary": "在广场和 c2 问候聊天。",
  "salience": 1.0,
  "tags": ["random_encounter"],
  "created_at": 10,
  "decay_rate": 0.01
}
```

## events[event_id]
```json
{
  "id": "evt-1",
  "type": "user_story",
  "created_at": 0,
  "scheduled_for": 0,
  "location_id": "loc-1",
  "actors": ["c1", "c2"],
  "payload": {"note": "在广场偶遇"},
  "origin": "manual",
  "status": "scheduled",
  "effects": [
    {"target": "c1", "field": "rel:c2", "delta": 0.2},
    {"target": "c2", "field": "state:mood", "delta": 0.1}
  ]
}
```

## 日志文件
- `event.json`：完整 NDJSON 记录（含全部字段，含原始 dialogue/incident）。
- `event.log`：纯文本，去除 `<think>`，格式示例：
  ```
  [1700000000] tick=5 type=random_encounter | incident=... | desc=... | dialogue=...
  ```
- `incident.json`：仅保存 incident（标题/描述），逐行 JSON。

## 编辑与加载
- 直接编辑 `world.json` 可调整设定；重启或切换世界时会重新加载。
- 角色/事件的新增/修改也可通过 API 完成，系统会自动写回 `world.json`。
