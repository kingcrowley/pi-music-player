# Unnamed RPG - Development Roadmap

## Philosophy

Build vertical slices — each phase produces something playable. Don't build systems in isolation. Every phase ends with a testable, demonstrable milestone.

## Phase 0: Foundation (Weeks 1-3) — ✅ Complete

**Goal:** Empty Godot project with core infrastructure running.

Tagged `Phase0-Foundation-Complete`. See CLAUDE.md "Current Status" for a summary of what shipped.

### Deliverables
- [x] New Godot 4.6 project with directory structure
- [x] Autoload skeleton: all 7 — GameManager, RulesEngine, PartyManager, NetworkManager, AudioManager, SaveManager, DataLoader
- [x] PF2e data files imported from HeroWeaver (classes, ancestries, spells, equipment, backgrounds — 19 JSON files total)
- [x] DataLoader: load and cache PF2e JSON data with ID lookup
- [x] Basic scene transitions (MainMenu -> Game)
- [x] Character data model (`scripts/models/character_data.gd`, Resource class)
- [x] RulesEngine autoload: ability_modifier, proficiency_bonus, calculate_hp, calculate_ac, calculate_attack_bonus, apply_map, calculate_perception, spell DC/attack, skills, derive_stats
- [x] GUT test infrastructure + initial tests for RulesEngine (61 tests passing at tag)
- [x] CLAUDE.md for the new project

**Milestone:** Can load PF2e data, create a character in code, calculate derived stats correctly. ✅

## Phase 1: The Grid (Weeks 4-6) — ✅ Playable Vertical Slice

**Goal:** Walk around a tile map and fight a battle.

See CLAUDE.md "Current Status" for the detailed component list. Phase 1 ships keyboard movement, fog of war, encounter triggering, and turn-based combat with Stride/Strike/End Turn against a goblin encounter.

### Deliverables
- [x] TileMap setup: 32x32 pixel tiles (placeholder ColorRects; real tileset deferred to Phase 2 sprite work)
- [x] Pathfinding: AStarGrid2D for grid movement, obstacle avoidance, difficult terrain costs
- [x] Party movement: top-down, tile-by-tile, keyboard input, pathfinding-driven
- [x] Camera: follows party, bounded to map edges
- [x] Fog of war: basic implementation (reveal tiles as party moves; mobile-renderer verification deferred to Phase 4 — see postmortem and Phase 4 sprite-upgrade pass)
- [x] Combat trigger: step on encounter tile -> transition to combat
- [x] Combat grid: same tile map but with turn-based controls
- [x] Turn order: initiative rolls, turn queue display
- [x] Basic actions: Move (Stride), Strike (melee), End Turn
- [x] Attack resolution: d20 + bonus vs AC, damage roll, HP tracking
- [x] Placeholder enemy AI: one behavior preset (`melee_aggressive`) — move toward nearest party member, Strike when adjacent. Full AI variety lands in Phase 2.
- [x] Death at 0 HP (simplified — full dying condition lands with Phase 2 condition work)
- [x] Combat end: all enemies dead -> return to exploration
- [x] Placeholder sprites: colored squares
- [x] ORC attribution screen: license text and formal "Licensed Material" declaration

**Milestone:** Walk through a 3-room dungeon, fight 2 goblins in grid combat, kill them or die. ✅

**Playable-minimum story (acceptance wording):** enter dungeon → move tile-by-tile with fog-of-war reveal → step onto encounter tile → initiative rolls → take PF2e turns with Stride/Strike/End Turn → win (all enemies dead, XP awarded) or lose (party wipe, game-over) → on win, exploration resumes with the party token anchored to the combat-exit tile. This is the full Phase 1 loop and the baseline every later phase must preserve.

**Note:** touch input is deferred to the mobile-export pass in Phase 4 alongside the other platform polish.

### Phase 1 Postmortem

**What worked**
- Vertical-slice discipline. Keyboard movement, fog of war, encounter trigger, turn-based combat, and exploration-return were all in one branch before polish started, so regressions were caught against a working loop instead of in isolation.
- Data-driven where it hurts: `DungeonMap` (AStarGrid2D + runtime occupancy), `DataLoader` JSON cache, and `MonsterData` JSON all stayed behind narrow interfaces, which let Phase 2 Slice 1 layer the condition framework on top without reshaping Phase 1 code.
- Pathfinding-with-occupancy (`find_path_avoiding_occupied`) turned out to be the key primitive — both player Stride and `EnemyAI` use it, and the Phase 2 stride-to-flank feature fell out of it cheaply.
- GUT tests tracked every system from the start. 160 tests at Slice 1 end, all green, with per-file coverage for dice / turn queue / combat actions / combat manager / enemy AI / dungeon map / fog of war / conditions / dying / flanking / slowed-stunned.

**What was deferred (and why)**
- Real sprites / tileset — kept as colored ColorRects so combat feel could be tuned before art commitment. Sprite z-ordering lives on the Phase 2 checklist.
- Mobile-renderer fog-of-war verification — no renderer-specific code yet, so there is nothing to verify; revisits alongside real sprites.
- Touch input — desktop-first was the right call for proving the core loop. Lands in Phase 4.
- `MonsterTemplate` / `MonsterInstance` split (see `05_DATA_MODELS.md`) — the single `MonsterData` resource still holds both layers. Acceptable while encounters are one-shot; must split before persistent dungeons / mid-dungeon saves land.
- Full dying/condition system — the Phase 1 stub was "drop at 0 HP, skip turn". Phase 2 Slice 1 replaced it with the real PF2e dying/wounded/recovery machine.

**What must remain stable for Phase 2 (frozen interfaces)**
The public surfaces below are treated as contracts for Phase 2+ work. Changes require a migration note, not a silent edit. Details and method signatures live in `02_ARCHITECTURE.md` under *Phase 1 Frozen Interfaces*.

- `DungeonMap`: `is_walkable`, `is_occupied`, `set_occupied`, `clear_occupied`, `find_path_avoiding_occupied`.
- `CombatManager`: `start_combat`, `get_current_combatant`, `get_turn_order`, `get_actions_remaining`, `get_condition_tracker`, `player_stride`, `player_strike`, `player_end_turn`, `execute_enemy_turn`, plus the `turn_started` / `action_performed` / `combat_ended` signals.
- `ConditionTracker`: `add_condition`, `remove_condition`, `set_value`, `get_value`, `has_condition`, `get_conditions`, `clear_entity`, `get_condition_max`.
- `CharacterData` / `MonsterData` runtime fields depended on by CombatManager/HUD/AI: `id`, `position`, `current_hp`, `max_hp`, `is_dead`, `armor_class`, and the name field. Phase 2 may *add* fields; it may not rename or remove these without coordinated HUD/AI/test updates.

## Phase 2: Character Creation + Full Combat (Weeks 7-10)

**Goal:** Create a character from scratch and fight with the full PF2e action economy.

### Deliverables
- [x] Character creation flow: ancestry, heritage, background, class (+subclass), ability scores, skills, caster spells, equipment, review (Slice 6 — single PC, 4 demo classes; `CharacterBuilder` rules core + wizard. In-engine smoke pending). **Deferred:** feats are recorded but inert (no feat framework); heritage/subclass effects not yet applied; fixed per-class kit (no equipment shop).
- [ ] Party formation: create up to 6 characters (Slice 6 ships single created PC + preset companions; full create-up-to-6 still pending)
- [x] 3-action economy: action points per turn, multi-attack penalty (Phase 1)
- [x] Ranged attacks: bows, thrown weapons, range penalties (Slice 4 — range increments, Volley, line-of-sight, cover tiers)
- [x] Spellcasting: spell slots (prepared casters), single-target spell effects done in Slice 5a (Heal, Stabilize, Magic Missile, Electric Arc with basic Reflex save). Slice 5b1 added AoE damage (Burning Hands cone, Heal 3-action emanation) + reusable `TargetPicker` for single/multi/cone/emanation. Slice 5b2 added buff spells (Bless self-emanation + Sustain), Fear, Will saves, status-bonus tracking + durations (`BuffTracker`), and AI casting (Support/Bless, Ranged/Fear, enemy `support_caster`). **Deferred to Phase 3:** Fleeing rider on Fear crit-fail (`TODO(phase3-fleeing-condition)`), choose-which-spell on Sustain when 2+ active (`TODO(phase3-multi-sustain)`). **Deferred further:** spontaneous casters, focus spells.
- [x] Conditions: the demo core 10 — Blinded, Dying, Flat-Footed, Frightened, Prone, Sickened, Slowed, Stunned, Unconscious, Wounded (Slice 1)
- [x] Dying/recovery: PF2e dying rules, recovery checks, flanking, flat-footed (Slice 1). **Treat Wounds deferred** (no skill-action framework yet — out-of-combat use case).
- [x] Hero Points: per-PC counter (start 1, max 3), reroll any check (take better), spend all to RAW-strict Avoid Death (CRB p. 467 — dying cleared, HP stays at 0, unconscious preserved, wounded **not** incremented). Slice 4 + 5a. Reroll trigger wired across all PC-authored d20 sites (melee strike, ranged strike, recovery check, Trip, Demoralize) in 5a; AoO reroll wired in 5b1. **Still deferred:**
  - [x] **`TODO(phase2-hp-d3)`** — done. Per-encounter milestone regen on `milestone: true` encounters wired in Slice 5a; session-half closed in Slice 5d via Long Rest (`PartyManager.long_rest(tracker)` raises every living PC's Hero Points to ≥1). True session-boundary semantics (save/load) tracked under `TODO(phase3-save-load-session)`.
- [x] Reaction buffer UI: ReactionBroker routes PC reactors through a modal prompt with 5s timeout, AI reactors through policy functions. Pattern is already multiplayer-ready (centralized async resolution). Slice 3.
- [x] AI companions: combat AI with 5 behaviour presets (Slice 5c — `aggressive` / `defensive` / `support` / `ranged` / `hold`). Exploration-mode follow deferred to a later slice (companions still move as the existing party token in dungeon mode).
- [x] Player tactical orders: companion-orders radial with 5 stable wedges, the only radial in the game (Slice 5c)
- [x] Direct control toggle: take over any companion mid-combat via the radial's center hub (Slice 5c)
- [x] Level up flow: XP gain, level up screen (ability boost, feat, spell selection) — generic data-driven engine to L10 (Slice 7); feats recorded-only, caster spell picks beyond L1 demo pool deferred
- [x] Enemy variety: 5+ creature types with different AI behaviors. Slice 8 delivered 4 new behaviors (defender, skirmisher, brute, commander) + morale-flee layer + 3 new creatures (goblin_dog, bugbear, goblin_warchief), bringing the roster to 9 monsters across 7 distinct behaviors. `EncounterBudget` PF2e XP/threat-tier helper added. `goblin_shieldbearer` reassigned to defender; `goblin_champion` to brute.
- [ ] Sprite z-ordering: replace Phase 1 ColorRect placeholders with real sprites and ensure characters/monsters render correctly behind/in front of walls, pillars, and tall terrain. Use YSort or explicit z_index per tile row.
- [x] **`TODO(phase2-stand)`** — done in Slice 5d. `CombatActions.execute_stand` (1 action, move trait, removes `prone`, no MAP bump) + `CombatManager.player_stand` routing through the generalized `_trigger_move_aoo`. HUD Stand button replaces Stride/Strike when active PC has `prone`. AoO crit on Stand interrupts: action consumed, prone persists.
- [x] **`TODO(phase2-spell-slot-rest)`** — done in Slice 5d. `SpellSlotTracker.refresh_to_max` invoked by `PartyManager.long_rest(tracker)`; `R` keybind + Rest button on exploration HUD.
- [x] **`TODO(phase2-ai-conditions)`** — done in Slice 5d. `CompanionAI.decide_actions` now takes `actions_remaining` + optional `tracker`; all 5 behaviors plan against the real action budget (no truncated 3-action plans for Slowed/Stunned PCs). Support adds cost-aware budgeting + a stride-to-heal reachability pre-check.
- [ ] **`TODO(phase3-rest-cost)`** — Long Rest is currently free-and-unlimited. Phase 3 should gate it on daily limit / consumables / town-only (PF2e RAW: 8 hours uninterrupted, food + water, one rest per 24 hours).
- [ ] **`TODO(phase3-save-load-session)`** — true session-boundary semantics for Hero Point regen and any future per-session effects. Requires save/load round-trip + a "new session" detection point.

**Milestone:** Create a party of 4, explore a dungeon, fight varied encounters, level up to 2, companions fight alongside you.

## Phase 3: The Town (Weeks 11-14)

**Goal:** A functioning town hub — the "home base" loop is complete.

### Deliverables
- [ ] Town map: pixel art town with buildings, NPCs
- [x] NPC dialogue system: dialogue trees, quest offering (Slice 3.4 `DialogueEngine` + `DialoguePanel` + `dialogues.json`; portraits + typewriter reveal deferred to `slice3.5-portraits` / `slice3.5-dialogue-typewriter`)
- [~] Shops: buy/sell equipment + potions (PF2e pricing — Slice 3.1 shop, Slice 3.2 EquipmentService + EquipmentPanel + Drink Potion). Scrolls + bombs deferred (`TODO(slice3.3-scrolls)`, `TODO(slice3.3-alchemists-fire)`).
- [x] Temple: healing, resurrection, condition removal (for a fee — Slice 3.3 `TempleService` + `TemplePanel` + `temple_services.json`; spell-tier pricing deferred to `TODO(slice3.4-temple-scaling)`)
- [x] Inn: rest (restore HP/spells), save game (Slice 3.1 `InnPanel` → `long_rest` + auto-save)
- [x] Tavern: recruit pre-built companion NPCs (PR #47 — Tavern panel, 8 data-driven companions, active party ≤6 + persistent reserve bench; HeroWeaver-imported recruits in PR #48)
- [x] Quest system: accept quest, track in journal, complete for rewards (Slice 3.4 `QuestManager` + `QuestEngine` + journal + reward flow; chains + fail states in 3.6)
- [x] 3-5 starter quests (fetch, kill, explore, escort, mystery) (Slice 3.4 first quest + Slice 3.5 quest content pack: 6 quests incl. a 2-quest chain; `clear_bandits` added in 4.1)
- [x] Journal/quest log UI (Slice 3.4 `QuestJournalPanel` opened from pause menu)
- [x] Save/load system: full game state serialization (Phase 2 Slice 9 `SaveManager` per-subsystem serialize/deserialize; named saves in the Save UX mini-slice, PR #27)
- [x] Game over screen: party wipe -> load last save (Slice 3.3 `GameOverScreen` + dungeon_scene defeat routing through SaveSlotPicker → GameManager.start_loaded_game)

**Milestone:** Full gameplay loop — create party, visit town, take a quest, enter dungeon, fight, return to town, sell loot, rest, repeat.

## Phase 4: Content & Polish (Weeks 15-20)

**Goal:** Enough content for a 2-4 hour demo experience.

### Deliverables
- [~] 3-5 dungeon areas with increasing difficulty (Slice 4.1 added the 25×20 Bandit Hideout as the 2nd dungeon via registry-driven routing; the Crypt slice added the 25×20 lightless Sunken Crypt as the 3rd, quest-gated behind `holy_symbol` via the new `unlock_condition` support — 3 of 3-5 done)
- [~] 15-20 unique enemy types with distinct AI (7 AI behaviors + bandits (4.1) + grapple/shove/disarm goblin variants (4.5b) + 4 undead — skeleton, zombie, ghoul, crypt wight — with the Crypt slice; count still growing)
- [~] Boss encounters (1-2) with special mechanics — the data-driven framework (recharging area attack + HP-threshold phases) ships with the `goblin_warchief` showcase in the dark warren boss room; a second boss lands with the Crypt slice. Deferred: summon-adds (needs TurnQueue insertion), legendary actions. The Crypt adds the second boss — a wight that breathes a necrotic **cone**, which closed the deferred cone planner; only summon-adds and legendary actions remain deferred.
- [x] Traps: Perception to detect, Thievery to disarm (Slice 4.6 — `DungeonFeatures` trap with basic-Reflex-save damage; pit/poison/arrow/magical flavor variants are authored atop the same engine)
- [x] Secret doors and hidden treasure (Slice 4.6 — hidden `secret_door` features revealed by passive/active Search, optional loot cache)
- [x] Locked doors/chests (Slice 4.6 — `chest` + `door` features; Pick Lock / Force Open; full-width corridor gate via `extra_tiles`)
- [x] Light/darkness (darkvision, torches, Light cantrip) — PR #55 (combat concealment: dim=concealed DC 5, dark=hidden DC 11, darkvision/low-light senses) + PR #56 (exploration vision-limited fog + tile shading + the Light cantrip). Deferred: LOS occlusion, magical darkness, manual douse/relight.
- [~] Environmental variety: caves, ruins, sewers, crypt — the Sunken Crypt ships (mostly-dark undead crypt built on the Light & Darkness systems); caves / ruins / sewers still to come
- [~] Loot tables balanced to PF2e treasure-by-level (Slice 4.7 — `TreasureTable` rolls level-banded weighted pools (`band_1_2`, `band_3_5`, ...) for monster drops + chests; full PF2e treasure-by-level gp budgeting still deferred — `TODO(treasure-gp-budget)`). Party Inventory slice moved item distribution to **per-character carry**: combat/chest drops route through a loot-assign modal (pick the recipient party member, default leader) instead of auto-appending to the leader; an equipment-panel Give-to action (`PartyManager.transfer_item`) redistributes afterward. Loot Logistics (PR #52) then closed both remaining gaps — quest-reward items route through the same assign modal (`loot-assign-quest-rewards`), and reserve/benched members can carry (`loot-assign-reserve-carry`, gated to town) — and added a pure PF2e **Bulk** resolver; Encumbrance Consequences (PR #53) gave Bulk combat teeth (encumbered → clumsy 1, over-max → immobilized, seeded at combat start). Still deferred: full gp budgeting (`TODO(treasure-gp-budget)`) and drop-item (`TODO(drop-item-on-ground)`) — the −10-ft encumbered Speed rider **closed** with the PC Speed & Movement slice (`Speed.for_pc` reads `Bulk.status` directly).
- [~] 10-15 magic items (Slice 4.7 — weapon/armor runes (potency 1/2, striking, flaming/frost/shock, armor potency 1, resilient) + 2 demo runed items (+1 Longsword, +1 Leather); Slice 4.8 — 5 wondrous worn items across new Amulet/Ring/Belt/Cloak slots (amulet_of_warding, sentinels_cloak, ring_of_awareness, belt_of_the_stalwart, ring_of_the_ward); ~7 concrete items plus the full weapon/armor rune combinatorial space)
- [x] PC Speed & Speed-bounded movement (branch `phase/4-pc-speed-movement`) — PCs gained a RAW `Speed` stat (ancestry + armor penalty + encumbered −10-ft rider, cached on `CharacterData`); Stride now moves up to Speed via a click-to-move destination picker instead of the accidental 1-tile HUD cap, bounded by one weighted movement cost model (`MoveTargeting`) shared with **path-aware Attacks of Opportunity** (each opponent reacts once as the mover leaves its reach; a crit disrupts the Stride). Sudden Charge derives from real Speed (2× Stride). Closed `encumbered-speed-penalty` / `speed-limited-movement` / `slice5-speed-stat`. Deferred: PF2e diagonal 5-10-5 cost (`diagonal-movement-cost`). The AI Movement Parity slice (branch `phase/4-ai-movement-parity`) then closed the AI gap — all four remaining companion approach branches close at full Speed via `_stride_toward`, and AI Strides (enemy + companion) walk their A* route through the shared `_resolve_strided_move` with path-aware AoO (parity with `player_stride`), closing `ai-parity-remaining` and `ai-move-aoo-path-aware`.
- [ ] Difficulty settings (Classic, Adventure, Story, Ironman)
- [ ] Pixel art sprite upgrades (characters, monsters, environment)
- [ ] Fog of war mobile-renderer verification — re-check the Phase 1 visibility shader against the real tileset once sprites land (no renderer-specific code today, so nothing to verify yet)
- [ ] Sound effects (combat, UI, exploration)
- [ ] Music (town theme, dungeon theme, combat theme)
- [ ] Main menu polish (title art, new game, continue, settings)

**Milestone:** Playable demo: 2-4 hours of content, 5 dungeons, full town, polished pixel art and audio.

## Phase 5: Multiplayer (Weeks 21-26)

**Goal:** Peer-to-peer co-op multiplayer working.

### Deliverables
- [ ] NetworkManager autoload: ENet peer-to-peer setup
- [ ] Lobby system: host creates game, share join code, clients connect
- [ ] Character sync: each player's character replicated to all peers
- [ ] Exploration sync: host-authoritative movement, all players see same map
- [ ] Combat sync: host resolves actions, broadcasts results to all clients
- [ ] Turn management: each player controls their character's turn
- [ ] Chat: simple text chat between players
- [ ] Disconnect handling: reconnect, or AI takes over disconnected player
- [ ] Unfilled slots: AI companions for slots without players
- [ ] Seeded RNG: shared random seed for deterministic dice rolls (replay/debug support)
- [ ] Latency testing and optimization

**Milestone:** 2-4 players can complete a dungeon together over the network.

## Phase 6: Monetization & Release (Weeks 27-32)

**Goal:** Ship the game.

### Deliverables
- [ ] Ad integration (AdMob): interstitial between dungeons, banner in town (non-intrusive)
- [ ] Premium upgrade: remove ads + bonus content (extra dungeon, cosmetics, etc.)
- [ ] Platform builds: Windows, Linux, Android, Web (iOS later)
- [ ] Storefront listings: itch.io, Google Play
- [ ] ORC license compliance: attribution page, license text
- [ ] Privacy policy, terms of service
- [ ] Tutorial / new player experience
- [ ] Bug fixing and balance pass
- [ ] Beta testing
- [ ] Launch

**Milestone:** Game live on at least 2 platforms.

## Post-Launch

- [ ] Story campaign (multi-dungeon narrative arc)
- [ ] iOS build
- [ ] Steam release
- [ ] Additional classes/ancestries
- [ ] Overworld map (travel between towns)
- [ ] PvP arena mode
- [ ] Dungeon editor (user-created content)
- [ ] Level cap increase (10 -> 20)
- [ ] Mod support

## Accessibility

Each phase ships with the accessibility baseline in [08_ACCESSIBILITY.md](08_ACCESSIBILITY.md) applied to its player-facing surfaces. A slice isn't "done" until visible focus, logical focus order, non-color state, and keyboard/controller parity are verified for every new screen, modal, or HUD element it adds. Phase 2 should also stand up a focus-entered TTS aid for menu verification — see 08 for the rationale.

## Risk Register

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Multiplayer desync | High | Host-authoritative model; host is sole source of dice rolls; seeded RNG in Phase 5 |
| Multiplayer complexity | High | Build single-player first, add networking as a layer |
| AI pathfinding | Medium | Use Godot's built-in AStarGrid2D for grid movement in Phase 1 |
| PF2e rules complexity | Medium | Implement subset first (core combat), expand incrementally |
| Art consistency | Medium | Standardize on 32x32 tiles; stick to one asset pack family, commission custom art later |
| Scope creep | High | Each phase has a hard deliverable — don't start next until current ships |
| Mobile/Web performance | Medium | Profile fog of war shaders on mobile renderer in Phase 1; pixel art is lightweight |
| Licensing misstep | Low | ORC license is clear and permissive; attribution screen in Phase 1 |
