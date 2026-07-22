# House Style Reference

This reference distills the uploaded code writing guide into concrete implementation choices for Ruby and Rails work.

## 1. Pragmatism over purity
- Avoid absolute rules like "never use callbacks" or "always use services".
- Judge a choice against the realistic alternative, not an imaginary perfect design.
- Prefer the simplest approach that fits the codebase and the ticket.

## 2. Domain-driven naming
- Use the language of the business domain, not generic technical names.
- Prefer names with intent and weight when the domain supports them.
- Use the same vocabulary across controllers, models, concerns, jobs, tests, and comments.
- When a model plays a domain role, a concern named after that role can be appropriate.

### Good signals
- The main public methods read like plain English in the domain.
- The code sounds like the product, not like infrastructure.

### Bad signals
- Generic verbs like `process`, `handle`, `execute`, `perform_task`, or `remove_placeholder` where the domain already has stronger language.
- Classes named `SomethingService` when a clearer domain object or model method exists.

## 3. Vanilla Rails is plenty
- Do not default to service objects, interactors, commands, or form objects.
- Controllers may talk to models directly.
- Let models expose clean, high-level public APIs.
- Push real complexity into cohesive internal collaborators, not a mandatory service layer.

### Decision gate — run before proposing a service (House rule #3)
- [ ] Can one model own this with a concern + PORO subsystem? → If yes, stop here. No service needed.
- [ ] Is the complexity private to one model method? → If yes, extract a named private PORO inside the model namespace. No service needed.
- [ ] Only if both boxes above are unchecked: a service is justified.

### Prefer
```ruby
class Boxes::DesignationsController
  def create
    @contact.designate_to(@box)
  end
end
```

### Avoid
```ruby
class Boxes::DesignationsController
  def create
    DesignationService.execute(contact: @contact, box: @box)
  end
end
```

## 4. Rich models, thin controllers
- Models should do things, not just store state.
- The controller's job is to translate the request into a domain operation.
- A model can be a facade over several private collaborators without becoming "fat" in the harmful sense.

### Prefer public APIs like
- `recording.incinerate`
- `contact.designate_to(box)`
- `account.terminate`

### Internal helpers are fine when warranted
- `Recording::Incineration`
- `Timeline::Aggregator`
- `Account::Closing::Purging`

The caller should usually see the first form, not the helper class.

## 5. Concerns done right
- A concern must represent a real trait or role.
- Use concerns to publish a clean domain-language surface on the model.
- Model-specific concerns belong under `app/models/model_name/`.
- Shared concerns belong under `app/models/concerns/`.
- Do not create a concern just to shorten a file.

### Good concern examples
- `Recording::Incineratable`
- `User::Examiner`
- `Account::Closable`

### Bad concern examples
- `User::Helpers`
- `Contact::Stuff`
- `Thing::Methods`

## 6. Active Record is not a compromise
- In database-backed applications, persistence and domain logic often belong together.
- Use associations and scopes heavily when they express the model naturally.
- Use delegated types, STI, or serialized attributes when they improve the object model.
- Extract a query object only when query complexity is substantial enough to justify it.

## 7. Callbacks and CurrentAttributes are tools, not smells
- Callbacks are acceptable for orthogonal lifecycle behavior.
- `Current` is acceptable for request-scoped audit or creator defaults.
- Avoid either one when they hide the main business workflow.
- Use suppression patterns only for exceptional contexts.

### Appropriate callback example
- create a companion record after create
- enqueue an orthogonal side effect
- record audit metadata

### Inappropriate callback example
- perform the entire core business workflow in chained callbacks
- hide cross-model orchestration that the reader needs to understand directly

## 8. Abstractions must earn their keep
Ask before introducing a class or method:
- Does it explain something important?
- Does it hide meaningful complexity?
- Is there real variation that justifies abstraction?
- Would an explicit `if` or small method be clearer?

### Prefer explicitness when there are only a few cases
- a `case` statement over metaprogramming
- a normal method over `method_missing`
- a direct call over a wrapper that only delegates

## 9. Fractal code quality
At every level of the code, preserve:
- **Domain language**: names match the problem space
- **Encapsulation**: callers can understand what a unit does without reading how
- **Cohesion**: each unit does one caller-facing thing
- **Symmetry**: stay at the same level of abstraction inside a method

## 10. Ruby consistency
- Use new hash syntax.
- Use single quotes when not interpolating.
- Prefer positive `if` forms over mentally awkward negative conditionals when the positive path is what matters.
- Use ternaries for simple inline choices.
- Use `%w` and `%i` when it improves consistency.
- Use `&&` and `||`, not `and` and `or`.

## 11. Turbo primitives
- Turbo Drive: full-page navigation (default; no code needed).
- Turbo Frames: partial updates where the user initiates an action and sees a scoped response (e.g., inline edit forms).
- Turbo Streams: server-pushed or broadcast real-time updates via ActionCable.
- Do not use Turbo Frames for form submission responses — use Streams or a redirect.
- Do not mix Frame and Stream responses for the same action.

## Decision rubric for implementation
When multiple implementations are possible, prefer the one that:
1. Uses domain language most naturally.
2. Keeps the controller thin.
3. Preserves a clean public model API.
4. Avoids ceremony that the codebase does not need.
5. Uses Rails-native features where they fit.
6. Makes the next change easier without adding speculative abstractions.
