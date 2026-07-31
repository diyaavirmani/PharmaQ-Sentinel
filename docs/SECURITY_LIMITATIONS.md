# Security And Limitations

## Security Review Checklist

- API keys are server-side only.
- `.env` is ignored and must not be committed.
- Frontend variables must not contain database URLs, MySQL passwords, OpenAI keys, or other secrets.
- Uploads are stored outside public frontend assets.
- API responses exclude internal upload storage paths.
- Uploaded HTML or email content is treated as text and escaped in previews.
- CORS must list explicit local origins; wildcard CORS is rejected.
- Backend exception responses must not expose SQL errors or credentials.
- AI output is validated with Pydantic before persistence.
- Audit events and complaint versions are append-only through normal repositories.
- Committed complaint records are not silently edited.

## Known Limitations

- Authentication, authorisation, user roles, electronic signatures, and production access control are not implemented.
- The project is not validated, certified, FDA-approved, or 21 CFR Part 11 compliant.
- Seed data is fictional and not real company data.
- Local performance measurements are not production-scale guarantees.
- Live OpenAI extraction depends on local, uncommitted API configuration.
- Deterministic demo mode is for labelled local demos only.
- Image OCR is not complete unless explicitly implemented in a later task.
- Containment simulation is simulation-only and does not create official inventory actions.
- Inspection briefs are review aids, not regulatory submissions.

## Regulatory Language

Allowed language:

- "AI-suggested"
- "draft recommendation"
- "requires authorised QA review"
- "simulation only"
- "fictional demonstration data"

Disallowed language:

- "FDA-approved"
- "validated"
- "Part 11 compliant"
- "confirmed root cause" without approved evidence
- "final regulatory routing decided by AI"
