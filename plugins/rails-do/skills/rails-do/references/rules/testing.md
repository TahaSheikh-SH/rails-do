---
title: RSpec & Testing
impact: HIGH
tags: rspec, testing, factory-bot, performance, specs
---

## RSpec & Testing

The goal is a fast, non-flaky test suite. The single biggest lever is minimizing
database writes. Follow this hierarchy strictly — only drop down to the next level
when the level above genuinely cannot work.

---

### The Object Creation Hierarchy

```
1. FactoryBot.build_stubbed  ← default; no DB hit, full AR feel
2. FactoryBot.build          ← when associations need to be traversable in memory
3. Mocks / stubs             ← when you need to verify interactions or fake collaborators
4. FactoryBot.create         ← last resort; only when DB persistence is genuinely required
```

**If you see `.create` in a spec, ask:** does this test actually require persistence?
Can it be replaced with `build_stubbed`, `build`, or a double?

---

### Arrange-Act-Assert (AAA)

Structure every example with three clearly separated phases. A blank line between phases makes the boundary explicit.

```ruby
it 'creates a new article' do
  user = create(:user)
  attributes = { title: 'Test Article', body: 'Content' }

  article = Article.create(attributes.merge(user: user))

  expect(article).to be_persisted
  expect(article.title).to eq('Test Article')
end
```

Single-expectation unit tests are the default. When multiple expectations share identical setup and test the same action, group them with `:aggregate_failures` rather than duplicating setup across separate examples.

---

### `aggregate_failures` for Shared-Setup Examples

Each `it` block re-runs all `let` and `before` hooks from scratch. When several expectations verify the same action — response status, body, redirect — splitting them into three `it` blocks means the same setup runs three times. Grouping with `:aggregate_failures` eliminates repeated setup while still reporting every failure instead of stopping at the first.

```ruby
# Slow — identical setup runs three times for one logical scenario
it 'returns 200' do
  patch :update, params: valid_params
  expect(response).to have_http_status(:ok)
end
it 'renders the show template' do
  patch :update, params: valid_params
  expect(response).to render_template(:show)
end
it 'sets a flash notice' do
  patch :update, params: valid_params
  expect(flash[:notice]).to be_present
end

# Fast — one setup, all three assertions, all failures visible
it 'updates the book successfully', :aggregate_failures do
  patch :update, params: valid_params

  expect(response).to have_http_status(:ok)
  expect(response).to render_template(:show)
  expect(flash[:notice]).to be_present
end
```

Use single-expectation examples when behaviors have meaningfully different setups or when each example tests a genuinely independent concern.

---

### `build_stubbed` First

`build_stubbed` returns a fully populated object that behaves like a saved record
(has an `id`, responds to `persisted?` → `true`) without touching the database.
Use it for any test that's about object behavior, not persistence.

```ruby
# Bad — hits the DB for no reason
let(:user) { create(:user) }

it 'returns the full name' do
  expect(user.full_name).to eq('Jane Doe')
end

# Good
let(:user) { build_stubbed(:user, first_name: 'Jane', last_name: 'Doe') }

it 'returns the full name' do
  expect(user.full_name).to eq('Jane Doe')
end
```

---

### `build` When Associations Must Be Traversable

`build` populates associations in memory without persisting. Use it when the test
logic needs to traverse `belongs_to` or `has_many` associations but doesn't need them
in the database.

```ruby
# build_stubbed associations are stubs — can't call AR methods on them
# build gives you real in-memory objects
let(:project) { build(:project, :with_tasks) }
```

---

### Mocks and Stubs for Collaborators and Interactions

When testing that one object calls another correctly — without caring about the
collaborator's internals — use doubles or `allow`/`expect` stubs.

```ruby
# Bad — creates the mailer infrastructure in the DB to verify delivery
it 'sends a welcome email' do
  user = create(:user)
  expect { user.welcome! }.to change { ActionMailer::Base.deliveries.count }.by(1)
end

# Good — stub the mailer, test the interaction
it 'sends a welcome email' do
  user = build_stubbed(:user)
  mailer = instance_double(UserMailer)
  allow(UserMailer).to receive(:welcome).with(user).and_return(mailer)
  allow(mailer).to receive(:deliver_later)

  user.welcome!

  expect(mailer).to have_received(:deliver_later)
end
```

---

### When `create` Is Acceptable

Use `create` only when the test genuinely depends on database behavior:

- Testing AR validations with uniqueness constraints (requires DB)
- Testing scopes and queries (requires real records in the DB)
- Integration / request specs (testing the full stack)
- Testing counter caches, `touch:`, or callbacks that fire `after_commit`

```ruby
# Requires DB — uniqueness constraint is enforced at DB level
it 'rejects duplicate email' do
  create(:user, email: 'same@example.com')
  user = build(:user, email: 'same@example.com')
  expect(user).not_to be_valid
end

# Requires DB — testing a scope query
it 'returns only active projects' do
  create(:project, :active)
  create(:project, :archived)
  expect(Project.active.count).to eq(1)
end
```

---

### Minimize Factory Trait Chains

Deep factory trait chains create many DB records implicitly. Prefer explicit, minimal
setups in the spec itself so it's clear what's being created.

```ruby
# Bad — what does :with_full_setup actually create?
let(:project) { create(:project, :with_full_setup) }

# Better — explicit, the spec is self-documenting
let(:project) { create(:project) }
let!(:task)   { create(:task, project: project) }
```

---

### Factory Attribute Order

Within a factory definition, follow this order:

1. Implicit associations (factory name only)
2. Attributes, alphabetically
3. Traits, alphabetically

```ruby
FactoryBot.define do
  factory :article do
    user
    category

    body         { 'Article content.' }
    published_at { Time.current }
    status       { :draft }
    title        { 'Sample Article' }

    trait :published do
      published_at { 1.day.ago }
      status       { :published }
    end

    trait :with_tags do
      after(:create) { |a| create_list(:tag, 3, article: a) }
    end
  end
end
```

---

### `let` vs `let!`

- `let` is lazy — the object is created only when first referenced. Prefer it.
- `let!` is eager — created before each example. Use only when the side effect of
  creation matters (e.g., a record needs to exist in the DB before a query runs).

---

### Use `let` Over Instance Variables

Never use `@instance_variables` in `before` blocks to set up test state. `let` is lazy, memoized per example, and cleaned up automatically.

```ruby
# Bad
before { @user = create(:user) }
it 'returns the name' do
  expect(@user.name).to eq('Alice')
end

# Good
let(:user) { create(:user) }
it 'returns the name' do
  expect(user.name).to eq('Alice')
end
```

---

### Declaration Order in Example Groups

Within any example group, declare helpers in this order: `subject` first, then `let`/`let!`, then `before`/`after` hooks.

```ruby
# Bad
describe Article do
  before { allow(Mailer).to receive(:deliver) }
  let(:user) { create(:user) }
  subject { create(:article) }
end

# Good
describe Article do
  subject(:article) { create(:article) }
  let(:user) { create(:user) }
  before { allow(Mailer).to receive(:deliver) }
end
```

---

### Shared Examples and Contexts: Use Sparingly

Shared examples reduce duplication but increase indirection. Only extract shared
examples when the same behavior genuinely applies to multiple unrelated subjects.
Don't use shared contexts just to DRY up `let` blocks — inline them.

---

### Avoid Test-Induced Design Damage

Never add code to the production application solely to make it easier to test.
If you find yourself adding a public method, accessor, or alternative constructor
that exists only for test setup, that's a red flag. Use mocks, stubs, or a fixture
instead.

**DHH:** _"That would qualify as test-induced design damage. Better to replace that
with a mock or a fixture session. We should never let our desire for ease of testing
bleed into the application itself."_

---

### No Inline Comments in Specs

Do not add comments that restate what the test code does. The spec structure (`describe`, `context`, `it`) and well-named helpers already express intent. Only add a comment when a non-obvious constraint or workaround requires explanation — the *why*, never the *what*.

---

### Named Subject

Name the `subject` so it can be referenced by a readable identifier. An anonymous `subject` is only appropriate when using the `is_expected` shorthand.

```ruby
# Bad — `subject` is opaque
describe Article do
  subject { create(:article) }
  it 'is not published on creation' do
    expect(subject).not_to be_published
  end
end

# Good — named, self-documenting
describe Article do
  subject(:article) { create(:article) }
  it 'is not published on creation' do
    expect(article).not_to be_published
  end
end

# Also fine — anonymous subject with is_expected shorthand
describe Article do
  subject { create(:article) }
  it { is_expected.not_to be_published }
end
```

---

### Controlling Time: Always Use `travel_to`

Tests that read the wall clock are invisible time bombs — they pass for the developer
who wrote them but fail for a colleague in another timezone or during an off-hours CI
run. Always freeze time explicitly with Rails' `travel_to`. Never stub `Time.now` or
`Date.today` directly.

```ruby
# Bad — breaks if run outside business hours or in a different timezone
it 'rejects notifications after hours' do
  post notifications_url, params: { ... }
  expect(response).to have_http_status(:unprocessable_entity)
end

# Good — test controls exactly what time it is
it 'rejects notifications after business hours' do
  travel_to(Time.use_zone('America/New_York') { Time.parse('2024-01-15T18:00') }) do
    post notifications_url, params: { ... }
    expect(response).to have_http_status(:unprocessable_entity)
  end
end
```

---

### Use Verifying Doubles

Plain `double(:foo)` lets you stub methods that don't exist on the real class — the
test stays green while production breaks. Verifying doubles (`instance_double`,
`class_double`) fail immediately if the method is missing or called with wrong arity.
Only fall back to `double` when you genuinely need a fully anonymous object.

```ruby
# Bad — stubs a method that might not exist
let(:mailer) { double('UserMailer') }
allow(mailer).to receive(:deliver_later)

# Good — fails at spec load time if UserMailer#deliver_later doesn't exist
let(:mailer) { instance_double(UserMailer) }
allow(mailer).to receive(:deliver_later)
```

Also avoid `allow_any_instance_of` / `expect_any_instance_of` — it is ambiguous with
receive counts and usually signals the object under test needs to be injected instead.

---

### Never Stub the System Under Test

Do not mock or stub methods on the class being tested. Doing so removes real behavior from the subject and turns the test into a tautology.

```ruby
# Bad — stubs behavior on the object under test
it 'processes payment' do
  order = Order.new
  allow(order).to receive(:calculate_total).and_return(100)
  expect(order.process_payment).to be true
end

# Good — exercises real behavior
it 'processes payment' do
  order = Order.new(line_items: [line_item])
  expect(order.process_payment).to be true
end
```

---

### Do Not Test Private Methods

Private methods are an implementation detail. Test the public interface that exercises them; the private logic is verified indirectly.

```ruby
# Bad — reaches into implementation via send
describe '#calculate_total (private)' do
  it 'sums line items' do
    expect(order.send(:calculate_total)).to eq(100)
  end
end

# Good — tests the public contract
describe '#total' do
  it 'returns the sum of line items' do
    expect(order.total).to eq(100)
  end
end
```

---

### Factory Sequences Are Not Test Data

Factory sequences (`:name { |n| "Category #{n}" }`) exist to prevent uniqueness
collisions, not to produce predictable values. Asserting against sequence-generated
strings couples the test to sequence state that resets between runs differently in
different contexts. When a value matters to the assertion, set it explicitly.

```ruby
# Bad — relies on sequence state; breaks if another factory call fires first
let(:category) { create(:category) }
it { expect(page).to have_content('Category 1') }

# Good — the intent is obvious and the value is stable
let(:category) { create(:category, name: 'Electronics') }
it { expect(page).to have_content('Electronics') }
```

---

### Naming: Contexts and Examples

Readable spec output comes from consistent naming. Follow two rules:

1. **Context descriptions** start with "when", "with", or "without". Every `context`
   block should have a matching negative counterpart — a lone context is a smell that
   the negative case was forgotten.
2. **Example descriptions** never start with "should" and never end with a conditional
   clause. Move the condition into a wrapping context instead.

```ruby
# Bad
it 'returns the display name if present' do ... end

# Good
context 'when display name is present' do
  it 'returns the display name' do ... end
end

context 'when display name is blank' do
  it 'returns nil' do ... end
end
```

The concatenated path (`Article when display name is present returns the display name`)
should read as a sentence.

---

### Naming: `describe` Blocks

Use Ruby documentation conventions for `describe` block names:

- `.method_name` for class methods
- `#method_name` for instance methods
- A noun phrase for logical groupings (`'validations'`, `'associations'`)

```ruby
describe '.find_by_slug' do   # class method
describe '#publish' do         # instance method
describe 'validations' do      # logical group
```

---

### Constants in Specs: Use `stub_const`

Constants (including classes and modules) declared inside `describe` blocks are defined
in the global namespace and leak between examples. Use `stub_const` for named constants
or an anonymous `Class.new` to keep things scoped.

```ruby
# Bad — FooClass leaks into every subsequent example
describe SomeClass do
  class FooClass < described_class; end
  it { expect(FooClass.new).to be_a(SomeClass) }
end

# Good — constant is scoped to this example only
describe SomeClass do
  before { stub_const('FooClass', Class.new(described_class)) }
  it { expect(FooClass.new).to be_a(SomeClass) }
end
```

---

### Stub HTTP Requests

Never hit real external services in the test suite — it makes tests slow, flaky, and
leaks data. Use `webmock` to stub at the HTTP adapter level, or `VCR` to record and
replay real responses.

```ruby
# Good — webmock stub, no network call made
before do
  stub_request(:post, 'https://api.example.com/notify')
    .to_return(status: 200, body: '{"ok":true}')
end
```

---

### Matchers

#### Predicate Matchers

Prefer RSpec's predicate matchers over asserting on the return value of a `?` method. They produce better failure messages and read more naturally.

```ruby
# Bad
expect(article.published?).to be true

# Good
expect(article).to be_published

# Also good — one-liner with named subject
it { is_expected.to be_published }
```

#### Use Built-in Matchers

Use RSpec's built-in matchers instead of wrapping Ruby boolean expressions.

```ruby
# Bad
expect(article.title.include?('lengthy')).to be true

# Good
expect(article.title).to include('lengthy')
```

#### `be` Without Arguments Is Too Broad

`be` without arguments passes for anything that is not `nil` or `false`. Be explicit about intent.

```ruby
# Bad — passes for any truthy value; intent is unclear
expect(article.author).to be

# Good
expect(article.author).to be_truthy      # when truthy is genuinely the intent
expect(article.author).not_to be_nil     # when checking for presence
expect(article.author).to be_an(Author)  # when checking type
```

---

### System Specs: Use Semantic Selectors

Never assert on CSS utility classes — they change for presentational reasons and carry no behavioral meaning. Use semantic selectors instead: `data-testid` attributes, ARIA attributes, visible text, or accessible labels.

```ruby
# Bad — coupled to styling implementation
expect(page).to have_css('.bg-red-500')
expect(page).to have_css('.opacity-100')

# Good — tests intent, not presentation
expect(page).to have_selector('[data-testid="error-banner"]')
expect(page).to have_css("[aria-hidden='false']")
expect(page).to have_content('Payment failed')
```

---

### Diagnosing a Slow Suite

When the test suite slows down unexpectedly:

1. **Profile**: `rspec --profile 10` shows the 10 slowest examples. A unit spec taking

   > 100ms almost always means an unexpected DB write or a heavy `before` block.

2. **Scope global hooks**: A `before` block in `spec_helper` that runs before every
   example and is only needed by a few specs is a common culprit. Use metadata tags to
   limit scope:

   ```ruby
   # spec_helper.rb
   config.before(:each, :with_billing_profile) do
     create(:billing_profile, user: user)
   end

   # only the specs that need it
   it 'shows billing info', :with_billing_profile do ... end
   ```

3. **Move factory associations to traits**: An `after(:create)` hook on a base factory
   runs every time that factory is used, even when the association isn't needed. Extract
   it into a named trait and call it explicitly only where required.

---

### Run Tests in Random Order

Add `--order random` to `.rspec`. RSpec prints the seed at the start of each run:

```
Randomized with seed 42701
```

If a failure only reproduces with a specific seed, rerun with `--seed 42701` to isolate
it. Tests that only pass in a particular order have hidden state coupling — shared mutable
state, missing database cleanup, or a `let!` side-effect that bleeds into a sibling
example. Random order surfaces these before they become CI-only mysteries.

---

### Profile Factories with test-prof

When a spec folder is slow and `rspec --profile` points at factory setup, use the test-prof factory profiler (already installed) to find the bottleneck:

```bash
FPROF=1 bundle exec rspec spec/services
```

Output shows invocation count, time per call, and total time per factory. Common culprits:

- **Associations on the base factory** — an `association :city` fires on every `create(:user)`, even when the city is irrelevant. Move it to a named trait.
- **`after(:create)` callbacks** — a callback that cascades into additional DB writes runs unconditionally. Extract it into a trait and opt in only where required.

```ruby
# Bad — city and profile created for every user, even in tests that don't need them
factory :user do
  association :city
  after(:create) { |u| u.create_profile! }
end

# Good — base factory is minimal; extras are opt-in traits
factory :user do
  trait :with_city { association :city }
  trait :with_profile { after(:create) { |u| u.create_profile! } }
end
```

---

### Mutation Testing (Advanced)

Code coverage tells you which lines ran. Mutation testing tells you whether your tests
would actually catch a bug. The `mutant` gem makes small automated changes to your
code — flipping a `>` to `>=`, removing a condition — then reruns the relevant specs.
A test suite that stays green after the mutation "missed" a real behavioral change.

Use it surgically on critical domain logic rather than the whole codebase (it's
compute-heavy). A surviving mutant in a billing calculation or an eligibility rule is
a concrete signal that the spec needs a stronger assertion, not just more lines covered.

---

### Testing Services That Wrap External Indexes

Services backed by an external index (Searchkick, OpenSearch, Elasticsearch) tend to
grow the same two bad habits: hitting the real index in unit specs, and asserting on
query internals instead of on outcomes. Both make tests slow, order-dependent, and
brittle to unrelated changes.

#### Prefer Stubs Over a Real Index

An external index is not a database — rollback does not clean it up. Documents indexed
during one example silently pollute later ones. The project disables Searchkick
callbacks by default; tests that need a real index must opt in with the `:search` tag
and take responsibility for cleanup.

Before reaching for a real index, ask: does this test actually need to verify that a
document is retrievable from the index, or does it just need the search call to return
something? The latter is almost always true in service specs, and a stub is the right
tool.

```ruby
# Bad — requires a live index, leaves stale documents, order-dependent
before { Model.reindex }

# Good — opt in explicitly when round-trip index behavior is the point
it "surfaces the record after indexing", :search do
  record = create(:record, title: "Example")
  Model.reindex
  expect(Model.search("example").results).to include(record)
end
```

Most service and unit specs should use stubs, not a real index.

#### Test Outcomes, Not Query Shape

The JSON a query builder assembles (`bool`, `filter`, `must`, query DSL) is an
implementation detail. It belongs in the spec for the class that builds it, not in
every caller's spec. Callers should assert on *what they got back*, not on *how the
query was constructed*.

```ruby
# Bad — a caller's spec asserting on query internals it doesn't own
expect(search_client).to have_received(:search).with(
  body: hash_including(query: hash_including(bool: hash_including(filter: [...])))
)

# Good — assert on delegation and output, leave DSL verification to the builder's spec
expect(QueryBuilder).to have_received(:execute)
expect(result.records).to be_an(Array)
```

#### Stub at the Pipeline Boundary, Not at the Hit Level

Search pipelines typically have a shape: `raw hits → transformer → output`. When the
transformer is a distinct collaborator, stub it. The upstream call (`.search`) then
only needs to satisfy the interface the transformer reads — usually just `total_count`.
Building elaborate fake hit objects to feed through a real transformer couples the
spec to both sides of a boundary it doesn't own.

```ruby
# Bad — hand-rolling fake hit objects to satisfy a collaborator the spec doesn't own
let(:hits) { [double("Hit", id: 1, title: "Example", content_types: [], ...)] }
let(:results) { double("Results", hits: hits, total_count: 1) }

# Good — stub the transformer; upstream only needs total_count
let(:result_hash) { {id: 1, title: "Example"} }
let(:raw_results) { double("Results", total_count: 1) }

before do
  allow(ResultTransformer).to receive(:call).and_return([result_hash])
  allow(Model).to receive(:search).and_return(raw_results)
end
```
