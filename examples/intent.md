freshlook is a single-file, stdlib-only Python CLI that asks a fresh, independent auditor where a codebase can be simplified.
`metrics` computes mechanical complexity hints (lines by directory, growth per week, duplicate names, dead Python files, largest functions) without tokens.
`run` sends those metrics and this intent to a headless `claude -p` that sees only a read-only copy of the committed tree, no user config, memory, hooks or instructions.
`diff` compares two reports to show what got simpler and what got worse.
It must stay small, portable (Linux, macOS, Windows), safe to interrupt, and honest about what it has verified.
