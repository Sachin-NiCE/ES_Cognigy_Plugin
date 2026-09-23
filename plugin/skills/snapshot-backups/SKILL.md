---
name: snapshot-backups
description: "Use when backing up a Cognigy project, rolling a project back to a previous state, undoing agent/flow changes, or working with Cognigy Snapshots — list, create, restore, delete."
---

# Snapshot Backups and Rollback

Tools: `list_snapshots`, `create_snapshot`, `restore_snapshot`, `delete_snapshot`,
`read_snapshot_task`. A Snapshot is an immutable copy of an **entire project**.

## Read this before offering a backup

- A snapshot covers the **whole project** — every AI Agent, Flow, Connection, LLM,
  Lexicon, Extension, Function, Playbook and Locale in it. Restoring reverts **all**
  of them, not just the one resource you're changing.
- A snapshot does **NOT** contain:
  - Endpoints
  - Knowledge AI — stores, sources, chunks
  - Intent Trainer learning data
  - Analytics, contact profiles, logs
  - Other snapshots or packages
- So for a project that uses Knowledge AI, a snapshot is **not a complete backup**.
  Say this in one line when you offer it.
- Restoring is **irreversible**: current resources are deleted and recreated from
  the snapshot, and every resource id in the project changes.
- There is no server-side gate here (unlike some Cognigy tooling) that forces a
  backup before a mutating call — offering one is a judgment call you make before
  any risky change (a snapshot restore, a bulk delete, etc.), not something enforced
  for you.

## Naming

`create_snapshot`'s `name` is optional. If omitted, it's generated as
`<ProjectName>-<Mon DD>-<HHMM>` (UTC), sanitized to Cognigy's resource-name format
(letters/digits/`_`/`-` only — spaces and colons are stripped). Pass an explicit
`name` only if the user wants something different; there's no separate "label"
field and no automatic version counter or plugin-identifying marker on the
snapshot, so `delete_snapshot` will delete **any** snapshot by id, including ones a
human created by hand in the Cognigy UI — always confirm with the user which
snapshot they mean (and that it's disposable) before deleting.

## Supported workflow

### Back up before a risky change

1. `list_snapshots { project_id }` — check the current count/names first if the
   project might be near Cognigy's snapshot limit (default 10/project; there's no
   pre-flight limit check here, so a `create_snapshot` call can simply fail if the
   project is full — tell the user to delete one in the Cognigy UI if that happens).
2. `create_snapshot { project_id }` (or pass `name`/`description` to be specific
   about what's being backed up and why).
3. Wait for the response's `task.status` to be `"done"` and `created: true`. If the
   task is still running when the internal wait times out, the response includes
   the task, which you can poll with `read_snapshot_task { project_id, task_id }`.

### Roll back to a snapshot

1. `list_snapshots { project_id }` to find the `snapshotId`.
2. Call `restore_snapshot { project_id, snapshot_id }` **without** `confirm` first.
   This returns a `preflight: true` response with a `warning` and performs no
   action — it does not call the Cognigy API at all.
3. Show the user the warning. Get explicit agreement.
4. Only then call `restore_snapshot { project_id, snapshot_id, confirm: true }`.
5. Afterwards:
   - Every resource id in the project has changed — re-list agents/flows/etc.
     before reusing any id from earlier in the conversation.
   - Remind the user that Knowledge AI content was not restored.
   - If restoring an older snapshot (not the one you just took), consider whether
     the user wants to snapshot the *current* state first, since it's about to be
     destroyed with no way back.

### Delete a snapshot

`delete_snapshot { project_id, snapshot_id }` deletes immediately — there's no
preflight step and no restriction to snapshots this plugin created. Confirm with
the user which snapshot and that it's safe to remove before calling it.

## Operations

### `list_snapshots`

Required: `project_id`
Optional: `limit` (default 25), `skip` (default 0), `name_filter`

### `create_snapshot`

Required: `project_id`
Optional: `name` (see Naming above), `description`

### `restore_snapshot`

Required: `project_id`, `snapshot_id`
Optional: `confirm` (default `False` — must be `True` to actually restore)

### `delete_snapshot`

Required: `project_id`, `snapshot_id`

### `read_snapshot_task`

Required: `project_id`, `task_id` — use when a `create`/`restore`/`delete` response
came back without a terminal status (it waits up to 600s internally by default).

## Notes

- Create/restore/delete are asynchronous Cognigy platform tasks; each tool waits
  for completion internally before returning, so `read_snapshot_task` is only
  needed for the rare task that outlives that wait.
- Downloading, packaging, or uploading snapshots isn't supported here — use
  `package-management` or the Cognigy UI for moving resources between projects
  instead.
