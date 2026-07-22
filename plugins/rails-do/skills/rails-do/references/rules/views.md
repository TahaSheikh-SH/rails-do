---
title: Views, Helpers & Hotwire
impact: MEDIUM
tags: views, partials, helpers, turbo, stimulus, hotwire
---

## Views, Helpers & Hotwire

### Partials vs. Model Methods vs. Helpers

If a partial has virtually no HTML and is mostly Ruby logic, it is in the wrong place:

| Content | Put it in |
|---|---|
| Markup + data | Partial |
| Pure Ruby logic, no markup | Helper or model method |
| Logic that reads model state | Model method (likely feature envy) |

```ruby
# Bad — a partial that's really a method
# _assignee_names.html.erb
<% event.assignees.map(&:name).join(", ") %>

# Good — model method
class Event
  def assignee_names
    assignees.pluck(:name).join(", ")
  end
end
```

---

### Helpers Take Explicit Parameters

Helpers must not reach into ivars. Pass what the helper needs explicitly.

```ruby
# Bad — magical ivar reference
def project_status_label
  @project.status.humanize
end

# Good
def project_status_label(project)
  project.status.humanize
end
```

---

### Tag Helpers Over Interpolated Strings

Use `tag.*` helpers when doing interpolation in HTML attributes.

```erb
<%# Bad — raw string interpolation %>
<meta name="current-user-id" content="<%= Current.user.id %>">

<%# Good %>
<%= tag.meta name: "current-user-id", content: Current.user.id if Current.user %>
```

---

### Double-Indent Tag Helper Attributes

When tag helpers have multiline attributes, double-indent the attributes relative to
the method to distinguish them from the block body.

```erb
<%# Bad %>
<%= tag.div class: "card",
  data: { controller: "card" } do %>

<%# Good %>
<%= tag.div class: "card",
    data: { controller: "card" } do %>
```

---

### Turbo Stream Canonical Style

Use the canonical bracket syntax for Turbo Stream targets that reference a record + identifier.

```erb
<%# Bad %>
<%= turbo_stream.update "card_#{@card.id}_new_comment", partial: "cards/comments/new" %>

<%# Good %>
<%= turbo_stream.update [@card, :new_comment], partial: "cards/comments/new", locals: { card: @card } %>
```

Turbo Stream styles should be consistent within a controller — pick one and use it everywhere.

---

### Stimulus: Targets Over CSS Selectors

In Stimulus controllers, use `data-*-target` attributes to reference elements rather than
`querySelector` with CSS class selectors. Targets are part of the controller's explicit
interface; CSS selectors are implementation details that break silently.

```javascript
// Bad
const input = this.element.querySelector('.js-input')

// Good
// In HTML: data-form-target="input"
this.inputTarget
```

---

### WebSocket / Turbo: Consider Live Updates

When a controller action renders a list or counter, ask: will this also update correctly
when new records arrive via WebSocket / Turbo Stream? If a Stimulus controller queries
the DOM on `connect` but doesn't listen for new elements, it will miss live additions.
Flag this as a potential correctness issue.

---

### Inline Jbuilder Partials

Prefer the inline partial syntax in Jbuilder over verbose `json.array!` blocks.

```ruby
# Bad
json.steps do
  json.array! @card.steps do |step|
    json.partial! "steps/step", step: step
  end
end

# Good
json.steps @card.steps, partial: "steps/step", as: :step
```
