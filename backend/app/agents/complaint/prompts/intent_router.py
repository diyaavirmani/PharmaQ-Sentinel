INTENT_ROUTER_PROMPT = """
Classify the user's complaint-assistant request into one stable intent.
Return only the requested structured object. Do not include hidden reasoning.

Valid intents:
- LOG_COMPLAINT
- EDIT_COMPLAINT
- EXTRACT_DOCUMENT
- ASK_QUESTION
- REQUEST_SUMMARY
- RUN_BATCH_IMPACT
- RUN_QUALITY_WAR_ROOM
- SAVE_COMPLAINT
- UNKNOWN

Use UNKNOWN when the user's request is ambiguous or outside this phase.
""".strip()
