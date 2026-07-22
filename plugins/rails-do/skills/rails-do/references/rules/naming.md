---
title: Naming
impact: MEDIUM
tags: naming, domain-language, readability
---

## Naming

### Domain-Driven Boldness

The highest-leverage move in code is bold, domain-expressive naming. Don't reach for
generic technical terms when the domain has a richer vocabulary.

```ruby
# Weak — generic, technical, forgettable
def remove_person_placeholder
  replace_with_placeholder
  remove_admin_roles
end

# Bold — domain-expressive, memorable, intentional
def decease
  erect_tombstone
  remove_administratorships
  remove_accesses_later
end
```

**Heuristic:** Write a plain-text description of the domain concept first. Look for words
that carry natural formality or weight — *petition* is different from *request* because it
implies ceremony. *Revoke* is different from *remove* because it implies authority. Use those distinctions.

---

### Naming Heuristics Checklist

- Does the name reflect a real domain concept, or a technical implementation detail?
- Is there a more specific, expressive word in the domain's vocabulary?
- Does the method name reflect its return value? (`collect` implies returning an array; use `create_mentions` when you don't care about the return value)
- Are you using `not_*` when a positive name exists? (`active` not `not_deleted`)
- Is the domain language consistent? (`source` everywhere, not `source` in one place and `container` in another)
- If a domain term was renamed, is it renamed *everywhere*? (e.g., dropping `thread` in favor of `message` everywhere)

---

### Consistent Domain Language

Once a term is established in the codebase, use it everywhere. Mixing synonyms forces
readers to ask "are these the same thing?" — which is always a waste of time.

```ruby
# Bad — two names for the same concept
class Notification
  belongs_to :container  # "container" appears nowhere else; domain uses "source"
end

# Good
class Notification
  belongs_to :source
end
```

---

### Positive Scope Names

```ruby
# Bad — double-negative mental overhead
scope :not_deleted, -> { where(deleted_at: nil) }
scope :not_archived, -> { where(archived_at: nil) }

# Good
scope :active,   -> { where(deleted_at: nil) }
scope :visible,  -> { where(archived_at: nil) }
```

---

### Method Names That Match Return Type

If a method name implies collection semantics (e.g., `collect`, `gather`, `find_all`),
it should return a collection. If the method is a command with a side effect, use a
verb that doesn't imply a return value.

```ruby
# Misleading — "collect" implies returning something, but this creates records
def collect_mentions(text)
  create_mentions_from(text)   # side effect, no return needed
end

# Good
def create_mentions(text)
  # ...
end
```
