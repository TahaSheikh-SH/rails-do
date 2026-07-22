# The Definitive Code Writing Guide

Principles drawn from 37signals' engineering blog, DHH's code reviews, and the Arkency style canon

## 1. Philosophy: pragmatism over purity

The greatest trap in software is the maximalist position — take a technique, outline its drawbacks, extrapolate you can't use it under any circumstance, and ban it forever. Good software development is a game of tradeoffs. Any choice you make comes with them.

The advice "never-ever do this, always do that" should put you on alert. When balancing convenience and purity, there is a rigidity threshold that causes more harm than good.

Always ask: compared to what? When critiquing a pattern or technique, evaluate it against the realistic alternative — not against an imaginary perfect solution. Callbacks with globals may look messy until you see the service-object factory you'd need instead.

## 2. Naming: domain-driven boldness

One of the highest-leverage moves in code is bold, domain-expressive naming. Don't be aseptic. A codebase that reads like plain English in the domain's own vocabulary is a pleasure to maintain.

```ruby
def remove_person_placeholder
  replace_with_placeholder
  remove_admin_roles
end
```

```ruby
def decease
  erect_tombstone
  remove_administratorships
  remove_accesses_later
end
```

Deceasing a person and erecting a tombstone communicates intent, domain reality, and has personality. It's more eloquent, concise, and memorable than the neutral alternative.

Use a dictionary when modeling. Write a plain-text description of the domain first. Look for words that carry natural formality or weight — petition is different from request because it implies ceremony. Code should reflect those distinctions.

### Roles as concerns

When a model plays a role in a domain interaction, name the concern after that role:

```ruby
class Contact < ApplicationRecord
  include Petitioner   # contacts petition for clearance
end

class User < ApplicationRecord
  include Examiner     # users examine those petitions
end
```

## 3. Architecture: vanilla Rails is plenty

The common critique — that vanilla Rails can only get you so far, that you eventually need services, interactors, or use-case objects — does not hold up in practice. 37signals runs Basecamp and HEY, serving millions of users, with 400+ controllers and 500+ models, all in vanilla Rails.

We don't default to creating services, commands, interactors, or form objects to implement controller actions. We don't separate application-layer and domain-layer artifacts into distinct folders or require ceremony classes to mediate between controllers and models.

Controllers access domain models directly. Models expose clean, high-level public APIs. Complex operations are delegated to cohesive sub-objects, not promoted to a separate architectural layer.

The DDD warning is worth heeding: "Don't lean too heavily toward modeling a domain concept as a Service. Using Services overzealously will usually result in an Anemic Domain Model." The original DDD book also acknowledges most real layered architectures are relaxed , with the presentation layer often accessing the domain layer directly.

## 4. Rich models, thin controllers

Build rich domain models — models that do things, not just hold data. The controller's job is to translate HTTP into domain operations, not to orchestrate business logic.

```ruby
class ContactsController
  def create
    contact = Contact.new(params)
    designation = Designation.create!(
      contact: contact, box: box
    )
    contact.save!
  end
end
```

```ruby
class Boxes::DesignationsController
  def create
    @contact.designate_to(@box)
    respond_to { ... }
  end
end
```

Prefer the first form in all three of these equivalent calls:

```ruby
recording.incinerate                          # best: hides complexity, reads like English
Recording::Incineration.new(recording).run    # ok: explicit, but shifts burden to caller
Recording::IncinerationService.execute(recording) # avoid: procedural, no domain voice
```

The first form does a better job of hiding complexity and doesn't shift the burden of composition to the caller. It feels more natural, like plain English. It feels more Ruby.

### The SRP at two levels

Distinguish between SRP violations at the interface level versus the implementation level. A Recording model that exposes #incinerate , #copy_to , and #archive is not fat — it's a facade. The actual work lives in Recording::Incineration , Recording::Copier , etc. The model is a well-organized front door, not a monolith.

## 5. Concerns done right

Rails concerns get a bad reputation because they can be misused as arbitrary code-splitting containers. Used correctly, they are one of the most powerful organization tools available.

### Where to put them

Model-specific concerns go in app/models/<model_name>/ . Shared concerns go in app/models/concerns/ . This removes the need to repeat the namespace on include.

```ruby
# app/models/recording.rb
class Recording < ApplicationRecord
  include Completable
  include Incineratable
  include Copyable
end

# app/models/recording/incineratable.rb
module Recording::Incineratable
  def incinerate
    Incineration.new(self).run
  end
end
```

### The litmus test for a good concern

A concern must represent a genuine has trait or acts as relationship. It should only contain things that belong together. Don't treat concerns as arbitrary containers to split large files. A User::Examiner concern only contains examiner behavior. A Recording::Copyable concern only contains copying behavior.

### Concerns + OOP = the sweet combo

Concerns don't replace good object-oriented design — they enhance it. A concern offers a clean domain-language API on the model while hiding a complex internal subsystem:

```ruby
account.terminate         # public interface via Account::Closable concern

# Inside Account::Closable, it delegates to:
Account::Closing::Purging.new(self).run
# or
Account::Closing::Incineration.new(self).run
# which share code via class inheritance
```

## 6. Active Record: embrace the blend

Active Record combines domain logic and persistence in the same class. Critics argue you should separate them. We disagree — because in a database-powered application, domain logic is indissolubly linked to persistence.

If your ORM blends perfectly with the host language, comes with good answers for persisting object models, and offers good encapsulation mechanisms — the question stops being "how do I isolate persistence from domain logic?" and becomes "why would I?"

Use associations extensively — they are a fundamental construct, just like inheritance:

```ruby
module Topic::Entries
  extend ActiveSupport::Concern
  included do
    has_many :entries, dependent: :destroy
    has_many :receipts, through: :entries
    has_many :addressed_contacts, -> { distinct }, through: :entries
    has_many :blocked_trackers, through: :entries, class_name: "Entry::BlockedTracker"
  end
end
```

Use scopes to express complex queries naturally. Use delegated types, single table inheritance, and serialized attributes when they fit your object model. Let Active Record do its heavy lifting.

### Encapsulate queries in dedicated objects when complexity justifies it

```ruby
class Timeline::Aggregator
  def events
    Event.where(id: event_ids).preload(:recording).reverse_chronologically
  end
  private
    def event_ids
      event_ids_via_optimized_query(1.week.ago) ||
        event_ids_via_regular_query
    end
end
```

## 7. Callbacks and CurrentAttributes

Both are sharp knives. They have real drawbacks when misused. They also have scenarios where they are the best tool available — and pretending otherwise produces worse code.

### Callbacks: for orthogonal concerns

Use callbacks to plug in secondary, orthogonal concerns into an object's lifecycle — things that don't belong in the primary responsibility of the model:

```ruby
module Bucketable
  included do
    after_create { create_bucket! account: account unless bucket.present? }
  end
end
```

This is good: creating a companion bucket is secondary to a project's own responsibilities. The callback expresses this declaratively without polluting project creation logic. For complex primary operations, use a factory instead — but name the threshold by complexity and cohesion, not by blanket rule.

### CurrentAttributes: for request-scoped context

```ruby
class Project < ApplicationRecord
  belongs_to :creator, class_name: "Person", default: -> { Current.person }
end
```

This captures that a creator is mandatory and defaults to the authenticated person — without the controller needing to know about it. The creator is an audit trait, not a structural part of project creation. Discharging the controller from knowing about it is correct.

### Callbacks + CurrentAttributes: powerful together

When tracking audit events, the combination means you can write:

```ruby
@project = Current.account.projects.create! create_project_params
```

...and the system automatically records who created it, from which IP, via which request — without any of that plumbing appearing in the controller. The alternative — a ProjectRecorder service that carries Current.person and request through the layers — mixes orthogonal concerns and is harder to understand, not easier.

### Suppress: for controlled exceptions

Use Event.suppress { ... } when you want default behavior to not fire in a specific exceptional context (like copying). The key word is exceptional — you normally want the default.

## 8. Abstraction discipline

The most common code review failure mode is premature or unjustified abstraction. An abstraction should earn its keep.

Ask: "Is this abstraction earning its keep?" If you can't point to 3+ real variations that need it, inline it. Methods and classes that don't explain anything or provide meaningful encapsulation should be removed.

A method that simply delegates to another with no added meaning; a class hierarchy with only two cases that could be an explicit if ; metaprogramming where a case statement would be clearer.

A Recording::Copier encapsulating a complex multi-step copy operation; a Timeline::Aggregator hiding optimized query logic; a Filing base class shared genuinely by Copy and Move .

### Explicit over clever

When there are only 2–3 cases, explicit case statements or defined methods beat metaprogramming. method_missing should be a last resort, not a shortcut. Base class extensions should only be added when they're on their way to an upstream patch — never just for local convenience.

### Inline when indirection doesn't add value

Notifiers and handlers that are anemic — just a wrapper with no logic of their own — should be inlined. The question is always: does this class explain something or enable something that couldn't be done more simply?

## 9. Fractal code quality

Good code is a fractal: you observe the same qualities repeated at every level of abstraction, from the top-level controller action down to the smallest private method.

The four qualities to maintain at every level:

Speak the language of the problem domain. Names at every layer — methods, modules, classes, variables — should map to real concepts in the domain.

Expose crystal-clear interfaces and hide details. At every level of the call stack, the reader should be able to understand what a unit does without needing to understand how.

Each unit does one thing from the point of view of its caller. A method orchestrating relay destinations is cohesive — all the items it calls are about relaying. Mixing relaying with auditing in the same method breaks cohesion.

Operate at the same level of abstraction. Within a method, if three of five calls are high-level (e.g. relay_to_webhooks_later ) and two are low-level SQL, the method is asymmetric and confusing. Extract or elevate until everything is at the same altitude.

```ruby
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

Notice: you don't need to read any implementation details to understand what this method does. That's the standard.

## 10. Code style and consistency

Code style matters not because of aesthetics, but because of communication. When everyone writes code with the same look, reading others' work requires no mental translation.

### The single most important property

We don't usually have time to parse others' code. We need to use it. If we share a style, we can take a look and understand. Prefer if condition over unless condition when the positive case is what matters — the double-negation forces mental parsing.

### Consistency trumps preference

The particular choice often matters less than making the same choice everywhere. Pick new or old hash syntax — pick one. Use single or double quotes — pick one rule and apply it. Inconsistency is the real cost, not any individual style decision.

### Ruby-specific consistency rules

```ruby
# use new hash syntax (Ruby >= 1.9)
key: 'value'              # not :key => 'value'

# single quotes when not interpolating
'some string'             # not "some string"

# ternary for simple inline conditionals
result = condition ? a : b

# % literals for arrays of strings/symbols
%w(a b c)                 # not ['a', 'b', 'c']
%i(a b c)                 # not [:a, :b, :c]

# avoid `and`/`or` — use `&&`/`||`
```

### Small steps, continuously

Don't try to fix a codebase's style all at once. Start with one language you write most. Make small changes continuously. Use linters and formatters configured to your team's agreed style. The goal is a codebase where any file looks like any other — no author fingerprints, no mood-of-the-day syntax.
