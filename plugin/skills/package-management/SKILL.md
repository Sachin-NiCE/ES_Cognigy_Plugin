---
name: package-management
description: "Use when exporting, importing, uploading, inspecting, or downloading Cognigy package zip files — including reusing an LLM plus its connection across projects."
---

# Package Management Guide

Tools: `list_exportable_resources`, `export_package`, `download_package`,
`upload_and_inspect_package`, `inspect_package`, `import_package`,
`read_package_task`.

## Important: file paths are on the SERVER, not the user's machine

This MCP server runs centrally (e.g. on a shared Linux host), not on the end
user's laptop. `download_package`'s `output_path` and
`upload_and_inspect_package`'s `file_path` are paths **on that server's
filesystem**. Don't assume a path the user gives you (e.g. `~/Downloads/foo.zip`)
exists there — check with the user whether the server has a shared/mounted
directory for this, and say plainly that a downloaded package lands on the server,
not their machine, unless they've confirmed such a mount exists.

## Supported workflow

### Transfer an LLM + connection between projects

Use when the target project is missing an LLM but another project already has a
working one (Cognigy connections are project-scoped — a `connectionId` from one
project is rejected in another, so this package flow is the way to move it).

1. `list_exportable_resources { project_id: "<sourceProjectId>" }`
2. From the returned resource graph, identify BOTH the `largeLanguageModel`
   resource id and its `connection` resource id.
3. `export_package { project_id: "<sourceProjectId>", resource_ids: ["<llmId>", "<connectionId>"], name: "llm-transfer" }`
4. `upload_and_inspect_package { project_id: "<targetProjectId>", file_path: "<savedTo from export_package>" }`
   — only works if the exported file is reachable at that path on the server.
5. `import_package { project_id: "<targetProjectId>", package_id: "<packageId from step 4>" }`

### Discover what can be exported

1. `list_exportable_resources { project_id }`
2. Review the returned graph and pick the resource ids to package.
3. `export_package { project_id, resource_ids, name }`

### Import a package

1. `upload_and_inspect_package { project_id, file_path }`
2. Review the returned preview (`packageResources` vs `projectResources`) — this
   diffs the package's and project's resource graphs so you can see what already
   exists (matched by `referenceId`) vs what would be newly created.
3. `import_package { project_id, package_id, resources, locale_mapping }`
4. If the response doesn't show `imported: true`, poll with
   `read_package_task { project_id, task_id }`.

### Export and hand off a package

1. `export_package { project_id, resource_ids, name, description }`
2. The response includes `packageId`; the archive itself is NOT downloaded yet.
3. `download_package { project_id, package_id, output_path }` to save the `.zip` —
   remember `output_path` is server-side (see above).

## Operations

### `list_exportable_resources`

Required: `project_id`
Returns the project's resource graph (`{projectId, graph}`), from which flows,
endpoints, knowledge stores, AI agents, connections, and LLM models can be
identified as export candidates.

### `export_package`

Required: `project_id`, `resource_ids`, `name`
Optional: `description`
Returns `{task, packageId}`. Dependencies aren't auto-included as a separate
parameter here — pick up dependent resource ids (e.g. a flow's LLM/connection)
from `list_exportable_resources` and include them explicitly in `resource_ids`.

### `download_package`

Required: `project_id`, `package_id`, `output_path`
`output_path` may be a directory (the package name + `.zip` is appended) or a
full file path. Returns `savedTo` (absolute path) and `fileUri`.

### `upload_and_inspect_package`

Required: `project_id`, `file_path`
Uploads the `.zip`, waits for extraction, then returns the same preview shape as
`inspect_package`.

### `inspect_package`

Required: `project_id`, `package_id`
Returns the import preview for an already-uploaded package without re-uploading.

### `import_package`

Required: `project_id`, `package_id`
Optional: `resources` (list of `{id, import: bool, strategy: "replace" | "re-identify"}`),
`locale_mapping` (list of `{packageLocaleId, agentLocaleId}`)

UI-parity defaults when `resources` is omitted or an item's `strategy` is
omitted: `knowledgeStore` resources default to `"replace"`; everything else
defaults to `"re-identify"`. `autoRename` is always applied internally. If
`resources` is omitted entirely, ALL resources from the package preview are
imported (locales excluded — those go through `locale_mapping` instead).

`locale_mapping`'s `packageLocaleId`/`agentLocaleId` must each be that
locale's own project-local mongo `_id` (confirmed against a live tenant —
the API returns a 400 "should be of format 'mongo-id'" for either field), not
the portable UUID `referenceId` the preview also shows for that locale. Get
the package side's `_id` from `inspect_package`'s `packageResources`, and the
target side's from `list_exportable_resources`' graph.

### `read_package_task`

Required: `project_id`, `task_id` — for a task that outlived its internal wait.

## Notes

- `export_package`/`upload_and_inspect_package`/`import_package` wait for their
  Cognigy platform task to finish internally (up to 600s by default) before
  returning; `read_package_task` is only needed if that wait is exceeded.
- There's no dedicated "list packages" or "delete package" tool here — these
  endpoints are unverified against a live tenant (see `server/tools/manage_packages.py`
  TODOs). If you need to enumerate or clean up packages, that currently has to
  happen in the Cognigy UI.
