---
title: Models & Domain Logic
impact: HIGH
tags: models, activerecord, domain-logic, fractal-quality
---

## Models & Domain Logic

### Rich Public APIs

Models must expose high-level, domain-expressive public methods. The controller should call
one method and be done with it — it should not orchestrate multi-step model operations.

**Bad — controller doing domain work:**
```ruby
def destroy
  @membership.update!(role: nil)
  @membership.user.notifications.delete_all
  AuditLog.record(:membership_removed, @membership)
end
```

**Good — model encapsulates the operation:**
```ruby
def destroy
  @membership.revoke!
end

# In Membership:
def revoke!
  update!(role: nil)
  user.notifications.delete_all
  AuditLog.record(:membership_removed, self)
end
```

---

### Fractal Code Quality

Good Rails code maintains four qualities at every level — class, method, line:

1. **Domain-driven** — names map to real domain concepts, not technical jargon
2. **Encapsulation** — caller understands what, not how
3. **Cohesion** — a method does one thing from the caller's perspective
4. **Symmetry** — all calls in a method operate at the same level of abstraction

```ruby
# Good — relay_now is symmetric and cohesive
def relay_now
  relay_to_or_revoke_from_timeline   # same altitude
  relay_to_webhooks_later            # same altitude
  relay_to_customer_tracking_later   # same altitude

  if recording
    relay_to_readers                 # same altitude
    relay_to_recipients              # same altitude
  end
end
```

If a method mixes high-level calls with low-level SQL or attribute assignments, it violates symmetry. Extract or elevate until everything is at the same altitude.

---

### Scopes Use Positive Names

```ruby
# Bad
scope :not_deleted, -> { where(deleted_at: nil) }
scope :not_popped,  -> { where(popped_at: nil) }

# Good
scope :visible, -> { where(deleted_at: nil) }
scope :active,  -> { where(popped_at: nil) }
```

---

### StringInquirer for Predicate Values

Avoid string comparisons for state/action fields:

```ruby
# Bad
event.action == "completed"

# Good — use .inquiry on the attribute
def action
  self[:action].inquiry
end

event.action.completed?
event.action.published?
```

---

### Delegated Types Over STI for Mixed Collections

When you have a timeline mixing different record types, prefer delegated types over
in-memory polymorphism or STI:

```ruby
class Message < ApplicationRecord
  delegated_type :messageable, types: %w[Comment EventSummary Attachment]
end

# Now you get a single paginatable, DB-sorted collection:
bubble.messages.order(:created_at).limit(20)
```

---

### `pluck` Over `map` for DB Values

```ruby
# Bad — loads full objects
event.assignees.map(&:name)

# Good — DB round-trip only for the column you need
event.assignees.pluck(:name)
```

---

### `update_all` for Bulk Operations Without Side Effects

```ruby
# Bad — instantiates every record, runs callbacks
cards.each { |c| c.touch }

# Good
cards.update_all(updated_at: Time.current)
```

Only use the callback-triggering version when you explicitly need the callbacks to fire.
