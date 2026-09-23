# Skills (placeholder)

No skills yet. When we add one, create `skills/<name>/SKILL.md` and list it
in `../.claude-plugin/plugin.json`:

```json
"skills": [
  "./skills/<name>/SKILL.md"
]
```

Skills auto-load into context when a user's request matches their
description — good fit for guided workflows (e.g. "how to size a snapshot
restore", "package export checklist") that don't need their own MCP tool.
