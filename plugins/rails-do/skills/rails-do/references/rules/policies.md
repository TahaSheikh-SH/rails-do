---
title: Authorization & Pundit Policies
impact: HIGH
tags: authorization, pundit, policies, security, multi-tenant
---

## Authorization & Pundit Policies

### Deny By Default

`ApplicationPolicy` inherits Pundit's default behavior: every action returns `false`
unless explicitly overridden. Never rely on a policy inheriting a permissive base action.

```ruby
class ApplicationPolicy
  attr_reader :user, :record

  def initialize(user, record)
    @user = user
    @record = record
  end

  # All actions denied by default — subclasses must explicitly permit
  def index?  = false
  def show?   = false
  def create? = false
  def update? = false
  def destroy? = false
end
```

---

### Authorize Every Action

Call `authorize` in every controller action that touches a resource. Never skip it.

```ruby
class ProjectsController < ApplicationController
  def show
    @project = Project.find(params[:id])
    authorize @project         # raises Pundit::NotAuthorizedError if denied
  end

  def index
    @projects = policy_scope(Project)  # scoped to what current_user can see
  end
end
```

`authorize` raises on denial — do not rescue it silently. Let the `rescue_from` in
`ApplicationController` handle the 403 or 404 response.

---

### `policy_scope` for Index Queries

Never query the full table and then filter in Ruby. Use `policy_scope(Model)` so the
scope is enforced at the database level.

```ruby
# Bad — loads unauthorized records into memory
@projects = Project.all.select { |p| policy(p).index? }

# Good — DB-level filter, no unauthorized records touch Ruby
@projects = policy_scope(Project)
```

The corresponding `Scope` class:

```ruby
class ProjectPolicy < ApplicationPolicy
  class Scope < ApplicationPolicy::Scope
    def resolve
      scope.where(account_id: user.account_id)
    end
  end
end
```

---

### Policy Patterns

#### Owner-Based Access
```ruby
class RecordingPolicy < ApplicationPolicy
  def show?   = record.account_id == user.account_id
  def update? = record.creator_id == user.id
  def destroy? = update?
end
```

#### Role-Based Access
```ruby
class AdminPolicy < ApplicationPolicy
  def index?  = user.admin?
  def destroy? = user.admin? && record != user   # admin can't delete themselves
end
```

#### Temporal Constraint
```ruby
class SubmissionPolicy < ApplicationPolicy
  def update? = record.deadline > Time.current && record.owner?(user)
end
```

---

### `permitted_attributes`

Use `permitted_attributes` in the policy to whitelist strong params per-action, rather
than duplicating `params.permit` across controllers.

```ruby
class ProjectPolicy < ApplicationPolicy
  def permitted_attributes
    base = %i[name description]
    user.admin? ? base + %i[account_id archived] : base
  end
end

# Controller
def project_params
  params.require(:project).permit(policy(@project).permitted_attributes)
end
```

---

### Testing Policies

Test every policy action and the scope. Use the policy's own interface — do not test
via controller request specs for authorization logic.

Use explicit, deterministic IDs so permitted vs. forbidden cases can't accidentally
match. If the `pundit-matchers` gem is installed, use `permit_action`/`forbid_action`
for brevity; otherwise assert on the policy method directly.

```ruby
RSpec.describe ProjectPolicy do
  # Explicit account IDs — no relying on build_stubbed defaults to differ
  let(:account_id)       { 42 }
  let(:other_account_id) { 99 }

  let(:user)    { build_stubbed(:user, account_id: account_id) }
  let(:project) { build_stubbed(:project, account_id: account_id, creator_id: user.id) }

  subject(:policy) { described_class.new(user, project) }

  context 'when user is the project owner (same account)' do
    # With pundit-matchers:
    it { is_expected.to permit_action(:show) }
    it { is_expected.to permit_action(:update) }
    it { is_expected.to forbid_action(:destroy) }

    # Without pundit-matchers (equivalent):
    # it { expect(policy.show?).to be true }
    # it { expect(policy.update?).to be true }
    # it { expect(policy.destroy?).to be false }
  end

  context 'when user belongs to a different account' do
    let(:project) { build_stubbed(:project, account_id: other_account_id) }

    # With pundit-matchers:
    it { is_expected.to forbid_action(:show) }
    it { is_expected.to forbid_action(:update) }

    # Without pundit-matchers:
    # it { expect(policy.show?).to be false }
    # it { expect(policy.update?).to be false }
  end

  describe ProjectPolicy::Scope do
    subject(:scope) { described_class.new(user, Project.all).resolve }

    it 'returns only projects in the user account' do
      expect(scope.to_sql).to include(account_id.to_s)
    end
  end
end
```

---

### Checklist Before Shipping Authorization Changes

- [ ] Every new controller action calls `authorize` or `policy_scope`
- [ ] `ApplicationController` has a `rescue_from Pundit::NotAuthorizedError` handler
- [ ] New policy has tests for both permitted and forbidden cases
- [ ] `policy_scope` used for every index-style query
- [ ] `permitted_attributes` updated if new fields were added to the model
