# Unnamed RPG - Architecture

## Overview

The game uses a layered architecture separating game rules (data-driven PF2e), game logic (combat, exploration, quests), presentation (pixel art rendering, UI), and networking (peer-to-peer multiplayer).

## High-Level Architecture

```
Layer 5: Networking        Peer-to-peer sync, lobby, state replication
Layer 4: Presentation      Pixel art rendering, UI, audio, camera
Layer 3: Game Logic        Combat manager, exploration, AI, quests
Layer 2: Rules Engine      PF2e mechanics, validation, stat calculation
Layer 1: Data              JSON rule files, save data, asset definitions
```

## Layer 1: Data (JSON + Resources)

### PF2e Rule Data
Reusable from HeroWeaver's existing JSON files where applicable:

| Data File | Content | Source |
|-----------|---------|--------|
| classes_pathfinder2e.json | 12 classes + subclasses, features, proficiencies (full PF2e data; only 4 classes playable in the demo — see `07_PF2E_SCOPE.md`) | HeroWeaver |
| ancestries_pathfinder2e.json | Ancestries + heritages, ability boosts/flaws | HeroWeaver |
| spells_pathfinder2e.json | Cantrips + spells by level | HeroWeaver |
| equipment_pathfinder2e.json | Weapons, armor, gear, prices | HeroWeaver |
| backgrounds_pathfinder2e.json | Backgrounds with skill/ability boosts | HeroWeaver |
| bestiary/*.json | Monster stat blocks, AI hints, loot tables (one file per creature) | **New** |
| dungeons/*.json | Dungeon layouts, encounter tables, traps | **New** |
| quests/*.json | Quest definitions, triggers, rewards | **New** |
| items_magic.json | Magic items, consumables, treasure | **New** |
| world_map.json | Town locations, dungeon entrances, overworld | **New** |

### Save Data
- Party state (characters, inventory, gold)
- World state (quests completed, dungeons cleared, NPCs met)
- Map state (fog of war, discovered areas)
- Multiplayer: host holds authoritative state

### Asset Definitions
- Tile maps (JSON or Godot TileSet resources)
- Sprite sheets (character, monster, environment)
- Audio cues (mapped to game events)

## Layer 2: Rules Engine

### Core Systems

| System | Responsibility |
|--------|---------------|
| StatCalculator | HP, AC, saves, attack bonuses, DCs from PF2e rules |
| ActionEconomy | 3-action turn system, reactions, free actions |
| SpellEngine | Spell slots, prepared/spontaneous casting, effects |
| SkillChecker | Skill checks with DC, degrees of success (crit/success/fail/crit-fail) |
| LevelManager | XP tracking, level-up flow, feat/spell selection |
| ConditionTracker | PF2e conditions (frightened, sickened, etc.), duration, stacking |
| BuffTracker | Status/circumstance/item bonuses + durations; resolves stacking (max for typed, sum for untyped) at query time (Slice 5b2) |
| CharacterBuilder | Pure PF2e level-1 character-build rules (ability boosts/flaws, skills, caster spells, kit, validate, build → derive_stats); drives the creation wizard (Slice 6) |

### PF2e Degrees of Success
Central to the rules engine — every check has four outcomes:
- **Critical Success:** Beat DC by 10+
- **Success:** Meet or beat DC
- **Failure:** Below DC
- **Critical Failure:** Below DC by 10+

Natural 20 upgrades one step, natural 1 downgrades one step.

## Layer 3: Game Logic

### Combat Manager
- **Grid system:** Square grid, 5ft per tile (PF2e standard)
- **Turn order:** Initiative (Perception or class feature), cycle through combatants
- **Action system:** 3 actions per turn (Strike, Move, Cast, etc.) + 1 reaction
- **AI controller:** Two separate preset systems, both decision-function based (no behavior trees). Monsters use `ai_behavior` set on the stat block (`melee_aggressive`, `ranged_kiter`, `support_caster`; future: boss). PC companions use `behavior_preset` on `CharacterData` (Slice 5c — `aggressive`, `defensive`, `support`, `ranged`, `hold`) with class-based defaults at combat start. Decision logic stays as direct code per behavior; see Layer 3 AI System.
- **Death & resurrection:** Characters drop at 0 HP, dying condition (PF2e rules), party can revive via spells/items/temple services

### Exploration Manager
- **Dungeon mode:** Tile-based top-down movement, fog of war, trap detection
- **Town mode:** NPC interaction, shops, quest givers, temple (resurrection), inn (rest)
- **Overworld mode:** Travel between locations (if scope allows)
- **Random encounters:** Encounter tables per region/dungeon level

### Quest Manager
- Quest states: available, active, complete, failed
- Trigger system: location-based, kill-count, item-delivery, NPC dialogue
- Rewards: XP, gold, items, reputation, new areas unlocked

### AI System
- **Enemy AI:** Direct decision functions dispatched by `monster.ai_behavior` (no behavior-tree formalism — see Combat Manager note above). Each behavior is a small `decide_actions(monster, party, dungeon)` function returning an action plan. Current behaviors:
  - `melee_aggressive` — close distance via pathfinding, Strike when adjacent (Phase 1)
  - `ranged_kiter` — Stride away from adjacent PCs, Strike at range, fall back to melee if no ranged attack data (Slice 4)
  - `support_caster` — Fear the nearest PC in range+LoS, then fall through to the kiter/melee plan; reads the monster's flat `spell_dc` (Slice 5b2, `goblin_caster`)
  - Future: boss (phase-based)
- **Companion AI (PC-side):** `CompanionAI.decide_actions(pc, party, enemies, dungeon_map, actions_remaining, tracker, buff_tracker)` dispatches on `pc.behavior_preset`. `actions_remaining` + optional `ConditionTracker` were added in Slice 5d so Slowed/Stunned PCs plan against their real budget and prone PCs prepend a Stand action; the `buff_tracker` param (Slice 5b2) lets Support cast Bless and Ranged cast Fear. Five presets shipped in Slice 5c:
  - `aggressive` — close to nearest living enemy, Strike when adjacent (Fighter default)
  - `defensive` — protect lowest-HP%-ally, intercept threats adjacent to that ally
  - `support` — cast Bless when allies are clustered and no one needs urgent healing (Slice 5b2), heal lowest-HP%-ally below 50%, stabilize dying, back-line position (Cleric default)
  - `ranged` — open with Fear on the highest-HP enemy in range+LoS (Slice 5b2), kite away from melee, ranged Strike (Wizard default; falls back to cantrips when no weapon)
  - `hold` — Strike only adjacent enemies, otherwise stay put
  - Class-based defaults applied by `CombatManager._reset_companion_defaults` at `start_combat`; `party[0]` is player-controlled, the rest run on AI. Player can swap presets or take direct control mid-combat via the companion-orders radial.
- **Difficulty scaling:** Encounter budget system (PF2e encounter building rules)

## Layer 4: Presentation

> **Accessibility:** every interactive surface in this layer (HUD, modals, menus) must meet the baseline in [08_ACCESSIBILITY.md](08_ACCESSIBILITY.md). Focus visibility, focus order, non-color state, and keyboard/controller parity are architectural requirements, not polish.

### Rendering
- **Top-down camera** with tile-based movement
- **Pixel art sprites:** 32x32 tiles (standardized — all sprites, tilesets, and characters use 32x32 to keep art swappable when transitioning from asset packs to custom art)
- **Animations:** Walk cycles, attack, cast, hit, death (sprite sheet based)
- **Effects:** Spell VFX (particle systems with retro feel), damage numbers, status icons
- **UI:** Retro-styled panels — party HP bars, action buttons, inventory, minimap

### Key Scenes

| Scene | Purpose |
|-------|---------|
| MainMenu | Title screen, new game, load, multiplayer lobby |
| CharacterCreation | PF2e character creation (ancestry, class, abilities, etc.) |
| TownMap | Town exploration, NPC interaction, shops |
| DungeonMap | Dungeon exploration, fog of war, encounters |
| CombatScene | Grid-based tactical combat |
| Inventory | Party inventory, equipment management |
| LevelUp | Level-up flow (feats, spells, ability boosts) |
| Journal | Quest log, bestiary, lore entries |

### Audio
- Chiptune/retro soundtrack (town theme, dungeon theme, combat theme, boss theme)
- 8-bit SFX (sword swing, spell cast, hit, miss, level up, door open)
- Ambient (dungeon drips, town bustle, wind)

## Layer 5: Networking

### Peer-to-Peer Architecture (Godot ENet)

```
Player 1 (Host)              Player 2-6 (Clients)
+-----------------+          +-----------------+
| Authoritative   |  <---->  | Local prediction |
| Game State      |  ENet    | + server sync    |
| Combat Manager  |          | Input sending    |
| Save Manager    |          | State receiving  |
+-----------------+          +-----------------+
```

### Multiplayer Model
- **Host = authority:** Host runs game logic, resolves combat, manages state
- **Clients send inputs:** "I want to move here", "I want to attack this"
- **Host broadcasts results:** State updates sent to all clients
- **Lobby system:** Host creates game, shares code/IP, clients join
- **Character ownership:** Each player controls 1 character; unfilled slots are AI companions
- **Solo mode:** Player directly controls 1 character, remaining 5 are AI companions that follow and fight alongside (player can issue tactical orders or take direct control in combat)

### Dice Rolls & Determinism
- **Host is sole source of all dice rolls** — clients never independently resolve RNG
- This eliminates desync risk for combat resolution (attacks, saves, damage)
- Seeded RNG planned for Phase 5 to support replay/debug features

### Sync Strategy
- **Combat:** Fully synchronized, host resolves all actions (including all dice rolls), broadcasts results
- **Exploration:** Host moves party, clients see synchronized map
- **Inventory:** Host-authoritative, clients request trades/changes
- **Save:** Host saves full game state; clients save their character data locally

### Latency Handling
- Turn-based combat is naturally latency-tolerant
- Exploration movement can use client-side prediction with host correction
- Action confirmations via RPC with timeout

## Directory Structure (Planned)

```
unnamed_rpg/
  project.godot
  CLAUDE.md
  data/
    pf2e/                  # PF2e rule data (sourced from HeroWeaver)
    bestiary/              # Monster definitions
    dungeons/              # Dungeon layouts
    quests/                # Quest definitions
    items/                 # Magic items, loot tables
    world/                 # World map, town data
  scripts/
    autoload/              # Global managers (GameManager, RulesEngine, PartyManager,
                           #                  NetworkManager, AudioManager, SaveManager,
                           #                  DataLoader — RulesEngine lives here because
                           #                  it's a singleton used everywhere)
    combat/                # Combat system (combat_manager, combat_actions, turn_queue,
                           #                dice, enemy_ai — enemy AI co-locates with the
                           #                combat code that drives it)
    dungeon/               # Dungeon exploration (dungeon_map, party_controller, fog_of_war)
    ui/                    # UI controllers
    network/               # Multiplayer networking (Phase 5)
    models/                # Data Resource classes (CharacterData, MonsterData, …)
  scenes/
    menus/                 # Title, lobby, settings
    combat/                # Combat grid, HUD
    exploration/           # Dungeon, town scenes
    ui/                    # Shared UI components
    characters/            # Character creation, level up
  assets/
    sprites/               # Character, monster, tile sprites
    tilesets/              # Godot TileSet resources
    audio/                 # Music + SFX
    fonts/                 # Pixel fonts
    ui/                    # UI art assets
  tests/                   # GUT tests
  addons/                  # Godot plugins
```

## Autoloads

| Autoload | Responsibility |
|----------|---------------|
| GameManager | Game state machine (menu, town, dungeon, combat), scene transitions |
| RulesEngine | PF2e stat calculation, action validation, skill checks |
| PartyManager | Party roster, inventory, gold, quest state |
| NetworkManager | ENet multiplayer, lobby, RPC dispatch, host/client role |
| AudioManager | Music + SFX playback, crossfade between scenes |
| SaveManager | Save/load game state to disk |
| DataLoader | Load and cache JSON rule data |

## Data Architecture

The game separates data into three distinct layers to keep multiplayer sync, save/load, and testing clean.

### Layer Separation

```
Static Rules Data (JSON)          Runtime State (Resources)         Presentation (Nodes/UI)
─────────────────────────          ─────────────────────────         ────────────────────────
PF2e classes, spells, items        CharacterData, MonsterState       Sprite positions, animations
Bestiary stat blocks               CombatState, DungeonState         HP bars, action buttons
Dungeon layouts, quest defs        QuestProgress, InventoryState     Damage numbers, VFX
Encounter tables, loot tables      SaveGame (aggregates runtime)     Turn order display, minimap

Read-only after load.              Mutated during gameplay.          Derived from runtime state.
Loaded by DataLoader.              Owned by managers (Party,         Rebuilt each frame/event.
Shared across all sessions.        Combat, Quest). Serialized        Never serialized.
Never modified at runtime.         for save/load and network sync.   Never sent over network.
```

### Rules

1. **Static data is immutable at runtime.** DataLoader caches JSON on startup. No system writes back to rule data. If a monster needs current HP, that lives in a runtime state object, not the bestiary entry.

2. **Runtime state is the single source of truth.** All game logic reads and writes runtime state. Combat resolution, AI decisions, quest progression — all operate on runtime objects.

3. **Presentation reads runtime state, never modifies it.** UI nodes observe state and update visuals. User input goes through managers (which validate and update state), never directly to presentation.

4. **Network sync operates on runtime state only.** Host serializes runtime state deltas and broadcasts to clients. Clients never need to sync static data (they load the same JSON files locally) or presentation state.

### Phase 1 Frozen Interfaces

At the end of Phase 1 and Phase 2 Slice 1 the public surfaces below are **frozen contracts**: Phase 2+ code may extend them, but may not rename, remove, or silently change the semantics of an existing method without a migration note in the phase plan. Violating a frozen contract means fixing every consumer (HUD, AI, tests, save format) in the same change.

**`DungeonMap`** (`scripts/dungeon/dungeon_map.gd`)
- `is_walkable(tile: Vector2i) -> bool`
- `is_occupied(tile: Vector2i) -> bool`
- `set_occupied(tile: Vector2i, entity_id: String) -> void`
- `clear_occupied(tile: Vector2i) -> void`
- `find_path_avoiding_occupied(from: Vector2i, to: Vector2i) -> Array[Vector2i]` — returns the first-step-onward path; terminates adjacent to `to` when `to` itself is solid.

**`CombatManager`** (`scripts/combat/combat_manager.gd`)
- Methods: `start_combat(party, enemies)`, `get_current_combatant() -> Dictionary`, `get_turn_order() -> Array`, `get_actions_remaining() -> int`, `get_condition_tracker() -> Node`, `player_stride(target_pos: Vector2i) -> bool`, `player_strike(target: Resource) -> Variant` (returns a result Dictionary on a resolved strike, or `null` when the action was rejected), `player_end_turn() -> void`, `execute_enemy_turn() -> Array`.
- Signals: `turn_started(combatant: Dictionary)`, `action_performed(result: Dictionary)`, `combat_ended(result: String)` (values: `"victory"` or `"defeat"`).
- Result dicts include stable keys: `type`, `attacker`, `target`, `entity`, `degree`, `d20`, `damage`, `flanked`, `flat_footed`, `position`. New keys may be added; existing keys may not be renamed.

**`ConditionTracker`** (`scripts/combat/condition_tracker.gd`)
- `add_condition(entity_id, condition_id, value=1) -> bool`
- `remove_condition(entity_id, condition_id) -> void`
- `set_value(entity_id, condition_id, value) -> void` (value 0 removes)
- `get_value(entity_id, condition_id) -> int`
- `has_condition(entity_id, condition_id) -> bool`
- `get_conditions(entity_id) -> Array[Dictionary]` (items: `{id, value}`)
- `clear_entity(entity_id) -> void`
- `get_condition_max(condition_id) -> int` (data-driven via DataLoader)

**`CharacterData` / `MonsterData` runtime fields** that CombatManager, HUD, and EnemyAI depend on:
- `id: String`, `position: Vector2i`, `current_hp: int`, `max_hp: int`, `is_dead: bool`, `armor_class: int`, plus the display-name field (`character_name` / `monster_name`).
- Phase 2 may *add* fields (companion flags, resistances, etc.); renames or removals require a coordinated HUD/AI/test sweep.

**`DataLoader`** (`scripts/autoload/data_loader.gd`)
- `get_condition(id) -> Dictionary` — contract: returns the condition definition from `data/pf2e/conditions.json`, or an empty Dictionary on miss. Consumers (`ConditionTracker.get_condition_max`, combat HUD badges) depend on this lookup existing.

### Save/Load Architecture

Save files serialize **runtime state only** — never static rules data, never presentation state.

```
SaveGame {
  schema_version: int           # For migration — incremented on breaking changes
  game_version: String          # Game build that created this save
  
  # Serialized runtime state
  party_state: { ... }          # Characters, inventory, gold
  world_state: { ... }          # Quests, dungeon progress, NPC flags
  map_state: { ... }            # Fog of war, discovered areas
  meta: { ... }                 # Play time, difficulty, save slot
}
```

**Schema versioning rules:**
- Every save includes `schema_version` (integer, starts at 1)
- When a data model changes in a way that breaks old saves, increment `schema_version`
- SaveManager maintains a migration table: `{ from_version: Callable }` that transforms old save data to the current schema
- Migrations run sequentially (v1 → v2 → v3) on load
- Save files that cannot be migrated show an error with the game version that created them

**Separate serialization concerns:**
- `CharacterData` has its own `to_dict()` / `from_dict()` for character sheets (used by save and network)
- World/dungeon/quest state has separate serialization (used by save only — network syncs deltas)
- Network messages are their own format (lightweight, delta-oriented) — see `05_DATA_MODELS.md`

## Performance Considerations

- **Tile maps:** Use Godot's TileMap node (GPU-accelerated, handles large maps)
- **Fog of war:** Shader-based or Light2D occlusion (not per-tile visibility checks)
- **AI:** Compute enemy turns off-thread if possible; budget AI thinking time
- **Network:** Minimize state sync — send deltas, not full state
- **Mobile:** Same stretch mode approach as HeroWeaver (canvas_items + expand)
