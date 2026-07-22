# Final Style Checklist

Run this checklist before presenting code.

## Ticket fit
- Does the change satisfy the ticket and acceptance criteria?
- Is the change set as small as it can be while still being clean?
- Did the implementation avoid inventing extra scope?

## Naming
- Are the main nouns and verbs taken from the domain rather than generic technical language?
- Do method, class, and concern names sound like the product domain?
- Did the code avoid filler names like `service`, `processor`, `handler`, or `manager` unless they are truly justified?

## Rails shape
- Is the controller thin?
- Does the main behavior live behind a clear model or domain object API?
- Did the change avoid ceremony classes that add no real clarity?

## Concerns and collaborators
- If a concern was added, is it a real role or trait?
- If a helper class was added, does it hide real complexity rather than merely relocate code?
- If a query object was added, is the query complex enough to deserve one?

## Active Record and lifecycle behavior
- Are associations, scopes, and validations used naturally?
- If a callback was added, is it orthogonal rather than the main business workflow?
- If `Current` was used, is it for request-scoped context and not as a substitute for core data modeling?
- For any collection rendered or iterated: is every association access covered by `includes`, `preload`, `eager_load`, or a counter cache?
- For Rails 8+ models: are `strict_loading` expectations set for associations that must never be lazy-loaded?
- For any new scope on a large table: was `EXPLAIN ANALYZE` run in development to verify index use?

## Abstraction discipline
- Did every new method or class earn its keep?
- Would an explicit conditional be clearer than the new abstraction?
- Was metaprogramming avoided unless the payoff is obvious?

## Fractal quality
- Are names domain-driven?
- Are method bodies cohesive?
- Are calls inside each method at roughly the same level of abstraction?
- Can a reader understand what each public method does without opening every helper?

## Ruby consistency
- New hash syntax
- Single quotes when not interpolating
- `&&` and `||` instead of `and` and `or`
- Positive conditionals where they improve readability
- Consistent syntax with surrounding files

## ViewComponent (when warranted — House rule #11)
Creation sequence: define slots → render children → add variants → write component tests → document the public API.
Before shipping: slots documented, variants complete, tests passing, accessibility reviewed.

## Tests and explanation
- Do tests describe behavior rather than implementation trivia?
- Is the final explanation short and concrete?
- If an assumption was necessary, is it stated once and no more?
