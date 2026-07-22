---
name: rails-do
description: Implements Ruby on Rails code changes from Jira tickets, issue writeups, bug reports, and surrounding repository context using a pragmatic, domain-driven house style. Use when the user provides a Jira ticket, acceptance criteria, or implementation context and wants Rails code, refactors, patches, or tests. It is not intended for sprint planning, ticket triage, status updates, or non-Rails coding tasks.
metadata:
  author: user-customized
  version: 2.1.0
  style-guide: definitive-code-writing-guide
---

# Implementing Rails Changes

**Ticket lifecycle:** Spec stub → dispatch decision (Subagent dispatch + Scope gate) → Implementation workflow → Archiving (Implementation workflow step 7).

## Hard rules

**Before doing anything:** confirm this ticket has an approved spec stub (see Spec stub section) — draft one first if it doesn't.

A Stop hook (bundled with this plugin as `scripts/verify_before_stop.py`) mechanically blocks turn-end if standardrb or the mapped rspec fails, for any layer with a 1:1 file-to-spec convention. It does not cover controllers, graphql, views, or migrations — the manual gates below are the only enforcement there, and pasting output still matters everywhere else for the user's own visibility into what ran. During TDD Red (below), an intentionally failing spec doesn't block — see the `tdd-red-expected` marker in that step.

**Never:**
- Run bare `rspec` — always `SKIP_COVERAGE=1 bundle exec rspec <specific_file>`
- Write implementation code before seeing a spec fail for the right reason (assertion failure, not a load error)
- Advance from Red to Green until spec output shows an assertion failure
- Advance from Green to Refactor until spec output shows all passing
- Claim completion without showing actual output of both standardrb and rspec
- Commit or push without explicit user approval
- Pass more than `goal_hint + acceptance_criteria + rails_rules + task` to a subagent
- Edit `db/schema.rb` directly
- Add inline comments that restate what the code does

## Subagent contract

Every subagent you mint receives exactly this contract — nothing else:

```
goal_hint:            <one sentence — what outcome proves this agent succeeded>
acceptance_criteria:  <2–4 bullets the verification subagent checks against explicitly>
rails_rules:          <excerpt from the relevant references/rules/*.md files for the layers this agent touches — consult the Rules Reference table; do not read CLAUDE.md>
task:                 <one specific, bounded thing to do>
schema:               {
                        "files_changed": ["string"],
                        "test_results": {
                          "status": "pass | fail",
                          "output": "rspec output snippet (≤20 lines, or the full failure/diff block if longer)"
                        },
                        "blockers": "string (describe blocker, or 'none')"
                      }
                      Pass this object as the schema: option in the Agent tool call.
                      The tool layer enforces shape — no prose token-limit instruction needed.
```

**Orchestrator chaining:** Read `blockers` first — if not `'none'`, surface immediately and stop. Pass `files_changed` from migration-agent as context to model-agent when the model depends on schema additions.

**Partial failure protocol:** When some subagents succeed and others fail or return incomplete results, do not halt the entire chain. Instead: (1) surface the failed agents' errors with the exact blocker described, (2) proceed with the successful agents' output, (3) note which layers are incomplete in the phase summary. Reserve a full halt for unrecoverable blockers only (schema does not exist, required file is missing, test has a load error not an assertion failure).

`acceptance_criteria` is derived from the ticket's acceptance criteria or BMAD story. It is what the verification pass checks against — not a restatement of the task.

**WRONG** — never do this:
```
Deploy subagent with: full plan text + all previous phase output + every CLAUDE.md
```

**CORRECT:**
```
goal_hint:            "CoveredLife#deactivate returns :ok on valid status transition"
acceptance_criteria:  - returns :ok symbol on valid transition
                      - returns :error on invalid status
                      - spec is green with 0 failures
rails_rules:          [excerpt from references/rules/models.md]
task:                 "Add deactivate method to app/models/covered_life.rb"
Pass schema: { files_changed, test_results: { status, output }, blockers }
```

**Verification agent contracts** (verify-agent, completeness-critic-agent — same "nothing else" rule applies):
```
verify-agent:              { acceptance_criteria, files_changed, standardrb_and_rspec_output }
returns:                   { "verdict": "pass | fail", "failed_criteria": ["string"] }

completeness-critic-agent: { acceptance_criteria, files_changed }
returns:                   { "verdict": "pass | gaps_found", "gaps": ["string"] }
```

## House rules

### 1) Favor domain language
- Name methods, classes, concerns, and variables after real domain concepts.
- Prefer intent-rich names over generic CRUD or service vocabulary.
- If the ticket introduces important domain terms, use them consistently across code, tests, and comments.

### 2) Prefer rich models and thin controllers
- Controllers should translate HTTP or params into one or two domain operations.
- Keep branching, workflow logic, and orchestration out of controllers when the behavior belongs to the domain.
- Prefer public model APIs that read like English.

### 3) Prefer model facades over service-first APIs

The preference order is: **concern + PORO subsystem → standalone service** — not the other way around.

**First, try a concern with a delegating PORO subsystem:**
- Expose a clean domain API via a concern: `account.terminate` via `Account::Closable`.
- The concern delegates internally to namespaced POROs: `Account::Closing::Purging`, `Account::Closing::Incineration`.
- The caller never sees the subsystem; the model stays non-fat.
- Prefer `recording.incinerate` over `Recording::IncinerationService.execute(recording)`.

Before proposing a service, run the decision gate in `references/style-guide.md` ("Vanilla Rails is plenty") — mandatory, not optional. Agents default to services too quickly.

**When a service is justified:**
- Run the generator first: `rails generate service <name> > /dev/null 2>&1; ls app/services/<name>.rb spec/services/<name>_spec.rb`
- Name it as a domain noun, not a verb: `Billing::InvoiceIssuance`, not `InvoiceIssuingService`.
- Do not default to a Result pattern — use it only if the caller needs to distinguish error cases.
- Do not create interactor, command, or form objects.

### 4) Use concerns only for real traits or roles
- A concern must represent a genuine has-a or acts-as trait.
- Model-specific concerns belong under `app/models/model_name/`.
- Shared cross-model concerns belong under `app/models/concerns/`.
- Do not use concerns as arbitrary file-splitting containers.

### 5) Lean into Active Record
- Prefer straightforward Active Record models, associations, scopes, delegated types, STI, and serialized attributes when they fit.
- Keep persistence and domain logic together when that is the most natural design.
- Introduce dedicated query objects only when the query is substantial enough to justify encapsulation.

### 6) Callbacks and Current are allowed when appropriate
- Use callbacks for orthogonal lifecycle concerns, not to hide the primary business workflow.
- Use Current for request-scoped defaults or audit context when that keeps controllers cleaner.
- Use suppression patterns only for narrow exceptional cases.

### 7) Migrations must be safe and reversible
- Every migration must use the reversible `def change` DSL or implement `def down` — never a one-way `def up` without `def down`.
- Do not mix DDL (schema changes) and data manipulation in the same migration. Large or slow backfills belong in a separate maintenance task. Small, safe data fixes (e.g., populating a newly-added NOT NULL column with a safe default) are acceptable if they complete in milliseconds on any production DB size.
- Use `disable_ddl_transaction!` when creating indexes concurrently (`algorithm: :concurrently`).
- Always declare `on_delete:` behavior on foreign key constraints — never leave cascade behavior implicit.
- Every foreign key column must have an index. Prefer partial indexes when the query has a known condition (e.g., `where: "status = 'active'"`).
- Composite indexes should order columns from most-selective to least-selective, matching the `WHERE` clause field order.

### 8) Authorization: deny-by-default when Pundit is in use
When the codebase uses Pundit:
- Call `authorize` before every controller action that touches a resource.
- Use `policy_scope(Model)` for index queries — never expose unscoped collections to end users.
- Policies are per-action — test each policy method and the scope.
- Never use params or user input as an authorization signal before `authorize` has run.
- When adding a new action to an existing controller, verify the corresponding policy class covers it.

### 9) Background jobs must be idempotent
- Design every job to be safe to run twice. Use `find_by` with an early return when the record may have been deleted before the job runs.
- Declare explicit retry strategy using `retry_on` and `discard_on`. Do not rely on the queue adapter's default retry count.
- Wrap long-running job logic in `around_perform` with `Timeout::Error` handling where appropriate.
- Do not enqueue a new job from inside a job unless it is a deliberate cascading pipeline and that intent is clearly named.

### 10) Abstractions must earn their keep
- Prefer explicit conditionals over clever indirection when there are only a few cases.
- Inline wrappers that add no meaning.
- Avoid `method_missing`, clever metaprogramming, or convenience base classes unless the payoff is obvious and real.

A `SimpleDelegator`-based presenter is acceptable as a view-layer decoration object when formatting a single display value (currency, dates, truncated strings) or decorating a model for a specific view context — not for complex HTML (use ViewComponent) or business rules (keep those on the model). Presenters belong in `app/presenters/`, named after the model they decorate: `InvoicePresenter`.

### 11) Fractal code quality
At every level aim for:
- domain-driven names
- encapsulation
- cohesion
- symmetry of abstraction

When a partial grows to contain meaningful conditional logic or is reused across three or more distinct contexts, evaluate whether a ViewComponent is warranted — creation sequence and pre-shipping checklist in `references/style-checklist.md`. Avoid ViewComponent for simple markup-only partials — the overhead is not worth it.

### 12) Ruby consistency
- Prefer new hash syntax.
- Prefer single quotes when not interpolating.
- Prefer positive `if` forms when the positive path is what matters.
- Use `%w` and `%i` where they improve consistency.
- Use `&&` and `||`, not `and` and `or`.

## Token efficiency

Every reference file costs tokens. Load nothing speculatively.

- Load rule files **only** when you are actively building in that area. A migration-only ticket needs `database.md`; it does not need `views.md` or `callbacks.md`.
- Load `references/style-guide.md` only for cross-cutting design questions, not as a warm-up for every task.
- Load `references/examples.md` only when a concrete implementation pattern would genuinely unlock the decision; skip it when the pattern is already clear.
- Load `references/style-checklist.md` once, at step 6 — not at the start.
- Load `references/tdd-checklist.md` only at the Refactor phase or the flaky-spec gate — not before.
- For pure formatting / linting tasks (no logic change), skip all rule files. Run `bundle exec standardrb --format progress` and present the diff. Do not load architecture or model rules.
- When dispatching subagents (see below), each agent loads only its own relevant rules, not the full set.

All rule files live at `references/rules/<name>.md`. Load only what you are actively building in — each file costs tokens.

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

## Spec stub

Before Scope gate or any implementation, every ticket gets a spec stub — one file, two layers. This runs unconditionally, even for a one-line fix: it is cheap to write, and it is where drift gets caught before code does.

**File:** `.rails-do/<ticket-key>/spec.md` (ticket-key = Jira key if given, else a short slug minted once and reused for the life of the ticket). Before minting a new key, check `.rails-do/` for an existing stub whose title or Problem already matches this ticket — reuse it rather than starting a duplicate. If `.rails-do/` is not already in `.gitignore`, add it — this is working state, not a deliverable.

**Layer 1 — Intent (locked once approved):**
```
# Spec: <ticket-key> — <one-line title>

## Problem
<what is broken or missing, and why it matters>

## Desired behavior
<what happens after the change>

## Acceptance criteria
- <bullet>

## Scope
In: <bullet>
Out: <bullet>

## Constraints
<performance, security, compatibility, API contract — or "none stated">

## Open questions
[NEEDS CLARIFICATION: <specific question>]

## Amendments
(none)
```

**Layer 2 — Grounding:**
```
## Grounding
- Existing pattern: <file:line of the closest analogous code, from a grep pass>
- Rule files: <task-type row this ticket maps to, from the loading table above>
- Test coverage: <spec files already covering this area, or "none found">
- Layers touched: <migration/model/service/policy/controller/graphql/job/view>
```
Grounding carries facts, not intent — the only layer that updates freely, with no approval, for the life of the ticket. (Layer 1 does not; see Amendment rule.)

### Drafting

0. Say one line before starting — e.g. "Drafting spec stub for `<ticket-key>`." — one line, not a play-by-play, so the user knows this step began.
1. Draft both layers immediately from the ticket text and prior context, plus your own inline research — before asking the user anything. Budget that research: at most 5 greps and 1 file read to find the closest analogous pattern and its spec.
   - Stay inline — don't dispatch a subagent for this. If the budget runs out before Grounding resolves, write what you have and tag the gap in Open questions (`[NEEDS CLARIFICATION: couldn't locate an existing pattern for X — where should this live?]`) instead of escalating research. A subagent for deeper research belongs to implementation, after Scope gate, once the ticket has cleared the 3+ layer threshold — not to drafting the stub.
2. Tag genuine gaps inline as `[NEEDS CLARIFICATION: <question>]` under Open questions. Do not ask a blanket set of questions; ask only what the draft could not resolve on its own.
3. Show the drafted `spec.md`. The user edits it directly or answers the tags in place.
4. **Gate:** every `[NEEDS CLARIFICATION]` tag must be resolved and Layer 1 explicitly approved — an edited file handed back, or an explicit "approved" / "looks good, proceed" — before any gate below runs. Silence or moving to another topic is not approval. Do not invent scope beyond what the approved spec states — one clearly stated assumption is acceptable; multiple silent assumptions are not.

### Resume

If `.rails-do/<ticket-key>/spec.md` already exists for this ticket:
1. Read it first. If Layer 1 isn't approved yet, resume Drafting from the open `[NEEDS CLARIFICATION]` tags.
2. If Layer 1 is approved, skip Drafting. Run `git status` / `git diff` for uncommitted work already written, and match any changed files against the Dispatch order (Subagent dispatch, below) to find which layer to resume from.
3. If nothing is uncommitted and no dispatch has happened yet, start at Implementation workflow step 1.

**WRONG** — never do this:
```
Ticket already has an approved .rails-do/<key>/spec.md — draft a new one anyway, ignoring it.
```

**CORRECT:**
```
Read .rails-do/<key>/spec.md → Layer 1 approved → git status shows the model file already
changed → resume at services, the next Dispatch order step after models — not from scratch.
```

### Amendment rule

Layer 1 is locked once approved. No silent edits.

When scope, behavior, or acceptance criteria change mid-implementation:
1. Do not rewrite Layer 1 in place.
2. Append a dated entry under Amendments: what changed, why, what it replaces.
3. Get the same explicit approval as the original spec (see Drafting gate above) before continuing implementation.

Layer 2 is exempt — see Grounding above.

### Voice

Spec and amendment text is terse and concrete, not narrated:
- Fact or decision first — no lead-in ("I'll now...", "Let's...", "As requested...").
- No restating the user's ask before answering it, no closing recap.
- No hedging filler ("just," "simply," "basically") and no filler adjectives ("robust," "comprehensive," "seamless") — if a word carries no information, cut it.
- Bullets for structured facts (criteria, scope, amendments), not paragraphs.

## Subagent dispatch

When a ticket touches **three or more distinct layers**, dispatch specialist subagents instead of implementing everything in one context. Each subagent starts fresh, loads only its layer's rules, and returns a focused diff. One dispatch round — one layer's specialist, or one dependency-ordered step when implementing inline without subagents — is a **phase**; other mentions of "phase" elsewhere in this skill mean the same thing.

**When to dispatch vs. implement inline:**

| Ticket scope | Approach |
|---|---|
| One or two files, single layer | Implement inline |
| 3+ layers (e.g., migration + model + spec + controller) | Dispatch subagents |
| Full feature from ticket to green tests | Always dispatch |

**Dispatch order** (dependency-first — never dispatch out of order):

```
migrations → models → services → query objects → policies → controllers → graphql → jobs → mailers → views + specs
```

**Required parallel pairs (dispatch in the same Agent tool call block — never sequentially):**
- migration-agent completes → dispatch model-agent + rspec-agent together
- model-agent completes → dispatch policy-agent + controller-agent together

**Compaction checkpoint:** on a Full-feature ticket, after the model-agent + rspec-agent pair completes and before dispatching policy-agent + controller-agent, run `/compact focus on <ticket-key>: keep the approved spec, Grounding, and files_changed so far; drop full subagent transcripts.` This is the natural midpoint of the Dispatch order, so the second half of a long chain doesn't carry the full first half's transcripts.

**Specialist subagent roles and what they load:**

| Subagent | Owns | Loads |
|---|---|---|
| migration-agent | Schema changes, indexes, FK constraints | `database.md` |
| model-agent | ActiveRecord model, associations, scopes, concerns + its own specs | `models.md`, `callbacks.md`, `testing.md` |
| service-agent | Services in `app/services/` for multi-model orchestration with no natural model home + its own specs. Try concern + PORO first (House rule #3). | `models.md`, `naming.md`, `testing.md` |
| policy-agent | Pundit policy and scope + its own specs | `policies.md` |
| controller-agent | HTTP orchestration, strong params + its own specs | `controllers.md`, `testing.md` |
| graphql-agent | Resolvers, types, mutations, subscriptions + their specs. Regenerate schema after implementing (see Pre-flight checklist). | `controllers.md`, `models.md`, `testing.md`, `app/graphql/AGENTS.md` |
| view-agent | ERB, Turbo primitives, Stimulus, ViewComponent + their specs | `views.md`, `testing.md` |
| job-agent | Background jobs, idempotency, retry + its own specs | `performance.md`, `testing.md` |
| query-object-agent | Complex query objects in `app/queries/` + their specs | `models.md`, `testing.md` |
| mailer-agent | ActionMailer mailers + their specs | `testing.md` |
| rspec-agent | Cross-cutting integration specs only (not layer specs — each specialist owns those) | `testing.md` |
| verify-agent | Adversarially checks acceptance_criteria against the implementation. Spawned once per phase after implementation completes — full contract in "How to dispatch" below. | `testing.md` |
| completeness-critic-agent | Checks for gaps (missing tests, error paths, edge cases, auth) after verify-agent passes — full contract in "How to dispatch" below. | `testing.md` |

**Project CLAUDE.md — load alongside rule files:**
Each specialist must also read the project's nested CLAUDE.md for its layer before implementing:

| Subagent | Also read |
|---|---|
| migration-agent | `db/CLAUDE.md` |
| model-agent | `app/models/CLAUDE.md` |
| graphql-agent | `app/graphql/CLAUDE.md`, `app/graphql/AGENTS.md` |
| job-agent | `app/jobs/CLAUDE.md` |
| rspec-agent | `spec/CLAUDE.md` |

**How to dispatch:**
1. Restate the ticket in domain language (brief).
2. Identify which specialists are needed (see roles table above).
3. For each specialist, call the **Agent tool** with the subagent contract as the prompt. Feed the previous layer's output only when the task requires it (e.g., migration output feeds model context).
4. Run `bundle exec standardrb --format progress` and `SKIP_COVERAGE=1 bundle exec rspec <all changed spec files>` and paste both outputs — verify-agent's verdict is checked against this, so it must be current before dispatching verify-agent.
5. Dispatch a verify-agent with the acceptance_criteria from the ticket, the files_changed list from the implementation agents, and the output from step 4. Gate completion on `verdict === "pass"`.

   **If verify-agent returns `verdict: "fail"`:**
   1. Surface `failed_criteria` to the user
   2. Fix the implementation for each failed criterion
   3. Re-run step 4, then re-dispatch verify-agent with the same `acceptance_criteria` and updated `files_changed`
   Maximum 2 retry cycles — capped lower than the Stop hook's 3, because each cycle here means changing code, not just re-running a check. On the 3rd failure, escalate as a blocker:
   > **Blocked — verify-agent:** [list failed_criteria] / [file:line where each assertion fails, from rspec output] / [what was attempted in each retry cycle] / [needs user decision]

   **When verify-agent returns `verdict: "pass"`:** dispatch completeness-critic-agent. If it returns `verdict: "gaps_found"`, surface `gaps` to the user as advisory items before proceeding to the completion gate.

**If subagents aren't available:** implement in a single linear pass in the same dependency order. Load only the rule files for the layer you're actively writing — not all at once.

## Scope gate

Run this when a ticket touches 5 or more of the stages listed in Dispatch order (Subagent dispatch, above) and no `+Nk` token budget directive was given in the session:

1. Count the distinct layers the ticket touches.
2. Ask:
   > "This ticket spans [N] layers and will dispatch [N] agents. Proceed with full depth, or focus on [highest-risk layer]?"
3. If the user says proceed, or a `+Nk` directive is present, dispatch normally.
4. **Budget-aware default (no `+Nk` directive, user says proceed without specifying depth):** Cap at the 3 highest-risk layers. If Required parallel pairs (Subagent dispatch, above) calls for two of those layers together, both count as one pair — never split a mandatory pair to fit the cap. rspec-agent, verify-agent, and completeness-critic-agent run regardless and aren't part of this count. State which layers were sampled and which were skipped. The user can re-invoke with a `+Nk` directive to lift the cap.

## Implementation workflow
1. Restate the ticket in domain language. Confirm it matches the approved spec stub's Layer 1 — if it doesn't, stop and log an Amendment (see Spec stub → Amendment rule) before continuing. Refresh the stub's Grounding layer as facts change; no approval needed for that layer.
2. Identify the smallest set of files that should change. When multiple layers are involved, build in the same dependency order as Dispatch order (Subagent dispatch, above). Do not write a controller method that calls a model API that does not yet exist. Lay the foundation before the walls.
3. **Grep for existing patterns** — before proposing architecture, search for analogous
   models, concerns, services, or query objects already in the codebase. Mirror the
   local pattern unless it clearly conflicts with the style guide.
   Also grep for N+1 risks in the files you're changing: any `.each` over an AR collection
   that accesses an association without `includes`, `preload`, or `eager_load`. In Rails 8+,
   prefer `strict_loading` on associations that must never be lazy-loaded. Use EXPLAIN ANALYZE
   in development to verify query plans for any non-trivial scope you introduce.
4. Decide the primary public API first — keep it Rails-native and easy to call. If the feature involves real-time or partial page updates, pick the right Turbo primitive — see `references/style-guide.md` (Turbo primitives).
5. **Write a failing spec first (TDD — Red).** Describe the behavior the ticket requires. A good spec has: one assertion per example, a descriptive name, clear Arrange-Act-Assert structure, and covers the happy path plus meaningful edge cases. Then make the smallest change to pass it (Green). Then refactor.

   **TDD phases — hard gates:**

   **Red — write the failing spec first:**
   1. Write or update the spec
   2. `SKIP_COVERAGE=1 bundle exec rspec <spec_file>`
   3. **Paste the rspec output into your response** — the gate passes only when the output is visible and shows an assertion failure (not a load error)
   4. Append `<spec_file>` to `.rails-do/<ticket-key>/tdd-red-expected` (one path per line, create if missing) — tells the Stop hook this failure is intentional, not a stop-worthy problem
   5. **Gate: do not write implementation code until failure output appears in the response**

   **Green — minimum change to pass:**
   1. Write the smallest implementation that makes the spec pass
   2. `SKIP_COVERAGE=1 bundle exec rspec <spec_file>`
   3. **Paste the rspec output into your response** — the gate passes only when output shows all examples passing
   4. Remove `<spec_file>` from `.rails-do/<ticket-key>/tdd-red-expected` if present — the Stop hook resumes enforcing it
   5. **Gate: do not advance until passing output appears in the response**
   6. Stop — do not add more than what makes it green

   **Refactor — clean while green:**
   1. Improve naming, structure, or clarity
   2. `SKIP_COVERAGE=1 bundle exec rspec <spec_file>` after each change
   3. **Paste the rspec output after each change** — revert immediately if any example goes red
   4. **Gate: must stay green throughout — revert and retry if it goes red**

   **WRONG** — never do this:
   ```
   Write implementation code. Then write specs to match what was built.
   ```

   **CORRECT:**
   ```
   Write spec → SKIP_COVERAGE=1 bundle exec rspec → see failure → write minimum code →
   SKIP_COVERAGE=1 bundle exec rspec → see passing → refactor → still passing
   ```

   **Refactoring rules (do not skip these):**
   - Never refactor a failing test — Green first, then refactor.
   - Make one small change at a time.
   - Run the full spec after every change.
   - If tests go red, undo the change immediately.

   Refactor-trigger list, matching refactoring moves, and the flaky-spec gate checklist are in `references/tdd-checklist.md` — read it now; this step isn't done until the flaky-spec gate there has been checked.

6. Review the result against `references/style-checklist.md`. Before presenting work as complete, run what the repo uses:
   - **Style:** `bundle exec standardrb --format progress`
   - **Tests:** `bundle exec rspec <changed_spec_files>` — prefix with `SKIP_COVERAGE=1` if this repo uses that env var.
   - **Security:** `bundle exec brakeman --no-pager` if brakeman is present; skip otherwise.
   Report failures inline. Only block completion for checks that the repo's CI pipeline enforces — flag others as follow-up nits.

   **Completion gate — a phase is done only when both outputs are pasted into the response:**
   ```bash
   bundle exec standardrb --format progress
   SKIP_COVERAGE=1 bundle exec rspec <the_spec_file_changed>
   ```

   **WRONG** — never do this:
   ```
   "Phase complete — implementation verified."
   ```

   **CORRECT** — paste actual output:
   ```
   $ bundle exec standardrb --format progress
   .....
   $ SKIP_COVERAGE=1 bundle exec rspec spec/models/covered_life_spec.rb
   3 examples, 0 failures
   ```

7. **Git rule:** After verification passes, run `git diff --cached`, propose a commit message, and wait for explicit user YES (see Hard rules).

   **WRONG** — never do this:
   ```
   Deploy a Commit subagent that runs: git add -A && git commit -m "..."
   ```

   **CORRECT:**
   ```
   Show git diff --cached output → propose message → wait for user YES → then commit
   ```

   **Archiving:** once the commit lands, move `.rails-do/<ticket-key>/` to `.rails-do/archive/<ticket-key>/` (see Spec stub for the file convention). Keeps the working directory to only in-flight tickets.

## Default output contract
When writing code or patches:
- Lead with a short implementation summary.
- Then show the files changed, patch, or code.
- Keep explanations brief and concrete.
- If the ticket is underspecified, make the smallest reasonable assumption and state it once.
- Do not apologize for choosing Rails-native patterns.

## When to consult bundled references
- Load the relevant `references/rules/*.md` file (see the task-type table under Token efficiency, above) when making area-specific decisions.
- Read `references/style-guide.md` for a concise cross-cutting summary of architecture, naming, and design choices.
- Read `references/style-checklist.md` before finalizing code.
- Read `references/tdd-checklist.md` at the Refactor phase and before marking spec work done (flaky-spec gate).
- Read `references/request-template.md` if the user needs help supplying better ticket or context input.
- Read `references/examples.md` if a concrete implementation pattern would help.
- Read `references/source-code-writing-guide.md` if nuance from the original guide is needed.

## Negative triggers
Also not for non-Rails/non-Ruby work — unless the user explicitly asks to adapt the style guide's spirit rather than follow Rails patterns.

---

## Failure handling

### Escalation protocol

Surface to the user immediately — do not guess past a blocker — when:
- A subagent cannot complete its task
- The plan contradicts what the code actually is
- A file or method that should exist does not

(Repeated verification failure has its own format — see "How to dispatch" → verify-agent's 3rd-failure escalation, above.)

Format:
> **Blocked — Phase [N]:** [what was attempted] / [what failed] / [what is needed to proceed]

### Pre-existing failure detection

When unexpected spec failures appear after a change:

1. `git stash`
2. Rerun the same spec file
3. Compare failure counts

Failures present both before and after stash are pre-existing noise — not ours to fix. Only failures that disappear after stash belong to this task. Unstash, then investigate only those.

### Pre-flight before claiming any phase done

- [ ] Targeted rspec output shown and green
- [ ] standardrb output shown and clean
- [ ] No new flaky spec patterns (checked against `references/tdd-checklist.md`)
- [ ] If any GraphQL files changed: `bundle exec rails graphql:schema:idl && bundle exec rails graphql:schema:llm_ops` run and schema files staged
- [ ] If proposing a commit: diff shown, message proposed, user has said YES
