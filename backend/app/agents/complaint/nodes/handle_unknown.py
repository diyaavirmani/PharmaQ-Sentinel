from app.agents.complaint.state import ComplaintAssistantState


def handle_unknown_node(state: ComplaintAssistantState) -> ComplaintAssistantState:
    question = state["clarification_question"] or (
        "Please tell me whether you want to log a complaint, ask a question, or review the current draft."
    )
    return {
        **state,
        "assistant_response": question,
        "clarification_required": True,
        "clarification_question": question,
        "changed_fields": [],
    }
