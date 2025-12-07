# 地图与坐标规划（map.json）

目标：为世界增加坐标支持，便于根据距离筛选事件/场景与角色位置。

## 存储位置
- 每个世界：`data/worlds/<world_id>/map.json`
- 保持与 `world.json` 解耦；两者都可持久化。

## 基本格式（示例）
```json
{
  "locations": [
    {
      "id": "loc-1",
      "name": "中央广场",
      "coords": { "x": 0, "y": 0 },
      "tags": ["公共", "集会"],
      "description": "城市中心的广场，有喷泉和市场摊位。"
    },
    {
      "id": "loc-2",
      "name": "松林小径",
      "coords": { "x": 5, "y": 3 },
      "tags": ["森林", "小径"],
      "description": "通往山脚的林间小路，时常有采药人经过。"
    }
  ],
  "zones": [
    {
      "id": "zone-1",
      "name": "旧城区",
      "description": "老建筑聚集的城区，包含多个坐标点。",
      "coords": [
        { "x": -2, "y": 1 },
        { "x": -1, "y": 2 },
        { "x": -1, "y": 0 }
      ],
      "contains": ["loc-1"]
    }
  ]
}
```

说明：
- `locations`：单点坐标；`coords` 为平面 XY（浮点或整数）。
- `zones`：多点或多边形场景，用 `coords` 列表表达覆盖范围，可选 `contains` 列举包含的地点 id。
- 若场景很大（如森林、城镇），优先用 `zones` 表达范围；单点事件可用 `locations`。

## 距离筛选逻辑（规划）
- 距离函数：欧氏距离 `sqrt((dx)^2 + (dy)^2)`；zones 可取到最近点或质心。
- 事件/场景选择：
  - 角色位置在 `location_id`（或 zone），根据距离阈值挑选“近邻”角色/地点参与同一事件线。
  - 可选参数：`distance_limit`（如 5.0），超过不参加本场景。
- 移动：`POST /world/characters/{id}/move` 时更新 `location_id` 与可选子坐标。

## API 规划
- GET `/world/map`：返回 map.json（locations+zones）。
- POST `/world/map`：更新地图；或拆分为创建/更新地点与区域。
- GET `/world/locations`：列出地点（含 coords）。
- POST `/world/characters/{id}/move`：更新角色位置（location_id/coords）。
- GET `/world/locations/distance?id1=&id2=`：距离查询（可选）。

## 事件/场景中的使用
- Timeline/Scene 生成时，提示中加入地点描述/坐标/区域标签。
- 参与者筛选：优先选择与场景地点距离最近的若干角色。
- 日志：在 story/event 记录中附带 location_id/coords 以便复盘或可视化。
