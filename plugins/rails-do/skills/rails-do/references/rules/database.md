---
title: Database & Schema
impact: HIGH
tags: database, migrations, indexes, activerecord, performance
---

## Database & Schema

### Migration Safety

Every migration must be reversible and safe to deploy without downtime:

- Use `def change` with reversible helpers, or implement `def down` — never a bare `def up`.
- **Never mix DDL and data in the same migration.** DDL runs inside a transaction; mixing in data manipulation makes the migration harder to reason about and slows deploys.
- **Large or slow backfills belong in a maintenance task** (not a migration). Small, safe data fixes — e.g., populating a newly-added NOT NULL column with a one-line default — are acceptable only if they complete in milliseconds on any production DB size. When in doubt, use a maintenance task.
- Use `disable_ddl_transaction!` with `algorithm: :concurrently` for indexes on large tables.
- Declare `on_delete:` on every foreign key — never leave cascade behavior implicit.
- Migration order must respect the model dependency graph: migrate referenced tables before referencing tables.

```ruby
# Bad — irreversible, mixes DDL and data
def up
  add_column :projects, :status, :string
  Project.update_all(status: 'active')
end

# Good — reversible schema change only
def change
  add_column :projects, :status, :string, null: false, default: 'active'
end
```

---

### DB Constraints Over AR Validations

AR validations are for producing user-facing error messages in forms. For integrity rules
(uniqueness, not-null, non-negative counts), use DB constraints and let the database raise.

```ruby
# Largely unnecessary — DB will enforce this anyway
validates :code, uniqueness: true
validates :usages, numericality: { greater_than_or_equal_to: 0 }

# Preferred: let it live in the migration
add_index :join_codes, :code, unique: true
add_check_constraint :join_codes, "usages >= 0"
```

**When AR validations ARE appropriate:** When you need a specific, user-friendly error
message surfaced in a form (e.g. "Email has already been taken").

---

### Indexes: Always Check These

Flag any migration that adds a column without checking whether it needs an index:

- Foreign keys (`*_id` columns) — always index
- Columns used in `where` clauses
- Columns used in `order` clauses on large tables
- Uniqueness constraints — both the DB constraint and the index
- Polymorphic columns — index both `{name}_type` and `{name}_id` together

```ruby
# Bad — foreign key with no index
add_column :comments, :project_id, :bigint

# Good
add_reference :comments, :project, foreign_key: true, index: true
```

---

### Counter Caches

If the PR calls `.count` on an association in a rendered collection, it's an N+1 waiting to happen. Use AR counter caches.

```ruby
# Bad — one COUNT query per row rendered
projects.each { |p| p.tasks.count }

# Good
belongs_to :project, counter_cache: true
# Then: project.tasks_count — no extra query
```

---

### Use `created_at` as Initial Timestamp Where Possible

If a new column tracks "first time X happened" and that time is creation, prefer setting
`last_active_at = created_at` on creation rather than introducing a separate default.

---

### Bulk Operations for Cache-Busting

When touching records just to invalidate caches (no callbacks needed):

```ruby
# Bad — instantiates objects, fires callbacks
cards.each(&:touch)

# Good
cards.update_all(updated_at: Time.current)
```
