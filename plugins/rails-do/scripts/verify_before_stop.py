#!/usr/bin/env python3
"""Stop hook: block turn-end if changed Ruby files have no passing spec.

Scope, deliberately: only app/{models,services,jobs,queries,policies,
decorators,presenters,validators,uploaders,mailers,concerns,scopes,
observers,interceptors,tasks}/**.rb, lib/**.rb, and spec/**.rb itself.
Controllers, graphql, views, channels, helpers, config, and db/migrate
are NOT checked here — this codebase doesn't use a 1:1 file-to-spec
convention for those layers, so a missing-spec check there would false-
positive on request/integration specs that legitimately live elsewhere.
Those layers still rely on the rails-do skill's own manual gates.

Backs off after MAX_RETRIES consecutive blocks in the same session so a
genuinely stuck fix can't loop forever without a human looking at it.

Known limitation: the git-status scan is repo-wide, not ticket-scoped.
Unrelated uncommitted Ruby files from other work get linted/tested too
and can block on a failure that has nothing to do with the ticket in
progress. Accepted rather than engineered around, since this runs on a
single personal checkout where one ticket is typically worked at a
time — keep unrelated WIP out of app/lib/spec, or stash it, before
starting a rails-do ticket.
"""
import json
import os
import subprocess
import sys

MAX_RETRIES = 3
COUNTER_DIR = "/tmp/rails-do-stop-hook"

MIRRORED_LAYERS = {
    "models", "services", "jobs", "queries", "policies", "decorators",
    "presenters", "validators", "uploaders", "mailers", "concerns",
    "scopes", "observers", "interceptors", "tasks",
}


def sh(cmd, cwd):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)


def repo_root(cwd):
    r = sh(["git", "rev-parse", "--show-toplevel"], cwd)
    return r.stdout.strip() if r.returncode == 0 else cwd


def changed_ruby_files(root):
    r = sh(["git", "status", "--porcelain"], root)
    files = []
    for line in r.stdout.splitlines():
        path = line[3:].strip()
        if not path.endswith(".rb"):
            continue
        if path.startswith("app/") or path.startswith("lib/") or path.startswith("spec/"):
            files.append(path)
    return files


def mapped_spec(path):
    parts = path.split("/")
    if path.startswith("lib/"):
        rest = "/".join(parts[1:])
        return f"spec/lib/{rest[:-3]}_spec.rb"
    if path.startswith("app/") and len(parts) >= 3:
        layer, rest = parts[1], "/".join(parts[2:])
        if layer in MIRRORED_LAYERS:
            return f"spec/{layer}/{rest[:-3]}_spec.rb"
    return None


def counter_file(session_id):
    os.makedirs(COUNTER_DIR, exist_ok=True)
    return os.path.join(COUNTER_DIR, f"{session_id}.count")


def clear_counter(path):
    if os.path.exists(path):
        os.remove(path)


def main():
    payload = json.load(sys.stdin)
    session_id = payload.get("session_id", "unknown")
    cwd = payload.get("cwd", os.getcwd())
    root = repo_root(cwd)
    counter_path = counter_file(session_id)

    changed = changed_ruby_files(root)
    if not changed:
        clear_counter(counter_path)
        sys.exit(0)

    lint = sh(["bundle", "exec", "standardrb", "--format", "progress", *changed], root)

    spec_files = set()
    missing_specs = []
    for f in changed:
        if f.startswith("spec/"):
            if os.path.isfile(os.path.join(root, f)):
                spec_files.add(f)
            continue
        spec = mapped_spec(f)
        if spec is None:
            continue
        if os.path.isfile(os.path.join(root, spec)):
            spec_files.add(spec)
        else:
            missing_specs.append((f, spec))

    test_result = None
    if spec_files:
        test_result = sh(
            ["env", "SKIP_COVERAGE=1", "bundle", "exec", "rspec",
             *sorted(spec_files), "--format", "progress"],
            root,
        )

    failed = lint.returncode != 0 or missing_specs or (test_result and test_result.returncode != 0)

    if not failed:
        clear_counter(counter_path)
        sys.exit(0)

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
        sys.exit(0)

    parts = [f"Verification failed before ending this turn (attempt {count}/{MAX_RETRIES}).\n"]
    if lint.returncode != 0:
        parts.append("standardrb:\n" + lint.stdout[-2000:])
    if missing_specs:
        parts.append(
            "No spec file found for changed source (TDD gate):\n"
            + "\n".join(f"  {src} -> {spec}" for src, spec in missing_specs)
        )
    if test_result and test_result.returncode != 0:
        parts.append("rspec:\n" + test_result.stdout[-2000:])
    parts.append("Fix and re-run before ending the turn.")
    sys.stderr.write("\n\n".join(parts))
    sys.exit(2)


if __name__ == "__main__":
    main()
