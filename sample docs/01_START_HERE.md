# Unnamed RPG - Start Here

## What Is This?

A retro-style (8/16-bit pixel art) turn-based tactical RPG built in Godot 4.6+, using the Pathfinder 2e rule system under the ORC license. Playable solo (one player controls a party of up to 6) or multiplayer (up to 6 players, one character each) via peer-to-peer networking.

Inspired by the *gameplay structure* of classic Gold Box RPGs like Pool of Radiance: explore a medieval fantasy city, take quests, delve into dungeons, fight grid-based tactical battles, level up, and repeat. Original setting, characters, and story.

## Project Goals

1. **Playable demo first** - One town hub + one dungeon + working combat system
2. **PF2e mechanics** - 3-action economy, grid-based tactical combat, full character creation
3. **Retro pixel art** - 8/16-bit aesthetic using asset packs initially, custom art later
4. **Solo + Multiplayer** - Full party control in solo; peer-to-peer co-op for up to 6 players
5. **Multi-platform** - Desktop (Windows/Linux/Mac), Mobile (Android/iOS), Web
6. **Monetization** - Ad-supported free tier + paid features/premium upgrade

## Why PF2e?

- **ORC License** - Nearly all PF2e content is available under the permissive Open RPG Creative (ORC) license
- **No Product Identity restrictions** like D&D's SRD (which only covers ~30% of content)
- **3-action economy** maps perfectly to turn-based tactical combat
- **Deep character building** - classes, ancestries, feats, spells provide massive replayability
- **Active community** - Large ecosystem of content and player familiarity

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Engine | Godot 4.6+ (mobile renderer) |
| Language | GDScript |
| Networking | Godot ENet multiplayer (peer-to-peer) |
| Rules Data | JSON (reusable from HeroWeaver where applicable) |
| Art | Pixel art asset packs (initially) |
| Audio | TBD (chiptune/retro OST) |
| Platform | Windows, Linux, Mac, Android, iOS, Web |
| Monetization | AdMob (ads) + IAP/Stripe (premium) |

## Relationship to HeroWeaver

This is a **separate project** that may leverage some HeroWeaver assets:
- PF2e JSON data files (classes, ancestries, spells, equipment, etc.) - already built and ORC-licensed
- Character data model patterns
- Validation engine concepts

However, this is a *game*, not a character generator. It will have its own codebase, scenes, and architecture. The shared data is a head start, not a dependency.

## Document Map

| Document | Purpose |
|----------|---------|
| [01_START_HERE.md](01_START_HERE.md) | This file - project overview and orientation |
| [02_ARCHITECTURE.md](02_ARCHITECTURE.md) | Technical architecture, systems design, data flow |
| [03_GAME_DESIGN.md](03_GAME_DESIGN.md) | Game mechanics, combat, progression, multiplayer |
| [04_ROADMAP.md](04_ROADMAP.md) | Phased development plan with milestones |
| [05_DATA_MODELS.md](05_DATA_MODELS.md) | Data structures, PF2e rule mapping, save format |
| [06_GITHUB_WORKFLOW_GUIDE.md](06_GITHUB_WORKFLOW_GUIDE.md) | Git branching, commits, and workflow strategy |
| [07_PF2E_SCOPE.md](07_PF2E_SCOPE.md) | PF2e rules support matrix — what's in demo vs. deferred |
| [08_ACCESSIBILITY.md](08_ACCESSIBILITY.md) | Accessibility baseline (WCAG + GAG) for all player-facing systems |

## Quick Reference

- **Engine:** Godot 4.6+ with mobile renderer
- **Art style:** Top-down 8/16-bit pixel art
- **Combat:** Grid-based, turn-based, PF2e 3-action economy
- **Party:** Up to 6 characters
- **Multiplayer:** Peer-to-peer, up to 6 players
- **License:** ORC (Pathfinder 2e content), proprietary (game code + original content)
- **Monetization:** Ads (free) + paid premium features
- **Demo target:** 1 town + 1 dungeon + combat + character creation
