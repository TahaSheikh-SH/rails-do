#!/usr/bin/env python3
"""Stop hook: block turn-end if changed Ruby files have no passing spec.

Scope, deliberately: only app/<layer>/**.rb for layers that already have
a mirrored spec/<layer>/ or test/<layer>/ directory in this repo (see
mapped_spec_or_test), lib/**.rb, and spec/**.rb or test/**.rb itself.
Controllers, graphql, views, channels, helpers, config, and db/migrate
are NOT checked here — this codebase doesn't use a 1:1 file-to-spec
convention for those layers, so a missing-spec check there would false-
positive on request/integration specs that legitimately live elsewhere.
Those layers still rely on the rails-do skill's own manual gates.

Backs off after MAX_RETRIES consecutive blocks in the same session so a
genuinely stuck fix can't loop forever without a human looking at it.

TDD Red phase means a spec is *supposed* to fail — blocking on that would
fight the workflow instead of enforcing it. Any spec path listed in a
.rails-do/<ticket-key>/tdd-red-expected file (one path per line, written
by the skill's Red step and cleared at Green) is excluded from the pass
requirement here. Everything else still enforces normally.

Lint tool (standardrb/rubocop), test framework (rspec/minitest), and a
SimpleCov coverage-skip env var (if any) are auto-detected per repo via
detect_toolchain() — nothing to configure by default. When detection is
genuinely ambiguous (not "no such tool in use", but "can't tell which
one"), the hook blocks turn-end and asks a question instead of guessing
— see Toolchain.questions below. Once the user answers, write the
answer to .rails-do/toolchain-override (one "key: value" line per
answer — lint/test/coverage_skip; "none" is a valid answer for any of
them) so the same question isn't asked again on the next run;
detect_toolchain() checks that file before running any auto-detection.

Known limitations, accepted rather than engineered around:
- The git-status scan is repo-wide, not ticket-scoped. Unrelated
  uncommitted Ruby files from other work get linted/tested too and can
  block on a failure that has nothing to do with the ticket in progress.
- The layer-to-spec/test mapping heuristic requires the mirrored
  directory (spec/<layer>/ or test/<layer>/) to already exist; it can't
  flag a missing spec for the very first file added under a brand-new
  layer.
- Detection reads only the top-level Gemfile.lock and checks spec/test
  directories relative to the git root; a monorepo or engine with its
  own toolchain outside the root isn't detected or enforced.
"""
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field

VALID_ENV_NAME_RE = re.compile(r"^[A-Z_][A-Z0-9_]*$")
SIMPLECOV_GUARD_RE = re.compile(r"(if|unless)\s+ENV\[['\"]([A-Za-z_][A-Za-z0-9_]*)['\"]\]")

LINT_COMMANDS = {
    "standardrb": ["bundle", "exec", "standardrb", "--format", "progress"],
    "rubocop": ["bundle", "exec", "rubocop", "--format", "progress"],
}
TEST_COMMANDS = {
    "rspec": ["bundle", "exec", "rspec", "--format", "progress"],
    "minitest": ["bundle", "exec", "rails", "test"],
}

MAX_RETRIES = 3
COUNTER_DIR = "/tmp/rails-do-stop-hook"


@dataclass
class Toolchain:
    lint: str = None
    test: str = None
    coverage_skip: tuple = None
    questions: list = field(default_factory=list)


def sh(cmd, cwd, env=None):
    run_env = {**os.environ, **env} if env else None
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, env=run_env)


def _read_text(path):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return fh.read()
    except (OSError, UnicodeDecodeError):
        return None


def _gemfile_lock_dependencies(root):
    text = _read_text(os.path.join(root, "Gemfile.lock"))
    if text is None:
        return set()
    lines = text.splitlines()
    try:
        start = next(i for i, line in enumerate(lines) if line.strip() == "DEPENDENCIES")
    except StopIteration:
        return set()
    deps = set()
    for line in lines[start + 1:]:
        if not line.startswith("  "):
            break
        stripped = line.strip()
        if stripped:
            deps.add(stripped.split()[0].rstrip("!"))
    return deps


def _read_toolchain_override(root):
    text = _read_text(os.path.join(root, ".rails-do", "toolchain-override"))
    if text is None:
        return {}
    override = {}
    for line in text.splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key, value = key.strip(), value.strip()
        if key and value:
            override[key] = value
    return override


def detect_lint(root, questions, override):
    if "lint" in override:
        value = override["lint"]
        if value in LINT_COMMANDS:
            return value
        if value == "none":
            return None
        # Unrecognized override value - ignore it and fall through to detection/asking again.

    deps = _gemfile_lock_dependencies(root)
    has_standard, has_rubocop = "standard" in deps, "rubocop" in deps
    if has_standard and has_rubocop:
        standard_cfg = os.path.isfile(os.path.join(root, ".standard.yml"))
        rubocop_cfg = os.path.isfile(os.path.join(root, ".rubocop.yml"))
        if standard_cfg and not rubocop_cfg:
            return "standardrb"
        if rubocop_cfg and not standard_cfg:
            return "rubocop"
        questions.append(
            "Both standard and rubocop gems are declared with no .standard.yml/"
            ".rubocop.yml to disambiguate - which lint tool does this repo use? "
            "(\"lint: standardrb\", \"lint: rubocop\", or \"lint: none\")"
        )
        return None
    if has_standard:
        return "standardrb"
    if has_rubocop:
        return "rubocop"
    return None


def detect_test(root, questions, override):
    if "test" in override:
        value = override["test"]
        if value in TEST_COMMANDS:
            return value
        if value == "none":
            return None
        # Unrecognized override value - ignore it and fall through to detection/asking again.

    rspec_helper = any(
        os.path.isfile(os.path.join(root, "spec", name))
        for name in ("rails_helper.rb", "spec_helper.rb")
    )
    minitest_helper = os.path.isfile(os.path.join(root, "test", "test_helper.rb"))
    if rspec_helper and minitest_helper:
        questions.append(
            "Both spec/ and test/ helpers were found - which test framework does "
            "this repo use? (\"test: rspec\", \"test: minitest\", or \"test: none\")"
        )
        return None
    if rspec_helper:
        return "rspec"
    if minitest_helper:
        return "minitest"
    questions.append(
        "No rspec or minitest helper was found - which test framework does this "
        "repo use, if any? (\"test: rspec\", \"test: minitest\", or \"test: none\")"
    )
    return None


def detect_coverage_skip(root, questions, override):
    if "coverage_skip" in override:
        value = override["coverage_skip"]
        if value == "none":
            return None
        if VALID_ENV_NAME_RE.match(value):
            return (value, "1")
        # Unrecognized override value - ignore it and fall through to detection/asking again.

    for rel in (".simplecov", "spec/rails_helper.rb", "spec/spec_helper.rb", "test/test_helper.rb"):
        text = _read_text(os.path.join(root, rel))
        if text is None:
            continue
        idx = text.find("SimpleCov.start")
        if idx == -1:
            continue
        window = text[max(0, idx - 200):idx]
        matches = list(SIMPLECOV_GUARD_RE.finditer(window))
        match = matches[-1] if matches else None
        if not match or not VALID_ENV_NAME_RE.match(match.group(2)):
            questions.append(
                "A SimpleCov guard was found but its skip variable couldn't be "
                "confidently resolved - what's the env var (if any) that skips "
                "coverage in this repo's test run? (\"coverage_skip: NAME\" or "
                "\"coverage_skip: none\")"
            )
            return None
        keyword, name = match.groups()
        return None if keyword == "if" else (name, "1")
    return None


def _test_enforcement_could_apply(changed, root):
    """Whether any changed file could plausibly need test enforcement, regardless
    of which framework turns out to be in use. Guards against asking "which test
    framework?" on a changeset that only touches an unenforced layer (controllers,
    views, migrations, ...) — the answer could never matter for that changeset."""
    for f in changed:
        if f.startswith(("spec/", "test/", "lib/")):
            return True
        parts = f.split("/")
        if f.startswith("app/") and len(parts) >= 3:
            layer = parts[1]
            if os.path.isdir(os.path.join(root, "spec", layer)) or os.path.isdir(
                os.path.join(root, "test", layer)
            ):
                return True
    return False


def detect_toolchain(root, changed):
    override = _read_toolchain_override(root)
    questions = []
    lint = detect_lint(root, questions, override)
    if _test_enforcement_could_apply(changed, root):
        test = detect_test(root, questions, override)
        coverage_skip = detect_coverage_skip(root, questions, override)
    else:
        test = None
        coverage_skip = None
    return Toolchain(lint=lint, test=test, coverage_skip=coverage_skip, questions=questions)


def repo_root(cwd):
    r = sh(["git", "rev-parse", "--show-toplevel"], cwd)
    return r.stdout.strip() if r.returncode == 0 else cwd


def changed_ruby_files(root):
    r = sh(["git", "status", "--porcelain"], root)
    files = []
    for line in r.stdout.splitlines():
        path = line[3:].strip()
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        if not path.endswith(".rb"):
            continue
        if path.startswith(("app/", "lib/", "spec/", "test/")):
            files.append(path)
    return files


def mapped_spec_or_test(path, toolchain, root):
    if toolchain.test is None:
        return None
    test_root = "spec" if toolchain.test == "rspec" else "test"
    suffix = "_spec.rb" if toolchain.test == "rspec" else "_test.rb"
    if path.startswith("lib/"):
        rest = path[len("lib/"):]
        return f"{test_root}/lib/{rest[:-3]}{suffix}"
    parts = path.split("/")
    if path.startswith("app/") and len(parts) >= 3:
        layer, rest = parts[1], "/".join(parts[2:])
        if os.path.isdir(os.path.join(root, test_root, layer)):
            return f"{test_root}/{layer}/{rest[:-3]}{suffix}"
    return None


def degraded_enforcement_note(changed, toolchain, root):
    if toolchain.test is None:
        return None
    layer_files = [f for f in changed if f.startswith(("app/", "lib/"))]
    if not layer_files:
        return None
    if any(mapped_spec_or_test(f, toolchain, root) for f in layer_files):
        return None
    return (
        "rails-do stop hook: test framework detected but no mirrored spec/test "
        "directory found for the changed layer(s) - enforcement produced nothing "
        "for this changeset."
    )


def expected_red_specs(root):
    expected = set()
    rails_do_dir = os.path.join(root, ".rails-do")
    if not os.path.isdir(rails_do_dir):
        return expected
    for ticket in os.listdir(rails_do_dir):
        marker = os.path.join(rails_do_dir, ticket, "tdd-red-expected")
        text = _read_text(marker)
        if text is not None:
            expected.update(line.strip() for line in text.splitlines() if line.strip())
    return expected


def counter_file(session_id):
    os.makedirs(COUNTER_DIR, exist_ok=True)
    return os.path.join(COUNTER_DIR, f"{session_id}.count")


def clear_counter(path):
    if os.path.exists(path):
        os.remove(path)


def run(payload):
    """Core hook logic. Returns the process exit code; writes messages to stderr."""
    session_id = payload.get("session_id", "unknown")
    cwd = payload.get("cwd", os.getcwd())
    root = repo_root(cwd)
    counter_path = counter_file(session_id)

    changed = changed_ruby_files(root)
    if not changed:
        clear_counter(counter_path)
        return 0

    toolchain = detect_toolchain(root, changed)
    degraded_note = degraded_enforcement_note(changed, toolchain, root)
    if degraded_note:
        sys.stderr.write(degraded_note + "\n")

    lint = None
    if toolchain.lint is not None:
        lint = sh([*LINT_COMMANDS[toolchain.lint], *changed], root)

    spec_files = set()
    missing_specs = []
    if toolchain.test is not None:
        test_root = "spec" if toolchain.test == "rspec" else "test"
        for f in changed:
            if f.startswith(f"{test_root}/"):
                if os.path.isfile(os.path.join(root, f)):
                    spec_files.add(f)
                continue
            spec = mapped_spec_or_test(f, toolchain, root)
            if spec is None:
                continue
            if os.path.isfile(os.path.join(root, spec)):
                spec_files.add(spec)
            else:
                missing_specs.append((f, spec))

    expected_red = expected_red_specs(root)
    enforced_specs = spec_files - expected_red

    test_result = None
    if toolchain.test is not None and enforced_specs:
        env = None
        if toolchain.coverage_skip:
            name, value = toolchain.coverage_skip
            env = {name: value}
        test_result = sh(
            [*TEST_COMMANDS[toolchain.test], *sorted(enforced_specs)],
            root,
            env=env,
        )

    failed = (
        (lint is not None and lint.returncode != 0)
        or missing_specs
        or (test_result is not None and test_result.returncode != 0)
        or bool(toolchain.questions)
    )

    if not failed:
        clear_counter(counter_path)
        return 0

    count = 1
    if os.path.exists(counter_path):
        with open(counter_path) as fh:
            count = int(fh.read().strip() or "0") + 1
    with open(counter_path, "w") as fh:
        fh.write(str(count))

    if count > MAX_RETRIES:
        clear_counter(counter_path)
        sys.stderr.write(
            f"rails-do stop hook: verification still failing after {MAX_RETRIES} attempts "
            "on this ticket. Backing off so this doesn't loop forever - a human needs to look "
            "at the last output above.\n"
        )
        return 0

    parts = [f"Verification failed before ending this turn (attempt {count}/{MAX_RETRIES}).\n"]
    if lint is not None and lint.returncode != 0:
        parts.append("lint:\n" + lint.stdout[-2000:])
    if missing_specs:
        parts.append(
            "No spec/test file found for changed source (TDD gate):\n"
            + "\n".join(f"  {src} -> {spec}" for src, spec in missing_specs)
        )
    if test_result is not None and test_result.returncode != 0:
        parts.append("tests:\n" + test_result.stdout[-2000:])
    if toolchain.questions:
        parts.append(
            "Toolchain detection is ambiguous:\n"
            + "\n".join(f"  - {q}" for q in toolchain.questions)
            + "\nAsk the user, then record the answer in .rails-do/toolchain-override "
              "(one \"key: value\" line per answer) before re-running."
        )
    parts.append("Fix and re-run before ending the turn.")
    sys.stderr.write("\n\n".join(parts))
    return 2


def main():
    payload = json.load(sys.stdin)
    sys.exit(run(payload))


if __name__ == "__main__":
    main()
