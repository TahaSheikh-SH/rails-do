# Eval: pact_safe refactor (rotom, PR #12565)

Not loaded during normal skill runs. Run on demand to check the skill
against a real ticket with documented human review, using fixed generic
criteria — not criteria keyed to this ticket's specific code shape.

## Criteria (apply to any ticket, any layer)
1. No comment in the final diff whose content is fully inferable from the
   code beneath it.
2. Where a human reviewer's actual PR feedback exists for this ticket,
   the skill's output matches it, or explicitly justifies a narrower
   scope — not silent under-delivery.
3. review-agent's gate output is non-trivial on at least one axis (not a
   rubber-stamp pass).

## Case: rotom lib/pact_safe, mdlima's review on PR #12565

**Ticket:** refactor `lib/pact_safe` — dead code, duplication, naming drift.

**Human reviewer ask (mdlima):** ownership inversion — `ContractGroup`
should own agreement URLs and unsigned-contract logic outright
(`ContractGroup.load` / `#agree` / `#disagree`), `Client` becomes a thin
HTTP layer.

**Result, pre-fix (SKILL.md before 2026-08-30 style-checklist/grounding/
architecture.md changes):**
1. FAIL — added a 4-line comment on `HttpClient.classify_error_response`
   restating its own name/logic. Not stripped; `style-checklist.md` had
   no comments rubric.
2. FAIL — removed dead code and duplication within the existing class
   shape; did not implement the ownership-inversion API mdlima asked
   for. Plan self-scoped this out before review-agent ran; review-agent
   graded against the plan's own criteria, not the ticket's actual ask.
   `architecture.md`'s anemic-model warning existed but wasn't loaded
   for this task type (service refactor, not "new class").
3. PARTIAL — review-agent's second run (after style-checklist gate fix)
   did surface a real naming issue, but never touched ownership scope.

**Expected after 2026-08-30 fixes** (comments rubric in style-checklist.md,
architecture.md added to model/service excerpt roles, grounding strips
Scope/Out before review-agent grades): re-run to confirm 1 and 2 both
pass. Not yet re-run — do so before treating this eval as green.
