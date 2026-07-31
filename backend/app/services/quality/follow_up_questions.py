from __future__ import annotations

QUESTION_BANK: dict[str, str] = {
    "complaint description": "What exactly was observed, including the defect appearance, timing, and how many units were involved?",
    "product identification": "What is the product name or material name shown on the pack, label, or certificate?",
    "complaint source": "Who reported the complaint, such as a customer, distributor, pharmacist, or internal site contact?",
    "customer identification": "Can you provide the complainant or customer name for follow-up by QA?",
    "reporter contact": "What phone number or email should QA use for follow-up with the reporter?",
    "batch or lot": "Is a batch or lot number visible on the container, blister, label, or certificate?",
    "receipt date": "On what date was this complaint received by the quality team?",
    "strength or grade": "What strength, grade, or potency is printed on the product label or document?",
    "dosage form": "What dosage form is involved, such as capsule, tablet, injection, or API powder?",
    "quantity affected": "How many units, packs, containers, or kilograms are affected?",
    "defect-observed date": "When did the customer first observe the defect?",
    "sample availability": "Is a sample of the affected product available for return and laboratory inspection?",
    "photograph availability": "Are photographs of the defect, label, and batch details available?",
    "patient consumption status": "Did any patient consume or use the product before the issue was noticed?",
    "adverse-event information": "Was any patient reaction, injury, lack of effect, or medical treatment reported?",
    "storage conditions": "How was the product stored and transported before the complaint was reported?",
    "market or country": "In which market, country, city, or distribution region was the issue observed?",
    "return sample arrangement": "Can the reporter arrange return of the affected sample and original packaging for QA inspection?",
}


def questions_for_missing_fields(missing_fields: list[str], *, limit: int = 3) -> list[str]:
    questions = []
    for field in missing_fields:
        question = QUESTION_BANK.get(field)
        if question and question not in questions:
            questions.append(question)
        if len(questions) == limit:
            break
    return questions
