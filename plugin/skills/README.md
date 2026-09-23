# Skills

One per feature area, mirroring the MCP tools in `../../server/app.py`:

- `snapshot-backups/` — `list_snapshots`, `create_snapshot`, `restore_snapshot`,
  `delete_snapshot`, `read_snapshot_task`
- `package-management/` — `list_exportable_resources`, `export_package`,
  `download_package`, `upload_and_inspect_package`, `inspect_package`,
  `import_package`, `read_package_task`
- `project-settings/` — `set_voice_preview`, `set_knowledge_ai`

Each auto-loads into context when a user's request matches its `description`
frontmatter. When we add a new tool area to `server/app.py` (agent creation,
knowledge/RAG, voice gateway, etc.), add a matching `skills/<name>/SKILL.md`
here and list it in `../.claude-plugin/plugin.json`'s `skills` array.
