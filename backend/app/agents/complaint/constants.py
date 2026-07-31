from __future__ import annotations

from enum import StrEnum


class ComplaintAssistantIntent(StrEnum):
    LOG_COMPLAINT = "LOG_COMPLAINT"
    EDIT_COMPLAINT = "EDIT_COMPLAINT"
    EXTRACT_DOCUMENT = "EXTRACT_DOCUMENT"
    ASK_QUESTION = "ASK_QUESTION"
    REQUEST_SUMMARY = "REQUEST_SUMMARY"
    RUN_BATCH_IMPACT = "RUN_BATCH_IMPACT"
    RUN_QUALITY_WAR_ROOM = "RUN_QUALITY_WAR_ROOM"
    SAVE_COMPLAINT = "SAVE_COMPLAINT"
    UNKNOWN = "UNKNOWN"


UNIMPLEMENTED_TOOL_MESSAGE = (
    "This assistant tool is not implemented in this phase. No complaint fields were changed."
)

PROMPT_VERSION_INTENT_ROUTER = "complaint-intent-router-v1"
PROMPT_VERSION_LOG_COMPLAINT = "complaint-log-extraction-v1"
PROMPT_VERSION_EDIT_COMPLAINT = "complaint-edit-operation-v1"
PROMPT_VERSION_DOCUMENT_EXTRACTION = "complaint-document-extraction-v1"
PROMPT_VERSION_PROVISIONAL_RISK = "complaint-provisional-risk-v1"
