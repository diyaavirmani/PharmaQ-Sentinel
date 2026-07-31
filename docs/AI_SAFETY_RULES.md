# AI Safety Rules

## AI Output Status

AI output must always be treated as a draft, suggestion, or recommendation until reviewed by authorized users.

The system must never describe AI-generated severity, root cause, CAPA, regulatory routing, or batch impact as a final authorized decision.

## Required Recommendation Metadata

Every AI recommendation must show:

- Evidence.
- Confidence.
- Limitations.
- Actual model used.
- Timestamp.

When evidence is weak or missing, the recommendation must say so.

## Missing Information

The AI must not invent missing complaint information.

If a value is not present in the source material or user correction, store it as null or `Not provided`. The assistant may ask for missing details, but it must not fabricate them.

## Correction Behavior

Natural-language corrections must be converted into explicit patches. The patch must identify changed fields and preserve unrelated fields.

The assistant must not:

- Perform full-object replacement for partial corrections.
- Delete unrelated fields.
- Hide uncertainty.
- Present inferred values as source facts.
- Apply corrections without auditability.

## Prompt and Model Governance

AI workflows must use LangGraph for orchestration and the backend OpenAI model gateway for model calls when AI functionality is implemented.

Model selection must be configuration-driven through backend environment variables. Model names must not be hardcoded throughout the codebase.

The actual model used must be recorded for every AI operation and every mutation involving AI.

## Regulatory Language Restrictions

The application must not claim to be:

- FDA-approved.
- Validated.
- Certified.
- 21 CFR Part 11 compliant.
- A replacement for authorized quality, safety, regulatory, or pharmacovigilance review.

The application may support quality workflows, but it must clearly separate AI assistance from human authorization.

## Pharmaceutical Domain Boundaries

The AI may assist with:

- Complaint extraction.
- Missing information detection.
- Draft risk assessment.
- Draft severity suggestions.
- Draft defect categorization.
- Draft investigation focus.
- Draft CAPA considerations.
- Draft regulatory routing indicators.
- Batch impact reasoning.
- War-room summarization and evidence organization.

The AI must not act as final authority for:

- Batch release or recall decisions.
- Regulatory reporting decisions.
- Medical diagnosis.
- Final root cause.
- Final CAPA.
- Final complaint closure.
- Final severity classification.

## Frontend Safety Requirements

- Complaint fields must be read-only.
- AI-generated content must be labeled as AI-generated.
- Recommendations must show evidence, confidence, and limitations.
- Mock records must be labeled as mock data.
- Users must be routed to the assistant for corrections.
- UI copy must not imply regulatory certification or final AI authority.

## Backend Safety Requirements

- Keep all OpenAI API keys server-side.
- Treat model output as untrusted input.
- Validate and normalize AI responses with Pydantic v2.
- Reject malformed patches.
- Apply changes only through audit-aware application services.
- Persist model metadata and actual model used.
- Log operational failures without leaking secrets.

## Demo Mode

`DEMO_AI_MODE` supports `live` and `deterministic`.

- `live` is the default for normal local development and production-like configuration.
- `deterministic` is allowed only for clearly labelled local demonstrations or tests.
- Production configuration must not default to deterministic mode.
- Deterministic outputs must come from stable rules or checked-in fixtures, not random fake answers.
- Deterministic output must not be described as a live OpenAI response.

## Inspection Brief Safety

The inspection brief is a review aid generated from a saved complaint version snapshot and linked immutable or append-only records. It must include the required disclaimer and must not be described as an official regulatory submission, regulator-approved document, validated record, Part 11 compliant record, or replacement for authorised QA review.

Inspection briefs must not expose internal storage paths, API keys, database credentials, hidden reasoning, prompt text, or model chain-of-thought.
