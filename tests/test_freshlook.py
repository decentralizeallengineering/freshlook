"""Tests for freshlook: metrics on a fixture repo, duplicate finder, dead-file finder, prompt assembly, run --dry-run."""
import importlib.machinery
import importlib.util
import os
import subprocess
import sys
import tempfile
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
    env = dict(os.environ, GIT_AUTHOR_NAME="Ann Example", GIT_AUTHOR_EMAIL="ann@example.invalid",
               GIT_COMMITTER_NAME="Ann Example", GIT_COMMITTER_EMAIL="ann@example.invalid")
    for cmd in (["init", "-q", "-b", "main"], ["add", "."], ["commit", "-q", "-m", "fixture"]):
        subprocess.run(["git", "-C", root, *cmd], check=True, env=env, capture_output=True, timeout=60)


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
            self.assertIn("command: claude -p --output-format text", r.stdout)
            self.assertIn("--model sonnet", r.stdout)
            self.assertIn("--allowedTools 'Read,Grep,Glob,", r.stdout)
            self.assertIn("CLAUDE_CONFIG_DIR=<fresh empty temp directory>", r.stdout)
            self.assertFalse(os.path.exists(os.path.join(d, "freshlook")))


if __name__ == "__main__":
    unittest.main()
