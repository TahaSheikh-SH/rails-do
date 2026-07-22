# rails-do

A Claude Code plugin that implements Ruby on Rails changes from a ticket, issue writeup, or bug report using a spec-driven workflow with hard TDD gates and dependency-ordered subagent dispatch.

## What it does

- Drafts a two-layer spec stub (Intent + Grounding) before any code, with an amendment rule so scope changes never silently overwrite the approved intent.
- Enforces Red -> Green -> Refactor with hard gates: no implementation before a failing spec, no advancing without pasted rspec/standardrb output.
- Dispatches specialist subagents in dependency order (migrations -> models -> services -> ... -> views) once a ticket crosses a 3-layer threshold, with a scope gate for anything larger.
- Ships a Stop hook that mechanically blocks turn-end if standardrb or the mapped rspec fails, for any Rails layer with a 1:1 file-to-spec convention (models, services, jobs, policies, and others — see [`SKILL.md`](plugins/rails-do/skills/rails-do/SKILL.md) for the full list). Controllers, GraphQL, views, and migrations aren't covered by the hook and rely on the workflow's own manual gates instead. The hook won't block on a spec you've deliberately left failing mid-TDD-Red — see the `tdd-red-expected` marker in the SKILL.md TDD section.

## Prerequisites

- A Ruby on Rails app using `bundle exec standardrb` for linting and `bundle exec rspec` for tests (the hook and workflow both assume `SKIP_COVERAGE=1` is meaningful in this repo — harmless if it isn't).
- Claude Code with plugin support.

## Install

From an interactive Claude Code session:

```
/plugin marketplace add https://github.com/TahaSheikh-SH/rails-do
/plugin install rails-do@rails-do
```

Or from a terminal, before starting a session:

```
claude plugin marketplace add https://github.com/TahaSheikh-SH/rails-do
claude plugin install rails-do@rails-do
```

If the skill or hook doesn't show up in a session that was already running, run `/reload-plugins` or restart.

Verify the install landed correctly with `claude plugin details rails-do@rails-do` — it should show `Skills (1) rails-do` and `Hooks (1) Stop`.

For local development, point `marketplace add` at a local path instead (e.g. `./rails-do` from the parent directory).

## House rules are opinions, not requirements

The twelve House rules in [`SKILL.md`](plugins/rails-do/skills/rails-do/SKILL.md) (concern + PORO subsystem before a standalone service, thin controllers, presenter conventions, and so on) are one team's specific Rails conventions, shipped as-is. They are not configurable in this version. If your team's conventions differ, fork the House rules section and the accompanying `references/style-guide.md` / `references/style-checklist.md` (both under `plugins/rails-do/skills/rails-do/references/`) rather than fighting the gates — the spec-stub workflow, TDD gates, and subagent dispatch mechanics underneath are the reusable part.

## Scope

Claude Code only, for now. The Stop hook and subagent dispatch rely on Claude-Code-specific mechanics (hooks, the Agent tool) with no equivalent on other platforms.
