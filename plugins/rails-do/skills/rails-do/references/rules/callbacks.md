---
title: Callbacks & CurrentAttributes
impact: MEDIUM
tags: callbacks, current-attributes, lifecycle, audit
---

## Callbacks & CurrentAttributes

Both are sharp knives. They have real drawbacks when misused. They also have scenarios
where they are the best tool — pretending otherwise produces worse code.

---

### Callbacks: For Orthogonal Concerns Only

Use callbacks to plug in secondary, *orthogonal* concerns into an object's lifecycle —
things that don't belong in the primary responsibility of the model.

**Good — secondary concern, clearly orthogonal:**
```ruby
module Bucketable
  included do
    after_create { create_bucket!(account: account) unless bucket.present? }
  end
end
```

Creating a companion bucket is secondary to a project's own creation logic. The callback
expresses this declaratively without polluting the primary flow.

**Bad — primary business logic in a callback:**
```ruby
after_create :send_welcome_email, :provision_workspace, :assign_default_role
```

If these are core to the creation operation, they should be in a named method called
explicitly, not hidden in callbacks.

**Rule:** If removing the callback would change the fundamental behavior of the model's
primary operation, it's not orthogonal — move it out of the callback.

---

### CurrentAttributes: For Request-Scoped Context

`Current` is appropriate for propagating request-scoped context (who is acting, from
where) into models without threading it through every method signature.

```ruby
# Good — creator is an audit trait, not structural to project creation
class Project < ApplicationRecord
  belongs_to :creator, class_name: "Person", default: -> { Current.person }
end

# Controller stays clean:
@project = Current.account.projects.create!(create_project_params)
# creator, IP, request context — all captured automatically
```

**Bad smell:** Reading `Current.*` deep inside a domain method that could receive the
value as an argument — this makes the method harder to test and creates hidden coupling.

---

### Callbacks + Current: Powerful Together for Auditing

The combination lets you write audit trails, event logs, and secondary effects without
any of that plumbing appearing in the controller. The alternative — a service that
carries `Current.person` and `request` through the layers — mixes orthogonal concerns
and is harder to understand, not easier.

---

### `Event.suppress` for Exceptional Contexts

Use `suppress` when you explicitly want default lifecycle behavior *not* to fire in a
specific, exceptional context (like copying or importing). The word "exceptional" is key —
the default should still fire in normal operation.

```ruby
Event.suppress do
  recording.copy_to(destination)
end
```

Don't use `suppress` to paper over callback complexity. If you're suppressing regularly,
the callbacks are probably in the wrong place.

---

### `after_save_commit` Shorthand

```ruby
# Verbose
after_commit :broadcast_update, on: %i[create update]

# Concise
after_save_commit :broadcast_update
```
