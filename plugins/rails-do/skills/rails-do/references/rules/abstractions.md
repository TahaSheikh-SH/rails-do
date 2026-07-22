---
title: Abstraction Discipline
impact: HIGH
tags: abstractions, indirection, metaprogramming, inline
---

## Abstraction Discipline

### Abstractions Must Earn Their Keep

The most common code review failure mode is premature or unjustified abstraction.
Before accepting any new class, module, or layer of indirection, apply the earning test.

**The Earning Test:** Can you point to 3+ real, existing variations that genuinely need this abstraction?
If not, inline it.

```ruby
# Over-abstracted — only one variation, adds nothing
class Projects::NotificationSender
  def initialize(project); @project = project; end
  def send!; ProjectMailer.notify(@project).deliver_later; end
end

# Inline it
ProjectMailer.notify(@project).deliver_later
```

---

### Anemic Wrappers Should Be Inlined

A method or class that simply delegates to another with no added logic, naming value,
or encapsulation should be deleted.

```ruby
# Bad — carries no weight
def send_notifications
  notifier.send!
end

# Bad — an "anemic" class
class Notifier
  def send!
    ProjectMailer.notify(@project).deliver_later
  end
end

# Just write the call directly
```

**DHH's test:** "Don't think this method is carrying its weight. Either it needs to explain something or you should just inline."

---

### Explicit Over Clever

When there are 2–3 cases, write them explicitly. Don't reach for metaprogramming.

```ruby
# Bad — method_missing for 2 cases
def method_missing(name, *args)
  if name.to_s.end_with?("_content")
    # ...
  end
end

# Good — explicit and obvious
case event.action
when "completed" then handle_completion
when "published"  then handle_publication
end
```

---

### No Base Class Extensions for Local Convenience

Adding methods to `ApplicationRecord`, `ApplicationController`, or Ruby core classes
should only happen when the method is heading upstream (to Rails, Ruby, or a gem).
Never add a base class extension just because it's convenient locally.

```ruby
# Bad — adding a method to String for one use case
class String
  def to_inquiry_object
    inquiry
  end
end

# Good — put it on the model that needs it
class Event < ApplicationRecord
  def action
    self[:action].inquiry
  end
end
```

---

### Class Hierarchies Require Justification

A base class shared by two subclasses is only justified if those subclasses genuinely
share behavior that can't live in a concern or module. Two subclasses with an `if` in
the base class is a sign the hierarchy is premature.

---

### `method_missing` Is a Last Resort

Use `method_missing` only when the set of methods is open-ended and genuinely unknown
at class definition time. For a closed set of 2–10 known methods, define them explicitly.
