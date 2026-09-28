"""manage_settings: project-level Voice Preview and Knowledge AI settings.

Both are partial updates against a single endpoint:
    PATCH /new/v2.0/projects/{projectId}/settings

TODO (unverified against a live tenant): no GET counterpart for reading
current settings was confirmed in the reference implementation we studied -
this module is write-only until that's confirmed.
"""

from __future__ import annotations

from typing import Any, Optional

from cognigy_client import CognigyClient, CognigyCreds

SPEECH_PROVIDERS = {
    "microsoft": "MicrosoftSpeechProvider",
    "google": "GoogleSpeechProvider",
    "aws": "AWSSpeechProvider",
    "deepgram": "DeepgramSpeechProvider",
    "elevenlabs": "ElevenLabsSpeechProvider",
    # Cognigy's docs also mention Speechmatics; its connection `type` string
    # is unconfirmed, so it's deliberately not mapped here yet.
}


def set_voice_preview(
    creds: CognigyCreds,
    project_id: str,
    provider: str,
    connection_id: Optional[str] = None,
) -> dict[str, Any]:
    if provider not in SPEECH_PROVIDERS:
        raise ValueError(
            f"Unsupported speech provider '{provider}'. Supported: {', '.join(SPEECH_PROVIDERS)}."
        )

    with CognigyClient(*creds) as client:
        if not connection_id:
            connection_id = _find_speech_connection(client, project_id, provider)
            if not connection_id:
                return {
                    "configured": False,
                    "error": (
                        f"No existing Connection for speech provider '{provider}' was found "
                        f"in project {project_id}. Bring one in via manage_packages, or create "
                        "it in the Cognigy UI, then retry with connectionId set."
                    ),
                }

        body = {
            "audioPreviewSettings": {
                "provider": provider,
                "connections": {provider: {"connectionId": connection_id}},
            }
        }
        result = client.patch(f"/new/v2.0/projects/{project_id}/settings", json=body)

    return {"configured": True, "provider": provider, "connectionId": connection_id, "result": result}


def set_knowledge_ai(
    creds: CognigyCreds,
    project_id: str,
    knowledge_search_model_id: Optional[str] = None,
    answer_extraction_model_id: Optional[str] = None,
    content_parser: Optional[str] = None,
    azure_di_connection_id: Optional[str] = None,
) -> dict[str, Any]:
    if content_parser == "azure" and not azure_di_connection_id:
        raise ValueError("azure_di_connection_id is required when content_parser is 'azure'.")

    body: dict[str, Any] = {}

    use_cases: dict[str, Any] = {}
    if knowledge_search_model_id:
        use_cases["knowledgeSearch"] = {"largeLanguageModelId": knowledge_search_model_id}
    if answer_extraction_model_id:
        use_cases["answerExtraction"] = {"largeLanguageModelId": answer_extraction_model_id}
    if use_cases:
        body["generativeAISettings"] = {"enabled": True, "useCasesSettings": use_cases}

    if content_parser:
        knowledge_ai: dict[str, Any] = {"fileExtractor": content_parser}
        if content_parser == "azure":
            knowledge_ai["azureDIConnectionId"] = azure_di_connection_id
        body["knowledgeAISettings"] = knowledge_ai

    if not body:
        raise ValueError(
            "Provide at least one of knowledge_search_model_id, answer_extraction_model_id, "
            "or content_parser."
        )

    with CognigyClient(*creds) as client:
        result = client.patch(f"/new/v2.0/projects/{project_id}/settings", json=body)

    return {"configured": True, "result": result}


def _find_speech_connection(client: CognigyClient, project_id: str, provider: str) -> Optional[str]:
    connection_type = SPEECH_PROVIDERS[provider]
    connections = client.get("/new/v2.0/connections", params={"projectId": project_id}) or {}
    items = connections.get("_embedded", {}).get("connections", []) or connections.get("items", [])
    for conn in items:
        if (
            conn.get("extension") == "@cognigy/audio-preview-provider"
            and conn.get("type") == connection_type
        ):
            return conn.get("_id") or conn.get("referenceId")
    return None
