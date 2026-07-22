# TDD Checklist

Reference for the Refactor phase and flaky-spec gate in Implementation workflow step 5.

## Refactor when you see
- A method longer than 10 lines
- Nesting deeper than 3 levels
- Obvious duplication
- An unclear name
- A complex boolean that could be extracted to a predicate method

## Refactoring moves (pick the smallest that fixes the smell)
- Extract Method
- Decompose Conditional / Simplify Guard Clauses
- Replace Magic Numbers with Named Constants
- Remove Duplication (DRY within a class)
- Introduce Parameter Object (when a method takes 4+ related args)
- Extract model-private collaborator from a fat method (a named private class or module inside the model's namespace, not a service object)

## Flaky spec checklist — gate before marking any spec work done
- Time-dependent assertions use `travel_to` or a fixed date — never bare `Time.current`, `Date.today`, or `Time.now`
- No positional assertions (`.first`, `[0]`) on queries without explicit `.order()`
- All outbound HTTP calls stubbed with WebMock or VCR — no live HTTP in specs
- Tests writing to Redis or `Rails.cache` clear those keys in an `after` hook
- Tests tagged `:search` clean up Searchkick index state explicitly
