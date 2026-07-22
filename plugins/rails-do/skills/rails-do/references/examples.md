# Implementation Examples

These are miniature examples that demonstrate the style direction.

## Example 1: Rich model API instead of orchestration in controller

### Prefer
```ruby
class Admin::Subscriptions::PausesController < ApplicationController
  def create
    subscription.pause_by!(Current.person)
    redirect_to admin_subscription_path(subscription)
  end

  private

  def subscription
    @subscription ||= Subscription.find(params[:subscription_id])
  end
end
```

```ruby
class Subscription < ApplicationRecord
  def pause_by!(person)
    transaction do
      update!(paused_at: Time.current, paused_by: person)
      renewal_jobs.scheduled.destroy_all
      events.create!(kind: 'paused', person: person)
    end
  end
end
```

### Avoid by default
```ruby
class Admin::Subscriptions::PausesController < ApplicationController
  def create
    PauseSubscriptionService.call(subscription, Current.person)
  end
end
```

The first version keeps the public API on the model and lets the controller stay thin.

## Example 2: Concern as a real trait

### Prefer
```ruby
class Subscription < ApplicationRecord
  include Renewable
end
```

```ruby
module Subscription::Renewable
  def renew!
    Renewal.new(self).run
  end
end
```

### Avoid
```ruby
module Subscription::Helpers
  def renew!
    RenewalService.execute(self)
  end
end
```

The preferred concern reflects a real trait and publishes a domain-language API.

## Example 3: Query object only when complexity justifies it

### Prefer
```ruby
class Subscription::RenewalCandidates
  def relation
    Subscription.active
      .where(paused_at: nil)
      .where('renews_on <= ?', Date.current)
      .includes(:account)
  end
end
```

Use a query object only after the relation is substantial enough to deserve a name.

## Example 4: Callback for an orthogonal concern

### Acceptable
```ruby
class Project < ApplicationRecord
  after_create :create_bucket!

  private

  def create_bucket!
    Storage::Bucket.create!(project: self, account: account)
  end
end
```

This is secondary lifecycle behavior, not the main project creation workflow.
