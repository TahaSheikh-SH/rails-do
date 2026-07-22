# Request Template

Use this when you want the skill to produce code from a ticket quickly and with minimal back-and-forth.

```text
Implement this in my Rails style.

Context:
- Product or business context:
- Relevant files, models, controllers, or jobs:
- Existing patterns to mirror:
- Constraints or non-goals:

Jira ticket:
- Key / title:
- Problem statement:
- Desired behavior:
- Acceptance criteria:
- Edge cases:

Output requested:
- Patch, diff, or full files:
- Tests to add or update:
- Notes on tradeoffs:
```

## Minimum viable input
Unstructured input is fine. At minimum, provide:
- the ticket text or bug report
- enough repository or feature context to know where the change belongs
- whether you want code, a patch, tests, or all three

## Good prompt example
```text
Implement this in my Rails style.

Context:
- We already create `Subscription` records from `Checkout::SessionsController#create`.
- Similar domain methods live on the model, not in service objects.
- Mirror the patterns used by `Account#terminate` and `Subscription::Renewable`.

Jira ticket:
- BILL-142: Pause a subscription without canceling it.
- Acceptance criteria:
  - customer support can pause a subscription from the admin UI
  - paused subscriptions stop renewal jobs
  - unpausing restores normal renewal behavior
  - actions are audited to the acting admin

Output requested:
- show the patch and the tests
```
