# Virtual Town - Minimal Architecture Seed

Goal: a small, extensible simulation that can evolve into a “virtual town” with adjustable time flow, AI-driven characters, a fate/event system, and incremental feature growth.

## High-Level Components
- Simulation Core: drives ticks, time scaling, and progression hooks (events, character updates, world updates).
- World State: stores global settings (background, epoch, rules), location graph (places, zones), and environmental variables.
- Characters: entities with identity, attributes, dynamic traits, memories, relationships, and goals.
- Fate/Event Engine: schedules and emits events (random, scripted, or background-driven), resolves outcomes, spawns follow-up hooks.
- Interaction/LLM Layer: calls Parallax-backed models to generate dialogue, inner monologue, or decisions based on current state and prompts.
- Persistence: snapshot world/characters/events for save/load; append-only logs for reproducibility.
- API Layer: minimal HTTP endpoints to read/write core entities, post events, and advance simulation (keeps frontends/thin clients simple).

## Minimal Data Model (JSON-friendly)
- World:
  - id, name, background (string), epoch/time, time_scale (multiplier), env_state (dict).
  - locations: [{id, name, type, connections:[id], tags:[]}].
- Character:
  - id, name, age, role/occupation, attributes (e.g., strength, empathy, curiosity), traits (stable), states (mood/fatigue/health), relationships:[{target_id, type, score}], memory:[memory_id], goals:[goal_id], flags (alive, child).
- Memory:
  - id, owner_id, summary, salience (0-1), tags, created_at, decay_rate.
- Event:
  - id, type, created_at, scheduled_for, location_id, actors:[char_id], payload (dict), origin (fate/manual/system), status (scheduled|resolved|cancelled), effects:[{target, field, delta|set}].
- FateRule (for dynamic generation):
  - id, trigger (cron/tick/probability/world_tag), conditions (predicates over world/characters), templates (event types/payloads), weight.

## Simulation Loop (minimal)
1) Tick = base unit (e.g., 1 minute in-world). Real-time interval = tick_duration / time_scale.
2) On each tick:
   - Apply scheduled events whose time <= now -> resolve effects, write logs, mutate world/characters.
   - Fate engine checks rules -> enqueue new events (with randomness + background).
   - Characters update: decay states, evaluate goals, pick intent.
   - Interaction: when dialogue/decision needed, call LLM with structured prompt (world + character sheet + recent memories + current event).
3) Persist: append log entry, optionally snapshot every N ticks.

## Prompts (LLM-facing skeletons)
- Character sheet prompt:
  - Inputs: world background, location context, character attributes/traits, relationships (top K), last N memories, current mood/states, current goal(s).
  - Ask for: a) intent summary, b) dialogue line (optional), c) state adjustments (json).
- Event reaction prompt:
  - Inputs: event payload + participants’ sheets.
  - Ask for: each participant’s reaction text + state deltas.
Keep strict JSON blocks for machine ingestion; keep free-text for surface dialogue.

## Minimal API (FastAPI-style suggestion)
- GET /world -> current world snapshot (lightweight).
- POST /world/time-scale {time_scale: float} -> set time multiplier.
- POST /characters -> create character (name, attributes, traits, role, is_child?).
- PATCH /characters/{id} -> update attributes/traits/states.
- GET /events?status=scheduled|recent -> inspect queue/history.
- POST /events -> inject manual event (payload + actors + scheduled_for).
- POST /simulate/step -> advance one tick (useful for deterministic/manual stepping).
- GET /logs/tail -> stream last N log lines.

## Extensibility Hooks
- Fate rules plug-in point: add/remove rules without changing core.
- Personality drift: after dialogues/events, apply trait nudges (bounded) based on interactions.
- Birth/adoption: event type that creates a new Character (child flag) and links relationships.
- Background evolution: background can mutate tags (e.g., “famine”, “festival”) that bias fate rules.
- Memory decay/selection: prune or lower salience to keep prompt budgets small.
- Multi-model: allow selecting model per task (dialogue vs. planning) via config.

## Frontend/UX Skeleton (plan ahead)
- Viewports: (a) World/time controls (play/pause, time-scale slider, tick step), (b) Map/locations with character presence, (c) Event feed/log pane, (d) Character sheet modal (traits, states, memories, relationships, recent dialogues), (e) Fate rule toggles/weights (later).
- Transport: start with REST polling for `/world`, `/events`, `/logs/tail`; evolve to Server-Sent Events or WebSocket for live feed.
- State slices to fetch: world snapshot (lightweight), scheduled/recent events, characters list (with minimal fields), per-character detail on demand.
- UI theming: keep UI decoupled—API-first; frontends should tolerate missing fields as features grow.

## Narrative Logging & Story Capture
- Append-only log channel for:
  - World ticks: timestamp, tick_id, time_scale.
  - Events: id/type/actors/location/payload/effects/status.
  - Dialogue/monologue: participant_id, text, source_event_id, mood/intent, derived trait nudges.
  - Fate decisions: rule_id, conditions hit, probability, enqueue result.
- Storage options:
  - Simple: newline-delimited JSON (NDJSON) in `src/town/logs/event.log`.
  - Later: SQLite/Postgres with tables for events, utterances, snapshots.
- API additions:
  - GET `/logs/tail` (exists) — add `kind` filter (event|dialogue|all) later.
  - Optional WebSocket/SSE `/stream/logs` for live UI feed.
- Prompt budget helper: keep short dialogue summaries per memory entry to rehydrate context without dumping full logs.

## Files/Dirs to Start With
- `src/town/core/time.py`: tick/time-scale management.
- `src/town/core/state.py`: world + characters + events in-memory store; persistence adapter.
- `src/town/fate/engine.py`: rule evaluation, event scheduling/resolution.
- `src/town/llm/prompts.py`: prompt templates for dialogue/intent/reaction.
- `src/town/api/routes.py`: minimal HTTP endpoints.
- `src/town/logs/` (data): append-only log (events + dialogue), snapshots (json or sqlite) optional.

## First Increment (smallest usable slice)
- Fixed background + 1 location.
- Create N characters via API with base attributes/traits.
- Manual time-scale control + tick endpoint.
- Fate engine with 1-2 simple rules (e.g., “morning greetings”, “random encounter”).
- Dialogue generation via LLM for a single interaction template.
- Event log + in-memory state (no complex persistence yet).

This gives a runnable skeleton that you can extend with richer fate rules, more locations, personality drift, births, and background-driven events.***
