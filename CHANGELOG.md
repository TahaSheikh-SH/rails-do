# Changelog

## 3.0.0

Breaking. Removes the Stop hook and its config surface — `verify_before_stop.py`,
`test_verify_before_stop.py`, the `hooks` key in `plugin.json`, `enforce:`
modes, `.rails-do/toolchain-override`, and the `tdd-red-expected` marker.
Verification is now the agent running the repo's lint and test commands
itself and pasting the output, not a mechanically enforced turn-end block.

Workflow restructured into four steps — Clarify, Plan, Execute, Verify —
replacing the prior spec-stub/dispatch/implementation-workflow layout.
The twelve house rules moved out of `SKILL.md` into
`references/house-rules.md`, with an index left in their place.
`SKILL.md` no longer refers to a project's `CLAUDE.md`; the orchestrator
excerpts everything a subagent needs into its dispatch payload instead.
