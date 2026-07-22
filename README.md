# rails-do

A Claude Code plugin that implements Ruby on Rails changes from a ticket, issue writeup, or bug report using a spec-driven workflow with hard TDD gates and dependency-ordered subagent dispatch.

## What it does

- Drafts a two-layer spec stub (Intent + Grounding) before any code, with an amendment rule so scope changes never silently overwrite the approved intent.
- Enforces Red -> Green -> Refactor with hard gates: no implementation before a failing spec, no advancing without pasted rspec/standardrb output.
- Dispatches specialist subagents in dependency order (migrations -> models -> services -> ... -> views) once a ticket crosses a 3-layer threshold, with a scope gate for anything larger.
- Ships a Stop hook that mechanically blocks turn-end if standardrb or the mapped rspec fails, for any Rails layer with a 1:1 file-to-spec convention (models, services, jobs, policies, and others — see SKILL.md for the full list). Controllers, GraphQL, views, and migrations aren't covered by the hook and rely on the workflow's own manual gates instead.

## Prerequisites

- A Ruby on Rails app using `bundle exec standardrb` for linting and `bundle exec rspec` for tests (the hook and workflow both assume `SKIP_COVERAGE=1` is meaningful in this repo — harmless if it isn't).
- Claude Code with plugin support.

## Install

```
/plugin marketplace add <path-or-git-url-to-this-repo>
/plugin install rails-do@rails-do
/reload-plugins
```

For local development, point `marketplace add` at a local path (e.g. `./rails-do` from the parent directory).

## House rules are opinions, not requirements

The twelve House rules in `SKILL.md` (concern + PORO subsystem before a standalone service, thin controllers, presenter conventions, and so on) are one team's specific Rails conventions, shipped as-is. They are not configurable in this version. If your team's conventions differ, fork the House rules section and the accompanying `references/style-guide.md` / `references/style-checklist.md` rather than fighting the gates — the spec-stub workflow, TDD gates, and subagent dispatch mechanics underneath are the reusable part.

## Scope

Claude Code only, for now. The Stop hook and subagent dispatch rely on Claude-Code-specific mechanics (hooks, the Agent tool) with no equivalent on other platforms.
