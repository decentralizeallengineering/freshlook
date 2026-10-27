"""Tests for freshlook: metrics on a fixture repo, duplicate finder, dead-file finder, growth by directory, config surface, ways in,
simplification candidates, metrics.json compatibility, prompt assembly, run --dry-run."""
import ast
import glob
import importlib.machinery
import json
import importlib.util
import os
import subprocess
import sys
import re
import tempfile
import textwrap
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
    git_commit(root, "fixture")


GIT_ENV = dict(os.environ, GIT_AUTHOR_NAME="Ann Example", GIT_AUTHOR_EMAIL="ann@example.invalid",
               GIT_COMMITTER_NAME="Ann Example", GIT_COMMITTER_EMAIL="ann@example.invalid")


def git_init(root):
    subprocess.run(["git", "-C", root, "init", "-q", "-b", "main"], check=True, env=GIT_ENV, capture_output=True, timeout=60)


def git_commit(root, msg, date=None):
    env = dict(GIT_ENV, GIT_AUTHOR_DATE=date + "T12:00:00", GIT_COMMITTER_DATE=date + "T12:00:00") if date else GIT_ENV
    for cmd in (["add", "-A"], ["-c", "commit.gpgsign=false", "commit", "-q", "-m", msg]):
        subprocess.run(["git", "-C", root, *cmd], check=True, env=env, capture_output=True, timeout=60)


def lines_of(n, fmt="x%d = %d\n"):
    return "".join(fmt % (k, k) for k in range(n))


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


DOWNLOAD_A = """
def download_file(url, dest, retries=3):
    \"\"\"Download a URL to a local file, retrying on network errors.\"\"\"
    last = None
    for attempt in range(retries):
        try:
            with urlopen(url, timeout=30) as resp, open(dest, "wb") as out:
                while True:
                    chunk = resp.read(65536)
                    if not chunk:
                        break
                    out.write(chunk)
            return dest
        except OSError as exc:
            last = exc
            log.warning("attempt %d failed: %s", attempt, exc)
    raise RuntimeError("download failed: %s" % last)
"""

# the same mechanism with every identifier renamed and every literal changed
DOWNLOAD_B = """
def download_files(source, target, tries=5):
    \"\"\"Fetch a file over HTTP into target, with retries.\"\"\"
    error = None
    for n in range(tries):
        try:
            with fetch(source, timeout=10) as r, open(target, "ab") as fh:
                while True:
                    block = r.read(1024)
                    if not block:
                        break
                    fh.write(block)
            return target
        except IOError as e:
            error = e
            logger.info("retry %d: %s", n, e)
    raise ValueError("could not fetch %s" % error)
"""

# same name tokens, different mechanism
DOWNLOAD_C = """
def download_file(record):
    \"\"\"Return the stored download file of a record as rows.\"\"\"
    rows = []
    for key, value in sorted(record.items()):
        if key.startswith("_"):
            continue
        rows.append({"key": key, "value": str(value), "size": len(str(value))})
    if not rows:
        return None
    return rows
"""

# a second, smaller duplicated pair whose names differ but whose docstrings match
SUMMARY_A = """
def render_summary(rows):
    \"\"\"Print a table of totals for the rows grouped by category.\"\"\"
    totals = {}
    for row in rows:
        totals[row["category"]] = totals.get(row["category"], 0) + row["amount"]
    for name in sorted(totals):
        print("%-20s %10.2f" % (name, totals[name]))
    return totals
"""

SUMMARY_B = """
def show_totals(items):
    \"\"\"Print a table of totals for the rows grouped by category.\"\"\"
    acc = {}
    for it in items:
        acc[it["kind"]] = acc.get(it["kind"], 0) + it["value"]
    for key in sorted(acc):
        print("%s: %d" % (key, acc[key]))
    return acc
"""


def make_duplicate_repo(root):
    write(root, "net/fetch.py", "from urllib.request import urlopen\nimport logging\nlog = logging.getLogger()\n" + DOWNLOAD_A)
    write(root, "tools/mirror.py", "from x import fetch, logger\n" + DOWNLOAD_B)
    write(root, "store/records.py", DOWNLOAD_C)
    write(root, "report/a.py", SUMMARY_A)
    write(root, "report/b.py", SUMMARY_B)
    write(root, "report/__init__.py", "from report import a, b\nfrom net import fetch\nfrom tools import mirror\nfrom store import records\n")
    write(root, "scratch/old_export.py", lines_of(40))
    git_init(root)
    git_commit(root, "fixture")


def fixture_pairs():
    """The 30 hand-labelled pairs in tests/fixtures/dup_pairs: (name, label, item a, item b)."""
    out = []
    for path in sorted(glob.glob(os.path.join(ROOT, "tests", "fixtures", "dup_pairs", "p*.py"))):
        with open(path, encoding="utf-8") as f:
            text = f.read()
        label = re.search(r"^# label: (\w+)", text, re.M).group(1)
        tree = ast.parse(text)
        a, b = (FL.def_item(node, os.path.basename(path), text.splitlines()) for node in tree.body)
        out.append((os.path.basename(path), label, a, b))
    return out


def precision_recall(rows):
    tp = sum(1 for label, pred in rows if pred and label == "duplicate")
    fp = sum(1 for label, pred in rows if pred and label != "duplicate")
    fn = sum(1 for label, pred in rows if not pred and label == "duplicate")
    return (tp / (tp + fp) if tp + fp else 0.0), (tp / (tp + fn) if tp + fn else 0.0), tp, fp


class Duplicates(unittest.TestCase):
    def test_clusters_confirmed_by_shape(self):
        with tempfile.TemporaryDirectory() as d:
            make_duplicate_repo(d)
            dup = FL.find_duplicates(FL.collect_items(d, FL.list_files(d)))
            labels = [c["label"] for c in dup["clusters"]]
            self.assertEqual(labels, ["2 ways to do download file", "2 ways to do print table totals rows"])
            big = dup["clusters"][0]
            self.assertEqual(sorted(m["where"] for m in big["members"]), ["net/fetch.py:5", "tools/mirror.py:3"])
            self.assertNotIn("store/records.py", " ".join(m["where"] for m in big["members"]))   # same name, different shape
            self.assertGreaterEqual(big["total_lines"], dup["clusters"][1]["total_lines"])
            self.assertEqual(big["removable_lines"], big["total_lines"] - max(m["lines"] for m in big["members"]))
            self.assertGreater(dup["candidate_pairs"], dup["confirmed_pairs"])
            md = FL.render_summary(FL.compute_metrics(d))
            self.assertIn("2 ways to do download file", md)
            self.assertIn("net/fetch.py:5 download_file", md)

    def test_shape_ignores_identifiers_and_literals(self):
        def shape(src):
            return FL.ast_shape(ast.parse(src).body[0])
        self.assertEqual(shape("def f(a):\n    return a + 1\n"), shape("def g(zz):\n    \"\"\"doc\"\"\"\n    return zz + 99\n"))
        self.assertNotEqual(shape("def f(a):\n    return a + 1\n"), shape("def f(a):\n    if a:\n        return a + 1\n"))

    def test_trivial_bodies_never_confirmed(self):
        a = FL.def_item(ast.parse("def get_name(self):\n    return self._name\n").body[0], "a.py", ["def get_name(self):", "    return self._name"])
        b = FL.def_item(ast.parse("def get_names(self):\n    return self._names\n").body[0], "b.py", ["def get_names(self):", "    return self._names"])
        self.assertEqual(FL.find_duplicates([a, b])["clusters"], [])

    def test_precision_on_hand_labelled_pairs(self):
        pairs = fixture_pairs()
        self.assertEqual(len(pairs), 30)
        self.assertEqual(sum(1 for p in pairs if p[1] == "duplicate"), 14)
        old, new = [], []
        for name, label, a, b in pairs:
            dup = FL.find_duplicates([a, b])
            self.assertEqual(dup["candidate_pairs"], 1, name)   # every pair is one the old name/docstring rule flagged
            old.append((label, True))
            new.append((label, dup["confirmed_pairs"] == 1))
        old_p, old_r, _, _ = precision_recall(old)
        new_p, new_r, tp, fp = precision_recall(new)
        # measured: old precision 14/30 = 0.47 (recall 1.0); new 11/11 = 1.00 (recall 11/14 = 0.79)
        self.assertAlmostEqual(old_p, 14 / 30)
        self.assertGreaterEqual(new_p, 0.9, (tp, fp))
        self.assertGreaterEqual(new_r, 0.7)


class Growth(unittest.TestCase):
    def test_numstat_paths(self):
        self.assertEqual(FL.numstat_path("pkg/{a.py => b.py}"), "pkg/b.py")
        self.assertEqual(FL.numstat_path("{old => new}/f.py"), "new/f.py")
        self.assertEqual(FL.numstat_path("pkg/{ => sub}/f.py"), "pkg/sub/f.py")
        self.assertEqual(FL.numstat_path("a.py => b.py"), "b.py")

    def test_growth_and_accretion(self):
        with tempfile.TemporaryDirectory() as d:
            git_init(d)
            write(d, "core/a.py", lines_of(20))
            git_commit(d, "core 1", "2026-01-05")
            write(d, "lib/x.py", lines_of(20))
            git_commit(d, "lib 1", "2026-01-06")
            write(d, "core/a.py", lines_of(30))
            git_commit(d, "core 2", "2026-01-12")
            write(d, "lib/x.py", lines_of(30))
            git_commit(d, "lib 2", "2026-01-13")
            write(d, "core/b.py", lines_of(200))
            git_commit(d, "core 3", "2026-01-19")
            for k, day in enumerate(("2026-01-20", "2026-01-21", "2026-01-22", "2026-01-27")):
                write(d, "lib/x.py", lines_of(29) + "x29 = %d\n" % (100 + k))
                git_commit(d, "lib tweak", day)
            write(d, "core/b.py", lines_of(350))
            git_commit(d, "core 4", "2026-01-26")
            m = FL.compute_metrics(d)
            g = m["growth_by_dir"]
            core, lib = g["dirs"]["core"], g["dirs"]["lib"]
            self.assertEqual(core["weeks"]["2026-W04"], {"added": 200, "deleted": 0, "commits": 1, "new_files": 1, "modified_files": 0})
            self.assertEqual((core["added"], core["deleted"], core["commits"]), (380, 0, 4))
            self.assertEqual((core["new_files"], core["modified_files"], core["new_to_modified_ratio"]), (2, 2, 1.0))
            self.assertEqual((lib["new_files"], lib["modified_files"], lib["new_to_modified_ratio"]), (1, 5, 0.2))
            self.assertEqual((lib["added"], lib["deleted"]), (34, 4))
            self.assertEqual(core["first_half"]["commits"], 2)
            self.assertEqual(core["second_half"]["net"], 350)
            self.assertTrue(core["accretion"])
            self.assertFalse(lib["accretion"])   # more commits, no growth
            self.assertEqual([a["dir"] for a in g["accretion"]], ["core"])
            self.assertEqual(sum(w["commits"] for w in m["history"]["weeks"].values()), 10)
            self.assertIn("accretion: core grew +350 lines", FL.render_summary(m))

    def test_not_a_git_repo(self):
        with tempfile.TemporaryDirectory() as d:
            write(d, "a.py", "x = 1\n")
            m = FL.compute_metrics(d)
            self.assertEqual(m["growth_by_dir"], {"dirs": {}, "accretion": []})
            self.assertEqual(m["config_surface"]["history"], [])


SETTINGS_PY = """\
import argparse
import os
from os import environ

DEBUG = os.environ.get("APP_DEBUG", "0") == "1"
TOKEN = os.getenv("APP_TOKEN")
HOME = os.environ["HOME"]
os.environ["WRITTEN_NOT_READ"] = "1"
if "APP_MODE" in os.environ:
    pass
ENABLE_NEW_UI = False


def cli():
    p = argparse.ArgumentParser()
    p.add_argument("-v", "--verbose", action="store_true")
    p.add_argument("--enable-cache", action="store_true")
    p.add_argument("path")
    return p


def read(config, cfg):
    host = config["database"]["host"]
    port = cfg.get("port", 5432)
    timeout = config.getint("net", "timeout")
    return host, port, timeout, environ.get("APP_REGION")


def flagged(client):
    return client.is_enabled("new-checkout")
"""


def make_config_repo(root):
    write(root, "app/settings.py", SETTINGS_PY)
    write(root, "app/views.py", "from django.conf import settings\n\n\ndef key():\n    return settings.SECRET_KEY\n")
    write(root, "web/index.js", "const port = process.env.PORT || 3000;\nprogram.option('-p, --port <n>', 'port');\n")
    write(root, "scripts/deploy.sh", '#!/bin/sh\nTARGET="${DEPLOY_TARGET:-staging}"\ncase "$1" in\n  -n|--dry-run) DRY=1 ;;\nesac\n')
    write(root, "config/defaults.yaml", "server:\n  host: 0.0.0.0\n  port: 8080\nfeature_dark_mode: true\n")
    write(root, ".env.example", "SECRET_KEY=\nAPP_TOKEN=\n")
    write(root, "tests/test_settings.py", "import os\nos.environ.get('TEST_ONLY')\n")


class ConfigSurface(unittest.TestCase):
    def test_counts_and_locations(self):
        with tempfile.TemporaryDirectory() as d:
            make_config_repo(d)
            c = FL.compute_metrics(d)["config_surface"]
            names = {k: [e["name"] for e in c[k]] for k in ("env_vars", "cli_flags", "config_keys", "feature_flags")}
            self.assertEqual(names["env_vars"], sorted(["APP_DEBUG", "APP_TOKEN", "HOME", "APP_MODE", "APP_REGION", "PORT", "DEPLOY_TARGET", "SECRET_KEY"]))
            self.assertEqual(names["cli_flags"], ["--dry-run", "--enable-cache", "--port", "--verbose"])
            self.assertEqual(names["config_keys"], sorted(["database.host", "port", "net.timeout", "SECRET_KEY", "server.host", "server.port",
                                                           "feature_dark_mode"]))
            self.assertEqual(names["feature_flags"], ["--enable-cache", "ENABLE_NEW_UI", "feature_dark_mode", "new-checkout"])
            self.assertEqual(c["counts"], {"env_vars": 8, "cli_flags": 4, "config_keys": 7, "feature_flags": 4, "total": 21})
            by = {e["name"]: e for e in c["env_vars"]}
            self.assertEqual(by["APP_TOKEN"]["where"], [".env.example:2", "app/settings.py:6"])
            self.assertEqual(by["APP_TOKEN"]["uses"], 2)
            self.assertEqual(by["DEPLOY_TARGET"]["where"], ["scripts/deploy.sh:2"])
            flags = {e["name"]: e for e in c["feature_flags"]}
            self.assertEqual((flags["ENABLE_NEW_UI"]["via"], flags["ENABLE_NEW_UI"]["where"]), ("constant", ["app/settings.py:11"]))
            self.assertEqual(flags["--enable-cache"]["via"], "cli")

    def test_growth_over_history(self):
        with tempfile.TemporaryDirectory() as d:
            git_init(d)
            write(d, "app.py", "import os\nA = os.getenv('A')\n")
            git_commit(d, "one", "2026-01-05")
            write(d, "app.py", "import os\nA = os.getenv('A')\nB = os.getenv('B')\n")
            git_commit(d, "two", "2026-02-05")
            make_config_repo(d)
            git_commit(d, "three", "2026-03-05")
            hist = FL.compute_metrics(d)["config_surface"]["history"]
            self.assertEqual([(h["date"], h["env_vars"]) for h in hist], [("2026-01-05", 1), ("2026-02-05", 2), ("2026-03-05", 10)])
            self.assertEqual(hist[-1]["total"], 23)
            self.assertEqual(len(FL.config_history(d, points=2)), 2)
            self.assertEqual(FL.config_history(d, points=0), [])


def make_entry_repo(root):
    write(root, "pyproject.toml", '[project]\nname = "mytool"\n\n[project.scripts]\nmytool = "mytool.cli:main"\n\n[tool.other]\nx = "y:z"\n')
    write(root, "setup.cfg", "[options.entry_points]\nconsole_scripts =\n    legacy-tool = mytool.legacy:run\n")
    write(root, "setup.py", 'from setuptools import setup\nsetup(entry_points={"console_scripts": ["third = mytool.third:main"]})\n')
    write(root, "package.json", '{"name": "@acme/jscli", "bin": {"jscli": "bin/jscli.js"}}\n')
    write(root, "mytool/__init__.py", "")
    write(root, "mytool/__main__.py", "from mytool.cli import main\nmain()\n")
    write(root, "mytool/cli.py", "def main():\n    pass\n\n\nif __name__ == '__main__':\n    main()\n")
    write(root, "mytool/legacy.py", "def run():\n    pass\n")
    write(root, "mytool/third.py", "def main():\n    pass\n")
    write(root, "mytool/web.py", textwrap.dedent("""\
        from flask import Blueprint, Flask
        app = Flask(__name__)
        bp = Blueprint("bp", __name__)


        @app.route("/")
        def index():
            return "hi"


        @app.route("/items", methods=["GET", "POST"])
        def items():
            return ""


        @bp.get("/health")
        def health():
            return ""


        def legacy():
            return ""


        app.add_url_rule("/legacy", view_func=legacy)
        """))
    write(root, "mytool/api.py", textwrap.dedent("""\
        from fastapi import APIRouter, FastAPI
        app = FastAPI()
        router = APIRouter()


        @app.get("/users/{uid}")
        async def get_user(uid: int):
            return {}


        @router.post("")
        def create():
            return {}


        @app.websocket("/ws")
        async def ws(sock):
            pass
        """))
    write(root, "mytool/notweb.py", "class C:\n    def get(self, p):\n        return lambda f: f\n\n\ncache = C()\n\n\n@cache.get('/x')\ndef f():\n    pass\n")
    write(root, "deploy/backup.timer", "[Unit]\nDescription=Nightly backup\n\n[Timer]\nOnCalendar=*-*-* 03:00:00\nPersistent=true\n\n[Install]\nWantedBy=timers.target\n")
    write(root, "deploy/backup.service", "[Service]\nType=oneshot\nExecStart=/usr/bin/python3 -m mytool backup\n")
    write(root, "tests/test_cli.py", "if __name__ == '__main__':\n    pass\n")
    git_init(root)
    git_commit(root, "fixture")


class EntryPoints(unittest.TestCase):
    def test_ways_in(self):
        with tempfile.TemporaryDirectory() as d:
            make_entry_repo(d)
            m = FL.compute_metrics(d)
            e = m["entry_points"]
            self.assertEqual(e["by_kind"], {"console_script": 4, "http_route": 7, "main_guard": 1, "main_module": 1, "scheduled_job": 1})
            self.assertEqual(e["count"], 14)
            got = {(i["kind"], i["name"]) for i in e["items"]}
            for want in [("console_script", "mytool"), ("console_script", "legacy-tool"), ("console_script", "third"), ("console_script", "jscli"),
                         ("main_module", "python -m mytool"), ("main_guard", "mytool/cli.py"),
                         ("http_route", "GET /"), ("http_route", "GET|POST /items"), ("http_route", "GET /health"), ("http_route", "GET /legacy"),
                         ("http_route", "GET /users/{uid}"), ("http_route", "POST /"), ("http_route", "WS /ws"), ("scheduled_job", "backup")]:
                self.assertIn(want, got)
            where = {i["name"]: i for i in e["items"]}
            self.assertEqual(where["mytool"]["where"], "pyproject.toml:5")
            self.assertEqual(where["GET|POST /items"]["where"], "mytool/web.py:11")
            self.assertEqual(where["backup"]["detail"], "OnCalendar=*-*-* 03:00:00 -> /usr/bin/python3 -m mytool backup")
            dead = [x["file"] for x in m["dead_python_candidates"]]
            self.assertNotIn("mytool/legacy.py", dead)   # a console-script target is not dead
            self.assertNotIn("mytool/third.py", dead)
            self.assertIn("## Ways in (14)", FL.render_summary(m))


OLD_KEYS = {"repo": str, "generated": str, "files": int, "loc_by_top_dir": dict, "loc_code": int, "loc_tests": int, "test_to_code_ratio": (int, float),
            "history": dict, "duplicates": dict, "dead_python_candidates": list, "largest_functions": list}


class Compatibility(unittest.TestCase):
    def test_metrics_json_keeps_old_shape_and_adds_candidates(self):
        with tempfile.TemporaryDirectory() as d:
            make_duplicate_repo(d)
            out = os.path.join(d, "out")
            r = subprocess.run([sys.executable, BIN, "metrics", d, "--out", out], capture_output=True, text=True, timeout=120)
            self.assertEqual(r.returncode, 0, r.stderr)
            with open(os.path.join(out, "metrics.json"), encoding="utf-8") as f:
                m = json.load(f)
            for key, typ in OLD_KEYS.items():
                self.assertIsInstance(m[key], typ, key)
            for key in ("weeks", "avg_added_per_week_first_half", "avg_added_per_week_second_half", "avg_commits_per_week_first_half",
                        "avg_commits_per_week_second_half", "net_lines"):
                self.assertIn(key, m["history"])
            self.assertIsInstance(m["duplicates"]["mechanisms"], list)
            for c in m["duplicates"]["clusters"]:
                self.assertIsInstance(c["kinds"], list)
                self.assertIsInstance(c["reason"], str)
                for x in c["members"]:
                    self.assertIsInstance(x["name"], str)
                    self.assertIsInstance(x["where"], str)
            for x in m["dead_python_candidates"]:
                self.assertIsInstance(x["file"], str)
                self.assertIsInstance(x["lines"], int)
            for x in m["largest_functions"]:
                self.assertTrue(set(x) >= {"name", "file", "line", "lines"})
            for key in ("growth_by_dir", "config_surface", "entry_points", "simplification_candidates"):
                self.assertIn(key, m)
            cands = m["simplification_candidates"]
            self.assertLessEqual(len(cands), 10)
            self.assertEqual([c["score"] for c in cands], sorted((c["score"] for c in cands), reverse=True))
            for c in cands:
                self.assertEqual(c["score"], round(c["lines_removable"] * c["confidence"], 1))
            kinds = [c["kind"] for c in cands]
            self.assertIn("merge_duplicates", kinds)
            self.assertIn("delete_dead_file", kinds)
            self.assertEqual(cands[0]["title"], "delete scratch/old_export.py (no import and no textual mention found)")
            with open(os.path.join(out, "metrics.md"), encoding="utf-8") as f:
                self.assertIn("## Top simplification candidates", f.read())

    def test_diff_against_old_report_footer(self):
        with tempfile.TemporaryDirectory() as d:
            make_config_repo(d)
            m = FL.compute_metrics(d)
        new = FL.report_footer(m)
        keys = json.loads(FL.FOOTER.search(new).group(1))
        self.assertEqual(keys["config_surface"], 21)
        old = '<!-- freshlook-metrics: {"files": 3, "loc_code": 10} -->'
        diff = FL.diff_reports(old, new)
        self.assertEqual(diff["worse"], ["files: 3 -> %d" % m["files"], "loc_code: 10 -> %d" % m["loc_code"]])
        self.assertEqual(FL.diff_reports(new.replace('"config_surface": 21', '"config_surface": 30'), new)["simpler"], ["config_surface: 30 -> 21"])


if __name__ == "__main__":
    unittest.main()
