import io
import os
import shutil
import tempfile
import unittest
from collections import namedtuple
from unittest.mock import patch

import verify_before_stop as vbs


class GemfileLockDependenciesTests(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def _write(self, rel, content):
        path = os.path.join(self.root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as fh:
            fh.write(content)

    def test_missing_gemfile_lock_returns_empty_set(self):
        self.assertEqual(vbs._gemfile_lock_dependencies(self.root), set())

    def test_parses_dependencies_section_only(self):
        self._write(
            "Gemfile.lock",
            "GEM\n"
            "  remote: https://rubygems.org/\n"
            "  specs:\n"
            "    rubocop (1.60.0)\n"
            "    standard (1.35.1)\n"
            "      rubocop (>= 1.60.0)\n"
            "\n"
            "DEPENDENCIES\n"
            "  standard\n"
            "  rails\n",
        )
        self.assertEqual(vbs._gemfile_lock_dependencies(self.root), {"standard", "rails"})

    def test_non_utf8_gemfile_lock_returns_empty_set(self):
        path = os.path.join(self.root, "Gemfile.lock")
        with open(path, "wb") as fh:
            fh.write(b"\xff\xfe\x00DEPENDENCIES\n  standard\n")
        self.assertEqual(vbs._gemfile_lock_dependencies(self.root), set())


class ReadToolchainOverrideTests(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def _write(self, rel, content):
        path = os.path.join(self.root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as fh:
            fh.write(content)

    def test_missing_file_returns_empty_dict(self):
        self.assertEqual(vbs._read_toolchain_override(self.root), {})

    def test_parses_key_value_lines(self):
        self._write(
            ".rails-do/toolchain-override",
            "lint: standardrb\ntest: none\ncoverage_skip: SKIP_COVERAGE\n",
        )
        self.assertEqual(
            vbs._read_toolchain_override(self.root),
            {"lint": "standardrb", "test": "none", "coverage_skip": "SKIP_COVERAGE"},
        )

    def test_ignores_malformed_lines(self):
        self._write(".rails-do/toolchain-override", "not a valid line\nlint: rubocop\n")
        self.assertEqual(vbs._read_toolchain_override(self.root), {"lint": "rubocop"})


class DetectLintTests(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def _write(self, rel, content=""):
        path = os.path.join(self.root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as fh:
            fh.write(content)

    def _gemfile(self, deps):
        self._write("Gemfile.lock", "DEPENDENCIES\n" + "\n".join(f"  {d}" for d in deps) + "\n")

    def test_standard_only(self):
        self._gemfile(["standard"])
        questions = []
        self.assertEqual(vbs.detect_lint(self.root, questions, {}), "standardrb")
        self.assertEqual(questions, [])

    def test_rubocop_only(self):
        self._gemfile(["rubocop"])
        questions = []
        self.assertEqual(vbs.detect_lint(self.root, questions, {}), "rubocop")
        self.assertEqual(questions, [])

    def test_neither_declared_no_question(self):
        self._gemfile(["rails"])
        questions = []
        self.assertIsNone(vbs.detect_lint(self.root, questions, {}))
        self.assertEqual(questions, [])

    def test_both_declared_standard_config_breaks_tie(self):
        self._gemfile(["standard", "rubocop"])
        self._write(".standard.yml")
        questions = []
        self.assertEqual(vbs.detect_lint(self.root, questions, {}), "standardrb")
        self.assertEqual(questions, [])

    def test_both_declared_rubocop_config_breaks_tie(self):
        self._gemfile(["standard", "rubocop"])
        self._write(".rubocop.yml")
        questions = []
        self.assertEqual(vbs.detect_lint(self.root, questions, {}), "rubocop")
        self.assertEqual(questions, [])

    def test_both_declared_no_tiebreak_asks(self):
        self._gemfile(["standard", "rubocop"])
        questions = []
        self.assertIsNone(vbs.detect_lint(self.root, questions, {}))
        self.assertEqual(len(questions), 1)
        self.assertIn("standard and rubocop", questions[0])

    def test_override_wins_over_detection(self):
        self._gemfile(["standard", "rubocop"])
        questions = []
        self.assertEqual(
            vbs.detect_lint(self.root, questions, {"lint": "rubocop"}), "rubocop"
        )
        self.assertEqual(questions, [])

    def test_override_none_confirms_no_lint_tool(self):
        self._gemfile(["standard", "rubocop"])
        questions = []
        self.assertIsNone(vbs.detect_lint(self.root, questions, {"lint": "none"}))
        self.assertEqual(questions, [])

    def test_invalid_override_falls_through_to_asking(self):
        self._gemfile(["standard", "rubocop"])
        questions = []
        self.assertIsNone(
            vbs.detect_lint(self.root, questions, {"lint": "eslint"})
        )
        self.assertEqual(len(questions), 1)


class DetectTestTests(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def _write(self, rel, content=""):
        path = os.path.join(self.root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as fh:
            fh.write(content)

    def test_rspec_via_rails_helper(self):
        self._write("spec/rails_helper.rb")
        questions = []
        self.assertEqual(vbs.detect_test(self.root, questions, {}), "rspec")
        self.assertEqual(questions, [])

    def test_rspec_via_spec_helper(self):
        self._write("spec/spec_helper.rb")
        questions = []
        self.assertEqual(vbs.detect_test(self.root, questions, {}), "rspec")
        self.assertEqual(questions, [])

    def test_minitest_via_test_helper(self):
        self._write("test/test_helper.rb")
        questions = []
        self.assertEqual(vbs.detect_test(self.root, questions, {}), "minitest")
        self.assertEqual(questions, [])

    def test_both_helpers_present_asks(self):
        self._write("spec/spec_helper.rb")
        self._write("test/test_helper.rb")
        questions = []
        self.assertIsNone(vbs.detect_test(self.root, questions, {}))
        self.assertEqual(len(questions), 1)
        self.assertIn("Both spec/ and test/", questions[0])

    def test_neither_helper_present_asks(self):
        questions = []
        self.assertIsNone(vbs.detect_test(self.root, questions, {}))
        self.assertEqual(len(questions), 1)
        self.assertIn("No rspec or minitest helper", questions[0])

    def test_override_none_confirms_no_test_framework(self):
        self._write("spec/spec_helper.rb")
        self._write("test/test_helper.rb")
        questions = []
        self.assertIsNone(vbs.detect_test(self.root, questions, {"test": "none"}))
        self.assertEqual(questions, [])


class MappedSpecOrTestTests(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def _mkdir(self, rel):
        os.makedirs(os.path.join(self.root, rel), exist_ok=True)

    def test_rspec_mirrored_layer(self):
        self._mkdir("spec/models")
        toolchain = vbs.Toolchain(test="rspec")
        self.assertEqual(
            vbs.mapped_spec_or_test("app/models/foo.rb", toolchain, self.root),
            "spec/models/foo_spec.rb",
        )

    def test_minitest_mirrored_layer(self):
        self._mkdir("test/models")
        toolchain = vbs.Toolchain(test="minitest")
        self.assertEqual(
            vbs.mapped_spec_or_test("app/models/foo.rb", toolchain, self.root),
            "test/models/foo_test.rb",
        )

    def test_unmirrored_layer_returns_none(self):
        self._mkdir("spec/unit")
        toolchain = vbs.Toolchain(test="rspec")
        self.assertIsNone(vbs.mapped_spec_or_test("app/models/foo.rb", toolchain, self.root))

    def test_lib_file_mapping_rspec(self):
        toolchain = vbs.Toolchain(test="rspec")
        self.assertEqual(
            vbs.mapped_spec_or_test("lib/foo/bar.rb", toolchain, self.root),
            "spec/lib/foo/bar_spec.rb",
        )

    def test_no_test_framework_returns_none(self):
        self._mkdir("spec/models")
        toolchain = vbs.Toolchain(test=None)
        self.assertIsNone(vbs.mapped_spec_or_test("app/models/foo.rb", toolchain, self.root))


class DegradedEnforcementNoteTests(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def _mkdir(self, rel):
        os.makedirs(os.path.join(self.root, rel), exist_ok=True)

    def test_fires_when_confident_test_framework_but_no_mirrored_dirs(self):
        self._mkdir("spec/unit")
        toolchain = vbs.Toolchain(test="rspec")
        note = vbs.degraded_enforcement_note(["app/models/foo.rb"], toolchain, self.root)
        self.assertIsNotNone(note)
        self.assertIn("no mirrored spec/test directory", note)

    def test_absent_when_some_file_maps(self):
        self._mkdir("spec/models")
        toolchain = vbs.Toolchain(test="rspec")
        note = vbs.degraded_enforcement_note(
            ["app/models/foo.rb", "app/controllers/foo_controller.rb"], toolchain, self.root
        )
        self.assertIsNone(note)

    def test_absent_when_no_test_framework_detected(self):
        toolchain = vbs.Toolchain(test=None)
        note = vbs.degraded_enforcement_note(["app/models/foo.rb"], toolchain, self.root)
        self.assertIsNone(note)

    def test_absent_when_no_layer_files_changed(self):
        toolchain = vbs.Toolchain(test="rspec")
        note = vbs.degraded_enforcement_note(["spec/models/foo_spec.rb"], toolchain, self.root)
        self.assertIsNone(note)


class DetectCoverageSkipTests(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def _write(self, rel, content):
        path = os.path.join(self.root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as fh:
            fh.write(content)

    def test_no_simplecov_reference(self):
        self._write("spec/spec_helper.rb", "RSpec.configure { |c| }\n")
        questions = []
        self.assertIsNone(vbs.detect_coverage_skip(self.root, questions, {}))
        self.assertEqual(questions, [])

    def test_opt_in_guard_leaves_unset(self):
        self._write(
            "spec/spec_helper.rb",
            "if ENV['COVERAGE']\n  SimpleCov.start 'rails'\nend\n",
        )
        questions = []
        self.assertIsNone(vbs.detect_coverage_skip(self.root, questions, {}))
        self.assertEqual(questions, [])

    def test_opt_out_guard_returns_skip_var(self):
        self._write(
            "spec/spec_helper.rb",
            "unless ENV['SKIP_COVERAGE']\n  SimpleCov.start 'rails'\nend\n",
        )
        questions = []
        self.assertEqual(
            vbs.detect_coverage_skip(self.root, questions, {}), ("SKIP_COVERAGE", "1")
        )
        self.assertEqual(questions, [])

    def test_unresolvable_guard_asks(self):
        self._write(
            "spec/spec_helper.rb",
            "if Rails.env.test?\n  SimpleCov.start 'rails'\nend\n",
        )
        questions = []
        self.assertIsNone(vbs.detect_coverage_skip(self.root, questions, {}))
        self.assertEqual(len(questions), 1)
        self.assertIn("SimpleCov", questions[0])

    def test_invalid_extracted_name_asks(self):
        self._write(
            "spec/spec_helper.rb",
            "unless ENV['skip_coverage']\n  SimpleCov.start 'rails'\nend\n",
        )
        questions = []
        self.assertIsNone(vbs.detect_coverage_skip(self.root, questions, {}))
        self.assertEqual(len(questions), 1)

    def test_non_utf8_helper_file_returns_none(self):
        path = os.path.join(self.root, "spec", "spec_helper.rb")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as fh:
            fh.write(b"\xff\xfe\x00SimpleCov.start\n")
        questions = []
        self.assertIsNone(vbs.detect_coverage_skip(self.root, questions, {}))
        self.assertEqual(questions, [])

    def test_multiple_guards_in_window_picks_the_one_nearest_the_call(self):
        self._write(
            "spec/spec_helper.rb",
            "if ENV['OTHER_FLAG']\n"
            "  puts 'unrelated'\n"
            "end\n"
            "unless ENV['SKIP_COVERAGE']\n"
            "  SimpleCov.start 'rails'\n"
            "end\n",
        )
        questions = []
        self.assertEqual(
            vbs.detect_coverage_skip(self.root, questions, {}), ("SKIP_COVERAGE", "1")
        )
        self.assertEqual(questions, [])

    def test_override_wins_over_detection(self):
        self._write(
            "spec/spec_helper.rb",
            "if Rails.env.test?\n  SimpleCov.start 'rails'\nend\n",
        )
        questions = []
        self.assertEqual(
            vbs.detect_coverage_skip(self.root, questions, {"coverage_skip": "SKIP_COV"}),
            ("SKIP_COV", "1"),
        )
        self.assertEqual(questions, [])

    def test_override_none_confirms_no_skip_var(self):
        self._write(
            "spec/spec_helper.rb",
            "if Rails.env.test?\n  SimpleCov.start 'rails'\nend\n",
        )
        questions = []
        self.assertIsNone(
            vbs.detect_coverage_skip(self.root, questions, {"coverage_skip": "none"})
        )
        self.assertEqual(questions, [])


class TestEnforcementCouldApplyTests(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def _mkdir(self, rel):
        os.makedirs(os.path.join(self.root, rel), exist_ok=True)

    def test_true_for_lib_file(self):
        self.assertTrue(vbs._test_enforcement_could_apply(["lib/foo.rb"], self.root))

    def test_true_for_spec_or_test_file_directly(self):
        self.assertTrue(
            vbs._test_enforcement_could_apply(["spec/models/foo_spec.rb"], self.root)
        )

    def test_true_when_mirrored_spec_dir_exists_for_layer(self):
        self._mkdir("spec/models")
        self.assertTrue(
            vbs._test_enforcement_could_apply(["app/models/foo.rb"], self.root)
        )

    def test_true_when_mirrored_test_dir_exists_for_layer(self):
        self._mkdir("test/models")
        self.assertTrue(
            vbs._test_enforcement_could_apply(["app/models/foo.rb"], self.root)
        )

    def test_false_for_unenforced_layer_with_no_mirrored_dir(self):
        self.assertFalse(
            vbs._test_enforcement_could_apply(["app/controllers/foo_controller.rb"], self.root)
        )


FakeResult = namedtuple("FakeResult", ["returncode", "stdout"])


def make_fake_sh(status_lines, lint_ok=True, test_ok=True):
    def fake_sh(cmd, cwd, env=None):
        if cmd[:2] == ["git", "rev-parse"]:
            return FakeResult(0, cwd + "\n")
        if cmd[:2] == ["git", "status"]:
            return FakeResult(0, "\n".join(status_lines) + "\n" if status_lines else "")
        if cmd[2] in ("standardrb", "rubocop"):
            return FakeResult(0 if lint_ok else 1, "" if lint_ok else "offense detected\n")
        return FakeResult(
            0 if test_ok else 1,
            "3 examples, 0 failures\n" if test_ok else "1 example, 1 failure\n",
        )
    return fake_sh


class RunIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.session_id = f"test-{id(self)}"
        self.counter_path = os.path.join(vbs.COUNTER_DIR, f"{self.session_id}.count")

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)
        if os.path.exists(self.counter_path):
            os.remove(self.counter_path)

    def _write(self, rel, content=""):
        path = os.path.join(self.root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as fh:
            fh.write(content)

    def _rspec_repo(self):
        self._write("Gemfile.lock", "DEPENDENCIES\n  standard\n  rspec-rails\n")
        self._write("spec/spec_helper.rb", "RSpec.configure { |c| }\n")
        self._write(".standard.yml")
        os.makedirs(os.path.join(self.root, "spec", "models"), exist_ok=True)

    def _payload(self):
        return {"session_id": self.session_id, "cwd": self.root}

    def test_no_changed_files_exits_0(self):
        with patch.object(vbs, "sh", make_fake_sh([])):
            self.assertEqual(vbs.run(self._payload()), 0)

    def test_lint_and_test_pass_exits_0(self):
        self._rspec_repo()
        self._write("app/models/foo.rb", "class Foo\nend\n")
        self._write("spec/models/foo_spec.rb", "RSpec.describe(Foo) {}\n")
        with patch.object(vbs, "sh", make_fake_sh(["?? app/models/foo.rb"])):
            self.assertEqual(vbs.run(self._payload()), 0)

    def test_missing_spec_blocks(self):
        self._rspec_repo()
        self._write("app/models/foo.rb", "class Foo\nend\n")
        with patch.object(vbs, "sh", make_fake_sh(["?? app/models/foo.rb"])):
            self.assertEqual(vbs.run(self._payload()), 2)

    def test_tdd_red_expected_excluded(self):
        self._rspec_repo()
        self._write("app/models/foo.rb", "class Foo\nend\n")
        self._write("spec/models/foo_spec.rb", "RSpec.describe(Foo) {}\n")
        self._write(".rails-do/TICKET-1/tdd-red-expected", "spec/models/foo_spec.rb\n")
        with patch.object(vbs, "sh", make_fake_sh(["?? app/models/foo.rb"], test_ok=False)):
            self.assertEqual(vbs.run(self._payload()), 0)

    def test_max_retries_backoff(self):
        self._rspec_repo()
        self._write("app/models/foo.rb", "class Foo\nend\n")
        with patch.object(vbs, "sh", make_fake_sh(["?? app/models/foo.rb"])):
            for _ in range(vbs.MAX_RETRIES):
                self.assertEqual(vbs.run(self._payload()), 2)
            self.assertEqual(vbs.run(self._payload()), 0)

    def test_ambiguous_toolchain_blocks_with_a_question(self):
        os.makedirs(os.path.join(self.root, "spec", "models"), exist_ok=True)
        self._write("app/models/foo.rb", "class Foo\nend\n")
        with patch.object(vbs, "sh", make_fake_sh(["?? app/models/foo.rb"])), \
             patch("sys.stderr", new_callable=io.StringIO) as fake_err:
            result = vbs.run(self._payload())
            self.assertEqual(result, 2)
            self.assertIn("ambiguous", fake_err.getvalue())
            self.assertIn("No rspec or minitest helper", fake_err.getvalue())

    def test_override_file_resolves_ambiguity_without_blocking(self):
        os.makedirs(os.path.join(self.root, "spec", "models"), exist_ok=True)
        self._write("app/models/foo.rb", "class Foo\nend\n")
        self._write(".rails-do/toolchain-override", "lint: none\ntest: none\n")
        with patch.object(vbs, "sh", make_fake_sh(["?? app/models/foo.rb"])):
            self.assertEqual(vbs.run(self._payload()), 0)

    def test_ambiguous_toolchain_survives_max_retries_then_backs_off(self):
        os.makedirs(os.path.join(self.root, "spec", "models"), exist_ok=True)
        self._write("app/models/foo.rb", "class Foo\nend\n")
        with patch.object(vbs, "sh", make_fake_sh(["?? app/models/foo.rb"])):
            for _ in range(vbs.MAX_RETRIES):
                self.assertEqual(vbs.run(self._payload()), 2)
            self.assertEqual(vbs.run(self._payload()), 0)
            # No override was ever written, so the next session_id (fresh counter)
            # asks again from scratch rather than staying silently resolved.
            self.assertEqual(vbs.run(self._payload()), 2)

    def test_unenforced_layer_change_does_not_trigger_a_question(self):
        # Only a controller changed, and controllers are explicitly not
        # enforced (no spec/controllers or test/controllers dir exists) - the
        # repo has no test helper either, but the question would be useless
        # for this changeset, so it must not block.
        self._write("app/controllers/foo_controller.rb", "class FooController\nend\n")
        with patch.object(vbs, "sh", make_fake_sh(["?? app/controllers/foo_controller.rb"])):
            self.assertEqual(vbs.run(self._payload()), 0)

    def test_minitest_changed_test_file_alone_is_tracked(self):
        # Only the test file changed (app/models/foo.rb already existed, untouched
        # this session) — this is the case that actually depends on
        # changed_ruby_files recognizing the "test/" prefix. Without that fix,
        # `changed` would be empty and run() would exit 0 before ever invoking the
        # (failing) test command; asserting on returncode 2 makes the fix's absence
        # visibly fail this test, rather than passing either way.
        self._write("Gemfile.lock", "DEPENDENCIES\n  rubocop\n")
        self._write("test/test_helper.rb")
        os.makedirs(os.path.join(self.root, "test", "models"), exist_ok=True)
        self._write("test/models/foo_test.rb", "class FooTest < Minitest::Test\nend\n")
        with patch.object(
            vbs, "sh",
            make_fake_sh(["?? test/models/foo_test.rb"], test_ok=False),
        ):
            self.assertEqual(vbs.run(self._payload()), 2)

    def test_renamed_file_uses_new_path_not_the_arrow_line(self):
        self._rspec_repo()
        self._write("app/models/foo.rb", "class Foo\nend\n")
        self._write("spec/models/foo_spec.rb", "RSpec.describe(Foo) {}\n")
        with patch.object(
            vbs, "sh",
            make_fake_sh(["R  app/models/bar.rb -> app/models/foo.rb"]),
        ):
            self.assertEqual(vbs.run(self._payload()), 0)

    def test_malformed_tdd_red_expected_does_not_crash(self):
        self._rspec_repo()
        self._write("app/models/foo.rb", "class Foo\nend\n")
        self._write("spec/models/foo_spec.rb", "RSpec.describe(Foo) {}\n")
        marker = os.path.join(self.root, ".rails-do", "TICKET-1", "tdd-red-expected")
        os.makedirs(os.path.dirname(marker), exist_ok=True)
        with open(marker, "wb") as fh:
            fh.write(b"\xff\xfe\x00spec/models/foo_spec.rb\n")
        with patch.object(vbs, "sh", make_fake_sh(["?? app/models/foo.rb"])):
            self.assertEqual(vbs.run(self._payload()), 0)


if __name__ == "__main__":
    unittest.main()
