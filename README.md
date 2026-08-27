# rails-do

A Claude Code plugin that implements Ruby on Rails changes from a ticket, issue writeup, or bug report using a spec-driven workflow: clarify, plan, execute, verify.

## What it does

- Clarifies ambiguous requirements with the user, once, batched, before planning.
- Drafts a two-layer plan file (Intent + Grounding) before any code, with an amendment rule so scope changes never silently overwrite the approved intent.
- Enforces Red -> Green -> Refactor with hard gates: no implementation before a failing spec, no advancing without pasted lint/test output.
- Dispatches specialist subagents in dependency order (migrations -> models -> services -> ... -> views) once a ticket crosses a 3-layer threshold, with a scope gate for anything larger.
- Verifies before calling a ticket done: runs the repo's lint and test commands and pastes the output.

## Prerequisites

- A Ruby on Rails app. The skill asks once which lint and test commands this repo uses if it can't tell, and notes the answer in the plan file.
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

If the skill doesn't show up in a session that was already running, run `/reload-plugins` or restart.

Verify the install landed correctly with `claude plugin details rails-do@rails-do` — it should show `Skills (1) rails-do`.

For local development, point `marketplace add` at a local path instead (e.g. `./rails-do` from the parent directory).

## House rules are opinions, not requirements

The twelve House rules in [`references/house-rules.md`](plugins/rails-do/skills/rails-do/references/house-rules.md) (concern + PORO subsystem before a standalone service, thin controllers, presenter conventions, and so on) are one team's specific Rails conventions, shipped as-is and not configurable in this version. If your team's conventions differ, fork the House rules file and the accompanying `references/style-guide.md` / `references/style-checklist.md` (both under `plugins/rails-do/skills/rails-do/references/`) rather than fighting the gates — the plan workflow, TDD gates, and subagent dispatch mechanics underneath are the reusable part.

## Scope

Plain Markdown plus reference files — works wherever Agent Skills are supported, and uses subagents when the environment provides them. House rules and rule files assume a Ruby on Rails codebase.
