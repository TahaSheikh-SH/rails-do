---
title: Architecture & Layers
impact: HIGH
tags: architecture, service-objects, concerns, vanilla-rails
---

## Architecture & Layers

### Vanilla Rails Is Plenty

37signals runs Basecamp and HEY — 400+ controllers, 500+ models — without a service layer.
Don't default to services, commands, interactors, or form objects to implement controller actions.

**Bad:**
```ruby
# A service object that just wraps model creation
class Projects::CreationService
  def initialize(account, params, creator)
    @account, @params, @creator = account, params, creator
  end

  def call
    @account.projects.create!(@params.merge(creator: @creator))
  end
end
```

**Good:**
```ruby
# Controller calls the model directly; model's public API is rich
@project = Current.account.projects.create!(create_project_params)
```

**Rule:** A service object is justified only when an operation coordinates across three or more AR models that don't share a natural root, or when placing it on any of those models would require that model to reach up into another bounded context. If it touches two models or fewer, it belongs on the richer of the two. When you do create one, name it after the domain action it performs (e.g., `Recording::Copier`, not `CopyRecordingService`).

---

### Controllers Access Domain Models Directly

Controllers should be thin orchestrators:
1. Retrieve the domain object
2. Call one high-level method on it
3. Redirect or render

```ruby
# Good — thin controller
def create
  @project = Current.account.projects.create!(create_project_params)
  redirect_to @project
end

def destroy
  @project.destroy!
  redirect_to projects_url
end
```

If a controller action is growing beyond ~10 lines of logic, that logic should move to the model, not to a service.

---

### Concerns: For Roles and Orthogonal Behavior

Use concerns to represent *roles* a model plays in the domain, or to isolate *orthogonal* lifecycle behavior. Do not use them as a filing cabinet for grouping unrelated methods.

**Good — role-based concern:**
```ruby
module Petitioner
  extend ActiveSupport::Concern
  # Contact petitions for clearance — methods specific to that role
end

class Contact < ApplicationRecord
  include Petitioner
end
```

**Bad — grouping dump:**
```ruby
module ProjectHelpers
  # Random mix of unrelated methods moved here to slim down the model
end
```

---

### Write Time vs Read Time

Data manipulation must happen at save time, not presentation time. In-memory sorting and filtering cannot be paginated.

**Bad:**
```ruby
# Can't paginate this
def thread_entries
  (comments + events).sort_by(&:created_at)
end
```

**Good:**
```ruby
# Delegated type — single table, DB-sorted, paginatable
bubble.messages.order(:created_at).page(params[:page])
```

Any time you see an in-memory merge/sort of multiple association types, flag it. The data model likely needs a join table or delegated type.

---

### Anemic Domain Model Warning

DDD warns: *"Don't lean too heavily toward modeling a domain concept as a Service. Using Services overzealously will usually result in an Anemic Domain Model."*

If models have thin public APIs and controllers/services do all the work, the architecture is inverted. Models should expose clean, high-level methods that read like business operations.

---

### Good Concerns vs. File-Size Concerns

A concern is extracted to reduce file size — not to add abstraction. The test: does the concern represent a named *capability* the model plays, or is it just behavior grouped by proximity?

Three questions before extracting a concern:
1. Does it represent a named role or capability a domain expert would recognise (e.g., `Archivable`, `CohortMovable`)?
2. Could another model plausibly include it in a different context? (Not required, but a strong positive signal.)
3. Does removing it leave the model clearly *less capable* in a describable way?

If the answers are no/no/no, it's a file split. Move the behavior back to the model.

**Bad — file split disguised as a concern:**
```ruby
module ProjectHelpers
  # Random methods moved here just to slim down Project
  def formatted_budget = ...
  def archive_stale_tasks! = ...
end
```

**Good — coherent capability:**
```ruby
module Archivable
  extend ActiveSupport::Concern
  def archive! = update!(archived_at: Time.current)
  def archived? = archived_at?
  scope :active, -> { where(archived_at: nil) }
end
```

---

### Monolith First

Do not introduce cross-service HTTP calls, separate Rails apps, or any pattern that moves logic out of the monolith — unless there is an explicit architectural justification.

A well-organized monolith with clear namespace boundaries is almost always cheaper than premature service decomposition. The organizational and operational cost of microservices arrives before the scaling benefit.

---

### CQRS is Rarely the Right Answer

Do not introduce separate read models, command buses, event sourcing, or write/read model splits unless there is an explicit audit trail or independent-scaling requirement.

In a Rails monolith: read and write through the same AR models. Add named scopes and query methods to the model to contain query complexity. Reserve CQRS for specific bounded contexts with hard requirements.

---

### Bounded Context via Namespace

When a model accumulates associations and behavior from unrelated domains, that is a bounded context violation. The fix is a namespace (module or Rails engine) that owns a focused view of the shared table — not more concerns on the same class.

```ruby
# Bad — one AR class serving incompatible contexts:
class Member < ApplicationRecord
  has_many :invoices        # billing
  has_many :appointments    # clinical
  has_one  :benefits_enrollment  # benefits
end

# Good — each context owns its own focused model:
module Clinical
  class Member < ApplicationRecord
    self.table_name = "members"
    has_many :appointments
  end
end
```
