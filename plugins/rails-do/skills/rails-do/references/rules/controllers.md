---
title: Controllers
impact: HIGH
tags: controllers, routing, rest, thin-controllers
---

## Controllers

### The Thin Controller Standard

A controller action should:
1. Find or build a domain object
2. Call one high-level method on it (or `create!`/`destroy!`)
3. Redirect or render

If an action does more than that, the extra logic belongs in the model.

```ruby
# Good
def create
  @project = Current.account.projects.create!(create_project_params)
  redirect_to @project
rescue ActiveRecord::RecordInvalid
  render :new, status: :unprocessable_entity
end
```

---

### `My::` Namespace for Current-User Resources

When a resource is always scoped to `Current.identity` or `Current.user`, it belongs
under the `My::` namespace. This signals there will be no `/resource/:id` route — only `/my/resource`.

```ruby
# Bad
class IdentitiesController < ApplicationController; end
# Routes: GET /identities/:id (but there's only ever one identity)

# Good
class My::IdentitiesController < ApplicationController; end
# Routes: GET /my/identity
```

---

### Implicit `respond_to`

Rails infers format from the request and available templates. Don't add a `respond_to`
block if both format templates exist.

```ruby
# Unnecessary — if show.html.erb and show.json.jbuilder exist, this adds nothing
def show
  respond_to do |format|
    format.html
    format.json
  end
end

# Just:
def show
end
```

---

### `head :no_content` for Non-Returning Updates

```ruby
# When the client doesn't need a body back:
def update
  @card.update!(card_params)
  head :no_content
end
```

---

### Helpers Receive Explicit Parameters

Never write helpers that reference ivars from the controller context. Make the dependency
explicit so the helper is testable and its inputs are obvious.

```ruby
# Bad
def project_member_count
  @project.members.count
end

# Good
def project_member_count(project)
  project.members.count
end
```

---

### Authorization: Unauthenticated Implies Unauthorized

If an action allows unauthenticated access, it's implied that it also allows unauthorized
access — you cannot authorize someone you haven't authenticated. Don't add separate
`allow_unauthorized_access` logic on top of `allow_unauthenticated_access`; elevate the
unauthenticated check to cover both.
