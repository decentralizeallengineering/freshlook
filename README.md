# freshlook

[![tests](https://github.com/decentralizeallengineering/freshlook/actions/workflows/tests.yml/badge.svg)](https://github.com/decentralizeallengineering/freshlook/actions/workflows/tests.yml) ![license](https://img.shields.io/badge/license-Apache--2.0-blue)

Escalation to a fresh, independent auditor: a completely independent look at a project, with the emphasis on stopping complexity from growing.

Why: a team that has worked on code for weeks stops seeing its own sprawl. `freshlook` first computes mechanical metrics (no tokens), then runs a headless
`claude -p` audit that sees only the code and a short intent statement. It gets no prior conclusions, no team memory, no instruction files (`CLAUDE.md` and similar
are stripped from the copy) and no hooks (a fresh empty config directory, project settings not loaded). Tools are read-only: Read, Grep, Glob and a few read-only shell commands.

## Install

Python 3.9+, `git`, and for `run` the `claude` command-line tool. Copy `bin/freshlook` onto your `PATH` and keep the `prompts/` directory next to `bin/`
(or set `FRESHLOOK_PROMPT` to another prompt file). No other dependencies.

## Configure

- `FRESHLOOK_MODEL`: default model for `run` (or pass `--model`). `FRESHLOOK_CLAUDE`: path of the `claude` executable.
- Credentials are never read by this tool. The clean config directory has no login, so use one of:
  - export `ANTHROPIC_API_KEY` (or `CLAUDE_CODE_OAUTH_TOKEN` from `claude setup-token`) in the environment; the child process inherits it; or
  - log in once inside a persistent clean directory, `CLAUDE_CONFIG_DIR=$HOME/.freshlook-claude claude`, then pass `--config-dir $HOME/.freshlook-claude` (or `FRESHLOOK_CONFIG_DIR`) on each run.

## Example

```
freshlook metrics ./myrepo                                  # writes ./freshlook/metrics.json and metrics.md
freshlook run ./myrepo --intent intent.md --dry-run         # prints the exact command, calls nothing
freshlook run ./myrepo --intent intent.md --model sonnet    # writes ./freshlook/report-<date>.md
freshlook diff freshlook/report-2026-01-01.md freshlook/report-2026-02-01.md
```

`metrics` reports lines of code by top-level directory, lines added per week against commits per week, possible duplicate mechanisms (name clustering plus docstring
token similarity), Python dead-file candidates from the import graph, the largest functions, and the test-to-code ratio. Results are hints and can contain false positives.
The audit prompt is `prompts/audit.md`; it asks for the purpose in 5 lines, the top 10 sources of complexity, what to delete or merge ranked by lines saved per risk,
what the intent asks for that the code does not do, and what a new maintainer would trip on first. `run` audits the committed tree (`git archive HEAD`) or a plain copy.

## Tests

`python3 -m unittest discover -s tests`

## License

Apache-2.0, see `LICENSE` and `NOTICE`.
