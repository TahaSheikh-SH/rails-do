---
title: Code Style & Consistency
impact: LOW
tags: style, ruby, consistency, readability
---

## Code Style & Consistency

Style matters not for aesthetics but for communication. When everyone writes code with
the same look, reading others' work requires no mental translation. Consistency trumps
any individual preference.

---

### Hash Syntax

Use new hash syntax (Ruby >= 1.9) everywhere. Never mix old and new in the same file.

```ruby
# Bad
{ :key => 'value', :other => 'thing' }

# Good
{ key: 'value', other: 'thing' }
```

---

### String Quotes

Single quotes when not interpolating. Double quotes only when interpolating or the string
contains a single quote.

```ruby
# Bad
"some string"
"Hello #{name}"   # fine — interpolating

# Good
'some string'
"Hello #{name}"
```

---

### Ternary for Simple Conditionals

```ruby
# Bad — 5 lines for a 1-line decision
result = nil
if condition
  result = something
else
  result = something_else
end

# Good
result = condition ? something : something_else
```

Only use ternary for simple, one-liner decisions. Multi-condition or nested ternaries
should be `if/else`.

---

### Avoid `unless` with Complex Conditions

`unless` is acceptable for simple, obviously negative conditions. Avoid it when the
condition has a positive reading or when it would be clearer as `if !`:

```ruby
# Hard to read — double negation
unless !user.active? || user.banned?

# Clear
if user.active? && !user.banned?
```

---

### `%w` and `%i` for Arrays of Strings/Symbols

```ruby
# Bad
['a', 'b', 'c']
[:a, :b, :c]

# Good
%w[a b c]
%i[a b c]
```

---

### `&&`/`||` Over `and`/`or`

`and`/`or` have different precedence than `&&`/`||` and produce subtle bugs. Avoid them.

```ruby
# Bad
result = do_something and log_it
return if record.invalid? or record.locked?

# Good
result = do_something && log_it
return if record.invalid? || record.locked?
```

---

### Method Visibility: `private` With Indent

Group private methods under a single `private` keyword. Prefer the indented style
(methods below `private` are indented to the same level as the public methods above).

```ruby
class Project < ApplicationRecord
  def public_api_method
    private_helper
  end

  private
    def private_helper
      # ...
    end
end
```

---

### Small Steps, Continuously

Don't attempt to fix all style issues in a PR that's doing something else. Note them
as nits and address in a follow-up. Style-only commits are fine and encouraged as
separate PRs.
