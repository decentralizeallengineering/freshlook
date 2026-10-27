# freshlook report: freshlook

Date: 2026-10-27. Model: claude-sonnet-5-5 (requested: CLI default).
Turns: 5 (limit 100). Wall time: 30 s (limit 1800 s). Cost: $0.1262, the CLI's list-price estimate (budget $5.00).
Tokens: 6 input, 3589 output, 33195 cache read, 21745 cache write. Denied tool calls: 0.
Independence: fresh empty config directory with no CLAUDE.md, settings, hooks, user plugins, skills or memory before and after the run; environment limited to ANTHROPIC_BASE_URL, CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC, CLAUDE_CONFIG_DIR, DISABLE_TELEMETRY, HOME, HTTPS_PROXY, LC_CTYPE, NODE_EXTRA_CA_CERTS, NODE_OPTIONS, NO_PROXY, PATH, SSL_CERT_FILE, TEMP, TMP, TMPDIR, https_proxy, no_proxy; tools Read, Grep, Glob confined to a read-only copy of the committed tree, unchanged after the audit.

## 1. What the project is for
- `bin/freshlook` is a Python CLI with three subcommands: `metrics`, `run` and `diff` (`bin/freshlook:778-799`).
- `metrics` counts lines, git churn, similar names, unimported Python files and the largest functions, and writes the results to `metrics.json` and `metrics.md` (`bin/freshlook:354-401`).
- `run` copies the repo into a read-only temp directory and starts `claude -p` there with a restricted tool set, a scrubbed environment and a clean config directory (`bin/freshlook:413-443`, `618-694`).
- It checks that the config directory is clean and that the copy is unchanged, then writes a dated report with a metrics footer (`bin/freshlook:591-615`, `675-692`).
- `diff` compares the footer numbers of two reports, and also matches the list items in sections 2, 3 and 5 by token overlap (`bin/freshlook:704-775`).

## 2. Top 10 sources of complexity
1. `cmd_run` does validation, metrics output, copying, independence checks, process launch, result parsing and cleanup in one 77-line function with six exit paths (`bin/freshlook:618-694`).
2. Independence enforcement is spread over several mechanisms: env allowlist, provider prefixes, forbidden-name sets, `config_problems`, `writable_paths` and `tree_digest` (`bin/freshlook:27-41`, `436-517`).
3. The duplicate detector uses an inverted index, union-find, Jaccard matching and a mechanism-word scan, and it found 0 clusters on this repo (`bin/freshlook:156-246`).
4. Dead-file detection resolves relative imports and module suffixes, and misses string references (`bin/freshlook:249-304`).
5. Multi-language function sizing uses brace-counting regexes for about 10 languages that are never tested here (`bin/freshlook:307-351`, `23`).
6. Windows and POSIX branches for process groups, kill, chmod and read-only handling (`bin/freshlook:496`, `520-559`).
7. The read-only copy has two code paths (`git archive` and `copytree`), a `tarfile` filter shim and three separate `os.walk` passes (`bin/freshlook:466-492`).
8. `diff` combines numeric metric comparison with fuzzy matching of free-text report items, using a regex footer and two hard-coded better/worse sets (`bin/freshlook:699-747`).
9. The tool has three separate file filters: `SKIP_DIRS` for the metrics file list, `STRIP_NAMES` for the copy, and `FORBIDDEN_CONFIG` for the config directory. They overlap and can disagree (`bin/freshlook:20`, `39-41`, `62`, `479`).
10. Several large literal constants (CODE_EXT, STOP_NAMES, STOP_TOKENS, MECHANISMS, PASS_ENV) tune heuristics that have no test or evidence behind them (`bin/freshlook:20-37`).

## 3. What to delete or merge
1. Delete the `MECHANISMS` scan and its constant, and the `mechanisms` part of the summary. Saves about 15 lines. Risk: low. (`bin/freshlook:26`, `241-245`, `393-394`)
2. Merge the duplicated metrics-writing block in `cmd_metrics` and `cmd_run` into one helper. Saves about 8 lines. Risk: low. (`bin/freshlook:581-587`, `644-649`)
3. Collapse the three `os.walk` passes in `make_readonly_copy`, and reuse the chmod loop in `remove_tree`. Saves about 10 lines. Risk: low. (`bin/freshlook:480-492`, `520-530`)
4. Drop the non-git branch of `make_readonly_copy`, `list_files` and `history`, and require git. This also makes the "committed tree" claim true. Saves about 20 lines. Risk: medium. (`bin/freshlook:65-67`, `143-144`, `477-479`)
5. Remove brace-language function sizing and keep Python only. Saves about 40 lines, plus related tests. Risk: medium, because it narrows the supported languages. (`bin/freshlook:23`, `307-351`)
6. Replace `find_duplicates` with a simple same-name-in-multiple-files check. Saves about 60 lines. Risk: medium, because it loses the docstring-similarity signal. (`bin/freshlook:156-246`)
7. Drop `PROVIDER_ENV` and the cloud-provider passthrough, and rely on `ANTHROPIC_*` plus a few named variables. Saves about 8 lines. Risk: medium, because Bedrock and Vertex users lose their credentials. (`bin/freshlook:37`, `439`)
8. In `diff`, compare only the footer metrics and drop the fuzzy section matching and `same_item`. Saves about 25 lines. Risk: medium. (`bin/freshlook:704-747`, `762-770`)
9. Simplify `dead_python_files` to match imported module names by basename. Saves about 20 lines. Risk: medium, because it produces more false positives. (`bin/freshlook:256-304`)
10. Split `cmd_run` into `prepare` and `audit` functions. This saves no lines but lowers branching. Risk: low.

## 4. What the intent asks for that the code does not do
- "Sees only a read-only copy of the committed tree": for a non-git repo, `copytree` copies uncommitted files, so this does not hold there. For a git repo, metrics come from `git ls-files` on the working tree while the audit sees `HEAD`. The two can disagree on a dirty tree (`bin/freshlook:60-62` against `471`, `478`).
- "Single-file": the tool also needs `prompts/audit.md` (`bin/freshlook:18`, `406-410`). If that file is missing, `run` fails with a raw `FileNotFoundError` traceback, and `main` only catches `KeyboardInterrupt`.
- "Portable (Linux, macOS, Windows)": nothing in the code I read shows Windows or macOS was exercised. The `taskkill` and `CREATE_NEW_PROCESS_GROUP` paths are untested in this tree (`bin/freshlook:536-537`, `552`). I did not read the tests to confirm.
- "Honest about what it has verified": the report header says the config directory was clean "before and after", but a user-supplied `--config-dir` is only checked for forbidden names, not contents (`bin/freshlook:612`). The "no hooks" claim relies on `settings.json` being absent, which is a name check only.

## 5. What would a new maintainer trip on first
- `SKIP_DIRS` contains `"freshlook"` because that is the default output directory. This silently excludes any real project directory with that name from metrics (`bin/freshlook:20`, `783`).
- `top_dir` returns `"."` for root files. `loc_by_top_dir` therefore needs a special reading for them (`bin/freshlook:93-94`).
- `find_duplicates` reads `items[:4000]` and skips any index key shared by more than 60 items, so large repos get silently incomplete results (`bin/freshlook:196-200`, `219`).
- `is_test` classes every file under `spec` or `test*` as a test. `largest_functions`, `collect_items` and `dead_python_files` all skip tests, so tests are never audited for size (`bin/freshlook:87-90`, `174`, `336`).
- The `diff` direction of "better" is hard-coded. `files` and `loc_tests` are treated inconsistently, and an increase in `avg_added_per_week_second_half` counts as worse even though `0.0` is also reported for a single week (`bin/freshlook:700-701`, `596`).
- The report footer is parsed with a regex, and section numbers are assumed to be single digits (`bin/freshlook:699`, `709`). Edited or reformatted reports silently produce empty diffs.
- Timeout, tool and flag behaviour is justified by "verified live" comments against one CLI version (2.1), with no way to re-check them. `--restricted` and `--safe-mode` may change in later versions (`bin/freshlook:27-29`, `416-418`).
- `dead_python_files` ignores the intent statement's emphasis on size: the tool reports `Python dead-file candidates (0)` for its own repo because its only Python file is the entry point.

<!-- freshlook-metrics: {"avg_added_per_week_second_half": 1663.0, "dead_python_candidates": 0, "duplicate_clusters": 0, "files": 11, "largest_function_lines": 77, "loc_code": 709, "loc_tests": 411, "test_to_code_ratio": 0.58} -->
