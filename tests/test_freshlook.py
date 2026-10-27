"""Tests for freshlook: metrics on a fixture repo, duplicate finder, dead-file finder, prompt assembly, run --dry-run, and the run path
with a stand-in claude that records what the auditor process can see (environment, config dir, working copy)."""
import importlib.machinery
import importlib.util
import json
import os
import signal
import stat
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "bin", "freshlook")


def load():
    loader = importlib.machinery.SourceFileLoader("freshlook_mod", BIN)
    spec = importlib.util.spec_from_loader("freshlook_mod", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


FL = load()


def write(root, rel, text):
    path = os.path.join(root, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def make_fixture(root):
    write(root, "app/core.py", '"""Core logic."""\nfrom app import util\n\n\ndef compute(x):\n    return util.double(x)\n')
    write(root, "app/util.py", 'def double(x):\n    return 2 * x\n')
    write(root, "app/orphan.py", 'def lonely():\n    return 1\n')
    write(root, "app/__init__.py", "")
    write(root, "tools/run.py", '#!/usr/bin/env python3\nprint("hi")\n')
    write(root, "tests/test_core.py", 'from app import core\n\n\ndef test_compute():\n    assert core.compute(2) == 4\n')
    git_init(root)


class T(unittest.TestCase):
    def test_metrics_on_fixture(self):
        with tempfile.TemporaryDirectory() as d:
            make_fixture(d)
            m = FL.compute_metrics(d)
            self.assertEqual(set(m["loc_by_top_dir"]), {"app", "tools", "tests"})
            self.assertEqual(m["loc_tests"], 3)
            self.assertGreater(m["test_to_code_ratio"], 0)
            self.assertEqual(sum(w["commits"] for w in m["history"]["weeks"].values()), 1)
            self.assertEqual(m["largest_functions"][0]["lines"], 2)
            md = FL.render_summary(m)
            self.assertIn("Lines of code by top-level directory", md)

    def test_duplicate_finder(self):
        items = [
            {"kind": "function", "name": "install_package", "file": "a.py:1", "doc": "Install the package into the target directory."},
            {"kind": "function", "name": "install_packages", "file": "b.py:1", "doc": "Unrelated words here for sure."},
            {"kind": "function", "name": "render_page", "file": "c.py:1", "doc": "Fetch the rows from the database and print a table of them."},
            {"kind": "function", "name": "show_table", "file": "d.py:1", "doc": "Fetch the rows from the database and print a table of them."},
            {"kind": "function", "name": "zebra", "file": "e.py:1", "doc": ""},
        ]
        names = [sorted(x["name"] for x in c["members"]) for c in FL.find_duplicates(items)["clusters"]]
        self.assertIn(["install_package", "install_packages"], names)
        self.assertIn(["render_page", "show_table"], names)
        self.assertEqual(len(names), 2)

    def test_mechanism_scan_catches_what_name_clustering_misses(self):
        # the self-audit ranked deleting this scan first; it is kept because it is the only signal for scattered deploy scripts
        items = [{"kind": "file", "name": n, "file": f, "doc": ""} for n, f in
                 (("deploy", "deploy.sh"), ("deploy_prod", "ops/deploy_prod.py"), ("deploy-staging", "scripts/deploy-staging.sh"), ("app", "app.py"))]
        found = FL.find_duplicates(items)
        self.assertEqual(found["clusters"], [])
        self.assertEqual([(m["mechanism"], m["count"]) for m in found["mechanisms"]], [("deploy", 3)])

    def test_metrics_command_writes_json_and_summary(self):
        with tempfile.TemporaryDirectory() as d:
            make_fixture(d)
            out = os.path.join(d, "out")
            r = subprocess.run([sys.executable, BIN, "metrics", d, "--out", out], capture_output=True, text=True, timeout=60)
            self.assertEqual(r.returncode, 0, r.stderr)
            with open(os.path.join(out, "metrics.md"), encoding="utf-8") as f:
                self.assertEqual(f.read(), r.stdout[:-1])
            with open(os.path.join(out, "metrics.json"), encoding="utf-8") as f:
                self.assertEqual(json.load(f)["loc_tests"], 3)

    def test_set_writable_round_trip(self):
        with tempfile.TemporaryDirectory() as d:
            write(d, "a/b/c.py", "x\n")
            FL.set_writable(d, False)
            self.assertEqual(FL.writable_paths(d), [])
            FL.set_writable(d, True)
            self.assertTrue(os.access(os.path.join(d, "a", "b"), os.W_OK))

    def test_dead_file_finder(self):
        with tempfile.TemporaryDirectory() as d:
            make_fixture(d)
            files = FL.list_files(d)
            dead = [x["file"] for x in FL.dead_python_files(d, files)]
            self.assertEqual(dead, ["app/orphan.py"])

    def test_prompt_assembly(self):
        prompt = FL.assemble_prompt("Make widgets for Ann Example.", "- code lines: 42")
        self.assertIn("Make widgets for Ann Example.", prompt)
        self.assertIn("- code lines: 42", prompt)
        self.assertNotIn("{{", prompt)
        for heading in ("1. What the project is for", "2. Top 10 sources of complexity", "3. What to delete or merge",
                        "4. What the intent asks for", "5. What would a new maintainer trip on first"):
            self.assertIn(heading, prompt)

    def test_run_dry_run(self):
        with tempfile.TemporaryDirectory() as d:
            make_fixture(d)
            intent = os.path.join(d, "intent.md")
            write(d, "intent.md", "A tiny app.\n")
            r = subprocess.run([sys.executable, BIN, "run", d, "--intent", intent, "--model", "sonnet", "--dry-run"],
                               check=False, capture_output=True, text=True, timeout=60, env=dict(os.environ, FRESHLOOK_CLAUDE="claude"))
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("command: claude -p --output-format json", r.stdout)
            self.assertIn("--model sonnet", r.stdout)
            self.assertIn("--tools Read,Grep,Glob ", r.stdout)
            self.assertIn("CLAUDE_CONFIG_DIR=<fresh empty temp directory>", r.stdout)
            self.assertFalse(os.path.exists(os.path.join(d, "freshlook")))

    def test_list_files_skips_directories_not_files_named_like_them(self):
        # bin/freshlook was dropped from metrics because "freshlook" (the output dir) is in SKIP_DIRS: found by running on itself
        with tempfile.TemporaryDirectory() as d:
            write(d, "bin/freshlook", "#!/usr/bin/env python3\nprint(1)\n")
            write(d, "freshlook/metrics.md", "x\n")
            self.assertEqual(FL.list_files(d), ["bin/freshlook"])
            git_init(d)
            subprocess.run(["git", "-C", d, "add", "-f", "freshlook"], check=True, capture_output=True, timeout=60)
            self.assertEqual(FL.list_files(d), ["bin/freshlook"])

    def test_single_week_history_has_no_half_averages(self):
        with tempfile.TemporaryDirectory() as d:
            make_fixture(d)
            md = FL.render_summary(FL.compute_metrics(d))
            self.assertIn("Weeks with commits: 1", md)
            self.assertNotIn("(first half)", md)

    def test_build_command_guards_and_tools(self):
        cmd = FL.build_command("opus", claude_bin="claude", max_turns=12, budget=1.5)
        self.assertEqual(cmd[cmd.index("--max-turns") + 1], "12")
        self.assertEqual(cmd[cmd.index("--max-budget-usd") + 1], "1.5")
        self.assertEqual(cmd[cmd.index("--tools") + 1], "Read,Grep,Glob")
        self.assertEqual(cmd[cmd.index("--permission-mode") + 1], "dontAsk")
        for flag in ("--restricted", "--strict-mcp-config", "--no-session-persistence"):
            self.assertIn(flag, cmd)
        self.assertNotIn("Bash", " ".join(cmd))
        self.assertNotIn("--setting-sources", cmd)
        bare = FL.build_command("", claude_bin="claude")
        self.assertNotIn("--max-turns", bare)
        self.assertNotIn("--max-budget-usd", bare)
        self.assertNotIn("--model", bare)

    def test_clean_env_is_an_allowlist(self):
        parent = {"PATH": "/bin", "HOME": "/home/ann", "https_proxy": "http://proxy:3128", "ANTHROPIC_API_KEY": "k", "AWS_REGION": "us-east-1",
                  "CLAUDE_CODE_OAUTH_TOKEN": "t", "CLAUDE_CONFIG_DIR": "/home/ann/.claude", "CLAUDECODE": "1", "CLAUDE_CODE_SESSION_ID": "s",
                  "CLAUDE_CODE_ADDITIONAL_DIRECTORIES_CLAUDE_MD": "1", "CLAUDE_CODE_SYNC_PLUGINS": "1", "GITHUB_TOKEN": "g", "PYTHONPATH": "/x"}
        env = FL.clean_env(parent, "/tmp/clean", "/tmp/work/tmp")
        self.assertEqual(env["CLAUDE_CONFIG_DIR"], "/tmp/clean")
        self.assertEqual((env["TMPDIR"], env["TMP"], env["TEMP"]), ("/tmp/work/tmp",) * 3)
        for kept in ("PATH", "HOME", "https_proxy", "ANTHROPIC_API_KEY", "CLAUDE_CODE_OAUTH_TOKEN"):
            self.assertEqual(env[kept], parent[kept])
        for dropped in ("CLAUDECODE", "CLAUDE_CODE_SESSION_ID", "CLAUDE_CODE_ADDITIONAL_DIRECTORIES_CLAUDE_MD", "CLAUDE_CODE_SYNC_PLUGINS",
                        "GITHUB_TOKEN", "PYTHONPATH", "AWS_REGION"):
            self.assertNotIn(dropped, env)
        bedrock = FL.clean_env(dict(parent, CLAUDE_CODE_USE_BEDROCK="1"), "/tmp/clean", "/tmp/work/tmp")
        self.assertEqual(bedrock["AWS_REGION"], "us-east-1", "AWS variables pass only when Bedrock is switched on")

    def test_config_problems(self):
        with tempfile.TemporaryDirectory() as cfg:
            self.assertEqual(FL.config_problems(cfg, {}), [])
            write(cfg, ".credentials.json", "{}")
            write(cfg, ".claude.json", "{}")
            write(cfg, "plugins/store/builtin.json", "{}")
            os.makedirs(os.path.join(cfg, "projects", "-src", "memory"))
            self.assertEqual(FL.config_problems(cfg, {}), [], "a login, built-in plugin store and empty memory dir are allowed")
            self.assertEqual(len(FL.config_problems(cfg, {"CLAUDE_CONFIG_DIR": cfg})), 1, "the user's real config dir is refused")
            for rel in ("CLAUDE.md", "settings.json", "skills/x/SKILL.md", "agents/a.md", "plugins/synced/p.json", "projects/-src/memory/MEMORY.md"):
                write(cfg, rel, "x")
            found = "\n".join(FL.config_problems(cfg, {}))
            for name in ("CLAUDE.md", "settings.json", "skills", "agents", "synced", "memory"):
                self.assertIn(name, found)

    def test_readonly_copy_strips_instructions_and_symlinks(self):
        with tempfile.TemporaryDirectory() as d, tempfile.TemporaryDirectory() as outside:
            write(outside, "CLAUDE.md", "secret instructions\n")
            for git_repo in (True, False):
                repo, dest = os.path.join(d, "repo%d" % git_repo), os.path.join(d, "copy%d" % git_repo)
                write(repo, "app/main.py", "print(1)\n")
                write(repo, "bin/freshlook", "#!/bin/sh\n")
                write(repo, "CLAUDE.md", "team notes\n")
                write(repo, "sub/AGENTS.md", "more notes\n")
                write(repo, ".claude/settings.json", '{"hooks": {}}\n')
                if hasattr(os, "symlink"):
                    os.symlink(os.path.join(outside, "CLAUDE.md"), os.path.join(repo, "notes.md"))
                if git_repo:
                    git_init(repo)
                FL.make_readonly_copy(repo, dest)
                files = sorted(FL.list_files(dest))
                self.assertEqual(files, ["app/main.py", "bin/freshlook"], "git=%s" % git_repo)
                self.assertEqual(FL.writable_paths(dest), [])
                self.assertEqual(FL.tree_digest(dest), FL.tree_digest(dest))
                self.assertTrue(FL.remove_tree(dest))
                self.assertFalse(os.path.exists(dest))

    def test_tree_digest_sees_any_change(self):
        with tempfile.TemporaryDirectory() as d:
            write(d, "a.py", "x = 1\n")
            before = FL.tree_digest(d)
            write(d, "a.py", "x = 2\n")
            self.assertNotEqual(before, FL.tree_digest(d))
            changed = FL.tree_digest(d)
            os.makedirs(os.path.join(d, "new"))
            self.assertNotEqual(changed, FL.tree_digest(d))

    def test_parse_result(self):
        ok = json.dumps({"type": "result", "is_error": False, "result": "## 1. What the project is for", "num_turns": 3})
        r, err = FL.parse_result(0, ok, "")
        self.assertIsNone(err)
        self.assertEqual(r["num_turns"], 3)
        capped = json.dumps({"is_error": True, "subtype": "error_max_turns", "errors": ["Reached maximum number of turns (1)"], "result": ""})
        r, err = FL.parse_result(1, capped, "")
        self.assertIsNone(r)
        self.assertIn("error_max_turns", err)
        self.assertIn("Reached maximum number of turns", err)
        r, err = FL.parse_result(1, "", "Invalid API key")
        self.assertIn("Invalid API key", err)


FAKE_CLAUDE = r"""#!%(python)s
import json, os, subprocess, sys, time
log, mode = %(log)r, %(mode)r
prompt = sys.stdin.read()
cfg = os.environ.get("CLAUDE_CONFIG_DIR", "")
with open(os.path.join(os.environ["TMPDIR"], "cli-scratch"), "w") as f:  # the real CLI writes TMPDIR/claude-<uid>/...
    f.write("x")
cwd_files = sorted(os.path.relpath(os.path.join(d, f), ".") for d, _, fs in os.walk(".") for f in fs)
with open(log, "w") as f:
    json.dump({"pid": os.getpid(), "argv": sys.argv[1:], "env": sorted(os.environ), "cfg": cfg, "cfg_files": os.listdir(cfg) if cfg else None,
               "cwd_files": cwd_files, "prompt_has_intent": "INTENT-MARKER" in prompt}, f)
if mode in ("hang", "hang_child"):
    child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(120)"])
    with open(log + ".pids", "w") as f:
        f.write("%%d %%d" %% (os.getpid(), child.pid))
    time.sleep(120)
if mode == "sync":
    os.makedirs(os.path.join(cfg, "skills", "synced"))
    with open(os.path.join(cfg, "skills", "synced", "SKILL.md"), "w") as f:
        f.write("a skill from the user's account\n")
if mode == "tamper":
    os.chmod("app", 0o755)
    os.chmod(os.path.join("app", "core.py"), 0o644)  # the copy is read-only; a non-root tamperer must undo that first
    with open(os.path.join("app", "core.py"), "a") as f:
        f.write("# changed\n")
if mode == "max_turns":
    print(json.dumps({"type": "result", "is_error": True, "subtype": "error_max_turns", "errors": ["Reached maximum number of turns (9)"],
                      "num_turns": 10, "result": ""}))
    sys.exit(1)
print(json.dumps({"type": "result", "subtype": "success", "is_error": False, "num_turns": 7, "total_cost_usd": 0.4321,
                  "result": "## 1. What the project is for\n- widgets\n",
                  "usage": {"input_tokens": 11, "output_tokens": 22, "cache_read_input_tokens": 33, "cache_creation_input_tokens": 44},
                  "modelUsage": {"claude-test-model": {"outputTokens": 22}},
                  "permission_denials": [{"tool_name": "Read", "tool_input": {"file_path": "/etc/hostname"}}]}))
"""


def git_init(root):
    env = dict(os.environ, GIT_AUTHOR_NAME="Ann Example", GIT_AUTHOR_EMAIL="ann@example.invalid",
               GIT_COMMITTER_NAME="Ann Example", GIT_COMMITTER_EMAIL="ann@example.invalid")
    for cmd in (["init", "-q", "-b", "main"], ["add", "."], ["commit", "-q", "-m", "fixture"]):
        subprocess.run(["git", "-C", root, *cmd], check=True, env=env, capture_output=True, timeout=60)


def alive(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    try:
        with open("/proc/%d/status" % pid) as f:
            return "\nState:\tZ" not in f.read()
    except OSError:
        return True


@unittest.skipUnless(os.name == "posix", "the stand-in claude is a POSIX script")
class Run(unittest.TestCase):
    """`freshlook run` end to end with a stand-in claude: what the auditor sees, guards, failure, timeout, Ctrl-C and cleanup."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = self.tmp.name
        self.repo = os.path.join(self.d, "repo")
        os.makedirs(self.repo)
        make_fixture(self.repo)
        write(self.repo, "CLAUDE.md", "team notes the auditor must not see\n")
        subprocess.run(["git", "-C", self.repo, "add", "."], check=True, capture_output=True, timeout=60)
        subprocess.run(["git", "-C", self.repo, "-c", "user.name=A", "-c", "user.email=a@example.invalid", "commit", "-qm", "notes"],
                       check=True, capture_output=True, timeout=60)
        self.intent = os.path.join(self.d, "intent.md")
        write(self.d, "intent.md", "INTENT-MARKER: a tiny app.\n")
        self.tmpdir = os.path.join(self.d, "tmp")
        os.makedirs(self.tmpdir)
        self.log = os.path.join(self.d, "fake.json")
        self.out = os.path.join(self.d, "out")

    def tearDown(self):
        FL.remove_tree(self.d)
        self.tmp.cleanup()

    def fake(self, mode="ok"):
        path = os.path.join(self.d, "fake-claude")
        with open(path, "w") as f:
            f.write(FAKE_CLAUDE % {"python": sys.executable, "log": self.log, "mode": mode})
        os.chmod(path, 0o755)
        return path

    def env(self, mode="ok", **extra):
        return dict(os.environ, FRESHLOOK_CLAUDE=self.fake(mode), TMPDIR=self.tmpdir, CLAUDE_CODE_SESSION_ID="parent-session", CLAUDECODE="1",
                    CLAUDE_CODE_ADDITIONAL_DIRECTORIES_CLAUDE_MD="1", **extra)

    def args(self, *more):
        return [sys.executable, BIN, "run", self.repo, "--intent", self.intent, "--out", self.out, *more]

    def seen(self):
        with open(self.log) as f:
            return json.load(f)

    def assert_cleaned(self):
        self.assertEqual(os.listdir(self.tmpdir), [], "temp copy and config dir must be removed")

    def test_auditor_sees_only_the_clean_copy_and_report_has_header(self):
        r = subprocess.run(self.args("--model", "opus", "--max-turns", "9", "--budget", "2"), capture_output=True, text=True, timeout=120,
                           env=self.env())
        self.assertEqual(r.returncode, 0, r.stderr)
        s = self.seen()
        self.assertTrue(s["prompt_has_intent"])
        self.assertEqual(s["cfg_files"], [], "the config dir starts empty: no CLAUDE.md, settings, hooks or memory")
        self.assertFalse(s["cfg"].startswith(os.path.expanduser("~")), s["cfg"])
        for leaked in ("CLAUDE_CODE_SESSION_ID", "CLAUDECODE", "CLAUDE_CODE_ADDITIONAL_DIRECTORIES_CLAUDE_MD"):
            self.assertNotIn(leaked, s["env"])
        self.assertNotIn("CLAUDE.md", [os.path.basename(p) for p in s["cwd_files"]])
        self.assertIn("app/core.py", s["cwd_files"])
        self.assertEqual(s["argv"][s["argv"].index("--max-turns") + 1], "9")
        self.assertEqual(s["argv"][s["argv"].index("--max-budget-usd") + 1], "2")
        with open(r.stdout.strip()) as f:
            report = f.read()
        self.assertIn("Model: claude-test-model (requested: opus).", report)
        self.assertIn("Turns: 7 (limit 9).", report)
        self.assertRegex(report, r"Wall time: \d+ s \(limit 1800 s\)")
        self.assertIn("Cost: $0.43", report)
        self.assertIn("budget $2.00", report)
        self.assertIn("Tokens: 11 input, 22 output, 33 cache read, 44 cache write. Denied tool calls: 1 (Read).", report)
        self.assertIn("## 1. What the project is for", report)
        self.assertIn("<!-- freshlook-metrics:", report)
        self.assert_cleaned()

    def test_turn_limit_failure_is_reported_and_cleaned(self):
        r = subprocess.run(self.args(), capture_output=True, text=True, timeout=120, env=self.env("max_turns"))
        self.assertEqual(r.returncode, 3)
        self.assertIn("error_max_turns", r.stderr)
        self.assertFalse(any(n.startswith("report-") for n in os.listdir(self.out)))
        self.assert_cleaned()

    def test_tampered_copy_discards_report(self):
        r = subprocess.run(self.args(), capture_output=True, text=True, timeout=120, env=self.env("tamper"))
        self.assertEqual(r.returncode, 4, r.stderr)
        self.assertIn("changed its read-only copy", r.stderr)
        self.assert_cleaned()

    def test_config_synced_in_during_run_discards_report(self):
        r = subprocess.run(self.args(), capture_output=True, text=True, timeout=120, env=self.env("sync"))
        self.assertEqual(r.returncode, 4, r.stderr)
        self.assertIn("skills", r.stderr)
        self.assertFalse(any(n.startswith("report-") for n in os.listdir(self.out)))
        self.assert_cleaned()

    def test_dirty_persistent_config_dir_is_refused(self):
        cfg = os.path.join(self.d, "persistent")
        write(cfg, "CLAUDE.md", "my personal instructions\n")
        r = subprocess.run(self.args("--config-dir", cfg), capture_output=True, text=True, timeout=120, env=self.env())
        self.assertEqual(r.returncode, 4)
        self.assertIn("CLAUDE.md", r.stderr)
        self.assertFalse(os.path.exists(self.log), "claude must not be started")

    def test_real_config_dir_is_refused(self):
        cfg = os.path.join(self.d, "real")
        os.makedirs(cfg)
        r = subprocess.run(self.args("--config-dir", cfg), capture_output=True, text=True, timeout=120, env=self.env(CLAUDE_CONFIG_DIR=cfg))
        self.assertEqual(r.returncode, 4)
        self.assertIn("real Claude config directory", r.stderr)

    def test_bad_guard_values_are_usage_errors(self):
        for bad in (["--max-turns", "-1"], ["--budget", "-2"], ["--timeout", "0"]):
            r = subprocess.run(self.args(*bad), capture_output=True, text=True, timeout=60, env=self.env())
            self.assertEqual(r.returncode, 2, bad)

    def wait_for_pids(self, proc):
        deadline = time.time() + 60
        while time.time() < deadline:
            if os.path.exists(self.log + ".pids"):
                with open(self.log + ".pids") as f:
                    text = f.read().split()
                if len(text) == 2:
                    return [int(x) for x in text]
            if proc.poll() is not None:
                self.fail("freshlook exited early: %s" % proc.communicate())
            time.sleep(0.1)
        self.fail("stand-in claude never started")

    def assert_dead(self, pids):
        deadline = time.time() + 15
        while time.time() < deadline and any(alive(p) for p in pids):
            time.sleep(0.1)
        self.assertFalse([p for p in pids if alive(p)], "auditor process tree must be killed")

    def test_timeout_kills_process_tree_and_cleans_up(self):
        proc = subprocess.Popen(self.args("--timeout", "3"), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=self.env("hang"))
        pids = self.wait_for_pids(proc)
        out, err = proc.communicate(timeout=60)
        self.assertEqual(proc.returncode, 3, err)
        self.assertIn("timed out", err)
        self.assert_dead(pids)
        self.assert_cleaned()

    def test_ctrl_c_and_sigterm_kill_process_tree_and_clean_up(self):
        for sig in (signal.SIGINT, signal.SIGTERM):
            proc = subprocess.Popen(self.args(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=self.env("hang"))
            pids = self.wait_for_pids(proc)
            proc.send_signal(sig)
            out, err = proc.communicate(timeout=60)
            self.assertEqual(proc.returncode, 130, err)
            self.assertIn("interrupted", err)
            self.assert_dead(pids)
            self.assert_cleaned()
            os.remove(self.log + ".pids")


if __name__ == "__main__":
    unittest.main()
