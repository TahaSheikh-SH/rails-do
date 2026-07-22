---
title: Performance & Scalability
impact: HIGH
tags: performance, n+1, caching, indexes, queries, background-jobs
---

## Performance & Scalability

### N+1 Queries

The most common Rails performance issue. Look for any `.each` or iteration over an
ActiveRecord collection that accesses an association.

```ruby
# Bad — N+1: one query per project to load tasks
projects.each do |project|
  puts project.tasks.count  # SELECT COUNT(*) for each project
end

# Good
projects.includes(:tasks).each do |project|
  puts project.tasks.size   # uses loaded association, no extra query
end

# Even better for counts: counter cache
project.tasks_count
```

**Where to look:**
- View partials that render associated records
- `.each` on collections followed by association access
- Serializers or API responses that traverse associations
- `count` calls on associations inside loops

---

### Missing Indexes

Every migration should be reviewed for index gaps:

```ruby
# Common misses:
add_column :events, :project_id, :bigint       # needs index
add_column :events, :status, :string           # needs index if queried
add_column :events, :token, :string            # needs unique index if used for lookup

# Correct
add_reference :events, :project, foreign_key: true, index: true
add_index :events, :token, unique: true
add_index :events, :status
```

Polymorphic associations need a composite index:
```ruby
add_index :notifications, [:notifiable_type, :notifiable_id]
```

---

### Touch Chains for Cache Invalidation

If a child record is updated but its parent's cache key doesn't change, stale content
will be served. Use `touch: true` to propagate cache invalidation up the association chain.

```ruby
# Bad — updating a comment won't invalidate the project cache
class Comment < ApplicationRecord
  belongs_to :project
end

# Good
class Comment < ApplicationRecord
  belongs_to :project, touch: true
end
```

Avoid complex cache key dependencies that span multiple models. Prefer simple touch chains.

---

### Avoid Complex Base-Page Cache Dependencies

A cached page or fragment should only depend on its own record's cache key. Adding
dependencies on unrelated models creates fragile, hard-to-reason-about cache invalidation.

```ruby
# Bad — page cache depends on unrelated association
cache [@page, @page.cards.maximum(:updated_at)] do

# Better — use touch: true so cards touching the page is sufficient
cache @page do
```

---

### Compute Summaries at Write Time

Sort keys, aggregated counts, and summary fields should be computed and stored when
data is written — not derived on every read.

```ruby
# Bad — sorting in memory at read time; can't paginate
def sorted_entries
  (comments + events).sort_by(&:created_at)
end

# Good — sort_key stored at write time; DB-sorted and paginatable
scope :chronological, -> { order(:sort_key) }
```

---

### Background Jobs for Non-Critical Work

Anything that doesn't need to complete before the response is returned should be enqueued:
- Email delivery
- External API calls (webhooks, analytics)
- Heavy computation
- Fan-out notifications

```ruby
# Bad — blocks the request
ProjectMailer.welcome(@project).deliver_now

# Good
ProjectMailer.welcome(@project).deliver_later
```

---

### `update_all` / `insert_all` for Bulk Operations

When updating many records without needing callbacks:

```ruby
# Bad — N queries + N object instantiations
cards.each { |c| c.update!(cached_at: Time.current) }

# Good — 1 query
cards.update_all(cached_at: Time.current)

# For inserts without callbacks:
Record.insert_all(rows)
```
