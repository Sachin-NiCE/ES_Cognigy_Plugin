# Subagents (placeholder)

No subagents yet. When we add one, create `agents/<name>.md` (frontmatter +
instructions, like a Claude Code subagent definition) and list it in
`../.claude-plugin/plugin.json`:

```json
"agents": [
  "./agents/<name>.md"
]
```

Good fit for multi-step workflows that should run in their own context and
report back a summary — e.g. a "snapshot before/after diff" agent, or a
guided package-import review loop.
