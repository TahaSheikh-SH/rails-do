---
name: rails-do
description: Implements Ruby on Rails code changes from Jira tickets, issue writeups, bug reports, and surrounding repository context using a pragmatic, domain-driven house style. Use when the user provides a Jira ticket, acceptance criteria, or implementation context and wants Rails code, refactors, patches, or tests. It is not intended for sprint planning, ticket triage, status updates, or non-Rails coding tasks.
metadata:
  author: user-customized
  version: 3.0.0
  style-guide: definitive-code-writing-guide
---

# Implementing Rails Changes

## Workflow

1. **Clarify** — ask what would change the implementation, batched, once.
2. **Plan** — draft `.rails-do/<ticket-key>/spec.md`, get it approved.
3. **Execute** — work the plan's file list in order; dispatch subagents past the layer threshold.
4. **Verify** — run lint and tests, paste the output.

## Hard rules

**Before anything:** confirm an approved plan exists (Step 2) — draft one if not.

**Always allowed:** reading code, grepping, `git status`/`git diff`; running the repo's detected lint or test command scoped to one file; drafting or updating the plan file.

**Ask first:** touching files outside the plan's stated scope; adding a gem dependency; changing CI/CD config.

**Never:** run the test command with no file scope; write implementation before a spec fails for the right reason (assertion failure, not a load error); claim completion without pasting actual lint and test output; commit or push without explicit user approval; pass a subagent more than `goal_hint + acceptance_criteria + rails_rules + workflow + task`; edit `db/schema.rb` directly; add comments that restate the code; edit the tracked `.gitignore` to hide `.rails-do/` — use `.git/info/exclude` only.

## Step 1 — Clarify

Ask the user, once, batched in a single message, only the questions whose
answers would change the implementation — not ones you can answer by reading
the repo. Typical: which model owns this behavior, whether to follow or
replace an existing pattern, what happens in an edge case the ticket doesn't
mention. If nothing is genuinely ambiguous, say so and go straight to the plan.

## Step 2 — Plan

Every ticket gets a plan file before Step 3 — even a one-line fix. Cheap to write, catches drift before code does.

**File:** `.rails-do/<ticket-key>/spec.md` (ticket-key = Jira key, else a short slug reused for the ticket's life). Check for an existing matching stub before minting a new key. Exclude `.rails-do/` via `.git/info/exclude`, never the tracked `.gitignore` — working state, not a deliverable.

**Layer 1 — Intent (locked once approved):**
```
# Spec: <ticket-key> — <one-line title>

## Problem
<what's broken or missing, and why it matters>
## Desired behavior
<what happens after the change>
## Acceptance criteria
- <bullet>
## Scope
In: <bullet> / Out: <bullet>
## Constraints
<perf, security, compatibility, API contract — or "none stated">
## Files to touch
<path>: <intent>  (repeat, execution order — Step 3 slices by this)
## Open questions
[NEEDS CLARIFICATION: <question>]
## Amendments
(none)
```

**Layer 2 — Grounding** (facts, updates freely, no approval): existing pattern (`file:line`), rule files mapped (Rules reference below), test coverage found, layers touched, dispatch plan (3+ layers only).

**Drafting:** draft both layers from the ticket text plus inline research — budget 5 greps, 1 file read — before asking anything. Tag gaps as `[NEEDS CLARIFICATION: <question>]`. Show the draft. **Gate:** every tag resolved and Layer 1 explicitly approved — silence isn't approval — before Step 3.

**Resume:** plan exists and Layer 1 approved → skip drafting, match `git status`/`git diff` against the file list to find where to resume.

**Amendment rule:** Layer 1 locked once approved, no silent edits. Mid-implementation changes get a dated Amendments entry (what/why/replaces) and the same approval as the original plan. Layer 2 is exempt.

**Voice:** terse, fact-first, no lead-in or filler, bullets over paragraphs.

## Step 3 — Execute

Unit of work: a plan slice (one line from the plan's file list), run in the plan's order. Subagents available → one per slice; otherwise work slices in order, single pass.

**Before implementing a slice:** restate the ticket in domain language (brief); grep for an existing analogous pattern to mirror; grep the files you're touching for N+1 risk (`.each` over an AR collection without `includes`/`preload`/`eager_load` — prefer `strict_loading` on Rails 8+, verify with `EXPLAIN ANALYZE`); for real-time or partial-page updates, pick the right Turbo primitive (`references/style-guide.md`).

**Layers** (count these): migration, model, service, policy, controller, graphql, view, job, query-object, mailer. Integration specs and the review pass don't count.

**Dispatch:** 1-2 files, one layer → inline. 3+ layers → dispatch subagents. Full feature → always dispatch.

**Order** (dependency-first): migrations → models → services → query objects → policies → controllers → graphql → jobs → mailers → views + specs.

**Required parallel pairs:** migration-agent → model-agent + rspec-agent together; model-agent → policy-agent + controller-agent together.

**Scope gate** (3+ layers, no `+Nk` directive): ask the user full depth vs. highest-risk layer only. No stated depth → cap at 3 highest-risk layers (never split a required pair); rspec-agent and review-agent always run. State what was sampled/skipped; `+Nk` lifts the cap.

**Subagent contract** — exactly this, nothing else. Orchestrator excerpts everything into the payload; a subagent never reads rule files or project config itself.
```
goal_hint:            <one sentence — what proves success>
acceptance_criteria:  <2-4 bullets, from the plan>
rails_rules:          <excerpt from references/rules/*.md for this layer>
workflow:             <TDD Red/Green/Refactor text, pasted in>
task:                 <one bounded thing to do>
schema:               { files_changed: [string], test_results: {status, output}, blockers: string }
```
Read `blockers` first; not `'none'` → surface and stop. Partial failure (some subagents fail): surface the blocker, keep the rest, note incomplete layers — don't halt the whole chain unless the blocker is unrecoverable.

**Roles → rules to excerpt:** migration `database.md` · model `models.md, callbacks.md, testing.md` · service `models.md, naming.md, testing.md` · policy `policies.md` · controller `controllers.md, testing.md` · graphql `controllers.md, models.md, testing.md, app/graphql/AGENTS.md` · view `views.md, testing.md` · job `performance.md, testing.md` · query-object `models.md, testing.md` · mailer `testing.md` · rspec `testing.md` (cross-cutting specs only) · review `testing.md`.

**TDD per slice:** Red — write/update spec, run, paste output; gate: assertion failure before implementing. Green — smallest change, run, paste output; gate: all passing, then stop. Refactor — improve while green, re-run each change, revert if red. See `references/tdd-checklist.md`.

**review-agent:** once per ticket, after every slice, dispatched or inline alike. `{ acceptance_criteria, grounding, files_changed, lint_and_test_output, style_checklist: references/style-checklist.md }` → `{ verdict, failed_criteria, style_gaps, gaps, excess_comments, excess_scope }`. Gate on `failed_criteria.length === 0`. Non-empty: re-dispatch a fix to the owning specialist, re-run lint/test, re-check — max 2 retries, then escalate. `style_gaps` non-empty: surface as a named, unresolved gap in the final report, don't ship past it silently. Empty otherwise: surface `gaps`/`excess_scope` advisory, strip `excess_comments` from the diff first.

**Git rule:** after verification, `git diff --cached`, propose a commit message, wait for user YES — never a subagent running `git commit`.

**Archiving:** once committed, move `.rails-do/<ticket-key>/` to `.rails-do/archive/<ticket-key>/`.

## Step 4 — Verify

Before reporting done: run the repo's lint and test commands for the files
you changed, paste the output. Either fails → not done. Can't tell which
commands this repo uses → ask once, note the answer in the plan file.

Run `bundle exec brakeman --no-pager` if present. GraphQL files changed → regenerate the schema (`bundle exec rails graphql:schema:idl && bundle exec rails graphql:schema:llm_ops`) and stage it. Style-checklist review already happened at review-agent's gate (Step 3) — don't re-check it here.

## House rules

Full text: `references/house-rules.md`. Load it when writing code, not when
planning.

1) Favor domain language · 2) Rich models, thin controllers ·
3) Model facades over service-first APIs · 4) Concerns for real traits only ·
5) Lean into Active Record · 6) Callbacks and Current allowed when appropriate ·
7) Migrations must be safe and reversible · 8) Deny-by-default authorization ·
9) Background jobs must be idempotent · 10) Abstractions must earn their keep ·
11) Fractal code quality · 12) Ruby consistency

## Rules reference

All rule files live at `references/rules/<name>.md`. Load only what you are actively building in — each file costs tokens. Load the cited section, not the whole file, where a section is cited. `references/style-checklist.md` always loads and always gates review-agent, for any hand-authored change — skip only for machine-generated output (migrations, `schema.rb`, GraphQL schema dumps).

| Task type | Load these rules |
|---|---|
| Spec-only change | `testing.md`, `style.md` |
| Migration only | `database.md` |
| Model + spec | `models.md`, `callbacks.md`, `naming.md`, `testing.md`, `style.md` |
| Service + spec | `models.md`, `naming.md`, `testing.md`, `style.md` |
| Controller + spec | `controllers.md`, `naming.md`, `testing.md`, `style.md` |
| GraphQL + spec | `controllers.md`, `models.md`, `naming.md`, `testing.md`, `style.md` |
| View / Hotwire + spec | `views.md`, `testing.md`, `style.md` |
| Authorization (Pundit) | `policies.md`, `controllers.md`, `testing.md` |
| New class / concern / module | `architecture.md`, `abstractions.md`, `naming.md` |
| Full feature | Dispatch subagents; each loads its own |

Other references, load only when they apply: `style-guide.md` (cross-cutting design questions), `examples.md` (a concrete pattern would help), `request-template.md` (better ticket input needed), `source-code-writing-guide.md` (extra nuance needed).

## Output contract

- Lead with a short implementation summary, then the files changed, patch, or code.
- Keep explanations brief and concrete.
- If underspecified, make the smallest reasonable assumption and state it once.
- Don't apologize for choosing Rails-native patterns.

## Negative triggers
Not for non-Rails/non-Ruby work — unless the user explicitly asks to adapt the style guide's spirit rather than follow Rails patterns.

## Failure handling

Surface to the user immediately — don't guess past a blocker — when a subagent can't finish, the plan contradicts the code, or a file/method that should exist doesn't. Format: `Blocked — [step]: [attempted] / [failed] / [needed]`.

**Pre-existing failures:** `git stash`, rerun the spec, compare failure counts. Failures present both before and after are pre-existing noise, not yours to fix. Unstash, investigate only what disappeared.

**Before claiming any step done:** Step 4's lint and test output are pasted and green, `references/tdd-checklist.md`'s flaky-spec gate is checked, review-agent's `failed_criteria` is empty on the ticket's final step, and — if proposing a commit — the diff is shown and the user has said YES.
