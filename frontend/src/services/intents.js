// Labels for the question type the backend used to pick the coach's prompt (user story 8).
// Only these known types get a label; "general", unknown, or missing types show none.

const INTENT_LABELS = {
  factual: 'Quick answer',
  explanation: 'Explanation',
  procedure: 'Step-by-step',
  scenario: 'Your situation',
  creative: 'Practice',
};

export function intentLabel(intent) {
  return Object.hasOwn(INTENT_LABELS, intent) ? INTENT_LABELS[intent] : null;
}
