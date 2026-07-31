# OpenAI Integration

PharmaQ Sentinel uses a server-side OpenAI model gateway for future AI-assisted tools. The gateway is intentionally reusable and does not implement complaint extraction, complaint editing, document parsing, LangGraph behavior, Batch Intelligence, or Quality War Room workflows by itself.

## Environment Variables

Configure OpenAI only in backend environment variables:

```text
LLM_PROVIDER=openai
OPENAI_API_KEY=
OPENAI_MODEL=
OPENAI_CONTEXT_MODEL=
OPENAI_TIMEOUT_SECONDS=60
OPENAI_MAX_RETRIES=2
OPENAI_TEMPERATURE=0
OPENAI_MAX_OUTPUT_TOKENS=3000
OPENAI_ENABLE_LIVE_TESTS=false
OPENAI_LOG_PROMPTS=false
OPENAI_ENABLE_TEST_CONNECTION=false
```

`OPENAI_MODEL` and `OPENAI_API_KEY` are required only when AI functionality is invoked. FastAPI must still start without them, and `/api/v1/ai/status` reports the AI service as unavailable rather than failing startup.

Never put a real API key in `.env.example`, documentation, frontend code, browser-visible configuration, logs, tests, or source control.

## Server-Side Security

The OpenAI API key is read through backend settings as a protected secret. React must never call OpenAI directly and must never receive `OPENAI_API_KEY`, database URLs, or provider credentials.

The gateway logs operational metadata only:

- request ID
- tool name
- provider
- requested and actual model
- latency
- retry count
- typed success or failure

By default, prompts, full complaint descriptions, uploaded document text, API keys, and complete model outputs are not logged.

`OPENAI_LOG_PROMPTS=true` may be used only in development. Even then, metadata logging is redacted where practical and should not be used with real production complaint data.

## Model Configuration

The model is selected from `OPENAI_MODEL`. Future workflows may use `OPENAI_CONTEXT_MODEL` for lower-cost context preparation, but the gateway does not hardcode model names.

Every gateway result includes:

- provider
- requested model
- actual model when returned by OpenAI
- response ID
- prompt version
- token usage when available
- latency
- retry count
- timestamp
- warnings

## Responses API

The gateway uses the official OpenAI Python SDK and the Responses API.

For structured output, the preferred path is:

```python
client.responses.parse(
    model=configured_model,
    instructions=system_instructions,
    input=user_input,
    text_format=PydanticSchema,
)
```

For text output, the gateway uses:

```python
client.responses.create(
    model=configured_model,
    instructions=system_instructions,
    input=user_input,
)
```

The SDK is configured with application-controlled retries disabled so PharmaQ Sentinel owns retry logging and retry limits.

## Structured Outputs

Structured outputs must use Pydantic `BaseModel` schemas. Arbitrary dictionaries are rejected for typed structured generation.

The gateway:

- requests schema-conforming output through the SDK parse helper when available
- validates the final object with Pydantic
- rejects unknown enum values and malformed numeric ranges
- never uses `eval`
- never executes model-generated code
- never converts invalid model output into fake success
- raises typed structured-output errors when parsing fails

## Fallback Parsing

If SDK compatibility requires fallback parsing, the gateway:

1. Extracts returned JSON text.
2. Removes a surrounding markdown JSON fence when present.
3. Parses with `json.loads`.
4. Validates with the target Pydantic schema.
5. Retries once with a concise schema-repair instruction.
6. Rejects the response if it remains invalid.

Regular expressions are not used as the primary JSON parser.

## Retries

Retries are bounded and use exponential backoff with jitter.

Retried failures include:

- temporary connection failures
- timeouts
- rate limits
- provider 5xx responses

The gateway does not retry:

- invalid API keys
- permission failures
- application schema errors
- malformed request parameters
- model-not-found failures

## Status And Connectivity

`GET /api/v1/ai/status` returns a safe configuration/status snapshot. It never returns API keys, organization secrets, raw exception objects, or database values.

The status response includes `demo_ai_mode`, which is safe to expose because it is not a secret.

The health endpoint does not make paid OpenAI requests.

`POST /api/v1/ai/test-connection` is available only when:

- `APP_ENV=development`
- `OPENAI_ENABLE_TEST_CONNECTION=true`

It uses a tiny prompt and a very small token limit. It is meant for local smoke testing only and must not include complaint data.

## Testing

Backend tests mock all OpenAI calls. Live OpenAI tests are disabled by default through `OPENAI_ENABLE_LIVE_TESTS=false`.

Use live smoke tests only with a local uncommitted `.env` file and controlled non-complaint test prompts.

## Cost And Latency

OpenAI calls may add cost and latency. Future tools should:

- keep prompts concise
- avoid sending full source documents unless necessary
- prefer structured schemas that return only required fields
- use small token limits for connectivity checks
- record latency and token usage for monitoring

## Limitations

The gateway does not make AI output authoritative. Future extraction, risk, routing, CAPA, Batch Intelligence, and Quality War Room tools must present AI output as draft recommendations with evidence, confidence, limitations, and actual model metadata.

## Live Versus Deterministic Demo Mode

`DEMO_AI_MODE=live` is the default.

`DEMO_AI_MODE=deterministic` is allowed only for explicitly labelled local demos when live OpenAI access is unavailable. Deterministic outputs must come from stable rules or checked-in fixtures and must not be described as live OpenAI responses.
