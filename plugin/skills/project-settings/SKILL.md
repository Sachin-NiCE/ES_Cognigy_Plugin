---
name: project-settings
description: "Use when configuring project-level Cognigy settings — voice preview / speech provider configuration and Knowledge AI settings (Knowledge Search model, answer extraction model, content parser)."
---

# Project Settings Guide

Tools: `set_voice_preview`, `set_knowledge_ai`.

## Voice Preview Settings

Configures the speech provider used by voice-enabled endpoints (e.g. WebRTC) for
speech synthesis/recognition.

### Quick start

```
set_voice_preview { project_id: "<24-char hex>", provider: "microsoft" }
```

This auto-detects an existing speech Connection for the provider in that project.

### With an explicit connection

```
set_voice_preview { project_id: "<24-char hex>", provider: "microsoft", connection_id: "<connection referenceId>" }
```

### Supported providers

| `provider`   | Connection type          |
| ------------ | ------------------------ |
| `microsoft`  | MicrosoftSpeechProvider  |
| `google`     | GoogleSpeechProvider     |
| `aws`        | AWSSpeechProvider        |
| `deepgram`   | DeepgramSpeechProvider   |
| `elevenlabs` | ElevenLabsSpeechProvider |

(Cognigy's own docs also mention Speechmatics as a supported provider, but its
connection type string is unconfirmed, so it isn't accepted here yet.)

### No speech connection found?

`set_voice_preview` returns `{configured: false, error: "..."}` rather than
failing outright. When that happens:

1. Tell the user no matching Connection exists in this project.
2. If one exists in another project, use `package-management` to export it (plus
   its dependencies) and `import_package` it into this project.
3. Otherwise the user needs to create the connection in the Cognigy UI.
4. Retry `set_voice_preview` once a connection exists.

## Knowledge AI Settings

Configures the project-level Knowledge Search / Answer Extraction models and
document content parser used by Knowledge AI. This is **separate** from the
embedding model a knowledge store itself uses for indexing — don't confuse the
two, and don't reuse the agent's own response-generation LLM here without
checking it's actually meant for Knowledge Search.

### Quick start

```
set_knowledge_ai {
  project_id: "<24-char hex>",
  knowledge_search_model_id: "<llm_model referenceId>",
  content_parser: "default"
}
```

Providing `knowledge_search_model_id` or `answer_extraction_model_id`
automatically enables generative AI settings for the project.

### With the Azure content parser

```
set_knowledge_ai {
  project_id: "<24-char hex>",
  content_parser: "azure",
  azure_di_connection_id: "<connection referenceId>"
}
```
`azure_di_connection_id` is required when `content_parser` is `"azure"` — the
tool raises a validation error otherwise.

### Fields

| Field                        | Meaning                                                                       |
| ---------------------------- | ------------------------------------------------------------------------------ |
| `knowledge_search_model_id`  | `llm_model` referenceId, SAME project, used for Knowledge Search               |
| `answer_extraction_model_id` | Optional `llm_model` referenceId, SAME project, used for Answer Extraction     |
| `content_parser`             | One of `default`, `legacy`, `azure`                                           |
| `azure_di_connection_id`     | Azure AI Document Intelligence connection referenceId (required for `azure`)  |

At least one of `knowledge_search_model_id`, `answer_extraction_model_id`, or
`content_parser` must be provided — `set_knowledge_ai` raises a validation error
if called with none of them.

### Important notes

- Model ids must come from the SAME project as `project_id`. To find candidates
  matching the Cognigy Settings UI dropdown, list `llm_model` resources filtered
  by `useCase: "knowledgeSearch"` in that project (via whatever resource-listing
  capability is available) rather than guessing.
- If reusing another project's Knowledge Search setup, import the exact
  source-project model via `package-management` before calling this — don't
  substitute a different model in the target project and expect equivalent
  behavior.
- Set these before creating a knowledge store, so the store's search behavior is
  configured from the start.

### Typical knowledge workflow

1. Ensure the target project has an embedding-capable model for the knowledge
   store itself (separate from Knowledge Search).
2. `set_knowledge_ai { project_id, knowledge_search_model_id, content_parser }`
3. Create the knowledge store and attach it to an agent (outside this skill's
   scope — see whatever knowledge/RAG tooling is available).
