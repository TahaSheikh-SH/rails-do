# House rules

Full text of the twelve house rules referenced from `SKILL.md`. Load this when
writing code, not when planning.

1. [Favor domain language](#1-favor-domain-language)
2. [Prefer rich models and thin controllers](#2-prefer-rich-models-and-thin-controllers)
3. [Prefer model facades over service-first APIs](#3-prefer-model-facades-over-service-first-apis)
4. [Use concerns only for real traits or roles](#4-use-concerns-only-for-real-traits-or-roles)
5. [Lean into Active Record](#5-lean-into-active-record)
6. [Callbacks and Current are allowed when appropriate](#6-callbacks-and-current-are-allowed-when-appropriate)
7. [Migrations must be safe and reversible](#7-migrations-must-be-safe-and-reversible)
8. [Authorization: deny-by-default when Pundit is in use](#8-authorization-deny-by-default-when-pundit-is-in-use)
9. [Background jobs must be idempotent](#9-background-jobs-must-be-idempotent)
10. [Abstractions must earn their keep](#10-abstractions-must-earn-their-keep)
11. [Fractal code quality](#11-fractal-code-quality)
12. [Ruby consistency](#12-ruby-consistency)

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
