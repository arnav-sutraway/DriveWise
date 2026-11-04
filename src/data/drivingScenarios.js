export const scenarios = [
  {
    id: 'four_way_stop',
    title: 'Four-way stop',
    prompt: 'How does a four-way stop work?',
    response: 'In this scripted example, E-1 from the east stopped first. It proceeds when the intersection and crosswalk are clear.',
    reminder: 'At a four-way stop, drivers generally proceed in arrival order. If two vehicles arrive at the same time, yield to the vehicle on your right. Local rules apply.',
    firstVehicle: 'E-1',
    firstApproach: 'East',
    order: ['E-1', 'W-1', 'N-1', 'S-1'],
  },
];

export const suggestedQuestions = [
  'How does a four-way stop work?',
  'How do I parallel park?',
  'How do I safely change lanes?',
  'What should I do at a yellow traffic light?',
];

export const suggestedPrompt = suggestedQuestions[0];
