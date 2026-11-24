"""Sort a learner's question into a type so the coach can answer it in the right shape (US 8).

Each type has its own prompt instructions and generation settings (see prompts.PROMPT_PROFILES).
The rules are checked in order and the first match wins, so a question such as
"What should I do if I miss my exit?" is a scenario even though it starts with "what".
Questions that match no rule are "general" and get the default instructions.
"""

import re

FACTUAL = "factual"
EXPLANATION = "explanation"
PROCEDURE = "procedure"
SCENARIO = "scenario"
CREATIVE = "creative"
GENERAL = "general"

QUESTION_TYPES = (FACTUAL, EXPLANATION, PROCEDURE, SCENARIO, CREATIVE, GENERAL)

_RULES = (
    # Practice material: quizzes, flash cards, memory aids.
    (CREATIVE, re.compile(
        r"\bquiz\b|\btest me\b|\bpractice (?:questions?|test|quiz)\b|\bflash ?cards?\b"
        r"|\bmnemonic\b|\bhelp me (?:remember|memori[sz]e)\b|\bmemory (?:aid|trick)\b"
        r"|\b(?:make up|come up with|write) (?:a|an|some) (?:rhyme|poem|song|story|example)\b"
    )),
    # The learner describes a situation and wants to know what to do in it.
    (SCENARIO, re.compile(
        r"\bwhat (?:should|do|would|must|can) i do\b|\bwhat if\b|\bwhat happens (?:if|when)\b"
        r"|\b(?:suppose|imagine|let's say)\b"
        r"|\b(?:if|when) (?:i|i'm|im|i am|my|someone|somebody|another|two|a|an|the) \w+"
    )),
    # Step-by-step how-to.
    (PROCEDURE, re.compile(
        r"\bhow (?:do|can|should|would) (?:i|you|we)\b(?! know\b)|\bhow to\b"
        r"|\bwhat are the steps\b|\bsteps (?:to|for)\b|\bwalk me through\b|\bteach me\b"
    )),
    # The reason behind a rule, or how something works.
    (EXPLANATION, re.compile(
        r"^why\b|\bwhy (?:do|does|is|are|should|must|can't|cannot|would|did)\b|\bexplain\b"
        r"|\bhow does\b|\bhow do .+ work\b|\bwhat(?:'s| is) the (?:reason|point|purpose)\b"
        r"|\bwhat does .+ mean\b|\bdifference between\b"
    )),
    # A direct lookup: a rule, number, or yes/no answer.
    (FACTUAL, re.compile(
        r"^(?:what|when|where|which|who|whose|is|are|am|can|could|do|does|must|may|should"
        r"|will|would|how (?:many|much|far|fast|long|old|soon|close|often|high|low|wide))\b"
    )),
)


def classify_question(question: str) -> str:
    """Return the question type for a learner's question (one of QUESTION_TYPES)."""
    text = re.sub(r"\s+", " ", question.lower().replace("’", "'")).strip()
    for question_type, pattern in _RULES:
        if pattern.search(text):
            return question_type
    return GENERAL
