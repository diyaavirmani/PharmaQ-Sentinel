# PharmaQ Sentinel Seven-Minute Demo Narration

All records shown in this demo are fictional demonstration data. AI outputs are draft recommendations for human quality review, not final authorized decisions.

## 0:00-0:30 - Landing And Workspace

PharmaQ Sentinel is an AI-assisted pharmaceutical complaint intelligence workspace for API and finished dosage form manufacturers. The first screen is intentionally simple: it frames the product, then opens the complaint workspace where the real work happens.

Inside the workspace, the left side is the controlled complaint record and the right side is the AI Complaint Intake Assistant. The form is read-only from the start. A user does not type directly into complaint fields. Complaint facts enter through assistant messages or uploaded source documents, and every change is handled as traceable draft data.

## 0:30-1:20 - Natural-Language Complaint Intake

I will start by logging a customer complaint in plain language. This is the same surface a quality user would use for pasted email text or a call-center note.

The assistant creates an extraction workflow, populates structured fields, and keeps the workspace visible while it works. Product, batch, customer, complaint type, date, quantity and suggested initial assessment appear in the read-only form. Missing details remain marked as not provided rather than guessed.

This first assessment is not a final severity decision. It is an AI-suggested draft with evidence, confidence and limitations so a reviewer can challenge it.

## 1:20-2:10 - Source Document Upload

Now I will upload a fictional complaint PDF. The upload happens in the same assistant panel, not in a separate document page. The source document is preserved unchanged, and derived text is treated separately.

The extraction progress area stays visible while the document is processed. When the PDF provides more detail, the same complaint draft is enriched rather than replaced. The application keeps the controlled form, the assistant conversation and the progress trace together in one workspace.

## 2:10-2:55 - Natural-Language Correction

Next I will add the complaint date using natural language.

Notice that only the complaint date field changes. The customer, product, batch, quantity, complaint description and other unrelated values stay intact. This is patch-and-merge behavior. PharmaQ Sentinel avoids silent full-object overwrites because those are dangerous in a quality record.

The change is also auditable: old value, new value, actor, reason, timestamp and tool context are retained.

## 2:55-3:25 - Evidence And Auditability

I will open evidence for the batch field. The evidence drawer overlays the workspace without adding another permanent column.

Here a reviewer can see how the current value was reached, including prior evidence and user correction context. The important point is that correction does not erase the history. It gives QA a way to reconstruct what changed, why it changed, and which source supported each value.

## 3:25-4:25 - Batch Blast-Radius Digital Twin

Now I will open Quality Intelligence and run Batch Intelligence. This uses the seeded fictional pharmaceutical network: related batches, packaging line PL-04, deviation DEV-2026-023, a linked CAPA, shared packaging materials, distribution and warehouse inventory.

The graph is not a recall decision. It is a decision-support view that helps QA see possible blast radius. I can also open a containment scope simulation. The modal clearly says simulation only; it does not change batch, shipment or inventory status.

This gives reviewers fast context while preserving the boundary between AI-assisted analysis and authorized quality action.

## 4:25-5:10 - AI Quality War Room

Next is the AI Quality War Room. The system organizes specialist perspectives: QA, manufacturing, packaging or supplier, pharmacovigilance and compliance audit.

Each specialist contributes draft findings, hypotheses and questions. The compliance auditor challenges unsupported final-cause language, which is exactly the safety behavior we want. The tool can accelerate review, but it must not claim a final root cause, CAPA or regulatory decision.

## 5:10-5:45 - Safety Signal Update

Now I will add a safety detail through the assistant: a possible adverse event was mentioned after customer exposure.

The system routes this cautiously as a possible pharmacovigilance review signal and asks for focused follow-up information. It does not diagnose the patient, and it does not decide reportability. It keeps the safety information attached to the same complaint draft.

## 5:45-6:20 - Investigation Support

In Investigation Support, the system surfaces duplicate or recurrence candidates and a draft investigation playbook. For this demo context, it can connect discoloration complaints, batch relationships and packaging-line signals.

Again, these are suggestions. The value is that QA gets a structured starting point with evidence and limitations instead of a black-box conclusion.

## 6:20-7:00 - Save, Ledger And Brief

Finally, I will save the reviewed demonstration complaint. Saving creates a committed QMS ledger record and an immutable version snapshot. The original draft history, source evidence and audit events remain connected.

The QMS Ledger shows the saved complaint record. Back in the workspace, Evidence and Audit can preview and export an inspection brief from the saved version snapshot.

That is the core PharmaQ Sentinel loop: controlled intake, read-only structured complaint data, assistant-mediated correction, evidence preservation, batch context, war-room review and a traceable ledger handoff.
