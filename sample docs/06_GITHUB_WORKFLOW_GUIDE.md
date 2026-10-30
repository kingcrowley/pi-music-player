# GitHub Workflow Guide for Unnamed RPG
## Git Strategy for Phased Development

**Purpose:** Document the actual Git workflow used on this project. Solo developer + AI assistant, slice-based delivery, PR-driven integration.
**Audience:** Solo developer + AI assistant.

---

## Overview

The workflow is intentionally simple:

- **`master`** is the integration branch. Everything that ships goes here.
- **Phase / slice branches** (`phase/2-slice5b1-aoe-multi-target`, etc.) hold work-in-progress.
- **PRs merge slice branches into `master`** as squash commits.
- **Tags mark each completed slice** (`Phase2-Slice5a-Complete`, etc.), not just whole phases.
- **GUT tests pass green** on the slice branch before the PR is opened.

There is no `develop` branch in active use. Slice branches PR directly into `master`.

---

## Branch Strategy

### `master`
- The single integration branch. Always green (tests passing) at every commit.
- Direct commits to `master` are avoided. Work happens on slice branches and lands via squash-merge PR.

### `phase/N-slice<n>-<short-description>`
- One branch per slice of work. A slice is a vertical-slice deliverable: playable, tested, mergeable.
- Examples actually used on the project:
  - `phase/0-foundation`
  - `phase/1-grid-combat`
  - `phase/2-conditions-dying`
  - `phase/2-slice2-reactions-trip-demoralize`
  - `phase/2-slice3-shield-block`
  - `phase/2-slice4-ranged-hero-points`
  - `phase/2-slice5a-casting-foundation`
  - `phase/2-slice5b1-aoe-multi-target`
  - `phase/2-slice5c-ai-companions`
- Lifetime: a slice (typically days to a couple of weeks).
- Commits on a slice branch can be granular (per task / per fix). The squash-merge collapses them to one commit on `master`, so granularity is for review and rollback inside the slice, not for `master` history.

### `bugfix/<short-description>`
- For bugs found between slices that don't belong to an active slice branch.
- Branch from `master`, fix, PR, merge. Same workflow as a slice — just smaller scope.

### Other branch prefixes (not currently in regular use)
- `ai-draft/` and `feature/` are documented in earlier versions of this guide. They are available if you want a sandbox for raw AI output before integrating it into a slice branch, but slice branches themselves already serve that role for this project's cadence.

### Branch hierarchy

```
master (integration, always green)
  ^
  |  squash-merge via PR
  |
phase/N-sliceX-name (one slice of work)
  |  fine-grained commits during the slice
  |  GUT tests green before opening PR
```

---

## Slice Workflow

### Start a slice

```bash
git checkout master
git pull origin master
git checkout -b phase/N-sliceX-short-description
```

Write a slice plan in `docs/plans/YYYY-MM-DD-phaseN-sliceX-name.md` (matching the existing `docs/plans/` examples). The plan lists tasks, frozen interfaces touched, and acceptance criteria.

### During the slice

Commit per task or per fix. Conventional-commit prefix + scope:

```bash
git commit -m "feat(combat): execute_trip Athletics vs Reflex"
git commit -m "test(trip): add 10 GUT tests covering all 4 degrees"
git commit -m "fix(hud): trip prone outcome must call update_party_sprite"
```

Run GUT before each commit:

```bash
"C:/Users/david/Desktop/Godot_v4.6.1/Godot_v4.6.1-stable_win64_console.exe" \
  --headless --path . -s addons/gut/gut_cmdln.gd -gexit
```

(Or `-gtest=res://tests/test_<file>.gd` to target one test file.)

### Before opening the PR

- [ ] All GUT tests pass on the slice branch
- [ ] Slice plan tasks are checked off (or explicitly deferred to a later slice with a `TODO(phaseN-...)` marker in code)
- [ ] CLAUDE.md "Current Status" updated with the slice's deliverables and test count
- [ ] Manual smoke test of the slice's playable surface in-engine

### Merging

PRs squash-merge into `master`. The PR title becomes the squash-commit subject; the body becomes the squash-commit body. Recent examples on this repo: PR #5 (`Phase2-Slice4-Complete`) → squash `96e2592`, PR #6 (`Phase2-Slice5a-Complete`) → squash `510bc16`.

After merge:

```bash
git checkout master
git pull origin master
git tag -a Phase2-Slice<n>-Complete -m "Phase 2 Slice <n>: <one-line summary>"
git push origin Phase2-Slice<n>-Complete
git branch -d phase/N-slice<n>-name      # local cleanup
git push origin --delete phase/N-slice<n>-name   # remote cleanup (optional)
```

---

## Tags

Tags mark **per-slice** completion, not just per-phase. This gives you a return-to-known-good point for every shippable chunk.

### Tag naming

- Phase-level: `PhaseN-<Name>-Complete` — e.g. `Phase0-Foundation-Complete`, `Phase1-Grid-Complete`.
- Slice-level: `Phase<N>-Slice<n>-Complete` — e.g. `Phase2-Slice4-Complete`, `Phase2-Slice5a-Complete`.

Use slice-level tags inside multi-slice phases (Phase 2 has 5+ slices and counting). Use a phase-level tag at the end of the phase if there's a meaningful "phase done" boundary.

### Tag commands

```bash
git tag                                                # list
git tag -a Phase2-Slice5a-Complete -m "summary"        # create annotated
git show Phase2-Slice5a-Complete                       # inspect
git push origin Phase2-Slice5a-Complete                # push one
git push origin --tags                                 # push all
git checkout Phase2-Slice5a-Complete                   # detached-head view
git checkout -b recovery/from-slice5a Phase2-Slice5a-Complete   # branch from tag
```

---

## GitHub Issues & Milestones

Issues are optional for this solo project. The slice plan (`docs/plans/YYYY-MM-DD-...md`) is the primary planning artifact; the PR description is the primary integration artifact.

If you do use issues:

- **Milestone = phase** (not slice). One milestone per phase.
- **Issue = task or deliverable** within a slice. Reference the slice plan in the issue body.
- **Issue title:** `[Phase N Slice X] <deliverable>`
- **Close issues from the squash-merge commit body** with `Closes #NN` so GitHub auto-closes them on merge.

### Labels

Keep the set small:

| Label | Used For |
|-------|----------|
| `combat` | Combat manager, actions, attack resolution, conditions |
| `rules` | PF2e rules engine, derived stats, action validation |
| `exploration` | TileMap, movement, fog of war, dungeon/town maps |
| `ai` | Enemy AI, companion behaviors |
| `ui` | HUD, menus, modals, picker |
| `data` | DataLoader, JSON, models, serialization |
| `save` | Save/load, schema migration |
| `network` | Multiplayer, lobby, sync |
| `content` | Dungeons, enemies, quests, items |
| `audio` | Music, SFX, ambient |
| `qa` | Testing, balance, bug triage |
| `scope` | Planning, scope decisions, doc updates |
| `bug` | Defect (use with `bugfix/` branch) |
| `accessibility` | WCAG / GAG baseline work — see `08_ACCESSIBILITY.md` |

---

## Commit Message Strategy

### Format

```
<type>(<scope>): <subject>

<body — optional>

<footer — optional, e.g. Closes #NN>
```

### Types

- `feat:` — new feature or significant addition
- `fix:` — bug fix
- `test:` — test additions or test fixes
- `refactor:` — no behavior change
- `perf:` — performance
- `docs:` — documentation only
- `chore:` — build, deps, tooling
- `review:` — review-fix follow-ups inside a slice (e.g. `f4f8062 review(slice5b1): doc signatures, range_tiles, defense-in-depth filter`)

### Scopes

Match the affected directory or system. Examples drawn from the actual git log:

- `combat`, `hud`, `combat-actions`, `combat-manager`
- `rules`, `data-loader`, `models`
- `dungeon`, `fog-of-war`, `tilemap`
- `ai`, `enemy-ai`
- `network` (Phase 5+)
- `tests`, `test-helpers`
- `docs`

### Subject rules

- Imperative mood ("add" not "added").
- Lowercase first letter.
- No trailing period.
- ≤ 70 chars (a touch more lenient than the classic 50 — readable subjects > rigid limit).

### Examples (good — pulled from this repo)

```
feat(combat): execute_trip Athletics vs Reflex
fix(hud): don't clobber picker rows with early _update_ui call
fix(hud): await async combat_manager calls (stride/trip/demoralize)
refactor(hud): collapse duplicated cancel branches in _unhandled_input
review(slice5b1): doc signatures, range_tiles, defense-in-depth filter
docs: Phase 2 Slice 5b1 status — AoE damage + multi-target UX
test(spell-system): cone resolver halves damage on save success
```

### Examples (bad)

```
Updated stuff                            # too vague
Fixed the bug                            # which bug?
feat: ADD DATA LOADER                    # caps; missing scope
feat(data-loader): loads json files      # not imperative
feat(combat): add Trip and Demoralize and the HUD buttons and tests   # too broad — split it
```

---

## Rollback Strategy

**Default to soft reverts.** `git revert` creates a new commit that undoes an old one — it preserves history, is always safe on shared branches, and can itself be reverted if you change your mind.

### If a slice merge breaks `master` (safe, always):

```bash
git log --oneline -10                      # find the offending squash commit
git revert <sha>                           # creates a revert commit; do NOT run a second `git commit`
git push origin master
```

### If you want to undo multiple recent commits:

```bash
git revert --no-commit HEAD~3..HEAD
git commit -m "revert: undo last 3 commits — see issue #NN"
```

### Destructive options (LOCAL, UNPUSHED only)

```bash
git branch -D phase/N-sliceX-broken        # delete a never-pushed branch you don't want
git reset --hard HEAD                      # throw away uncommitted work
git reset --hard Phase2-Slice4-Complete    # rewind a LOCAL branch back to a tag
```

> ⚠️ Never `git push --force` `master` (or any branch someone else may have pulled). Force-push on a shared branch destroys their work without warning. To undo something on `master`, use `git revert` and let history move forward.

### If you lose work:

```bash
git reflog                                 # last ~30 days of HEAD positions, including orphaned commits
git checkout <sha>
git switch -c recovery/found-it
```

---

## AI-Generated Code

When committing AI-generated code into a slice branch:

1. Run the scene — does the engine still load?
2. Read the diff — does the code make sense?
3. Run GUT — do tests pass?
4. Commit on the slice branch with a normal `feat:` / `fix:` message. The PR body is a fine place to note "this slice was AI-assisted" if you want the audit trail; it's not required per-commit.

The earlier-documented `ai-draft/` branch prefix is available if you want a quarantine before merging into the slice branch, but in practice slice branches already provide enough isolation.

---

## Daily Checklist

### Start of day

- [ ] `git status` — clean working tree?
- [ ] `git pull origin master` if returning to `master` between slices
- [ ] On the right branch? `git branch`

### During the day

- [ ] Commit per task / per fix
- [ ] Run GUT before each commit (at least targeted tests; full suite before PR)
- [ ] Keep commits atomic — one idea per commit

### End of day

- [ ] Everything committed (no uncommitted files)
- [ ] GUT green on the slice branch
- [ ] `git push origin <slice-branch>` so work survives local disk loss
- [ ] `git log --oneline -5` — does the history read cleanly?

---

## Critical Rules

1. **`master` stays green.** Squash-merge only after GUT is green on the slice branch.
2. **Pull before pushing** to avoid noise merges.
3. **Commit frequently.** Small commits roll back cleanly.
4. **Run GUT before commit.** Broken commits waste future-you's time.
5. **Tag every shippable slice.** Slice tags are your return-to-known-good points.
6. **No force-push to `master`.** Use `git revert`.
7. **Delete merged slice branches** locally and on the remote.
8. **Slice plan + CLAUDE.md status updates** are part of the slice, not optional polish.

---

## Decision Tree

### "Should I commit now?"

- Does this change work? → yes → commit
- Is the change atomic (one idea)? → yes → commit
- Is the commit message clear? → yes → commit
- Otherwise → finish the thought, then commit

### "Which branch?"

- New slice work → `phase/N-sliceX-short-description` from `master`
- Bug between slices → `bugfix/short-description` from `master`
- Quarantining raw AI output → `ai-draft/...` (optional; usually unnecessary)
- Production → `master` (via squash-merge PR)

### "How granular should commits be inside a slice?"

- Per task in the slice plan, or per fix during review.
- Squash-merge collapses them into one `master` commit anyway, so optimize the slice-branch history for *your* review and rollback, not for `master`'s long-term log.

---

## Git Commands Reference

### Daily

```bash
git status
git add <file>                                # prefer specific files over `git add .`
git commit -m "type(scope): subject"
git push origin <branch>
git pull origin master
git log --oneline -10
git branch
git checkout -b phase/N-sliceX-name
git checkout <existing-branch>
```

### Review

```bash
git diff
git diff master..HEAD                         # what does this slice add over master?
git log --stat
git show <sha>
git log --graph --oneline --all --decorate
```

### Tags

```bash
git tag
git tag -a Phase2-Slice<n>-Complete -m "summary"
git show Phase2-Slice<n>-Complete
git push origin Phase2-Slice<n>-Complete
git push origin --tags
git checkout Phase2-Slice<n>-Complete
```

### GUT

```bash
# Full suite
"C:/Users/david/Desktop/Godot_v4.6.1/Godot_v4.6.1-stable_win64_console.exe" \
  --headless --path . -s addons/gut/gut_cmdln.gd -gexit

# Single file
"C:/Users/david/Desktop/Godot_v4.6.1/Godot_v4.6.1-stable_win64_console.exe" \
  --headless --path . -s addons/gut/gut_cmdln.gd \
  -gtest=res://tests/test_<file>.gd -gexit
```

---

**Unnamed RPG GitHub Workflow Guide**
