# freshlook

[![tests](https://github.com/decentralizeallengineering/freshlook/actions/workflows/tests.yml/badge.svg)](https://github.com/decentralizeallengineering/freshlook/actions/workflows/tests.yml) ![license](https://img.shields.io/badge/license-Apache--2.0-blue)

Escalation to a fresh, independent auditor: a completely independent look at a project, with the emphasis on stopping complexity from growing.

Why: a team that has worked on code for weeks stops seeing its own sprawl. `freshlook` first computes mechanical metrics (no tokens), then runs a headless
`claude -p` audit that sees only the code and a short intent statement. It gets no prior conclusions, no team memory, no instruction files (`CLAUDE.md` and similar
are stripped from the copy) and no hooks (a fresh empty config directory, `--restricted` so no settings files are loaded). Its only tools are Read, Grep and Glob,
confined to a read-only copy of the committed tree; there is no shell.

## Install

Python 3.9+, `git`, and for `run` the `claude` command-line tool (verified with 2.1.311; `--restricted`, `--safe-mode`, `--max-turns` and
`--max-budget-usd` must exist in your version). Copy `bin/freshlook` onto your `PATH` and keep the `prompts/` directory next to `bin/`
(or set `FRESHLOOK_PROMPT` to another prompt file). No other dependencies.

## Configure

- `FRESHLOOK_MODEL`: default model for `run` (or pass `--model`). `FRESHLOOK_CLAUDE`: path of the `claude` executable.
- Credentials are never read by this tool. The auditor gets an allowlisted environment: OS basics, proxy and CA variables, `ANTHROPIC_*`, `AWS_*`,
  `CLAUDE_CODE_OAUTH_TOKEN` and the Bedrock/Vertex switches. Every other variable, including the parent session's `CLAUDE_*` ones, is dropped.
  The clean config directory has no login, so use one of:
  - export `ANTHROPIC_API_KEY` (or `CLAUDE_CODE_OAUTH_TOKEN` from `claude setup-token`) in the environment; or
  - log in once inside a persistent clean directory, `CLAUDE_CONFIG_DIR=$HOME/.freshlook-claude claude`, then pass `--config-dir $HOME/.freshlook-claude` (or `FRESHLOOK_CONFIG_DIR`) on each run.
    `run` refuses (exit 4) a directory that is your real config directory or that holds `CLAUDE.md`, `settings.json`, hooks, skills, agents, user plugins or memory.
- Guards: `--max-turns N` (default 100), `--budget USD` (default 5, the CLI's own list-price estimate), `--timeout SECONDS` (default 1800). 0 turns or 0 budget means no limit.
  The report header records the model the CLI used, turns, wall time, tokens and that estimate.

## Example

```
freshlook metrics ./myrepo                                  # writes ./freshlook/metrics.json and metrics.md
freshlook run ./myrepo --intent intent.md --dry-run         # prints the exact command, calls nothing
freshlook run ./myrepo --intent intent.md --model sonnet    # writes ./freshlook/report-<date>.md
freshlook run ./myrepo --intent intent.md --max-turns 40 --budget 2
freshlook diff freshlook/report-2026-01-01.md freshlook/report-2026-02-01.md
```

`metrics` reports lines of code by top-level directory, lines added per week against commits per week, possible duplicate mechanisms (name clustering plus docstring
token similarity), Python dead-file candidates from the import graph, the largest functions, and the test-to-code ratio. Results are hints and can contain false positives.
The audit prompt is `prompts/audit.md`; it asks for the purpose in 5 lines, the top 10 sources of complexity, what to delete or merge ranked by lines saved per risk,
what the intent asks for that the code does not do, and what a new maintainer would trip on first. `run` audits the committed tree (`git archive HEAD`) or a plain copy,
without symlinks. Exit codes: 2 usage error, 3 audit failed (including the turn or budget limit), 4 an independence check failed, 130 interrupted.

## What has been verified, and what has not

Verified live on Linux (Ubuntu container, Python 3.13, `claude` 2.1.311, auth through the environment's API proxy), October 2026:

- `freshlook metrics .` and `freshlook run . --intent examples/intent.md` on this repository, end to end. The unedited report is
  [`examples/self-audit.md`](examples/self-audit.md): Sonnet 5.5, 5 turns, 30 s, about $0.13 by the CLI's estimate, no temp files left behind.
- The first live runs found these problems, now fixed:
  - The inherited environment made the "clean" auditor reuse the parent's session id and sync its plugins, skills and login into the clean config directory.
  - An `--allowedTools` Bash pattern did not stop other shell commands.
  - `Read` could open files outside the copy.
  - The CLI's `$TMPDIR/claude-<uid>/` folder outlived the run.
  - `bin/freshlook` was missing from its own metrics.
- `tests/test_live.py` (`FRESHLOOK_LIVE=1`) plants three canaries: a `CLAUDE.md` in the repo, a `CLAUDE.md` and a `SessionStart` hook in the
  caller's `CLAUDE_CONFIG_DIR`, and a file outside the copy that the intent tells the auditor to read. In the live run, none reached the report,
  the hook did not fire, and the outside read was denied (the header shows `Denied tool calls: 1 (Read)`).
- `--max-turns 1` and `--budget 0.001` end the real CLI's run with `error_max_turns` and `error_max_budget_usd`, and `freshlook` exits 3.
- `--timeout 4`, Ctrl-C (SIGINT) and SIGTERM during a real audit: `freshlook` exits 3, 130 and 130. No `claude` process or temp directory was left behind.

Covered only by tests with a stand-in `claude`: the report being discarded (exit 4) when the copy changes or user configuration appears in
the config directory. With the real CLI, neither has happened.

Not verified:

- **Windows and macOS.** The Windows code paths (`taskkill`, `CREATE_NEW_PROCESS_GROUP`, the `claude.cmd` lookup, clearing read-only flags
  before delete) are written but untested; the stand-in tests are POSIX only. The CI runs on Ubuntu only.
- **Auth other than this container's.** Only auth injected by the environment's API proxy was tested. `ANTHROPIC_API_KEY`,
  `CLAUDE_CODE_OAUTH_TOKEN` and a login inside a persistent `--config-dir` were not.
- **Other CLI versions.** A version without `--restricted`, `--safe-mode` or `--max-turns` should fail, and `freshlook` should pass on the CLI's
  error output. Neither has been tried.
- **Org-managed settings.** Managed (policy) settings and managed hooks still apply inside the clean directory. That is by the CLI's design and
  `freshlook` cannot turn them off.
- **Running as root.** Permission bits do not stop root, so the read-only guarantee rests on the tool set, which has no write tool and no shell,
  plus the before/after content hash of the copy.

## Tests

`python3 -m unittest discover -s tests` (the live test is skipped unless `FRESHLOOK_LIVE=1`; set `FRESHLOOK_LIVE_MODEL` to change its default `haiku`)

## License

Apache-2.0, see `LICENSE` and `NOTICE`.
