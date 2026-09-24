---
name: project-lifecycle
description: "Use when creating, listing, or deleting Cognigy projects. create_project auto-provisions a default Environment Setup flow that needs per-environment credentials filled in before use."
---

# Project Lifecycle Guide

Tools: `list_projects`, `create_project`, `delete_project`.

## Creating a project

```
create_project { name: "My New Project" }
```

This does more than an empty `POST /v2.0/projects` would:

1. Creates the project.
2. Provisions it with a default **Environment Setup** flow, imported from a
   trimmed, secret-scrubbed template (`server/templates/environment_setup/` —
   see `server/templates/build_environment_setup_template.py` for exactly
   what was kept/dropped from the original reference flow).
3. Renames that flow to match the project's `name`.

The response includes `projectId`, `flowId`, `flowName`, and `flowRenamed`.
If `flowRenamed` is `false`, the template flow wasn't found after import —
tell the user and don't claim the flow was set up.

### The template flow, and what's still missing

The provisioned flow is: `Start → Payload data from Studio (code) →
Code : Env Variables (code) → Set Session Config (2) → Lookup Environment
(switch on context.configuration.environment) → {Default / DEV / QA / PROD →
a per-environment code node} → End`.

**Every per-environment code node's `baseUrl`, `client_id`, and
`client_secret` are deliberately blank** (the source template had a
disabled node, an HTTP-request-and-beyond chain, and real per-tenant
credentials — all removed/scrubbed on purpose; see the template builder
script for the full rationale). **Always tell the user, right after
`create_project` succeeds, that they still need to fill in the DEV/UAT/PROD
`baseUrl`/`client_id`/`client_secret` values (and the endpoint URL tokens in
`Code : Env Variables`) in the Cognigy UI before this flow does anything
useful.** Never invent or guess values for these — they're customer/tenant
specific.

## Listing projects

```
list_projects { }
```
Optional: `limit` (default 25), `skip` (default 0).

## Deleting a project

**This is a soft delete, matching `snapshot-backups`' philosophy**:
`delete_project` renames the project with a `DELETE_` prefix and never
actually removes it. Flows, agents, and endpoints inside stay live and
reachable — say this explicitly, don't let the user think the project or its
contents are gone.

1. `delete_project { project_id }` **without** `confirm` first — returns a
   `preflight: true` warning and changes nothing.
2. Show the user the warning, get explicit agreement.
3. `delete_project { project_id, confirm: true }`.

Calling it again on an already-`DELETE_`-prefixed project is a no-op and
returns `alreadyMarked: true` — safe to retry.

## Notes

- There is no real project deletion here, by design — if the user needs the
  project actually gone, they (or an org admin) must delete it in the
  Cognigy UI.
- `create_project`'s locale handling: Cognigy's package-merge API expects
  each side's locale identified by its own project-local `_id` (a mongo-style
  hex id), not the portable UUID `referenceId` you'd expect from the package
  preview — confirmed against a live tenant. This is already handled inside
  `create_project`; it's called out here only so nobody "fixes" it back to
  `referenceId` later.
